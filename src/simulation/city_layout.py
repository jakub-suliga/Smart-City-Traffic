import random
from typing import List, Tuple
from .intersection import Intersection
from .street import Street


class city_layout:
    def __init__(
        self, intersection_count: int = 4, street_count: int = 4, seed: int = 42
    ):
        self.intersection_count = intersection_count
        self.street_count = street_count
        self.seed = seed

        self.intersections: List[Intersection] = []
        self.streets: List[Street] = []

        self.city = self.create_city_graph(intersection_count, street_count, seed)

    def create_city_graph(
        self, intersection_count: int = 4, street_count: int = 4, seed: int = 42
    ) -> None:
        # Parameter prüfen
        if intersection_count < 1:
            raise ValueError("Es muss mindestens eine Kreuzung vorhanden sein.")
        if street_count < intersection_count - 1:
            raise ValueError(
                f"Für einen zusammenhängenden Graphen sind mindestens {intersection_count - 1} Straßen notwendig."
            )
        if intersection_count >= 3 and street_count > (4 * intersection_count):
            raise ValueError(
                f"Für {intersection_count} Kreuzungen sind maximal {4 * intersection_count} Straßen möglich (planar)."
            )

        random.seed(seed)

        # 1. Zufällige Positionen für die Kreuzungen generieren (z. B. im Bereich 0 bis 100)
        positions: List[Tuple[float, float]] = []
        for _ in range(intersection_count):
            x = random.uniform(0, 100)
            y = random.uniform(0, 100)
            positions.append((x, y))

        # 2. Intersection-Objekte erstellen und die Positionen setzen
        self.intersections = []
        for pos in positions:
            inter = Intersection(streets=[])
            inter.position = pos
            self.intersections.append(inter)

        # Hilfsfunktion: Überprüft, ob sich zwei Strecken (als Segmente) schneiden (außer an gemeinsamen Endpunkten)
        def segments_intersect(
            p1: Tuple[float, float],
            p2: Tuple[float, float],
            p3: Tuple[float, float],
            p4: Tuple[float, float],
        ) -> bool:
            # Falls Endpunkte identisch sind, wird nicht als Schnitt gewertet.
            if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
                return False

            def orientation(
                a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
            ) -> int:
                val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
                if abs(val) < 1e-9:
                    return 0  # kollinear
                return (
                    1 if val > 0 else 2
                )  # 1: im Uhrzeigersinn, 2: gegen den Uhrzeigersinn

            def on_segment(
                a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
            ) -> bool:
                if min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and min(a[1], c[1]) <= b[
                    1
                ] <= max(a[1], c[1]):
                    return True
                return False

            o1 = orientation(p1, p2, p3)
            o2 = orientation(p1, p2, p4)
            o3 = orientation(p3, p4, p1)
            o4 = orientation(p3, p4, p2)

            if o1 != o2 and o3 != o4:
                return True

            if o1 == 0 and on_segment(p1, p3, p2):
                return True
            if o2 == 0 and on_segment(p1, p4, p2):
                return True
            if o3 == 0 and on_segment(p3, p1, p4):
                return True
            if o4 == 0 and on_segment(p3, p2, p4):
                return True

            return False

        # 3. Einen zufälligen Spannbaum (mit intersection_count - 1 Kanten) erzeugen, um Zusammenhängigkeit zu garantieren.
        available = list(range(intersection_count))
        connected = [available.pop(0)]  # Starte mit der ersten Kreuzung
        spanning_edges: List[Tuple[int, int]] = []

        while available:
            new_vertex = available.pop(random.randint(0, len(available) - 1))
            existing_vertex = random.choice(connected)
            spanning_edges.append((existing_vertex, new_vertex))
            connected.append(new_vertex)

        # Die Straßen des Spannbaums erzeugen
        for i, j in spanning_edges:
            length = random.randint(50, 300)  # zufällige Länge
            speed_limit = random.randint(
                30, 120
            )  # zufällige Geschwindigkeitsbegrenzung
            street = Street(length, speed_limit, i, j)
            self.streets.append(street)
            self.intersections[i].streets.append(street)
            self.intersections[j].streets.append(street)

        # 4. Zusätzliche Straßen hinzufügen, bis street_count erreicht ist.
        extra_edges_needed = street_count - (intersection_count - 1)
        candidates = []
        for i in range(intersection_count):
            for j in range(i + 1, intersection_count):
                # Falls die Kante bereits im Spannbaum existiert, überspringen.
                if (i, j) in spanning_edges or (j, i) in spanning_edges:
                    continue
                candidates.append((i, j))
        random.shuffle(candidates)

        extra_edges_added = 0
        for i, j in candidates:
            if extra_edges_added >= extra_edges_needed:
                break
            p1 = self.intersections[i].position
            p2 = self.intersections[j].position

            # Prüfen, ob der neue Streckenabschnitt mit einer bereits existierenden Straße (ohne gemeinsamen Knoten) schneidet.
            conflict = False
            for street in self.streets:
                a = self.intersections[street.start].position
                b = self.intersections[street.end].position
                # Gemeinsame Endpunkte sind erlaubt.
                if i in (street.start, street.end) or j in (street.start, street.end):
                    continue
                if segments_intersect(p1, p2, a, b):
                    conflict = True
                    break
            if conflict:
                continue

            # Kein Konflikt – füge die neue Straße hinzu.
            length = random.randint(50, 300)
            speed_limit = random.randint(30, 120)
            new_street = Street(length, speed_limit, i, j)
            self.streets.append(new_street)
            self.intersections[i].streets.append(new_street)
            self.intersections[j].streets.append(new_street)
            extra_edges_added += 1

        if extra_edges_added < extra_edges_needed:
            print(
                f"Warnung: Es konnten nur {extra_edges_added} zusätzliche Straßen hinzugefügt werden, "
                f"anstatt der gewünschten {extra_edges_needed} (Planaritätsbedingte Einschränkung)."
            )


# Beispiel zur Nutzung:
if __name__ == "__main__":
    # Erzeuge ein city_layout mit 6 Kreuzungen und 8 Straßen
    layout = city_layout(intersection_count=6, street_count=8, seed=123)
    print("Kreuzungen (mit Positionen):")
    for i, inter in enumerate(layout.intersections):
        print(f" {i}: {inter.position}")
    print("Straßen (als Verbindungen zwischen den Knoten):")
    for street in layout.streets:
        print(
            f" {street.start} <--> {street.end}, Länge: {street.length}, Limit: {street.speed_limit}"
        )
