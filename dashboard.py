import dash
from dash import dcc, html, dash_table, Input, Output, State
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from config import MONGO_URI

# Use Bootstrap for beautiful styling
external_stylesheets = [dbc.themes.BOOTSTRAP]

# Connect to MongoDB and query the Daily summaries collection
DB_NAME = "training_data"
SUMMARY_COLLECTION = "Daily summaries"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[SUMMARY_COLLECTION]

# Query the summary collection once
summary_df = pd.DataFrame([day for doc in collection.find() for day in doc.get("daily_summary", [])])
summary_df["Date"] = pd.to_datetime(summary_df["Date"])

# For pages 1 & 2, remove Stage 0 from the summary data
df = summary_df[summary_df["Stage"] != 0].copy()

# Get unique RatIDs and Stages for pages 1 & 2
rat_ids = df["RatID"].unique()
rat_id_options = [{"label": f"Rat {rat}", "value": rat} for rat in rat_ids]
stages = sorted(df["Stage"].unique())
stage_options = [{"label": f"Stage {stage}", "value": stage} for stage in stages]

# Define metric options for pages 1 & 2
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

# Metrics available ONLY for Phase 1 (Page 1)
phase_1_metrics = {
    "FP_total": "Total False Positives",
    "TP_total": "Total True Positives",
    "Latency to corr sample_avg": "Average Latency to Correct Sample",
    "Num pokes corr sample_avg": "Average Pokes to Correct Sample",
    "Num pokes inc sample_avg": "Average Pokes to Incorrect Sample",
    "Time in corr sample_avg": "Average Time in Correct Sample",
    "Time in inc sample_avg": "Average Time in Incorrect Sample"
}

# For the Recap page, use the full summary_df (which includes stage 0)
progress_df = summary_df.copy()

# Get unique RatIDs and Stages for the Recap page
progress_rat_ids = progress_df["RatID"].unique()
progress_rat_id_options = [{"label": f"Rat {rat}", "value": rat} for rat in progress_rat_ids]
progress_stages = sorted(progress_df["Stage"].unique())
progress_stage_options = [{"label": f"Stage {stage}", "value": stage} for stage in progress_stages]

# --- Navigation Bar (includes link to the Recap page) ---
navbar = html.Div(
    [
        html.Div(
            [
                html.A("Overview", href="/", style={"color": "white", "textDecoration": "none", "fontSize": "20px"}),
                html.A("Averages", href="/averages", style={"color": "white", "textDecoration": "none", "fontSize": "20px", "marginLeft": "20px"}),
                html.A("Recap", href="/progress", style={"color": "white", "textDecoration": "none", "fontSize": "20px", "marginLeft": "20px"}),
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

# --- Page 1 Layout: Rat Behavior Analysis ---
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
                value=["all"],
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

# --- Page 2 Layout: Averages per Stage ---
page_2_layout = html.Div([
    navbar,
    html.H1("Calculate Average Performances", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px"}),

    # Dropdown for Stage Selection
    html.Div([
        html.H3("Select Stage"),
        dcc.Dropdown(
            id="averages-stage-dropdown",
            options=stage_options,
            value=stages[0],
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
            value=["all"],
            multi=True,
            clearable=False,
            style={"width": "50%", "margin": "auto"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    # Display area for the aggregated averages (widget)
    html.Div(id="averages-display", style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"}),
])

# --- Page 3 Layout: Recap (Progress Profiles) ---
page_3_layout = html.Div([
    navbar,
    html.H1("Rat Progress Profiles", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px"}),

    # Dropdown for Stage Selection (from summary data, includes stage 0)
    html.Div([
        html.H3("Select Stage"),
        dcc.Dropdown(
            id="progress-stage-dropdown",
            options=progress_stage_options,
            value=progress_stage_options[0]["value"],
            clearable=False,
            style={"width": "50%", "margin": "auto"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    # Dropdown for RatID Selection
    html.Div([
        html.H3("Select Rat IDs"),
        dcc.Dropdown(
            id="progress-ratid-dropdown",
            options=[{"label": "All Rat IDs", "value": "all"}] + progress_rat_id_options,
            value=["all"],
            multi=True,
            clearable=False,
            style={"width": "50%", "margin": "auto"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),

    # Display area for the progress profiles
    html.Div(id="progress-display", style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"})
])

# --- App Layout with Multi-Page Support ---
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# --- Callback to Switch Between Pages ---
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/averages":
        return page_2_layout
    elif pathname == "/progress":
        return page_3_layout
    else:
        return page_1_layout

# --- Callback to Update Metric Dropdown Based on Stage Selection (Page 1) ---
@app.callback(
    Output("metric-dropdown", "options"),
    Output("metric-dropdown", "value"),
    Input("stage-dropdown", "value")
)
def update_metric_options(selected_stage):
    if selected_stage == 1:
        metric_options = [{"label": label, "value": metric} for metric, label in phase_1_metrics.items()]
        default_value = "FP_total"
    else:
        metric_options = [{"label": label, "value": metric} for metric, label in all_metrics.items()]
        default_value = "FP_total"
    return metric_options, default_value

# --- Callback to Update the Line Graph (Page 1) ---
@app.callback(
    Output("line-graph", "figure"),
    Input("ratid-dropdown", "value"),
    Input("stage-dropdown", "value"),
    Input("metric-dropdown", "value"),
    Input("time-range", "value")
)
def update_line_graph(selected_rats, selected_stage, selected_metric, time_range):
    if "all" in selected_rats:
        filtered_df = df[df["Stage"] == selected_stage]
    else:
        filtered_df = df[(df["Stage"] == selected_stage) & (df["RatID"].isin(selected_rats))]
    
    filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    filtered_df = filtered_df.groupby("RatID").head(time_range)

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

# --- Callback to Update the Averages Display (Page 2) ---
@app.callback(
    Output("averages-display", "children"),
    Input("averages-stage-dropdown", "value"),
    Input("averages-metric-dropdown", "value"),
    Input("averages-ratid-dropdown", "value")
)
def update_averages_display(selected_stage, selected_metric, selected_rat_ids):
    if "all" in selected_rat_ids:
        filtered_df = df[df["Stage"] == selected_stage]
    else:
        filtered_df = df[(df["Stage"] == selected_stage) & (df["RatID"].isin(selected_rat_ids))]

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

# --- Callback to Update the Recap (Progress Profiles) (Page 3) ---
@app.callback(
    Output("progress-display", "children"),
    Input("progress-stage-dropdown", "value"),
    Input("progress-ratid-dropdown", "value")
)
def update_progress_display(selected_stage, selected_rat_ids):
    # Filter progress_df (summary data) based on the selected stage
    filtered = progress_df[progress_df["Stage"] == selected_stage]
    if "all" not in selected_rat_ids:
        filtered = filtered[filtered["RatID"].isin(selected_rat_ids)]
    
    profile_cards = []
    # Group the summary data by RatID
    for rat, group in filtered.groupby("RatID"):
        # Sort by Date so that the most recent day's record is last
        group = group.sort_values("Date")
        days_in_stage = group["Date"].nunique()  # Count distinct days
        
        if selected_stage == 0:
            # For Stage 0, use the most recent day's summary
            most_recent = group.iloc[-1]
            trials_completed = most_recent.get("trials_completed", 0) if "trials_completed" in most_recent else 0
            # Count trials on the most recent day where Max_HH is at least 4
            trials_at_4 = trials_completed if most_recent.get("Max_HH", 0) >= 4 else 0
            
            profile_text = [
                html.P(f"Days in Stage 0: {days_in_stage}"),
                html.P(f"Most Recent Day Trials Completed: {trials_completed}"),
                html.P(f"Trials with HeadHold ≥ 4: {trials_at_4}")
            ]
        else:
            # For stages 1, 2, 3: count days and sum successful trials 
            # (we define successful trials as days where FP_total is 0 and count TP_total)
            successful_trials = group[group["FP_total"] == 0]["TP_total"].sum()
            profile_text = [
                html.P(f"Days in Stage {selected_stage}: {days_in_stage}"),
                html.P(f"Successful Trials (TP_total when FP_total=0): {successful_trials}")
            ]
        
        card = dbc.Card(
            [
                dbc.CardHeader(html.H4(f"Rat {rat}")),
                dbc.CardBody(profile_text)
            ],
            style={"width": "300px", "margin": "10px", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"}
        )
        profile_cards.append(card)
    
    if not profile_cards:
        return html.Div("No data found for the selected criteria.", style={"textAlign": "center", "marginTop": "20px"})
    
    return html.Div(profile_cards, style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"})

# --- Run the App ---
if __name__ == "__main__":
    app.run_server(debug=True)
