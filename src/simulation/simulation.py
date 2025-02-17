import random
from typing import List

from .city_layout import city_layout
from .vehicle import Vehicle


class Simulator:
    def __init__(self, vehicle_count: int = 10, seed: int = 42):
        self.vehicle_count = vehicle_count
        self.seed = seed
        self.city_layout = city_layout(seed=self.seed)

        self._create_vehicles()

    def _create_vehicles(self) -> None:
        streets = self.city_layout.streets
        random.seed(self.seed)
        for street in range(self.vehicle_count):
            vehicle = Vehicle()
            street.add_vehicle(vehicle)
