import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Load and convert data to mM
molar_masses = {
    "Li": 6.94, "Na": 22.99, "Mg": 24.31, "Al": 26.98, "Si": 28.09, "K": 39.10, "Ca": 40.08,
    "Ti": 47.87, "Cr": 51.99, "Mn": 54.94, "Fe": 55.85, "Co": 58.93, "Ni": 58.69, "Cu": 63.55,
    "Zn": 65.38, "As": 74.92, "Sr": 87.62, "Mo": 95.95, "Cd": 112.41, "Ba": 137.33, "Pb": 207.2
}

def ppb_to_mM(row):
    elem = row["Element"]
    conc = row["Concentration"]
    if elem in molar_masses:
        return conc / molar_masses[elem] / 1000
    return conc

original_data = pd.read_csv("data/full_cleaned_icp_pho2.csv")
original_data = original_data[~original_data["Sample_ID"].str.contains("BLANK|Rinse", na=False)]
original_data["Concentration"] = pd.to_numeric(original_data["Concentration"], errors="coerce")
original_data["Time"] = pd.to_numeric(original_data["Time"], errors="coerce")
original_data = original_data.dropna(subset=["Concentration", "Time"])
original_data["Concentration"] = original_data.apply(ppb_to_mM, axis=1)

oxygen_groups = ["A", "D"]
co2_groups = ["A", "B"]
original_data["O2"] = original_data["Group"].isin(oxygen_groups)
original_data["CO2"] = original_data["Group"].isin(co2_groups)
cleaned_data = original_data.copy()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2("ICP Plot Explorer"),
    dbc.Row([
        dbc.Col([
            html.Label("Shale ID"),
            dcc.Dropdown(id="shale_id", options=[{"label": sid, "value": sid} for sid in sorted(original_data["Shale_ID"].dropna().unique())]),

            html.Label("Element"),
            dcc.Dropdown(id="element"),

            html.Label("Sample Type"),
            dcc.Checklist(
                id="sample_type",
                options=[{"label": t, "value": t} for t in ["Disk", "Dust"]],
                value=["Disk", "Dust"],
                inline=True
            ),

            html.Label("Font Size"),
            dcc.Slider(8, 22, 1, value=14, id="font_size"),

            html.Label("Point Size"),
            dcc.Slider(3, 20, 1, value=10, id="point_size"),

            html.Button("Reset Data", id="reset_btn", n_clicks=0),
            html.Button("Download CSV", id="download_btn"),
            dcc.Download(id="download")
        ], width=3),

        dbc.Col([
            dcc.Graph(id="plot", config={"displaylogo": False}),
            html.Div(id="click_log"),
            html.Br(),
            html.Div([
                html.H6("O₂ / CO₂ Condition Legend:"),
                html.Ul([
                    html.Li("", style={"listStyleType": "none", "display": "inline-block", "width": "15px", "height": "15px", "backgroundColor": "#FF0000", "marginRight": "8px"}),
                    html.Span("O₂ present"),
                    html.Br(),
                    html.Li("", style={"listStyleType": "none", "display": "inline-block", "width": "15px", "height": "15px", "backgroundColor": "#0000FF", "marginRight": "8px"}),
                    html.Span("O₂ absent"),
                    html.Br(),
                    html.Span("Line Style: ", style={"marginRight": "8px", "fontWeight": "bold"}),
                    html.Span("Solid = CO₂ present, Dashed = CO₂ absent")
                ])
            ], style={"fontSize": "14px", "marginTop": "10px"})
        ])
    ])
])

@app.callback(
    Output("element", "options"),
    Input("shale_id", "value")
)
def update_elements(shale_id):
    elements = sorted(original_data[original_data["Shale_ID"] == shale_id]["Element"].dropna().unique())
    return [{"label": e, "value": e} for e in elements]

@app.callback(
    Output("plot", "figure"),
    Input("shale_id", "value"),
    Input("element", "value"),
    Input("sample_type", "value"),
    Input("font_size", "value"),
    Input("point_size", "value"),
    Input("plot", "clickData"),
    Input("reset_btn", "n_clicks"),
    State("plot", "figure")
)
def update_plot(shale_id, element, sample_type, font_size, point_size, clickData, reset_clicks, current_fig):
    global cleaned_data
    trigger = ctx.triggered_id

    if trigger == "reset_btn":
        cleaned_data = original_data.copy()

    dff = cleaned_data[(cleaned_data["Shale_ID"] == shale_id) & (cleaned_data["Element"] == element)]
    if sample_type:
        dff = dff[dff["Sample_Type"].isin(sample_type)]

    if clickData and trigger == "plot":
        pt = clickData["points"][0]
        clicked_time = pt["x"]
        clicked_y = pt["y"]
        clicked_id = pt["text"] if "text" in pt else None
        if clicked_id:
            cleaned_data = cleaned_data[~(
                (cleaned_data["Sample_ID"] == clicked_id) &
                (cleaned_data["Time"] == clicked_time) &
                (cleaned_data["Element"] == element)
            )]
            dff = dff[~(
                (dff["Sample_ID"] == clicked_id) &
                (dff["Time"] == clicked_time)
            )]

    if dff.empty:
        return px.scatter(title="No data available for this selection.")

    dff["Color"] = dff["O2"].apply(lambda x: "#FF0000" if x else "#0000FF")
    dff["Dash"] = dff["CO2"].apply(lambda x: "solid" if x else "dash")

    fig = go.Figure()
    for combo in dff["Sample_Combo"].unique():
        subset = dff[dff["Sample_Combo"] == combo]
        fig.add_trace(go.Scatter(
            x=subset["Time"], y=subset["Concentration"],
            mode="lines+markers",
            marker=dict(size=point_size, color=subset["Color"].iloc[0]),
            line=dict(dash=subset["Dash"].iloc[0], color=subset["Color"].iloc[0]),
            name=combo,
            text=subset["Sample_ID"]
        ))

    if element == "pH":
        yaxis_label = "pH"
    elif element == "O2":
        yaxis_label = "O₂ (mM)"
    else:
        yaxis_label = f"{element} (mM)"

    fig.update_layout(
        title=f"Shale {shale_id}: [{element}]",
        title_font_size=font_size + 4,
        font=dict(size=font_size),
        xaxis_title="Time (days)",
        yaxis_title=yaxis_label,
        xaxis=dict(showgrid=False, rangemode="tozero"),
        yaxis=dict(showgrid=False, rangemode="tozero"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

@app.callback(
    Output("download", "data"),
    Input("download_btn", "n_clicks"),
    prevent_initial_call=True
)
def download_csv(n):
    return dcc.send_data_frame(cleaned_data.to_csv, "data/full_cleaned_icp_pho2.csv")

if __name__ == "__main__":
    app.run(debug=True)
