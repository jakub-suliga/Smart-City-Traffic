# app.py
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import networkx as nx

from ..simulation import city_layout  # Importiere unsere angepasste CityLayout-Klasse


def city_to_plotly(layout):
    """
    Konvertiert ein CityLayout-Objekt in eine Plotly-Figur unter Verwendung eines planaren Layouts.
    """
    # Falls intersections als 2D‑Array vorliegt, flachen wir es zu einer Liste ab.
    if isinstance(layout.intersections[0], list):
        flat_intersections = []
        coord_to_id = {}
        id_to_pos = {}
        node_id = 0
        for i, row in enumerate(layout.intersections):
            for j, inter in enumerate(row):
                flat_intersections.append(inter)
                coord_to_id[(i, j)] = node_id
                id_to_pos[node_id] = inter.position
                node_id += 1
    else:
        flat_intersections = layout.intersections
        coord_to_id = {i: i for i in range(len(flat_intersections))}
        id_to_pos = {i: inter.position for i, inter in enumerate(flat_intersections)}

    # Erstelle einen NetworkX-Graphen.
    G = nx.Graph()
    for node_id in id_to_pos:
        G.add_node(node_id)

    # Füge Kanten hinzu – beachte, dass in den Street-Objekten die Endpunkte als (i,j)-Tupel gespeichert sind.
    for street in layout.streets:
        start_id = coord_to_id[street.start]
        end_id = coord_to_id[street.end]
        G.add_edge(
            start_id, end_id, length=street.length, speed_limit=street.speed_limit
        )

    # Versuche, ein planäres Layout zu berechnen; falls das fehlschlägt, verwende die hinterlegten Positionen.
    try:
        pos = nx.planar_layout(G)
    except Exception:
        pos = id_to_pos

    # Kanten-Trace
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

    # Knoten-Trace
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

# Erzeuge einen initialen CityLayout.
# Hier interpretieren wir "input-intersections" als Anzahl der Zeilen und "input-streets" als Anzahl der Spalten.
default_layout = city_layout(grid_rows=4, grid_cols=4, seed=42)
initial_fig = city_to_plotly(default_layout)

# Layout der Dash-App: Linke Spalte zeigt den Graph, rechte Spalte Eingabefelder.
app.layout = html.Div(
    style={"display": "flex", "flexDirection": "row", "height": "100vh"},
    children=[
        # Linke Spalte: Graphanzeige
        html.Div(
            style={"flex": "1", "borderRight": "2px solid #ddd", "padding": "10px"},
            children=[
                dcc.Graph(id="city-graph", figure=initial_fig, style={"height": "100%"})
            ],
        ),
        # Rechte Spalte: Eingabefelder
        html.Div(
            style={"flex": "1", "padding": "10px"},
            children=[
                html.H2("City Layout Generator"),
                html.Label("Anzahl der Zeilen:"),
                dcc.Input(id="input-intersections", type="number", value=4, min=1),
                html.Br(),
                html.Br(),
                html.Label("Anzahl der Spalten:"),
                dcc.Input(id="input-streets", type="number", value=4, min=1),
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


# Callback: Aktualisiere den Graph, wenn der Button geklickt wird.
@app.callback(
    [Output("city-graph", "figure"), Output("error-message", "children")],
    [Input("generate-button", "n_clicks")],
    [
        State("input-intersections", "value"),
        State("input-streets", "value"),
        State("input-seed", "value"),
    ],
)
def update_graph(n_clicks, grid_rows, grid_cols, seed):
    if n_clicks is None or n_clicks == 0:
        raise dash.exceptions.PreventUpdate
    try:
        new_layout = city_layout(grid_rows=grid_rows, grid_cols=grid_cols, seed=seed)
        new_fig = city_to_plotly(new_layout)
        return new_fig, ""
    except Exception as e:
        return dash.no_update, f"Fehler: {str(e)}"


if __name__ == "__main__":
    app.run_server(debug=True)
