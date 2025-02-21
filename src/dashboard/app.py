import matplotlib.pyplot as plt
import matplotlib.animation as animation
import shapely.geometry
import mplcursors  # <-- Wichtig, installiere mit `pip install mplcursors`

# Aus deinem lokalen Paket (ggf. Pfad anpassen):
from ..simulation import Simulator


def position_on_street(street, s):
    """
    Liefert (x, y) als Interpolation auf der Street-Polylinie
    für die Distanz s (Position auf der Street in Metern).
    """
    linestr = shapely.geometry.LineString(street.coords)
    point = linestr.interpolate(s)
    return point.x, point.y


def main():
    # 1) Erzeuge eine Simulator-Instanz
    sim = Simulator(place_name="Berlin, Germany", dist_m=500)

    # Starte initial ein paar Fahrzeuge
    for _ in range(30):
        sim.spawn_vehicle()

    # 2) Erstelle eine Matplotlib-Figur
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title("Verkehrs-Simulation (interaktiv)")
    ax.set_xlabel("x-Koordinate (Proj.)")
    ax.set_ylabel("y-Koordinate (Proj.)")

    # 3) Zeichne alle Straßen als Linien (grau)
    for st_id, st in sim.streets.items():
        x_vals = [p[0] for p in st.coords]
        y_vals = [p[1] for p in st.coords]
        ax.plot(x_vals, y_vals, color="gray", linewidth=1)

    # 4) Zeichne alle Intersections als Marker (grün)
    intersection_x = []
    intersection_y = []
    for node_id, inter in sim.intersections.items():
        intersection_x.append(inter.x_coord)
        intersection_y.append(inter.y_coord)
    intersections_scatter = ax.scatter(
        intersection_x,
        intersection_y,
        c="green",
        s=40,
        marker="x",
        label="Intersections",
    )

    # 5) Vorbereitung für die Fahrzeug-Punkte (rot)
    vehicle_scatter = ax.scatter([], [], c="red", s=20, label="Fahrzeuge")

    # Optional: Legende
    ax.legend()

    # (A) Globale Liste oder Dict, um Mapping "Index -> Fahrzeug" zu haben
    # Da Matplotlibs scatter per default "index" = Reihenfolge in set_offsets.
    # => Wir speichern pro Frame die IDs.
    vehicle_ids = []

    # (B) Für die Routenanzeige brauchen wir eine "aktuelle Route-Linie"
    current_route_line = None

    def init():
        """
        Initialisierungsfunktion für FuncAnimation.
        Setzt Achsen-Grenzen usw.
        """
        all_x = []
        all_y = []
        for st in sim.streets.values():
            for xx, yy in st.coords:
                all_x.append(xx)
                all_y.append(yy)

        # Falls wir Koordinaten haben, Achsenlimit setzen
        if all_x and all_y:
            margin = 100
            ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
            ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

        return (vehicle_scatter,)

    def update(frame):
        """
        Update-Funktion pro Frame:
        - Einen Zeitschritt simulieren
        - Alle Fahrzeugpositionen updaten
        - Scatter-Punkte aktualisieren
        """
        sim.step(dt=1.0)

        # Positionen aller Fahrzeuge sammeln
        xs = []
        ys = []
        # Leeren wir "vehicle_ids", füllen neu
        vehicle_ids.clear()

        for v in sim.vehicles:
            st = v.current_street
            x, y = position_on_street(st, v.position_s)
            xs.append(x)
            ys.append(y)
            vehicle_ids.append(v.vehicle_id)  # ID merken

        # In den Scatter "einspielen"
        vehicle_scatter.set_offsets(list(zip(xs, ys)))

        return (vehicle_scatter,)

    # 6) Interaktive Hover-Funktionalität mit mplcursors
    cursor = mplcursors.cursor(vehicle_scatter, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        nonlocal current_route_line  # Wir ändern den im äußeren Scope

        idx = sel.index  # Index in der aktuellen Scatter-Reihenfolge
        veh_id = vehicle_ids[idx] if idx < len(vehicle_ids) else None

        # Passendes Vehicle-Objekt holen
        v_obj = None
        for v in sim.vehicles:
            if v.vehicle_id == veh_id:
                v_obj = v
                break

        if v_obj is None:
            sel.annotation.set_text("Unbekanntes Fahrzeug")
            return

        # Tooltip-Text: ID, Geschwindigkeit, ggf. Ampelstatus etc.
        txt = f"Fahrzeug-ID: {v_obj.vehicle_id}\nSpeed: {v_obj.speed:.2f} m/s"
        sel.annotation.set_text(txt)

        # (Optional) Route-Linie einzeichnen
        # Zuerst alte Linie entfernen (falls noch vorhanden)
        if current_route_line is not None:
            current_route_line.remove()
            current_route_line = None

        # Sammle alle Koordinaten auf der Route
        route_xs = []
        route_ys = []
        for st_id in v_obj.route_streets:
            st_obj = sim.streets[st_id]
            route_xs += [p[0] for p in st_obj.coords]
            route_ys += [p[1] for p in st_obj.coords]

        # Zeichne Route als blaue Linie
        (current_route_line,) = ax.plot(route_xs, route_ys, color="blue", linewidth=2)

    @cursor.connect("remove")
    def on_remove(sel):
        # Beim Verlassen (unhover) die Route-Linie wieder entfernen
        nonlocal current_route_line
        if current_route_line is not None:
            current_route_line.remove()
            current_route_line = None

    # 7) Matplotlib-Animation erstellen
    ani = animation.FuncAnimation(
        fig, update, frames=200, init_func=init, interval=200, blit=True
    )

    plt.show()


if __name__ == "__main__":
    main()
