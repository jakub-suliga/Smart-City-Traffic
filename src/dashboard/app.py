# app.py
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import networkx as nx

# Importiere deinen city_layout Generator
from simulation import city_layout


def networkx_to_plotly(G):
    # Berechne das Layout (Positionen der Knoten)
    pos = nx.spring_layout(G, seed=42)

    # Erstelle separate Listen für die Kantenkoordinaten
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    # Erstelle den Trace für die Kanten
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    # Erstelle separate Listen für die Knotenkoordinaten und Texte
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(node))

    # Erstelle den Trace für die Knoten
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        text=node_text,
        mode="markers+text",
        textposition="top center",
        hoverinfo="text",
        marker=dict(size=20, color="skyblue", line=dict(width=2)),
    )

    # Erstelle und gebe die Figure zurück
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="City Layout",
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

# Erzeuge einen initialen Graph mit Standardparametern
default_layout = city_layout(intersection_count=4, street_count=4, seed=42)
initial_fig = networkx_to_plotly(default_layout.graph)

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
        # Kein Klick: Keine Aktualisierung
        raise dash.exceptions.PreventUpdate
    try:
        # Generiere den neuen city_layout Graph
        new_layout = city_layout(
            intersection_count=intersections, street_count=streets, seed=seed
        )
        new_fig = networkx_to_plotly(new_layout.graph)
        return new_fig, ""
    except Exception as e:
        # Bei einem Fehler gebe diesen als Nachricht aus, ohne den Graph zu verändern.
        return dash.no_update, f"Fehler: {str(e)}"


if __name__ == "__main__":
    app.run_server(debug=True)
