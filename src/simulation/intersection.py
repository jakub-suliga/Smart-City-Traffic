from street import Street
from vehicle import Vehicle


class Intersection:
    def __init__(self, streets):
        self.streets = streets

    def simulate(self, street: int):
        dest = self.streets[street].getLastVehicle().get_destination()
        if dest == 0:
            vehc = self.streets[street].removeVehicle()
            self.streets[(street + 1) % 3].addVehicle(vehc)
        elif dest == 1:
            vehc = self.streets[street].removeVehicle()
            self.streets[(street + 3) % 3].addVehicle(vehc)
        else:
            vehc = self.streets[street].removeVehicle()
            self.streets[(street + 2) % 3].addVehicle(vehc)
