# Dash App with Color-Coded O2/CO2 Legend
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Load datasets
exp1_path = "C:/Users/KathrynFarber/OneDrive - USF - eStore/Documents/SFA-shale/data/icpTotRaw.csv"
exp2_path = "C:/Users/KathrynFarber/OneDrive - USF - eStore/Documents/SFA-shale/data/Exp2_TotICP.csv"
bis_path = "C:/Users/KathrynFarber/OneDrive - USF - eStore/Documents/SFA-shale/data/exBis12TotIcp.csv"

def load_experiment(path, label):
    df = pd.read_csv(path)
    df = df[df.iloc[:, 0] != "Blank"].copy()
    df.rename(columns={df.columns[0]: "Sample_ID"}, inplace=True)
    df["Sample_ID"] = df["Sample_ID"].astype(str)
    df["Time"] = df["Sample_ID"].str.extract(r"t([0-9.]+)").astype(float)
    df["Sample_Type"] = df["Sample_ID"].str.lower().apply(lambda x: "Disk" if "disk" in x else "Dust" if "dust" in x else None)
    df[["Sample_Number", "Group"]] = df["Sample_ID"].str.extract(r"(\d{2})([A-D])")
    df["Sample_Combo"] = df["Sample_Number"] + df["Group"]
    df["Experiment"] = label
    id_vars = ["Sample_ID", "Time", "Sample_Type", "Group", "Sample_Number", "Sample_Combo", "Experiment"]
    value_vars = [col for col in df.columns if col not in id_vars]
    df_long = df.melt(id_vars=id_vars, value_vars=value_vars, var_name="Element", value_name="Concentration")
    df_long.dropna(subset=["Concentration"], inplace=True)
    if label == "Exp2":
        df_long["Concentration"] *= 1000
    df_long["Element"] = df_long["Element"].str.extract(r"^\d*([A-Z][a-z]?)")
    return df_long

# Load and combine
df_all = pd.concat([
    load_experiment(exp1_path, "Exp1"),
    load_experiment(exp2_path, "Exp2"),
    load_experiment(bis_path, "BIS")
], ignore_index=True)

# Add Shale_ID column
df_all["Shale_ID"] = df_all["Sample_Number"] + df_all["Experiment"].apply(lambda x: "-BIS" if x == "BIS" else "")
df_all["Shale_ID"] = df_all["Shale_ID"].astype(str)
shale_ids = sorted(df_all["Shale_ID"].dropna().unique())

# Custom colors
custom_colors = {
    "63A": "#8B0000", "67A": "#8B0000", "60A": "#8B0000", "64A": "#8B0000",
    "63D": "#FF6347", "67D": "#FF6347", "60D": "#FF6347", "64D": "#FF6347",
    "63B": "#00008B", "67B": "#00008B", "60B": "#00008B", "64B": "#00008B",
    "63C": "#4682B4", "67C": "#4682B4", "60C": "#4682B4", "64C": "#4682B4"
}

# App setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H2("ICP Plot Explorer"),
    dbc.Row([
        dbc.Col([
            html.Label("Shale ID"),
            dcc.Dropdown(id="shale_id", options=[{"label": sid, "value": sid} for sid in shale_ids], value="64"),
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
                    html.Li("", style={"listStyleType": "none", "display": "inline-block", "width": "15px", "height": "15px", "backgroundColor": "#8B0000", "marginRight": "8px"}),
                    html.Span("O₂ + CO₂"),
                    html.Br(),
                    html.Li("", style={"listStyleType": "none", "display": "inline-block", "width": "15px", "height": "15px", "backgroundColor": "#FF6347", "marginRight": "8px"}),
                    html.Span("O₂ only"),
                    html.Br(),
                    html.Li("", style={"listStyleType": "none", "display": "inline-block", "width": "15px", "height": "15px", "backgroundColor": "#00008B", "marginRight": "8px"}),
                    html.Span("CO₂"),
                    html.Br(),
                    html.Li("", style={"listStyleType": "none", "display": "inline-block", "width": "15px", "height": "15px", "backgroundColor": "#4682B4", "marginRight": "8px"}),
                    html.Span("none")
                ])
            ], style={"fontSize": "14px", "marginTop": "10px"})
        ])
    ])
])

# Initialize memory
cleaned_data = df_all.copy()

@app.callback(
    Output("element", "options"),
    Input("shale_id", "value"),
    State("element", "value")
)
def update_elements(shale_id, current_element):
    filtered = df_all[df_all["Shale_ID"] == shale_id]
    elements = sorted(filtered["Element"].dropna().unique())
    return [{"label": e, "value": e} for e in elements]

@app.callback(
    Output("plot", "figure"),
    Input("shale_id", "value"),
    Input("element", "value"),
    Input("sample_type", "value"),
    Input("font_size", "value"),
    Input("point_size", "value"),
    Input("plot", "clickData"),
    State("plot", "figure")
)
def update_plot(shale_id, element, sample_type, font_size, point_size, clickData, current_fig):
    global cleaned_data

    dff = cleaned_data[(cleaned_data["Shale_ID"] == shale_id) & (cleaned_data["Element"] == element)]
    if sample_type:
        dff = dff[dff["Sample_Type"].isin(sample_type)]

    if clickData and ctx.triggered_id == "plot":
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

    fig = px.scatter(
        dff, x="Time", y="Concentration", color="Sample_Combo", symbol="Sample_Type",
        color_discrete_map=custom_colors, title=f"Shale {shale_id}: [{element}]",
        text="Sample_ID"
    )
    fig.update_traces(mode="lines+markers", marker=dict(size=point_size))
    fig.update_layout(
        title_font_size=font_size + 4,
        xaxis_title="Time (days)",
        yaxis_title=f"{element} Concentration",
        font=dict(size=font_size),
        xaxis=dict(showgrid=False, rangemode="tozero"),
        yaxis=dict(showgrid=False, rangemode="tozero")
    )
    return fig

@app.callback(
    Output("download", "data"),
    Input("download_btn", "n_clicks"),
    prevent_initial_call=True
)
def download_csv(n):
    return dcc.send_data_frame(cleaned_data.to_csv, "cleaned_icp_data.csv")

if __name__ == "__main__":
    app.run(debug=True)
#run python icp_dash_app.py