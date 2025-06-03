import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Load the cleaned data
icp_df = pd.read_csv("data/cleaned_icp_data.csv")
ph_o2_df = pd.read_csv("data/phO2.csv")

# Convert Time to float from Sample_ID
icp_df["Time"] = icp_df["Sample_ID"].astype(str).str.extract(r"t(\d+\.?\d*)")[0].astype(float)

# Add CO2 and O2 columns based on Group
oxygen_groups = ["A", "D"]
co2_groups = ["A", "B"]
icp_df["O2"] = icp_df["Group"].isin(oxygen_groups)
icp_df["CO2"] = icp_df["Group"].isin(co2_groups)


# DASH APP
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H3("ICP + pH/O₂ Dashboard"),
    dbc.Row([
        dbc.Col([
            html.Label("Shale ID"),
            dcc.Dropdown(id="shale_id", options=[{"label": sid, "value": sid} for sid in sorted(icp_df["Shale_ID"].dropna().unique())], value="64"),

            html.Label("Element"),
            dcc.Dropdown(id="element", options=[{"label": e, "value": e} for e in sorted(icp_df["Element"].dropna().unique())], value="Mg"),

            html.Label("Sample Type"),
            dcc.Checklist(
                id="sample_type",
                options=[{"label": t, "value": t} for t in icp_df["Sample_Type"].dropna().unique()],
                value=["Disk"],
                inline=True
            ),

            html.Label("Font Size"),
            dcc.Slider(8, 22, 1, value=14, id="font_size"),

            html.Label("Point Size"),
            dcc.Slider(3, 20, 1, value=10, id="point_size")
        ], width=3),

        dbc.Col([
            dcc.Graph(id="plot", config={"displaylogo": False}),
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
    Output("plot", "figure"),
    Input("shale_id", "value"),
    Input("element", "value"),
    Input("sample_type", "value"),
    Input("font_size", "value"),
    Input("point_size", "value")
)
def update_plot(shale_id, element, sample_type, font_size, point_size):
    dff = icp_df[(icp_df["Shale_ID"] == shale_id) & (icp_df["Element"] == element)]
    if sample_type:
        dff = dff[dff["Sample_Type"].isin(sample_type)]

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

    fig.update_layout(
        title=f"Shale {shale_id}: [{element}]",
        title_font_size=font_size + 4,
        font=dict(size=font_size),
        xaxis_title="Time (days)",
        yaxis_title=f"{element} Concentration",
        xaxis=dict(showgrid=False, rangemode="tozero"),
        yaxis=dict(showgrid=False, rangemode="tozero"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

if __name__ == "__main__":
    app.run(debug=True)
