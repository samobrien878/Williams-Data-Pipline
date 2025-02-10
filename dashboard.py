import dash
from pymongo import MongoClient
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Connect to MongoDB
MONGO_URI = "mongodb+srv://@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "Daily summaries"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

df = pd.DataFrame([day for doc in collection.find() for day in doc.get("daily_summary", [])])

# Ensure Date column is in datetime format
df["Date"] = pd.to_datetime(df["Date"])

#creating dropdown options
rat_id_options = [{"label": "All RatIDs", "value": "all"}] + [{"label": f"Rat {rat}", "value": rat} for rat in sorted(df["RatID"].unique())]
stage_options = [{"label": f"Stage {stage}", "value": stage} for stage in sorted(df["Stage"].unique())]
# Metrics available for the Y-axis selection
metric_labels = {"FP_total": "Total False Positives",
                 "S_FP_total": "Total Sample False Positives",
                 "M_FP_total": "Total Match False Positives",
                 "TP_total": "Total True Positives",
                 "Latency to corr sample_avg": "Average Latency to Correct Sample",
                 "Latency to corr match_avg": "Average Latency to Correct Match",
                 "Num pokes corr sample_avg": "Average Pokes to Correct Sample",
                 "Time in corr sample_avg": "Average Time in Correct Sample",
                 "Num pokes inc sample_avg": "Average Pokes to Incorrect Sample",
                 "Num pokes corr match_avg": "Average Pokes to Correct Match",
                 "Time in corr match_avg": "Average Time in Correct Match"}

metric_options = [{"label": label, "value": metric} for metric, label in metric_labels.items()]
                 
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
                value="all", #default
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.H3("Select Stage"),
            dcc.Dropdown(
                id="stage-dropdown",
                options=stage_options,
                value=stage_options[0]["value"], #default
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.H3("Select Metric"),
            dcc.Dropdown(
                id="metric-dropdown",
                options= metric_options,
                value="FP_total", #default
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

    # Time Range Selection
    html.H3("Select Time Range"),
    dcc.RadioItems(
        id="time-range",
        options=[
            {"label": "Last 7 Entries per Rat", "value": 7},
            {"label": "Last 14 Entries per Rat", "value": 14},
            {"label": "Last 30 Entries per Rat", "value": 30}
        ],
        value=7,
        inline=True,
        style={"fontSize": "18px", "marginBottom": "20px"}
    ),

    # Line Graph and Widgets Layout
    html.Div([
        dcc.Graph(id="line-graph", style={"width": "80%", "height": "600px", "display": "inline-block"}),

        html.Div([
            html.Div(id="hover-widget", style={"textAlign": "center", "fontSize": "22px"})  # Hover widget
        ], style={"width": "18%", "display": "inline-block", "verticalAlign": "top"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

])


# Callback to update graph and widgets
@app.callback(
    Output("line-graph", "figure"),
    Output("hover-widget", "children"),  
    [Input("ratid-dropdown", "value"),
     Input("stage-dropdown", "value"),
     Input("metric-dropdown", "value"),
     Input("time-range", "value")]
)
def update_graph(selected_ratid, selected_stage, selected_metric, selected_rows):
    # Print the raw selected values for debugging
    print(f"Selected RatID: {selected_ratid} (type: {type(selected_ratid)})")
    print(f"Selected Stage: {selected_stage} (type: {type(selected_stage)})")
    print(f"Selected Metric: {selected_metric} (type: {type(selected_metric)})")
    print(f"Selected Time Range: {selected_rows} (type: {type(selected_rows)})")

    # Filter the DataFrame based on the selected RatID and Stage
    filtered_df = df

    # Filter by RatID
    if selected_ratid != "all":
        filtered_df = filtered_df[filtered_df["RatID"] == int(selected_ratid)]  # Ensure RatID is an int
        if filtered_df.empty:
            return {}, "No data available for the selected filters. Please try different filters."

    # Filter by Stage
    if selected_stage is not None:
        filtered_df = filtered_df[filtered_df["Stage"] == int(selected_stage)]  # Ensure Stage is an int

    # Ensure each RatID has exactly selected_rows points
    filtered_df = (
        filtered_df.sort_values(by="Date")
        .groupby("RatID")
        .tail(selected_rows)
    )

    if filtered_df.empty:
        return {}, "No data available for the selected filters. Please try different filters."

    # Assign Trial numbers (1-N) for each RatID
    filtered_df["Trial"] = filtered_df.groupby("RatID").cumcount() + 1

    # Create the figure using Plotly Express
    fig = px.line(
        filtered_df,
        x="Trial",
        y=selected_metric,
        color="RatID" if selected_ratid == "all" else None,
        title=f"{selected_metric} Over Last {selected_rows} Entries per Rat",
        labels={"Trial": "Trial Number", selected_metric: "Value"},
        markers=True,
        template="plotly_white",
        hover_data={"Date": "|%B %d, %Y"}  # Show date when hovering
    )

    fig.update_layout(
        title_font_size=24,
        xaxis_title="Trial Number",
        yaxis_title="Value",
        xaxis=dict(tickmode="linear", dtick=1, showgrid=True, gridwidth=1, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        font=dict(size=16),
        hovermode="closest"  # Show only the hovered point
    )

    # Hover Widget
    hover_widget = html.Div([
        html.H4("Hover Over Points", style={"fontSize": "22px"}),
        html.P("Hover to see details", style={"fontSize": "18px"})
    ]) if selected_ratid == "all" else ""

    return fig, hover_widget

if __name__ == "__main__":
    app.run_server(debug=True)