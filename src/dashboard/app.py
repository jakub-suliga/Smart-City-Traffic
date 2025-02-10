# app.py
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import networkx as nx

from ..simulation import city_layout


def city_to_plotly(layout):
    """
    Konvertiert ein city_layout-Objekt in eine Plotly-Figur unter Verwendung eines planaren Layouts,
    sodass sich die Kanten (sofern möglich) nicht überschneiden.
    """
    # Erstelle einen NetworkX-Graphen aus den Kreuzungen und Straßen
    G = nx.Graph()
    for i, inter in enumerate(layout.intersections):
        G.add_node(i)
    for street in layout.streets:
        G.add_edge(
            street.start,
            street.end,
            length=street.length,
            speed_limit=street.speed_limit,
        )

    # Versuche, ein planares Layout zu berechnen. Falls dies fehlschlägt,
    # werden als Fallback die in der Simulation hinterlegten Positionen genutzt.
    try:
        pos = nx.planar_layout(G)
    except Exception as e:
        pos = {i: inter.position for i, inter in enumerate(layout.intersections)}

    # Erstelle den Trace für die Kanten
    edge_x = []
    edge_y = []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=2, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    # Erstelle den Trace für die Knoten
    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[str(node) for node in G.nodes()],
        textposition="top center",
        hoverinfo="text",
        marker=dict(showscale=False, color="#FFA07A", size=10, line=dict(width=2)),
    )

    # Erzeuge die Plotly-Figur
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    return fig


# Initialisiere die Dash-App
app = dash.Dash(__name__)

# Erzeuge einen initialen city_layout mit Standardparametern
default_layout = city_layout(intersection_count=4, street_count=4, seed=42)
initial_fig = city_to_plotly(default_layout)

# Definiere das Layout der App: linke Spalte für den Graph, rechte Spalte für die Parameter
app.layout = html.Div(
    style={"display": "flex", "flexDirection": "row", "height": "100vh"},
    children=[
        # Linke Spalte: Anzeige des Graphen
        html.Div(
            style={
                "flex": "1",
                "borderRight": "2px solid #ddd",
                "padding": "10px",
            },
            children=[
                dcc.Graph(id="city-graph", figure=initial_fig, style={"height": "100%"})
            ],
        ),
        # Rechte Spalte: Eingabe der Parameter
        html.Div(
            style={"flex": "1", "padding": "10px"},
            children=[
                html.H2("City Layout Generator"),
                html.Label("Anzahl der Kreuzungen:"),
                dcc.Input(id="input-intersections", type="number", value=4, min=1),
                html.Br(),
                html.Br(),
                html.Label("Anzahl der Straßen:"),
                dcc.Input(id="input-streets", type="number", value=4, min=0),
                html.Br(),
                html.Br(),
                html.Label("Seed:"),
                dcc.Input(id="input-seed", type="number", value=42),
                html.Br(),
                html.Br(),
                html.Button("Graph neu generieren", id="generate-button", n_clicks=0),
                html.Div(
                    id="error-message", style={"color": "red", "marginTop": "10px"}
                ),
            ],
        ),
    ],
)


# Callback: Aktualisiere den Graph, wenn der Button geklickt wird
@app.callback(
    [Output("city-graph", "figure"), Output("error-message", "children")],
    [Input("generate-button", "n_clicks")],
    [
        State("input-intersections", "value"),
        State("input-streets", "value"),
        State("input-seed", "value"),
    ],
)
def update_graph(n_clicks, intersections, streets, seed):
    if n_clicks is None or n_clicks == 0:
        # Noch kein Klick – keine Aktualisierung
        raise dash.exceptions.PreventUpdate
    try:
        # Generiere einen neuen city_layout-Graphen
        new_layout = city_layout(
            intersection_count=intersections, street_count=streets, seed=seed
        )
        new_fig = city_to_plotly(new_layout)
        return new_fig, ""
    except Exception as e:
        # Bei einem Fehler: Gib den Fehlertext aus, ohne den aktuellen Graphen zu verändern.
        return dash.no_update, f"Fehler: {str(e)}"


if __name__ == "__main__":
    app.run_server(debug=True)
