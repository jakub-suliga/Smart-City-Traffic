import math
import random
import heapq
import time
import logging
import osmnx as ox
import networkx as nx
import shapely
import shapely.geometry
import shapely.ops

from typing import Dict, List, Tuple, Optional

###############################################################################
# 1) GLOBALE PARAMETER, HILFSFUNKTIONEN
###############################################################################

# Ampelphasen
PHASE_GREEN = 0
PHASE_YELLOW = 1
PHASE_RED = 2
PHASE_REDYELLOW = 3

# Dauer pro Phase
PHASE_DURATIONS = {
    PHASE_GREEN: 15.0,
    PHASE_YELLOW: 3.0,
    PHASE_RED: 15.0,
    PHASE_REDYELLOW: 2.0,
}

# Fahrzeug-Profile
#  speed_factor, reaction_time
VEHICLE_PROFILES = {
    "raser": (1.50, 0.8),
    "normal": (1.00, 1.0),
    "slow_driver": (0.75, 1.5),
}


def distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


###############################################################################
# 2) TURN-LANES-AUSWERTUNG
###############################################################################


def parse_turn_lanes(turn_lanes_str: str) -> List[List[str]]:
    """
    Parst z. B. "left|through;right" in:
      [ ["left"], ["through","right"] ]
    d. h. pro Spur eine Liste an erlaubten Richtungen.
    Mögliche Werte in OSM: left, right, through, slight_left, slight_right usw.
    Hier behandeln wir "slight_left" als "left" und "slight_right" als "right".
    """
    if not turn_lanes_str:
        return []
    # Spur-Einträge durch "|"
    lane_entries = turn_lanes_str.split("|")
    result = []
    for lane_entry in lane_entries:
        # z. B. "through;right"
        directions = []
        for d in lane_entry.split(";"):
            # Normalisieren slight_left -> left
            if "left" in d:
                directions.append("left")
            elif "right" in d:
                directions.append("right")
            elif "through" in d:
                directions.append("through")
            else:
                # Unbekannte Einträge
                directions.append(d)
        result.append(directions)
    return result


###############################################################################
# 3) AMPELPHASEN PRO (STREET, LANE)
###############################################################################


class TrafficLightPhase:
    def __init__(self, phase=PHASE_RED, time_in_phase=0.0):
        self.phase = phase
        self.time_in_phase = time_in_phase


class TrafficLightController:
    """
    Spur-spezifische Ampeln. Alle Spuren haben standardmäßig denselben
    globalen Phasenzyklus. Man kann es aber erweitern (z. B. separate Gruppen).
    """

    def __init__(self, incoming_spurs: List[Tuple[int, int]]):
        """
        incoming_spurs: Liste aller (street_id, lane_index),
        die zu dieser Intersection führen.
        """
        self.lights: Dict[Tuple[int, int], TrafficLightPhase] = {}
        for sp in incoming_spurs:
            self.lights[sp] = TrafficLightPhase(phase=PHASE_RED, time_in_phase=0.0)

        # Einfach: Alle Spuren gleichzeitig
        self.global_phase = PHASE_RED
        self.time_in_global_phase = 0.0

    def update(self, dt: float):
        self.time_in_global_phase += dt
        duration = PHASE_DURATIONS[self.global_phase]

        if self.time_in_global_phase >= duration:
            self.time_in_global_phase = 0.0
            if self.global_phase == PHASE_GREEN:
                self.global_phase = PHASE_YELLOW
            elif self.global_phase == PHASE_YELLOW:
                self.global_phase = PHASE_RED
            elif self.global_phase == PHASE_RED:
                self.global_phase = PHASE_REDYELLOW
            elif self.global_phase == PHASE_REDYELLOW:
                self.global_phase = PHASE_GREEN

        # Setze diese globale Phase für alle Spuren
        for sp, tl in self.lights.items():
            tl.phase = self.global_phase
            tl.time_in_phase = self.time_in_global_phase

    def is_green_or_yellow(self, street_id: int, lane_index: int) -> bool:
        tl = self.lights.get((street_id, lane_index))
        if not tl:
            # Keine Ampel => treat as green
            return True
        return tl.phase == PHASE_GREEN or tl.phase == PHASE_YELLOW


###############################################################################
# 4) INTERSECTION
###############################################################################


class Intersection:
    """
    Intersection repräsentiert einen Knoten.
    Hat eine TrafficLightController-Instanz (falls incoming Spuren vorhanden).
    """

    def __init__(self, node_id):
        self.id = node_id
        self.traffic_lights: Optional[TrafficLightController] = None

    def set_traffic_lights(self, tl: TrafficLightController):
        self.traffic_lights = tl

    def can_vehicle_enter(self, street_id: int, lane_index: int) -> bool:
        """
        Prüft, ob Ampelphase = Grün/Gelb für (street_id, lane_index).
        """
        if not self.traffic_lights:
            return True
        return self.traffic_lights.is_green_or_yellow(street_id, lane_index)


###############################################################################
# 5) STREET
###############################################################################


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


###############################################################################
# 6) ROUTENPLANUNG (DIJKSTRA)
###############################################################################


def build_adjacency(
    intersections: Dict[str, Intersection], streets: Dict[int, Street], bidir=False
) -> Dict[str, List[Tuple[str, float, int]]]:
    """
    Erzeugt Adjazenz: node_id -> [(neighbor_node, cost, street_id), ...].
    cost = street.length.
    Falls bidir=True => wir tun u->v und v->u.
    """
    adj = {}
    for nid in intersections:
        adj[nid] = []

    for st_id, st in streets.items():
        u = st.start_node
        v = st.end_node
        cost = st.length
        adj[u].append((v, cost, st_id))
        if bidir:
            # Nur wenn die Straße real bidirektional,
            # aber hier abstrahiert => tun wir's immer:
            adj[v].append((u, cost, st_id))

    return adj


def dijkstra_route(
    adj: Dict[str, List[Tuple[str, float, int]]], start_n: str, goal_n: str
) -> List[int]:
    """
    Gibt eine Liste von Street-IDs zurück, die vom Start- zum Ziel-Knoten führen.
    """
    heap = [(0.0, start_n, [])]
    visited = set()
    while heap:
        dist, node, path_st = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        if node == goal_n:
            return path_st
        for nbr, cost, st_id in adj[node]:
            if nbr not in visited:
                new_dist = dist + cost
                new_path = path_st + [st_id]
                heapq.heappush(heap, (new_dist, nbr, new_path))
    return []


###############################################################################
# 7) FAHRZEUG-KLASSE
###############################################################################


class Vehicle:
    """
    Enthält:
      - current_street
      - lane_index
      - position_s
      - route (Liste Street-IDs)
      - reaktionszeit, speed_factor, ...
      - logik, ob turn_dir 'left'/'right' => passendes Spurwechseln,
        aber nur wenn street.lane_dirs[lane_index] das Abbiegen erlaubt.
    """

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

        # Basis-Temp-Limit
        self.base_speed_limit = current_street.speed_limit * self.speed_factor
        self.done = False

    def current_street_id(self) -> int:
        return self.current_street.id if self.current_street else -1

    def update(self, dt: float, leader: Optional["Vehicle"]):
        if self.done:
            return

        dist_to_end = self.current_street.length - self.position_s

        # Kollisionsvermeidung
        desired_accel = self.max_accel
        if leader and leader.current_street_id() == self.current_street_id():
            if leader.lane_index == self.lane_index:
                gap = leader.position_s - self.position_s - 5.0
                if gap < self.speed * self.reaction_time:
                    desired_accel = -self.max_decel

        # Prüfe, ob wir uns auf den nächsten Abbiegevorgang vorbereiten müssen
        turn_dir = self._next_turn_direction()

        # Falls wir abbiegen wollen, checken wir, ob unsere Spur das erlaubt
        # Falls NICHT, versuche Spurwechsel
        if turn_dir and dist_to_end < 50.0:
            # Erlaubt current_street.lane_dirs[self.lane_index] diesen Turn?
            if not self._lane_allows_turn(
                self.current_street, self.lane_index, turn_dir
            ):
                # Versuche Spurwechsel
                # - left => lane_index++ (sofern < num_lanes-1)
                # - right => lane_index-- (sofern > 0)
                if turn_dir == "left":
                    if self.lane_index < self.current_street.num_lanes - 1:
                        self.lane_index += 1
                elif turn_dir == "right":
                    if self.lane_index > 0:
                        self.lane_index -= 1

        # Ampel abfragen
        if dist_to_end < 20.0:
            end_n = self.current_street.end_node
            inter = self.intersections_map.get(end_n)
            if inter:
                if not inter.can_vehicle_enter(self.current_street.id, self.lane_index):
                    desired_accel = -self.max_decel

        # Speed Limit
        street_limit = self.current_street.speed_limit
        final_limit = min(street_limit * self.speed_factor, self.base_speed_limit)

        # Geschwindigkeitsupdate
        new_speed = self.speed + desired_accel * dt
        new_speed = max(0.0, min(new_speed, final_limit))

        # Positionsupdate
        new_pos = self.position_s + new_speed * dt
        if new_pos >= self.current_street.length:
            new_pos = self.current_street.length
            new_speed = 0.0
            # Intersection:
            end_n = self.current_street.end_node
            inter = self.intersections_map.get(end_n)
            if inter:
                # Ampel
                if not inter.can_vehicle_enter(self.current_street.id, self.lane_index):
                    self.speed = 0.0
                    self.position_s = new_pos
                    return
                else:
                    # Street wechseln
                    self.route_index += 1
                    if self.route_index >= len(self.route_streets):
                        self.done = True
                        return
                    next_st_id = self.route_streets[self.route_index]
                    next_st = self.streets_map[next_st_id]

                    # Lane anpassen => wir bleiben in (lane_index oder 0)
                    # aber check, ob lane existiert
                    ln = min(self.lane_index, next_st.num_lanes - 1)

                    self.current_street = next_st
                    self.lane_index = ln
                    self.position_s = 0.0
                    self.speed = 0.0
                    self.base_speed_limit = next_st.speed_limit * self.speed_factor
                    return
            else:
                # kein Intersection => fertig
                self.done = True
        else:
            self.speed = new_speed
            self.position_s = new_pos

    def _next_turn_direction(self) -> Optional[str]:
        """
        Ermittelt, ob der nächste Übergang 'left','right','through' sein könnte.
        Dazu vergleicht man grob die Winkel der current_street und der nächsten Street.
        Hier ist es vereinfacht: wir gucken nur "left" vs "right" vs "through".
        """
        if self.route_index >= len(self.route_streets) - 1:
            return None
        next_st_id = self.route_streets[self.route_index + 1]
        next_st = self.streets_map[next_st_id]
        # Bestimme Vektor am Ende der current_street
        ccoords = self.current_street.coords
        v1 = (ccoords[-1][0] - ccoords[-2][0], ccoords[-1][1] - ccoords[-2][1])
        # Bestimme Vektor am Anfang der next_street
        ncoords = next_st.coords
        v2 = (ncoords[1][0] - ncoords[0][0], ncoords[1][1] - ncoords[0][1])
        a1 = math.atan2(v1[1], v1[0])
        a2 = math.atan2(v2[1], v2[0])
        diff = math.degrees(a2 - a1)
        # Normalisiere auf -180..180
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
        """
        Checkt, ob lane st.lane_dirs[ln] das gegebene 'turn' ('left','right','through') enthält.
        """
        if ln < 0 or ln >= st.num_lanes:
            return False
        # lane_dirs[ln] ist z. B. ['left'] oder ['through','right']
        directions = st.lane_dirs[ln]
        return (
            (turn in directions or "through" in directions)
            if turn == "through"
            else (turn in directions)
        )


###############################################################################
# 8) CLIPPING UND STADTAUFBAU
###############################################################################


def clip_line_at_polygon(
    line: shapely.geometry.LineString, polygon: shapely.geometry.Polygon
) -> Optional[shapely.geometry.LineString]:
    """
    Schneidet eine Linie an polygon zurecht.
    Gibt None zurück, wenn komplett outside.
    """
    inter = line.intersection(polygon)
    if inter.is_empty:
        return None
    if isinstance(inter, shapely.geometry.LineString):
        return inter
    elif isinstance(inter, shapely.geometry.MultiLineString):
        # Nimm das längste Segment
        longest_part = max(inter.geoms, key=lambda g: g.length)
        return longest_part
    elif isinstance(inter, shapely.geometry.GeometryCollection):
        # Filter LineStrings
        lines = [g for g in inter.geoms if isinstance(g, shapely.geometry.LineString)]
        if not lines:
            return None
        longest_part = max(lines, key=lambda g: g.length)
        return longest_part
    return None


# OSMnx Settings: Timeout, Logging einschalten
ox.settings.timeout = 300  # 300 Sekunden Timeout
ox.settings.log_console = True  # Konsolen-Logs (Overpass-Anfragen etc.)
ox.settings.use_cache = True  # Ergebnisse lokal cachen, beschleunigt Folgeläufe


def build_city_graph(
    place_name: str, dist_m=2000
) -> Tuple[Dict[str, "Intersection"], Dict[int, "Street"]]:
    """
    Lädt einen Ausschnitt (Umkreis dist_m) rund um 'place_name' mit OSMnx,
    projiziert das Ganze, clippt es an einen Kreis-Puffer und erzeugt
    unsere Intersection-/Street-Struktur.

    Wichtige Änderungen:
    - Kein Alexanderplatz-Fallback mehr
    - Falls place_name ein (Multi)Polygon liefert, wird der centroid genommen
    - Logging, Timeout, Cache sind aktiv
    """

    print(f"[build_city_graph] Starte für: {place_name}, dist_m={dist_m} m")

    # 1) Geometrie via geocode_to_gdf
    print("[build_city_graph] Ermittele Geometrie via ox.geocode_to_gdf...")
    center_gdf = ox.geocode_to_gdf(place_name)

    if center_gdf.empty:
        print(
            f"[build_city_graph] WARNUNG: Kein Ergebnis für place_name='{place_name}'!"
        )
        return {}, {}

    geom = center_gdf.geometry.iloc[0]
    print(f"  -> Geometrie: {geom}, Typ={geom.geom_type}")

    # (A) Falls kein Point => centroid
    if geom.geom_type != "Point":
        print(
            f"[build_city_graph] '{place_name}' ist kein Point (Typ={geom.geom_type}). Nehme den Centroid."
        )
        geom = geom.centroid
        print(f"  -> Neuer Mittelpunkt: {geom}, Typ={geom.geom_type}")

    # 2) Kreis-Puffer
    center_point = geom
    boundary_polygon = center_point.buffer(dist_m)
    if not boundary_polygon.is_valid:
        print("[build_city_graph] FEHLER: boundary_polygon ist ungültig.")
        return {}, {}
    print(f"  -> boundary_polygon Fläche={boundary_polygon.area:.2f} m^2")

    bigger_polygon = boundary_polygon.buffer(
        500.0
    )  # etwas größer, damit Randstraßen nicht fehlen
    print(f"  -> bigger_polygon Fläche={bigger_polygon.area:.2f} m^2")

    # 3) Graph laden
    print("[build_city_graph] Starte ox.graph_from_polygon(...)")
    start_t = time.time()
    try:
        G = ox.graph_from_polygon(
            polygon=bigger_polygon, simplify=False, network_type="drive"
        )
    except Exception as e:
        print(f"[build_city_graph] FEHLER bei graph_from_polygon: {e}")
        return {}, {}
    duration = time.time() - start_t
    print(f"[build_city_graph] graph_from_polygon fertig nach {duration:.2f} s.")

    if not G or len(G.nodes) == 0:
        print("[build_city_graph] WARNUNG: Graph ist leer (keine Nodes).")
        return {}, {}

    # 4) Projektion in Meter
    print("[build_city_graph] Projiziere Graph mit ox.project_graph...")
    G = ox.project_graph(G)
    print(f"  -> Projektierter Graph: #Nodes={len(G.nodes)}, #Edges={len(G.edges)}")

    # --- Ab hier wie gehabt ---
    # Intersection- und Street-Klassen müssten vorher definiert sein
    # (oder du importierst sie in dieses Modul).

    # 5) Knoten im boundary_polygon halten
    node_dict: Dict[str, Tuple[float, float]] = {}
    kept_nodes = 0
    for node, data in G.nodes(data=True):
        x = data["x"]
        y = data["y"]
        pt = shapely.geometry.Point(x, y)
        if boundary_polygon.contains(pt):
            node_dict[str(node)] = (x, y)
            kept_nodes += 1
    print(f"  -> {kept_nodes} Knoten innerhalb dist_m={dist_m} beibehalten.")

    # 6) Kanten clippen und Street-Objekte bauen
    streets_map: Dict[int, "Street"] = {}
    street_id_counter = 1
    edges_used = 0

    print(
        f"[build_city_graph] Durchsuche {len(G.edges)} Kanten, clippe an boundary_polygon..."
    )
    for u, v, key, edata in G.edges(keys=True, data=True):
        geom_line = edata.get("geometry", None)
        if geom_line is None:
            x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
            x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]
            geom_line = shapely.geometry.LineString([(x1, y1), (x2, y2)])

        clipped = clip_line_at_polygon(geom_line, boundary_polygon)
        if not clipped:
            continue
        edges_used += 1

        maxspeed = edata.get("maxspeed", "50")
        if isinstance(maxspeed, list):
            maxspeed = maxspeed[0]
        try:
            ms_val = float(maxspeed)
        except:
            ms_val = 50.0
        speed_limit = ms_val / 3.6

        tlanes = edata.get("turn:lanes", "")
        if isinstance(tlanes, list):
            tlanes = tlanes[0]

        lanes_tag = edata.get("lanes", 1)
        try:
            lanes_tag = int(lanes_tag)
        except:
            lanes_tag = 1

        parsed = parse_turn_lanes(tlanes)
        nlanes = max(lanes_tag, len(parsed))
        while len(parsed) < nlanes:
            parsed.append(["through"])

        coords_list = list(clipped.coords)
        x_u, y_u = coords_list[0]
        x_v, y_v = coords_list[-1]

        su = str(u)
        if not boundary_polygon.contains(shapely.geometry.Point(x_u, y_u)):
            su = f"pseudo_{u}_{v}_start_{street_id_counter}"

        sv = str(v)
        if not boundary_polygon.contains(shapely.geometry.Point(x_v, y_v)):
            sv = f"pseudo_{v}_{u}_end_{street_id_counter}"

        # pseudo-Knoten ggf. eintragen
        if su not in node_dict:
            node_dict[su] = (x_u, y_u)
        if sv not in node_dict:
            node_dict[sv] = (x_v, y_v)

        # Street-Objekt anlegen
        st = Street(
            st_id=street_id_counter,
            start_node=su,
            end_node=sv,
            coords=coords_list,
            speed_limit=speed_limit,
            lane_dirs=parsed,
        )
        streets_map[street_id_counter] = st
        street_id_counter += 1

        # Bidirektionale Kante?
        oneway = edata.get("oneway", False)
        if oneway in [False, "False", 0, "0"]:
            rev_coords = list(reversed(coords_list))
            st2 = Street(
                st_id=street_id_counter,
                start_node=sv,
                end_node=su,
                coords=rev_coords,
                speed_limit=speed_limit,
                lane_dirs=parsed,
            )
            streets_map[street_id_counter] = st2
            street_id_counter += 1

    print(f"  -> {edges_used} Kanten erfolgreich geclippt/übernommen.")

    # 7) Intersection-Objekte
    intersection_map: Dict[str, "Intersection"] = {}
    for nid, (xx, yy) in node_dict.items():
        intersection_map[nid] = Intersection(nid)

    # Ampeln anlegen
    in_spurs: Dict[str, List[Tuple[int, int]]] = {}
    for st_id, st_obj in streets_map.items():
        end_n = st_obj.end_node
        if end_n not in in_spurs:
            in_spurs[end_n] = []
        for ln in range(st_obj.num_lanes):
            in_spurs[end_n].append((st_id, ln))

    for n_id, inter in intersection_map.items():
        if n_id in in_spurs:
            inc = in_spurs[n_id]
            tl = TrafficLightController(inc)
            inter.set_traffic_lights(tl)

    print(
        "[build_city_graph] Fertig. Intersections:",
        len(intersection_map),
        "Streets:",
        len(streets_map),
    )
    return intersection_map, streets_map


###############################################################################
# 9) SIMULATOR
###############################################################################


class Simulator:
    def __init__(self, place_name: str, dist_m=5000):
        # 1) Baue City Graph
        self.intersections, self.streets = build_city_graph(place_name, dist_m)
        # 2) adjacency
        self.adjacency = build_adjacency(self.intersections, self.streets, bidir=False)

        # 3) Finde Randknoten (Spawn)
        self.spawn_nodes = self._find_boundary_nodes()

        # Liste Fahrzeuge
        self.vehicles: List[Vehicle] = []
        self.next_vid = 1000

    def _find_boundary_nodes(self) -> List[str]:
        """
        Wähle Knoten, die potenziell am Rand sind (out_degree=1 in adjacency).
        """
        boundary = []
        for node, edges in self.adjacency.items():
            if len(edges) <= 1:
                boundary.append(node)
        return boundary

    def update_traffic_lights(self, dt: float):
        for inter in self.intersections.values():
            if inter.traffic_lights:
                inter.traffic_lights.update(dt)

    def spawn_vehicle(self):
        if not self.spawn_nodes:
            return
        start_n = random.choice(self.spawn_nodes)
        goal_n = random.choice(self.spawn_nodes)
        while goal_n == start_n:
            goal_n = random.choice(self.spawn_nodes)
        route_st = dijkstra_route(self.adjacency, start_n, goal_n)
        if not route_st:
            return
        # Hole die erste Street
        first_st_id = route_st[0]
        st_obj = self.streets[first_st_id]
        # Lane
        lane_idx = random.randint(0, st_obj.num_lanes - 1)
        # Profile
        prof = random.choice(list(VEHICLE_PROFILES.keys()))
        v = Vehicle(
            vehicle_id=self.next_vid,
            profile=prof,
            current_street=st_obj,
            lane_index=lane_idx,
            route_streets=route_st,
            streets_map=self.streets,
            intersections_map=self.intersections,
        )
        self.next_vid += 1
        self.vehicles.append(v)

    def step(self, dt: float):
        # 1) Ampeln
        self.update_traffic_lights(dt)

        # 2) Pro (street, lane) => sort vehicles
        street_lane_map: Dict[Tuple[int, int], List[Vehicle]] = {}
        for v in self.vehicles:
            key = (v.current_street_id(), v.lane_index)
            if key not in street_lane_map:
                street_lane_map[key] = []
            street_lane_map[key].append(v)

        for key, vlist in street_lane_map.items():
            vlist.sort(key=lambda x: x.position_s)
            for i, veh in enumerate(vlist):
                leader = vlist[i - 1] if i > 0 else None
                veh.update(dt, leader)

        # 3) Entferne fertige
        before = len(self.vehicles)
        self.vehicles = [v for v in self.vehicles if not v.done]
        after = len(self.vehicles)

        # 4) Optional: spawn bei vielen entfernten
        removed = before - after
        for _ in range(removed):
            if random.random() < 0.7:
                self.spawn_vehicle()

    def run(self, steps=100, dt=1.0):
        # initial spawn
        for _ in range(10):
            self.spawn_vehicle()

        for step in range(steps):
            self.step(dt)
            if step % 10 == 0:
                print(f"Step {step} -> #Vehicles={len(self.vehicles)}")


###############################################################################
# 10) HAUPTPROGRAMM
###############################################################################
if __name__ == "__main__":
    place = "Berlin, Germany"  # Beispiel-Stadt
    dist_km = 5
    print(f"Erstelle clipped City-Graph für {place}, Umkreis {dist_km} km ...")
    sim = Simulator(place_name=place, dist_m=dist_km * 10)

    print("Starte Simulation (50 Schritte, dt=1.0s)...")

    sim.run(steps=50, dt=1.0)
    print(f"Fertig. {len(sim.vehicles)} Fahrzeuge verbleiben im System.")
