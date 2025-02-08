from street import Street
from vehicle import Vehicle


class Intersection:
    def __init__(self, incoming_streets, outgoing_streets):
        self.incoming_streets = incoming_streets
        self.outgoing_streets = outgoing_streets

    def simulate(self):
        self.incoming_streets[0].getLastVehicle().get_destination()
