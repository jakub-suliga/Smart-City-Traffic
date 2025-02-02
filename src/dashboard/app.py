# src/dashboard/app.py
import dash
from dash import html, dcc
import plotly.graph_objects as go

# Dash-App initialisieren
app = dash.Dash(__name__)

# Beispielhafte 2D-Karte (Simulation) erstellen
# Hier kannst du später deine Simulationsdaten einbinden
map_fig = go.Figure()
map_fig.add_trace(go.Scatter(
    x=[1, 2, 3, 4],         # Beispielkoordinaten
    y=[10, 11, 12, 13],
    mode="markers",
    marker=dict(size=12, color='red'),
    name="Fahrzeuge"
))
map_fig.update_layout(
    title="2D Simulationskarte",
    xaxis_title="X-Achse",
    yaxis_title="Y-Achse"
)

# Layout definieren: linke Spalte für die Karte, rechte Spalte für das Dashboard
app.layout = html.Div(
    style={'display': 'flex', 'flexDirection': 'row', 'height': '100vh'},
    children=[
        # Linke Spalte: 2D Karte
        html.Div(
            style={
                'flex': '1',            # Nimmt den gleichen Platz wie die rechte Spalte
                'borderRight': '2px solid #ddd',
                'padding': '10px'
            },
            children=[
                dcc.Graph(
                    id='map-graph',
                    figure=map_fig,
                    style={'height': '100%'}
                )
            ]
        ),
        # Rechte Spalte: Dashboard (Steuerungen, Anzeigen, etc.)
        html.Div(
            style={
                'flex': '1',
                'padding': '10px'
            },
            children=[
                html.H2("Dashboard"),
                html.Div("Hier kannst du Einstellungen vornehmen und den Erfolg überwachen."),
                # Beispiel: Ein Slider zur Simulationseinstellung
                html.Label("Verkehrsaufkommen:"),
                dcc.Slider(
                    id='traffic-slider',
                    min=0,
                    max=100,
                    step=1,
                    value=50,
                    marks={i: str(i) for i in range(0, 101, 10)}
                ),
                html.Br(),
                html.Button("Simulation Starten", id="start-button", n_clicks=0),
                html.Div(id='simulation-status', children="Simulationserfolg: 0%")
            ]
        )
    ]
)

if __name__ == '__main__':
    app.run_server(debug=True)
