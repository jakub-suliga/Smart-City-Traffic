import math
from typing import Dict, List, Optional

from .intersection import Intersection
from .street import Street

VEHICLE_PROFILES = {
    "raser": (1.50, 0.8),
    "normal": (1.00, 1.0),
    "slow_driver": (0.75, 1.0),
}


class Vehicle:
    def __init__(
        self,
        vehicle_id: int,
        profile: str,
        current_street: Street,
        lane_index: int,
        route_streets: List[int],
        streets_map: Dict[int, Street],
        intersections_map: Dict[str, Intersection],
    ):
        self.vehicle_id = vehicle_id
        self.profile = profile
        sf, rt = VEHICLE_PROFILES[profile]
        self.speed_factor = sf
        self.reaction_time = rt

        self.current_street = current_street
        self.lane_index = lane_index
        self.position_s = 0.0
        self.route_streets = route_streets
        self.route_index = 0
        self.streets_map = streets_map
        self.intersections_map = intersections_map

        self.speed = 0.0
        self.max_accel = 2.0
        self.max_decel = 4.0

        self.base_speed_limit = current_street.speed_limit * self.speed_factor
        self.done = False

    def current_street_id(self) -> int:
        return self.current_street.id if self.current_street else -1

    def update(self, dt: float, leader: Optional["Vehicle"]):
        if self.done:
            return

        dist_to_end = self.current_street.length - self.position_s

        desired_accel = self.max_accel
        if leader and leader.current_street_id() == self.current_street_id():
            if leader.lane_index == self.lane_index:
                gap = leader.position_s - self.position_s - 5.0
                if gap < self.speed * self.reaction_time:
                    desired_accel = -self.max_decel

        turn_dir = self._next_turn_direction()

        if turn_dir and dist_to_end < 50.0:
            if not self._lane_allows_turn(
                self.current_street, self.lane_index, turn_dir
            ):
                if turn_dir == "left":
                    if self.lane_index < self.current_street.num_lanes - 1:
                        self.lane_index += 1
                elif turn_dir == "right":
                    if self.lane_index > 0:
                        self.lane_index -= 1

        if dist_to_end < 20.0:
            end_n = self.current_street.end_node
            inter = self.intersections_map.get(end_n)
            if inter:
                if not inter.can_vehicle_enter(self.current_street.id, self.lane_index):
                    desired_accel = -self.max_decel

        street_limit = self.current_street.speed_limit
        final_limit = min(street_limit * self.speed_factor, self.base_speed_limit)

        new_speed = self.speed + desired_accel * dt
        new_speed = max(0.0, min(new_speed, final_limit))

        new_pos = self.position_s + new_speed * dt
        if new_pos >= self.current_street.length:
            new_pos = self.current_street.length
            new_speed = 0.0
            end_n = self.current_street.end_node
            inter = self.intersections_map.get(end_n)
            if inter:
                if not inter.can_vehicle_enter(self.current_street.id, self.lane_index):
                    self.speed = 0.0
                    self.position_s = new_pos
                    return
                else:
                    self.route_index += 1
                    if self.route_index >= len(self.route_streets):
                        self.done = True
                        return
                    next_st_id = self.route_streets[self.route_index]
                    next_st = self.streets_map[next_st_id]
                    ln = min(self.lane_index, next_st.num_lanes - 1)

                    self.current_street = next_st
                    self.lane_index = ln
                    self.position_s = 0.0
                    self.speed = 0.0
                    self.base_speed_limit = next_st.speed_limit * self.speed_factor
                    return
            else:
                self.done = True
        else:
            self.speed = new_speed
            self.position_s = new_pos

    def _next_turn_direction(self) -> Optional[str]:
        if self.route_index >= len(self.route_streets) - 1:
            return None
        next_st_id = self.route_streets[self.route_index + 1]
        next_st = self.streets_map[next_st_id]
        ccoords = self.current_street.coords
        v1 = (ccoords[-1][0] - ccoords[-2][0], ccoords[-1][1] - ccoords[-2][1])
        ncoords = next_st.coords
        v2 = (ncoords[1][0] - ncoords[0][0], ncoords[1][1] - ncoords[0][1])
        a1 = math.atan2(v1[1], v1[0])
        a2 = math.atan2(v2[1], v2[0])
        diff = math.degrees(a2 - a1)
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        if diff > 30:
            return "right"
        elif diff < -30:
            return "left"
        else:
            return "through"

    def _lane_allows_turn(self, st: Street, ln: int, turn: str) -> bool:
        if ln < 0 or ln >= st.num_lanes:
            return False
        directions = st.lane_dirs[ln]
        return (
            (turn in directions or "through" in directions)
            if turn == "through"
            else (turn in directions)
        )
