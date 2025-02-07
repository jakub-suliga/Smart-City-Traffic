import numpy as np
from vehicle import Vehicle


class Street:
    def __init__(self, length, speed_limit, start, end):
        self.length = length
        self.speed_limit = speed_limit
        self.start = start
        self.end = end
        self.vehicles = np.full(length, None, dtype=object)

    def getVehicleCount(self):
        """Returns the number of vehicles on the street."""
        return sum(1 for v in self.vehicles if v is not None)

    def getLastVehicle(self):
        """
        Returns the vehicle in the last occupied slot (highest index)
        or None if there are no vehicles.
        """
        for i in range(self.length - 1, -1, -1):
            if self.vehicles[i] is not None:
                return self.vehicles[i]
        return None

    def addVehicle(self, vehicle):
        """
        Inserts a vehicle at the starting position (index 0).
        If that position is already occupied, returns False.
        Otherwise, places the vehicle and returns True.
        """
        if self.vehicles[0] is not None:
            return False
        self.vehicles[0] = vehicle
        return True

    def removeVehicle(self):
        """
        Removes the vehicle at the last occupied position (highest index)
        and returns it. If no vehicle is present, returns None.
        """
        removed_vehicle = self.vehicles[self.length - 1]
        self.vehicles[i] = None
        return removed_vehicle

    def simulate(self):
        """
        Simulates one time step where each vehicle attempts to move one slot forward:
          - If the cell in front is occupied or the vehicle is already at the end,
            it remains in place.
          - Otherwise, it moves one slot forward.
        Movements are performed simultaneously; decisions are based on the old configuration,
        and the result is stored in a new state array.
        """
        new_state = np.full(self.length, None, dtype=object)
        for i in range(self.length):
            vehicle = self.vehicles[i]
            if vehicle is not None:
                # If not at the end and the cell ahead (from the old configuration) is free, move forward.
                if i < self.length - 1 and self.vehicles[i + 1] is None:
                    new_state[i + 1] = vehicle
                else:
                    # Vehicle stays in its current position
                    new_state[i] = vehicle
        self.vehicles = new_state
