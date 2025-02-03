# src/simulation/city_layout.py
import networkx as nx


class city_layout:
    def __init__(self, intersection_count=4, street_count=4, seed=42):
        self.graph = self.create_city_graph(intersection_count, street_count, seed)

    def create_city_graph(self, intersection_count=4, street_count=4, seed=42):
        city_graph = nx.Graph()
        city_graph.add_nodes_from(range(intersection_count))

        return city_graph


if __name__ == "__main__":
    graph = create_city_graph()
    print("Knoten (Kreuzungen):", list(graph.nodes(data=True)))
    print("Kanten (Straßen):", list(graph.edges(data=True)))
