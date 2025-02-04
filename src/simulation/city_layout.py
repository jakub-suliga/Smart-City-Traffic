# city_layout.py
import random
import networkx as nx


class city_layout:
    def __init__(self, intersection_count=4, street_count=4, seed=42):
        self.graph = self.create_city_graph(intersection_count, street_count, seed)

    def create_city_graph(self, intersection_count=4, street_count=4, seed=42):
        # Validierung der Parameter:
        if intersection_count < 1:
            raise ValueError("intersection_count muss mindestens 1 sein.")

        if intersection_count == 1:
            if street_count > 0:
                raise ValueError("Mit nur 1 Kreuzung können keine Straßen existieren.")
            # Bei 1 Kreuzung und 0 Straßen: Erzeuge einen Graphen mit einem Knoten.
            city_graph = nx.Graph()
            city_graph.add_node(0)
            return city_graph

        # Mindestzahl an Straßen für einen zusammenhängenden Graphen
        if street_count < intersection_count - 1:
            raise ValueError(
                "street_count muss mindestens intersection_count - 1 betragen, um einen verbundenen Graphen zu erstellen."
            )

        # Maximale Anzahl an Kanten unter Beachtung, dass jeder Knoten maximal 4 Kanten haben darf:
        max_possible_edges = min(
            intersection_count * (intersection_count - 1) // 2, 2 * intersection_count
        )
        if street_count > max_possible_edges:
            raise ValueError(
                f"Mit {intersection_count} Kreuzungen und einem maximalen Grad von 4 können höchstens {max_possible_edges} Straßen existieren."
            )

        random.seed(seed)
        city_graph = nx.Graph()
        # Knoten hinzufügen
        city_graph.add_nodes_from(range(intersection_count))

        # Schritt 1: Erzeuge einen zufälligen Spannbaum, um Konnektivität zu gewährleisten.
        nodes = list(range(intersection_count))
        random.shuffle(nodes)
        connected = {nodes[0]}
        remaining = set(nodes[1:])

        while remaining:
            current = random.choice(list(connected))
            new_node = random.choice(list(remaining))
            city_graph.add_edge(current, new_node)
            connected.add(new_node)
            remaining.remove(new_node)

        # Schritt 2: Füge zusätzliche zufällige Kanten hinzu, bis die gewünschte Anzahl erreicht ist.
        current_edge_count = city_graph.number_of_edges()
        attempts = 0
        max_attempts = 1000  # Verhindert Endlosschleifen

        while current_edge_count < street_count and attempts < max_attempts:
            node1, node2 = random.sample(range(intersection_count), 2)
            if city_graph.has_edge(node1, node2):
                attempts += 1
                continue
            if city_graph.degree(node1) >= 4 or city_graph.degree(node2) >= 4:
                attempts += 1
                continue
            city_graph.add_edge(node1, node2)
            current_edge_count += 1
            attempts = 0  # Reset der Versuche bei Erfolg

        if current_edge_count < street_count:
            raise RuntimeError(
                "Es war nicht möglich, alle gewünschten Straßen hinzuzufügen unter Einhaltung der Bedingungen."
            )

        return city_graph


# Beispiel zur Nutzung:
if __name__ == "__main__":
    try:
        layout = city_layout(intersection_count=10, street_count=15, seed=42)
        G = layout.graph
        print("Knoten und ihre Grade:")
        for node, degree in G.degree():
            print(f"Knoten {node}: Grad {degree}")
        print("\nKanten:")
        for edge in G.edges():
            print(edge)
    except Exception as e:
        print("Fehler:", e)
