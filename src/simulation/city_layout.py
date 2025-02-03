# src/simulation/city_layout.py
import networkx as nx


def create_city_graph():
    # Erstelle einen ungerichteten Graphen
    city_graph = nx.Graph()

    # Beispiel: Knoten als Kreuzungen hinzufügen (mit Koordinaten als Attribute)
    city_graph.add_node("Kreuzung_A", pos=(0, 0))
    city_graph.add_node("Kreuzung_B", pos=(1, 2))
    city_graph.add_node("Kreuzung_C", pos=(3, 1))
    city_graph.add_node("Kreuzung_D", pos=(4, 3))

    # Beispiel: Kanten als Straßen hinzufügen (optional mit Gewicht oder Länge)
    city_graph.add_edge("Kreuzung_A", "Kreuzung_B", weight=2)
    city_graph.add_edge("Kreuzung_B", "Kreuzung_C", weight=3)
    city_graph.add_edge("Kreuzung_C", "Kreuzung_D", weight=2)
    city_graph.add_edge("Kreuzung_A", "Kreuzung_C", weight=4)

    return city_graph


if __name__ == "__main__":
    graph = create_city_graph()
    print("Knoten (Kreuzungen):", list(graph.nodes(data=True)))
    print("Kanten (Straßen):", list(graph.edges(data=True)))
