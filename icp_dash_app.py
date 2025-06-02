import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Load cleaned data
original_data = pd.read_csv("data/cleaned_icp_data.csv")
cleaned_data = original_data.copy()

# Assign treatment condition
def assign_condition(group):
    if group == "A":
        return "O2 + CO2"
    elif group == "B":
        return "CO2"
    elif group == "D":
        return "O2"
    elif group == "C":
        return "None"
    else:
        return "Unknown"

cleaned_data["Condition"] = cleaned_data["Group"].apply(assign_condition)
original_data["Condition"] = original_data["Group"].apply(assign_condition)

# Define colors for each condition
condition_colors = {
    "O2 + CO2": "#8B0000",  # Dark Red
    "CO2": "#00008B",       # Dark Blue
    "O2": "#FF6347",        # Light Red
    "None": "#4682B4",      # Light Blue
    "Unknown": "gray"
}

# Set up Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Label("Shale ID"),
            dcc.Dropdown(id="shale_id", options=[{"label": sid, "value": sid} for sid in sorted(original_data["Shale_ID"].dropna().unique(), key=str)], value=None),

            html.Label("Element"),
            dcc.Dropdown(id="element", options=[{"label": el, "value": el} for el in sorted(original_data["Element"].dropna().unique())], value=None),

            html.Label("Sample Type"),
            dcc.Checklist(id="sample_type", options=[{"label": t, "value": t} for t in original_data["Sample_Type"].dropna().unique()], value=["Disk", "Dust"], inline=True),

            html.Button("Reset Data", id="reset_btn", n_clicks=0),
        ], width=3),

        dbc.Col([
            dcc.Graph(id="plot")
        ], width=9)
    ]),

    html.Div([
        html.Div("Legend:", style={"fontWeight": "bold", "marginTop": "20px"}),
        html.Div([
            html.Span("O2 + CO2", style={"backgroundColor": "#8B0000", "color": "white", "padding": "5px", "marginRight": "10px"}),
            html.Span("CO2", style={"backgroundColor": "#00008B", "color": "white", "padding": "5px", "marginRight": "10px"}),
            html.Span("O2", style={"backgroundColor": "#FF6347", "padding": "5px", "marginRight": "10px"}),
            html.Span("None", style={"backgroundColor": "#4682B4", "padding": "5px"})
        ])
    ])
])

@app.callback(
    Output("plot", "figure"),
    Input("shale_id", "value"),
    Input("element", "value"),
    Input("sample_type", "value"),
    Input("reset_btn", "n_clicks")
)
def update_plot(shale_id, element, sample_type, n_clicks):
    global cleaned_data
    if ctx.triggered_id == "reset_btn":
        cleaned_data = original_data.copy()

    df = cleaned_data.copy()

    if shale_id:
        df = df[df["Shale_ID"] == shale_id]
    if element:
        df = df[df["Element"] == element]
    if sample_type:
        df = df[df["Sample_Type"].isin(sample_type)]

    fig = px.scatter(
        df,
        x="Time", y="Concentration",
        color="Condition",
        color_discrete_map=condition_colors,
        symbol="Sample_Type",
        hover_data=["Sample_ID"],
        labels={"Concentration": "[ppb]"},
        title=f"Shale {shale_id}: [{element}]" if shale_id and element else "ICP Concentrations"
    )

    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
