import dash
from pymongo import MongoClient
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Connect to MongoDB
MONGO_URI = "mongodb+srv://:@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "Daily summarys"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
documents = collection.find()

df = pd.DataFrame([entry for doc in collection.find() for entry in doc.get("daily_summary", [])])

# Ensure Date column is in datetime format
df["Date"] = pd.to_datetime(df["Date"])

# Get unique RatIDs
rat_ids = df["RatID"].unique()
rat_id_options = [{"label": "All RatIDs", "value": "all"}] + [{"label": f"Rat {rat}", "value": rat} for rat in rat_ids]

# Get unique Stages (No "All Stages" Option)
stages = sorted(df["Stage"].unique())
stage_options = [{"label": f"Stage {stage}", "value": stage} for stage in stages]  # No "All Stages"

# Metrics available for the Y-axis selection
metrics = [
    "FP_total", "S_FP_total", "M_FP_total",  # False Positives
    "TP_total",  # True Positives
    "Latency to corr sample_avg", "Latency to corr match_avg"  # Latency Metrics
]

# False Positive Metrics (for conditional display of Timeout widget)
false_positive_metrics = ["FP_total", "S_FP_total", "M_FP_total"]

# Initialize Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Rat Behavior Analysis Dashboard", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px"}),

    # Data Table
    html.H3("Data Overview", style={"textAlign": "left", "marginBottom": "10px"}),
    dash_table.DataTable(
        id="data-table",
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_header={"fontWeight": "bold", "backgroundColor": "#e6e6e6"},
        style_cell={"textAlign": "center", "padding": "10px"}
    ),

    # Dropdown Filters
    html.Div([
        html.Div([
            html.H3("Select RatID"),
            dcc.Dropdown(
                id="ratid-dropdown",
                options=rat_id_options,
                value="all",  # Default selection is "All RatIDs"
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.H3("Select Stage"),
            dcc.Dropdown(
                id="stage-dropdown",
                options=stage_options,
                value=stages[0],  # Default to first available stage
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.H3("Select Metric"),
            dcc.Dropdown(
                id="metric-dropdown",
                options=[{"label": metric, "value": metric} for metric in metrics],
                value="FP_total",  # Default selection
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

    # Time Range Selection
    html.H3("Select Time Range"),
    dcc.RadioItems(
        id="time-range",
        options=[
            {"label": "Last 7 Entries", "value": 7},
            {"label": "Last 14 Entries", "value": 14},
            {"label": "Last 30 Entries", "value": 30}
        ],
        value=14,  # Default to last 14 rows
        inline=True,
        style={"fontSize": "18px", "marginBottom": "20px"}
    ),

    # Line Graph and Widgets Layout
    html.Div([
        dcc.Graph(id="line-graph", style={"width": "80%", "height": "600px", "display": "inline-block"}),
        
        html.Div([
            html.Div(id="timeout-widget", style={"textAlign": "center", "fontSize": "22px", "marginBottom": "20px"}),
            html.Div(id="hover-widget", style={"textAlign": "center", "fontSize": "22px"})  # Hover widget
        ], style={"width": "18%", "display": "inline-block", "verticalAlign": "top"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

])


# Callback to update line graph based on metric selection, RatID filter, Stage filter, and time range
@app.callback(
    Output("line-graph", "figure"),
    Output("timeout-widget", "children"),  # Output for the Timeout Widget
    Output("hover-widget", "children"),  # Output for the Hover Widget
    [Input("metric-dropdown", "value"),
     Input("ratid-dropdown", "value"),
     Input("stage-dropdown", "value"),
     Input("time-range", "value")]
)
def update_graph(selected_metric, selected_ratid, selected_stage, selected_rows):
    # Filter by Stage
    filtered_df = df[df["Stage"] == selected_stage]

    # Filter by RatID
    if selected_ratid != "all":
        filtered_df = filtered_df[filtered_df["RatID"] == selected_ratid]

    # Sort and get last N rows
    filtered_df = filtered_df.sort_values(by="Date").tail(selected_rows)

    # Create line graph
    fig = px.line(filtered_df, x="Date", y=selected_metric, color="RatID" if selected_ratid == "all" else None,
                  title=f"{selected_metric} Over Last {selected_rows} Entries | "
                        f"RatID: {'All' if selected_ratid == 'all' else selected_ratid} | Stage: {selected_stage}",
                  labels={"Date": "Date", selected_metric: "Value"},
                  markers=True,
                  template="plotly_white")

    fig.update_layout(
        title_font_size=24,
        xaxis_title="Date",
        yaxis_title="Value",
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        font=dict(size=16),
        hovermode="x unified"
    )

    # Compute Average Timeout Widget
    if selected_metric in false_positive_metrics:
        avg_timeout_per_row = round(filtered_df["Timeout_total"].mean(), 2)  # Avg Timeouts per row
        timeout_text = f"Avg Timeouts per Entry: {avg_timeout_per_row}"
        timeout_widget = html.Div([
            html.H4("Timeout Info", style={"fontSize": "22px"}),
            html.P(timeout_text, style={"fontWeight": "bold", "color": "#d9534f", "fontSize": "20px"})  # Red color for emphasis
        ])
    else:
        timeout_widget = ""

    # Hover Widget for Identifying RatID
    if selected_ratid == "all":
        hover_widget = html.Div([
            html.H4("Hover Over Points", style={"fontSize": "22px"}),
            html.P("Hover over the graph to see RatID", style={"fontSize": "18px"})
        ])
    else:
        hover_widget = ""  # Hide if a specific RatID is selected

    return fig, timeout_widget, hover_widget


# Run the App
if __name__ == "__main__":
    app.run_server(debug=True)
