from typing import Optional, List
from .vehicle import Vehicle


class Street:
    length: int
    speed_limit: int
    start: int
    end: int
    vehicles: List[Optional[Vehicle]]

    def __init__(self, length: int, speed_limit: int, start: int, end: int) -> None:
        self.length = length
        self.speed_limit = speed_limit
        self.start = start
        self.end = end
        self.vehicles = [None] * length

    def get_vehicle_count(self) -> int:
        """Returns the number of vehicles on the street."""
        return sum(1 for v in self.vehicles if v is not None)

    def get_last_vehicle(self) -> Optional[Vehicle]:
        """
        Returns the vehicle in the last occupied slot (highest index)
        or None if there are no vehicles.
        """
        return self.vehicles[-1]

    def add_vehicle(self, vehicle: Vehicle) -> bool:
        """
        Inserts a vehicle at the starting position (index 0).
        If that position is already occupied, returns False.
        Otherwise, places the vehicle and returns True.
        """
        if self.vehicles[0] is not None:
            return False
        self.vehicles[0] = vehicle
        return True

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
