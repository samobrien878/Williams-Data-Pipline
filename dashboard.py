import dash
from dash import dcc, html, dash_table, Input, Output, State
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from config import MONGO_URI

#prism color palette for line graphs
prism = ["rgb(95, 70, 144)", "rgb(29, 105, 150)", "rgb(56, 166, 165)",
         "rgb(15, 133, 84)", "rgb(115, 175, 72)", "rgb(237, 173, 8)", 
         "rgb(225, 124, 5)", "rgb(204, 80, 62)", "rgb(148, 52, 110)",
         "rgb(11, 64, 112)", "rgb(102, 102, 102)"]

# Use the Cerulean theme for a colorful, professional look
external_stylesheets = [dbc.themes.CERULEAN]

# -----------------------------
# MongoDB Connection and Data
# -----------------------------
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
progress_rat_ids = progress_df["RatID"].unique()
progress_rat_id_options = [{"label": f"Rat {rat}", "value": rat} for rat in progress_rat_ids]
progress_stages = sorted(progress_df["Stage"].unique())
progress_stage_options = [{"label": f"Stage {stage}", "value": stage} for stage in progress_stages]

# -----------------------------
# Styling (Colorful & Professional Theme)
# -----------------------------
navbar_style = {
    "backgroundColor": "rgb(29, 105, 150)",  
    "padding": "10px",
    "position": "sticky",
    "top": "0",
    "zIndex": "1000",
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "borderBottom": "2px solid #0056b3",
    "fontFamily": "Garamond, serif"
}

graph_page_style = {
    "backgroundColor": "#D3D3FF",  #matches graph scheme
    "padding": "20px",
    "color": "#333",
    "minHeight": "100vh",
    "fontFamily": "Arial, sans-serif"

}
page_container_style = {
    "backgroundColor": "#FFFFFF",  # light background for readability
    "padding": "20px",
    "color": "#333",
    "minHeight": "100vh",
    "fontFamily": "Arial, sans-serif"
}

card_style = {
    "width": "300px",
    "margin": "10px",
    "backgroundColor": "white",
    "border": "1px solid #007bff",
    "borderRadius": "5px",
    "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.1)"
}

card_header_style = {
    "backgroundColor": "#007bff",
    "color": "white",
    "padding": "10px",
    "fontWeight": "bold",
    "borderTopLeftRadius": "5px",
    "borderTopRightRadius": "5px"
}

# -----------------------------
# Navigation Bar
# -----------------------------
navbar_component = html.Div(
    html.Div([
        html.A("Overview", href="/", style={"color": "white", "textDecoration": "none", "fontSize": "30px", "marginLeft" : "100px"}),
        html.A("Averages", href="/averages", style={"color": "white", "textDecoration": "none", "fontSize": "30px"}),
        html.A("Recap", href="/progress", style={"color": "white", "textDecoration": "none", "fontSize": "30px", "marginRight" : "100px"})
    ], style=navbar_style)
)

# -----------------------------
# Page Layouts
# -----------------------------

# Page 1: Rat Behavior Analysis
page_1_layout = html.Div([
    navbar_component,
    html.H1("Rat Behavior Analysis Dashboard", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px"}),
    html.Div([
        html.H3("Data Overview", style={"textAlign": "left", "marginBottom": "10px"}),
        dash_table.DataTable(
            id="data-table",
            columns=[{"name": col, "id": col} for col in df.columns],
            data=df.to_dict("records"),
            page_size=10,
            style_table={"overflowX": "auto"},
            style_header={"fontWeight": "bold", "backgroundColor": "rgb(29, 105, 150)", "color": "white"},
            style_cell={"textAlign": "center", "padding": "10px", "backgroundColor": "white", "color": "#333", "border": "1px solid rgb(29, 105, 150)"},
            style_data_conditional = [
                {
                    "if": {"state": "selected"},
                    "backgroundColor": "rgba(29, 105, 150, 0.5)",
                    "border" : "1px solid rgb(29, 105, 150)"
                },
                {
                    "if": {"state": "active"},
                    "backgroundColor":"rgba(29, 105, 150, 0.5)",
                    "border" : "1px solid rgb(29, 105, 150)"
                }
            ]
        )
    ]),
    html.Div([
        html.Div([
            html.H3("Select RatID", style={"color": "#333"}),
            dcc.Dropdown(
                id="ratid-dropdown",
                options=[{"label": "All Rat IDs", "value": "all"}] + rat_id_options,
                value=["all"],
                multi=True,
                clearable=False,
                style={"backgroundColor": "white", "color": "#333"}
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),
        html.Div([
            html.H3("Select Stage", style={"color": "#333"}),
            dcc.Dropdown(
                id="stage-dropdown",
                options=stage_options,
                value=stages[0],
                clearable=False,
                style={"backgroundColor": "white", "color": "#333"}
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"}),
        html.Div([
            html.H3("Select Metric", style={"color": "#333"}),
            dcc.Dropdown(
                id="metric-dropdown",
                options=[{"label": label, "value": metric} for metric, label in all_metrics.items()],
                value="FP_total",
                clearable=False,
                style={"backgroundColor": "white", "color": "#333"}
            ),
        ], style={"width": "32%", "display": "inline-block", "padding": "10px"})
    ], style={"display": "flex", "justifyContent": "space-between"}),
    html.Div([
        html.H3("Select Time Range", style={"color": "#333"}),
        dcc.RadioItems(
            id="time-range",
            options=[
                {"label": "Last 7 Days per Rat", "value": 7},
                {"label": "Last 14 Days per Rat", "value": 14},
                {"label": "Last 30 Days per Rat", "value": 30}
            ],
            value=7,
            inline=True,
            style={"fontSize": "18px", "marginBottom": "20px", "color": "#333"},
            labelStyle={"margin-right": "20px", "color": "#333"}
        )
    ]),
    dcc.Graph(id="line-graph")
], style=graph_page_style)

# Page 2: Averages per Stage
page_2_layout = html.Div([
    navbar_component,
    html.H1("Calculate Average Performances", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px", "color": "#333"}),
    html.Div([
        html.H3("Select Stage", style={"color": "#333"}),
        dcc.Dropdown(
            id="averages-stage-dropdown",
            options=stage_options,
            value=stages[0],
            clearable=False,
            style={"width": "50%", "margin": "auto", "backgroundColor": "white", "color": "#333"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),
    html.Div([
        html.H3("Select Metric", style={"color": "#333"}),
        dcc.Dropdown(
            id="averages-metric-dropdown",
            options=[{"label": label, "value": metric} for metric, label in all_metrics.items()],
            value="FP_total",
            clearable=False,
            style={"width": "50%", "margin": "auto", "backgroundColor": "white", "color": "#333"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),
    html.Div([
        html.H3("Select Rat IDs", style={"color": "#333"}),
        dcc.Dropdown(
            id="averages-ratid-dropdown",
            options=[{"label": "All Rat IDs", "value": "all"}] + rat_id_options,
            value=["all"],
            multi=True,
            clearable=False,
            style={"width": "50%", "margin": "auto", "backgroundColor": "white", "color": "#333"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),
    html.Div(id="averages-display", style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"})
], style=page_container_style)

# Page 3: Recap (Progress Profiles)
page_3_layout = html.Div([
    navbar_component,
    html.H1("Rat Progress Profiles", style={"textAlign": "center", "fontSize": "36px", "marginBottom": "20px", "color": "#333"}),
    html.Div([
        html.H3("Select Stage", style={"color": "#333"}),
        dcc.Dropdown(
            id="progress-stage-dropdown",
            options=progress_stage_options,
            value=progress_stage_options[0]["value"],
            clearable=False,
            style={"width": "50%", "margin": "auto", "backgroundColor": "white", "color": "#333"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),
    html.Div([
        html.H3("Select Rat IDs", style={"color": "#333"}),
        dcc.Dropdown(
            id="progress-ratid-dropdown",
            options=[{"label": "All Rat IDs", "value": "all"}] + progress_rat_id_options,
            value=["all"],
            multi=True,
            clearable=False,
            style={"width": "50%", "margin": "auto", "backgroundColor": "white", "color": "#333"}
        ),
    ], style={"textAlign": "center", "marginBottom": "20px"}),
    html.Div(id="progress-display", style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"})
], style=page_container_style)

# -----------------------------
# App Layout and Page Routing
# -----------------------------
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
], style={"backgroundColor": "#f7f7f7"})

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

# -----------------------------
# Callbacks for Page 1
# -----------------------------
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
        title=f"{selected_metric} Over Time (Last {time_range} Days per Rat)",
        color_discrete_sequence=prism
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_metric,
        legend_title="RatID",
        paper_bgcolor = "#FFFFFF",
        plot_bgcolor = "#FFFFFF",
        font=dict(color="#333"),
        title=dict(font=dict(color="#333")),
        xaxis=dict(showgrid=False, zeroline=False, color="#333"),
        yaxis=dict(showgrid=False, zeroline=False, color="#333"),
        colorway= prism
    )
    return fig

# -----------------------------
# Callback for Page 2
# -----------------------------
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
        gauge_fig.update_layout(
            paper_bgcolor = "#FFFFFF",
            plot_bgcolor = "#FFFFFF",
            font=dict(color="#333"),
            title=dict(font=dict(color="#333")),
            xaxis=dict(showgrid=False, zeroline=False, color="#333"),
            yaxis=dict(showgrid=False, zeroline=False, color="#333"),
            colorway= prism
        )
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
        gauge_fig.update_layout(
            paper_bgcolor = "#FFFFFF",
            plot_bgcolor = "#FFFFFF",
            font=dict(color="#333"),
            title=dict(font=dict(color="#333")),
            xaxis=dict(showgrid=False, zeroline=False, color="#333"),
            yaxis=dict(showgrid=False, zeroline=False, color="#333"),
            colorway= prism
        )
        return dcc.Graph(figure=gauge_fig, style={"width": "50%", "margin": "auto"})

# -----------------------------
# Callback for Page 3 (Recap)
# -----------------------------
@app.callback(
    Output("progress-display", "children"),
    Input("progress-stage-dropdown", "value"),
    Input("progress-ratid-dropdown", "value")
)
def update_progress_display(selected_stage, selected_rat_ids):
    filtered = progress_df[progress_df["Stage"] == selected_stage]
    if "all" not in selected_rat_ids:
        filtered = filtered[filtered["RatID"].isin(selected_rat_ids)]
    
    profile_cards = []
    for rat, group in filtered.groupby("RatID"):
        group = group.sort_values("Date")
        days_in_stage = group["Date"].nunique()
        most_recent = group.iloc[-1]
        trials_completed = most_recent.get("trials_completed", 0)
        successful_trials = trials_completed  # For stages 1,2,3, use the most recent day's trials_completed
        
        profile_text = html.Div([
            html.P(f"Has spent {days_in_stage} days in Stage {selected_stage}.", style={"fontSize": "16px", "margin": "5px 0", "color": "#333"}),
            html.P(f"Last session completed {successful_trials} successful trials.", style={"fontSize": "16px", "margin": "5px 0", "color": "#333"})
        ])
        
        # Create a square icon with a green color
        icon = html.Div(style={
            "width": "48px",
            "height": "48px",
            "backgroundColor": "green",
            "display": "inline-block",
            "marginRight": "10px",
            "borderRadius": "5px"
        })
        
        card = dbc.Card(
            [
                dbc.CardHeader(html.H4([icon, f"Rat {rat}"], style=card_header_style)),
                dbc.CardBody(profile_text)
            ],
            style=card_style
        )
        profile_cards.append(card)
    
    if not profile_cards:
        return html.Div("No data found for the selected criteria.", style={"textAlign": "center", "marginTop": "20px", "fontSize": "18px", "color": "#333"})
    
    return html.Div(profile_cards, style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center"})

# -----------------------------
# Run the App
# -----------------------------
if __name__ == "__main__":
    app.run_server(debug=True)
