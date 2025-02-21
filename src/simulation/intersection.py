from .TrafficLight import TrafficLightController
from typing import Optional


class Intersection:
    """
    Intersection repräsentiert einen Knoten.
    Hat eine TrafficLightController-Instanz (falls incoming Spuren vorhanden).
    """

    def __init__(self, node_id, x=0.0, y=0.0):
        self.id = node_id
        self.traffic_lights: Optional[TrafficLightController] = None
        self.x_coord = x
        self.y_coord = y

    def set_traffic_lights(self, tl: TrafficLightController):
        self.traffic_lights = tl

    def can_vehicle_enter(self, street_id: int, lane_index: int) -> bool:
        """
        Prüft, ob Ampelphase = Grün/Gelb für (street_id, lane_index).
        """
        if not self.traffic_lights:
            return True
        return self.traffic_lights.is_green_or_yellow(street_id, lane_index)
