from typing import List, Optional
from .street import Street
from .vehicle import Vehicle


class Intersection:
    streets: List[Street]

    def __init__(self, streets: List[Street]) -> None:
        self.streets = streets

    def simulate(self, street_index: int) -> None:
        vehicle: Optional[Vehicle] = self.streets[street_index].get_last_vehicle()
        if vehicle is None:
            return

        dest = vehicle.get_destination()
        if dest == 0:
            target_index = (street_index + 1) % 4
        elif dest == 1:
            target_index = (street_index + 2) % 4
        else:
            target_index = (street_index + 3) % 4

        added = self.streets[target_index].add_vehicle(removed_vehicle)
        if added:
            removed_vehicle = self.streets[street_index].remove_vehicle()
