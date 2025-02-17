import random
from typing import Optional, List
from .vehicle import Vehicle


class Street:
    length: int
    speed_limit: int
    start: int
    end: int
    vehicles: List[Optional[Vehicle]]
    num_vehicles: int

    def __init__(self, length: int, speed_limit: int, start: int, end: int) -> None:
        self.length = length
        self.speed_limit = speed_limit
        self.start = start
        self.end = end
        self.vehicles = [None] * length
        self.num_vehicles = 0

    def get_vehicle_count(self) -> int:
        """Returns the number of vehicles on the street."""
        return sum(1 for v in self.vehicles if v is not None)

    def get_last_vehicle(self) -> Optional[Vehicle]:
        """
        Returns the vehicle in the last occupied slot (highest index)
        or None if there are no vehicles.
        """
        return self.vehicles[-1]

    def _add_vehicle_pos(self, vehicle: Vehicle, pos: int) -> bool:
        if self.vehicles[pos] is not None:
            return False
        self.vehicles[pos] = vehicle
        return True

    def add_vehicle(
        self,
        vehicle: Vehicle,
    ) -> bool:
        return self._add_vehicle_pos(vehicle, 0)

    def create_vehicle(self, vehicle_number: int) -> bool:
        if (
            vehicle_number > self.length
            or vehicle_number < 0
            or self.num_vehicles + vehicle_number > self.length
        ):
            raise ValueError("Invalid number of vehicles")
        for i in range(vehicle_number):
            vehicle = Vehicle()
            added = False
            while not added:
                pos = random.randint(0, self.length - 1)
                added = self._add_vehicle_pos(vehicle, pos)

    def remove_vehicle(self) -> Optional[Vehicle]:
        """
        Removes the vehicle at the last occupied position (highest index)
        and returns it. If no vehicle is present, returns None.
        """
        removed_vehicle = self.vehicles[-1]
        self.vehicles[-1] = None
        return removed_vehicle

    def simulate(self) -> None:
        """
        Simulates one time step where each vehicle attempts to move one slot forward:
          - If the cell in front is occupied or the vehicle is already at the end,
            it remains in place.
          - Otherwise, it moves one slot forward.
        Movements are performed simultaneously; decisions are based on the old configuration,
        and the result is stored in a new state list.
        """
        new_state: List[Optional[Vehicle]] = [None] * self.length
        for i in reversed(range(self.length)):
            vehicle = self.vehicles[i]
            if vehicle is not None:
                if i < self.length - 1 and self.vehicles[i + 1] is None:
                    new_state[i + 1] = vehicle
                else:
                    new_state[i] = vehicle
        self.vehicles = new_state
