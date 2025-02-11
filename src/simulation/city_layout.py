import random
from typing import List, Tuple
from .intersection import Intersection
from .street import Street


class city_layout:
    def __init__(self, grid_rows: int = 4, grid_cols: int = 4, seed: int = 42):
        """
        Erzeugt ein toroidales Gitter mit grid_rows x grid_cols Kreuzungen.
        Jede Kreuzung ist über wrap‑around mit genau 4 Straßen verbunden.
        """
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.seed = seed

        # Hier speichern wir die Kreuzungen als 2D‑Array (Liste von Listen)
        self.intersections: List[List[Intersection]] = []
        # Alle erzeugten Straßen sammeln wir in einer Liste
        self.streets: List[Street] = []

        self._create_grid()

    def _create_grid(self) -> None:
        random.seed(self.seed)
        # 1. Erzeuge das 2D‑Array der Kreuzungen.
        self.intersections = []
        for i in range(self.grid_rows):
            row = []
            for j in range(self.grid_cols):
                inter = Intersection(streets=[])
                # Hier setzen wir die Position; für eine natürliche Darstellung verwenden wir (x, y) = (j, -i)
                inter.position = (j, -i)
                row.append(inter)
            self.intersections.append(row)

        # 2. Erzeuge die Straßen so, dass jede Kreuzung exakt 4 Verbindungen erhält.
        # Wir fügen für jede Kreuzung zwei Kanten hinzu – eine nach Osten und eine nach Süden –
        # wobei durch wrap‑around auch die westlichen bzw. nördlichen Verbindungen abgedeckt werden.
        for i in range(self.grid_rows):
            for j in range(self.grid_cols):
                current = self.intersections[i][j]

                # Verbindung nach Osten (wrap‑around, falls j == grid_cols‑1)
                east_j = (j + 1) % self.grid_cols
                east_neighbor = self.intersections[i][east_j]
                length_east = random.randint(50, 300)
                speed_limit_east = random.randint(30, 120)
                street_east = Street(length_east, speed_limit_east, (i, j), (i, east_j))
                self.streets.append(street_east)
                current.streets.append(street_east)
                east_neighbor.streets.append(street_east)

                # Verbindung nach Süden (wrap‑around, falls i == grid_rows‑1)
                south_i = (i + 1) % self.grid_rows
                south_neighbor = self.intersections[south_i][j]
                length_south = random.randint(50, 300)
                speed_limit_south = random.randint(30, 120)
                street_south = Street(
                    length_south, speed_limit_south, (i, j), (south_i, j)
                )
                self.streets.append(street_south)
                current.streets.append(street_south)
                south_neighbor.streets.append(street_south)
