import osmnx as ox
import networkx as nx

from typing import Dict, List, Tuple

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
