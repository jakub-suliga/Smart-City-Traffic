import random
import math
import heapq
import time
import logging
import osmnx as ox
import networkx as nx
import shapely
import shapely.geometry
import shapely.ops

from typing import Dict, List, Tuple, Optional

from .TrafficLight import TrafficLightController
from .intersection import Intersection
from .street import Street
from .vehicle import VEHICLE_PROFILES, Vehicle


class Simulator:
    ox.settings.timeout = 300
    ox.settings.log_console = True
    ox.settings.use_cache = True

    def __init__(self, place_name: str, dist_m=5000):
        # 1) Baue City Graph
        self.intersections, self.streets = self.build_city_graph(dist_m)
        # 2) adjacency
        self.adjacency = self.build_adjacency(
            self.intersections, self.streets, bidir=False
        )

        # 3) Finde Randknoten (Spawn)
        self.spawn_nodes = self._find_boundary_nodes()

        # Liste Fahrzeuge
        self.vehicles: List[Vehicle] = []
        self.next_vid = 1000

    def dijkstra_route(
        self, adj: Dict[str, List[Tuple[str, float, int]]], start_n: str, goal_n: str
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
        route_st = self.dijkstra_route(self.adjacency, start_n, goal_n)
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

    def build_adjacency(
        self,
        intersections: Dict[str, Intersection],
        streets: Dict[int, Street],
        bidir=False,
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

    def build_city_graph(
        self,
        dist_m: float = 2000,
    ) -> Tuple[Dict[str, "Intersection"], Dict[int, "Street"]]:
        """
        Lädt einen Ausschnitt (Umkreis dist_m) rund um feste Koordinaten in Berlin
        und erzeugt daraus Intersection-/Street-Objekte (mit turn:lanes, Ampeln etc.).

        1) Nutzt `ox.graph_from_point`, anstatt geocode_to_gdf.
        2) Projiziert den Graph in Meter-Koordinaten.
        3) Liest Knoten und Kanten aus und baut:
        - Intersection-Objekte (einfache Knoten)
        - Street-Objekte (Kanten)
        - Ampeln, falls 'turn:lanes' oder 'lanes' existieren.
        4) Gibt intersection_map, streets_map zurück.
        """

        # 1) Feste Koordinaten für Berlin-Mitte, z.B. Brandenburger Tor
        berlin_lat = 52.52
        berlin_lon = 13.405

        print(
            f"[build_city_graph] Lade Graph für Berlin-Koords ({berlin_lat}, {berlin_lon}), dist={dist_m} m"
        )

        # 2) Laden via graph_from_point
        G = ox.graph_from_point(
            center_point=(berlin_lat, berlin_lon),
            dist=dist_m,
            dist_type="bbox",  # oder 'network'
            simplify=False,
            network_type="drive",
        )
        print(f"   -> Geladener Graph: #Nodes={len(G.nodes)}, #Edges={len(G.edges)}")

        # 3) Projektion
        print("[build_city_graph] Projiziere Graph mit ox.project_graph...")
        G = ox.project_graph(G)
        print(
            f"   -> Projektierter Graph: #Nodes={len(G.nodes)}, #Edges={len(G.edges)}"
        )

        # Jetzt bauen wir unsere Strukturen:
        intersection_map: Dict[str, "Intersection"] = {}
        streets_map: Dict[int, "Street"] = {}

        # 4) Alle Knoten in Intersection-Objekte fassen
        for node_id, data in G.nodes(data=True):
            # node_id ist meist eine Zahl, wir machen zur Sicherheit einen String draus
            str_id = str(node_id)
            # Intersection ist eine einfache Klasse, die nur 'id' speichert und ggf. Ampel
            intersection_map[str_id] = Intersection(str_id)

        # 5) Alle Kanten auswerten
        street_id_counter = 1
        for u, v, key, edata in G.edges(keys=True, data=True):
            # Koordinaten der Polylinie (falls geometry fehlt, nur direkter Start->End)
            geom_line = edata.get("geometry", None)
            if geom_line is None:
                x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
                x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]
                geom_line = shapely.geometry.LineString([(x1, y1), (x2, y2)])

            coords_list = list(geom_line.coords)

            # Geschwindigkeitslimit
            maxspeed = edata.get("maxspeed", "50")
            if isinstance(maxspeed, list):
                maxspeed = maxspeed[0]
            try:
                ms_val = float(maxspeed)
            except:
                ms_val = 50.0
            speed_limit = ms_val / 3.6  # km/h -> m/s

            # turn:lanes
            tlanes = edata.get("turn:lanes", "")
            if isinstance(tlanes, list):
                tlanes = tlanes[0]

            # lanes
            lanes_tag = edata.get("lanes", 1)
            try:
                lanes_tag = int(lanes_tag)
            except:
                lanes_tag = 1

            parsed = self.parse_turn_lanes(tlanes)
            nlanes = max(lanes_tag, len(parsed))
            # Wenn turn:lanes weniger Spuren angibt als "lanes", füllen wir 'through' auf:
            while len(parsed) < nlanes:
                parsed.append(["through"])

            # Street-Objekt anlegen
            str_u = str(u)
            str_v = str(v)

            st = Street(
                st_id=street_id_counter,
                start_node=str_u,
                end_node=str_v,
                coords=coords_list,
                speed_limit=speed_limit,
                lane_dirs=parsed,
            )
            streets_map[street_id_counter] = st
            street_id_counter += 1

            # Prüfen, ob die Straße bidirektional ist
            oneway = edata.get("oneway", False)
            # Falls oneway == False (oder "False", "0"), legen wir eine Rückrichtung an
            if oneway in [False, "False", 0, "0"]:
                rev_coords = list(reversed(coords_list))
                st2 = Street(
                    st_id=street_id_counter,
                    start_node=str_v,
                    end_node=str_u,
                    coords=rev_coords,
                    speed_limit=speed_limit,
                    lane_dirs=parsed,  # gleiche Spur-Infos
                )
                streets_map[street_id_counter] = st2
                street_id_counter += 1

        # 6) Ampeln an den Knoten anlegen
        # Dazu sammeln wir: pro Node => Liste aller (street_id, lane_index),
        # die dort enden.
        in_spurs: Dict[str, List[Tuple[int, int]]] = {}
        for st_id, st_obj in streets_map.items():
            end_n = st_obj.end_node
            if end_n not in in_spurs:
                in_spurs[end_n] = []
            for ln in range(st_obj.num_lanes):
                in_spurs[end_n].append((st_id, ln))

        # Für jeden Knoten (Intersection) schauen wir, ob er eingehende Spuren hat
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

    def parse_turn_lanes(self, turn_lanes_str: str) -> List[List[str]]:
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
