import dash
from dash import dcc, html, dash_table, Input, Output, State
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

# Use Bootstrap for beautiful styling
external_stylesheets = [dbc.themes.BOOTSTRAP]

# Connect to MongoDB
MONGO_URI = "mongodb+srv://obriensam878:1234@serverlessinstance0.gqqyx4s.mongodb.net/"
DB_NAME = "training_data"
COLLECTION_NAME = "Daily summaries"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

df = pd.DataFrame([day for doc in collection.find() for day in doc.get("daily_summary", [])])

# Ensure Date column is in datetime format
df["Date"] = pd.to_datetime(df["Date"])

# Remove Phase 0 from the dropdown options
df = df[df["Stage"] != 0]

# Get unique RatIDs
rat_ids = df["RatID"].unique()
rat_id_options = [{"label": f"Rat {rat}", "value": rat} for rat in rat_ids]

# Get unique Stages (excluding Phase 0)
stages = sorted(df["Stage"].unique())
stage_options = [{"label": f"Stage {stage}", "value": stage} for stage in stages]

# Define metric options
all_metrics = {
    "FP_total": "Total False Positives",
    "S_FP_total": "Total Sample False Positives",
    "M_FP_total": "Total Match False Positives",
    "TP_total": "Total True Positives",
    "Latency to corr sample_avg": "Average Latency to Correct Sample",
    "Latency to corr match_avg": "Average Latency to Correct Match",
    "Num pokes corr sample_avg": "Average Pokes to Correct Sample",
    "Time in corr sample_avg": "Average Time in Correct Sample",
    "Num pokes inc sample_avg": "Average Pokes to Incorrect Sample",
    "Num pokes corr match_avg": "Average Pokes to Correct Match",
    "Time in corr match_avg": "Average Time in Correct Match"
}

# Metrics available ONLY for Phase 1
phase_1_metrics = {
    "FP_total": "Total False Positives",
    "TP_total": "Total True Positives",
    "Latency to corr sample_avg": "Average Latency to Correct Sample",
    "Num pokes corr sample_avg": "Average Pokes to Correct Sample",
    "Num pokes inc sample_avg": "Average Pokes to Incorrect Sample",
    "Time in corr sample_avg": "Average Time in Correct Sample",
    "Time in inc sample_avg": "Average Time in Incorrect Sample"
}

# Initialize Dash App
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)

# Sticky Navigation Bar
navbar = html.Div(
    [
        html.Div(
            [
                html.A("Rat Behavior Analysis", href="/", style={"color": "white", "textDecoration": "none", "fontSize": "20px"}),
                html.A("Averages per Stage", href="/averages", style={"color": "white", "textDecoration": "none", "fontSize": "20px", "marginLeft": "20px"}),
            ],
            style={
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "backgroundColor": "#007BFF",
                "padding": "10px",
                "position": "sticky",
                "top": "0",
                "zIndex": "1000",
                "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
            },
        )
    ]
)

# Layout for the first page (Rat Behavior Analysis)
page_1_layout = html.Div([
    navbar,
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
                options=[{"label": "All Rat IDs", "value": "all"}] + rat_id_options,
                value=["all"],  # Default to "All Rat IDs"
                multi=True,
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.H3("Select Stage"),
            dcc.Dropdown(
                id="stage-dropdown",
                options=stage_options,
                value=stages[0],
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),

        html.Div([
            html.H3("Select Metric"),
            dcc.Dropdown(
                id="metric-dropdown",
                options=[{"label": label, "value": metric} for metric, label in all_metrics.items()],
                value="FP_total",
                clearable=False
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

    # Time Range Selection
    html.H3("Select Time Range"),
    dcc.RadioItems(
        id="time-range",
        options=[
            {"label": "Last 7 Days per Rat", "value": 7},
            {"label": "Last 14 Days per Rat", "value": 14},
            {"label": "Last 30 Days per Rat", "value": 30}
        ],
        value=7,
        inline=True,
        style={"fontSize": "18px", "marginBottom": "20px"},
        labelStyle={"margin-right": "20px"}
    ),

    # Line Graph
    dcc.Graph(id="line-graph"),
])

# Layout for the second page (Averages)
page_2_layout = html.Div([
    navbar,
    html.H1("Average Performance per Stage", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px"}),

    # Dropdown for Stage Selection
    html.Div([
        html.H3("Select Stage"),
        dcc.Dropdown(
            id="averages-stage-dropdown",
            options=stage_options,
            value=stages[0],  # Default to the first stage
            clearable=False,
            style={"width": "50%", "margin": "auto"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    # Dropdown for Metric Selection
    html.Div([
        html.H3("Select Metric"),
        dcc.Dropdown(
            id="averages-metric-dropdown",
            options=[{"label": label, "value": metric} for metric, label in all_metrics.items()],
            value="FP_total",
            clearable=False,
            style={"width": "50%", "margin": "auto"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    # Multi-select Dropdown for Rat IDs
    html.Div([
        html.H3("Select Rat IDs"),
        dcc.Dropdown(
            id="averages-ratid-dropdown",
            options=[{"label": "All Rat IDs", "value": "all"}] + rat_id_options,
            value=["all"],  # Default to "All Rat IDs"
            multi=True,  # Allow multiple selections
            clearable=False,
            style={"width": "50%", "margin": "auto"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    # Display area for the aggregated averages (widget)
    html.Div(id="averages-display", style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"}),
])

# App Layout with Multi-Page Support
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# Callback to switch between pages
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/averages":
        return page_2_layout
    else:
        return page_1_layout

# Callback to update metric dropdown based on Stage selection (Page 1)
@app.callback(
    Output("metric-dropdown", "options"),
    Output("metric-dropdown", "value"),
    Input("stage-dropdown", "value")
)
def update_metric_options(selected_stage):
    if selected_stage == 1:
        # Return phase 1-specific metrics
        metric_options = [{"label": label, "value": metric} for metric, label in phase_1_metrics.items()]
        default_value = "FP_total"  # Default selection
    else:
        # Return all metrics
        metric_options = [{"label": label, "value": metric} for metric, label in all_metrics.items()]
        default_value = "FP_total"  # Default selection
    return metric_options, default_value

# Callback to update the line graph (Page 1)
@app.callback(
    Output("line-graph", "figure"),
    Input("ratid-dropdown", "value"),
    Input("stage-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("time-range", "value")
)
def update_line_graph(selected_rats, selected_stage, selected_metric, time_range):
    # 'selected_rats' is a list from the multi-select dropdown.
    if "all" in selected_rats:
        filtered_df = df[df["Stage"] == selected_stage]
    else:
        filtered_df = df[(df["Stage"] == selected_stage) & (df["RatID"].isin(selected_rats))]
    
    # Sort by Date and get the last N entries per RatID
    filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    filtered_df = filtered_df.groupby("RatID").head(time_range)

    # Create the line graph with markers enabled
    fig = px.line(
        filtered_df,
        x="Date",
        y=selected_metric,
        color="RatID",
        markers=True,
        title=f"{selected_metric} Over Time (Last {time_range} Days per Rat)"
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_metric,
        legend_title="RatID"
    )
    return fig

# Callback to update the averages display (Page 2) with aggregated average calculation
@app.callback(
    Output("averages-display", "children"),
    Input("averages-stage-dropdown", "value"),
    Input("averages-metric-dropdown", "value"),
    Input("averages-ratid-dropdown", "value")
)
def update_averages_display(selected_stage, selected_metric, selected_rat_ids):
    # Filter data based on selected Stage and Rat IDs
    if "all" in selected_rat_ids:
        filtered_df = df[df["Stage"] == selected_stage]
    else:
        filtered_df = df[(df["Stage"] == selected_stage) & (df["RatID"].isin(selected_rat_ids))]

    # If a single rat (not "all") is selected, display that rat's average gauge
    if len(selected_rat_ids) == 1 and selected_rat_ids[0] != "all":
        if not filtered_df.empty:
            avg_value = filtered_df[selected_metric].mean()
            max_value = filtered_df[selected_metric].max()
        else:
            avg_value = 0
            max_value = 1
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_value,
            title={'text': f"Rat {selected_rat_ids[0]} Average {all_metrics[selected_metric]}"},
            gauge={'axis': {'range': [0, max_value * 1.1]}}
        ))
        return dcc.Graph(figure=gauge_fig, style={"width": "50%", "margin": "auto"})
    else:
        # For multiple rats (or "all") compute the aggregated average over all data rows
        if not filtered_df.empty:
            aggregated_avg = filtered_df[selected_metric].mean()
            max_value = filtered_df[selected_metric].max()
        else:
            aggregated_avg = 0
            max_value = 1
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=aggregated_avg,
            title={'text': f"Aggregated Average {all_metrics[selected_metric]}"},
            gauge={'axis': {'range': [0, max_value * 1.1]}}
        ))
        return dcc.Graph(figure=gauge_fig, style={"width": "50%", "margin": "auto"})

# Run the App
if __name__ == "__main__":
    app.run_server(debug=True)
