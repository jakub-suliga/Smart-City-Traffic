import osmnx as ox
import networkx as nx
import shapely
import shapely.geometry
import shapely.ops

from typing import Dict, List, Tuple, Optional


class Street:
    """
    Street speichert:
      - start_node, end_node
      - points (Polylinie)
      - length
      - speed_limit (m/s)
      - num_lanes
      - turn_lanes_info: pro Spur => set of directions (z. B. {'left','through'})
    """

    def __init__(
        self,
        st_id: int,
        start_node,
        end_node,
        coords: List[Tuple[float, float]],
        speed_limit: float,
        lane_dirs: List[List[str]],
    ):
        """
        lane_dirs: turn:lanes-Interpretation pro Spur. Bsp:
                   [ ['left'], ['through','right'] ]
        num_lanes = len(lane_dirs)
        """
        self.id = st_id
        self.start_node = start_node
        self.end_node = end_node
        self.coords = coords
        self.length = shapely.geometry.LineString(coords).length
        self.speed_limit = speed_limit
        self.lane_dirs = lane_dirs
        self.num_lanes = len(lane_dirs)
