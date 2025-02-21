import matplotlib.pyplot as plt
import matplotlib.animation as animation
import shapely.geometry

# Aus deinem lokalen Paket:
from ..simulation import Simulator


def position_on_street(street, s):
    """
    Liefert (x, y) als Interpolation auf der Street-Poly-Linie
    für die Distanz s (Position auf der Street in Metern).
    """
    linestr = shapely.geometry.LineString(street.coords)
    point = linestr.interpolate(s)
    return point.x, point.y


def main():
    # Erzeuge eine Simulator-Instanz
    # place_name = "Berlin, Germany" und dist_m = 5000 als Beispiel
    sim = Simulator(place_name="Berlin, Germany", dist_m=500)

    # Starte initial ein paar Fahrzeuge
    for _ in range(30):
        sim.spawn_vehicle()

    # Erstelle eine Matplotlib-Figur
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title("Verkehrs-Simulation")
    ax.set_xlabel("x-Koordinate (Proj.)")
    ax.set_ylabel("y-Koordinate (Proj.)")

    # 1) Zeichne alle Straßen als Linien
    for st_id, st in sim.streets.items():
        x_vals = [p[0] for p in st.coords]
        y_vals = [p[1] for p in st.coords]
        ax.plot(x_vals, y_vals, color="gray", linewidth=1)

    # 2) Vorbereitung für die Fahrzeug-Punkte
    # Wir legen einmal ein Scatter-Objekt an, das pro Frame aktualisiert wird
    vehicle_scatter = ax.scatter([], [], c="red", s=20, label="Fahrzeuge")

    # Optional: Legende aktivieren
    ax.legend()

    def init():
        """
        Initialisierungsfunktion für FuncAnimation.
        Hier könnten wir die Achsen-Grenzen festlegen.
        """
        # Passe x-/y-Bereiche an, z.B. aus allen Street-Koordinaten
        all_x = []
        all_y = []
        for st in sim.streets.values():
            for x, y in st.coords:
                all_x.append(x)
                all_y.append(y)
        if all_x and all_y:
            margin = 100  # etwas Luft an den Rändern
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

        # Einen Simulationsschritt (z. B. dt=1.0s)
        sim.step(dt=1.0)

        # Positionen aller Fahrzeuge sammeln
        xs = []
        ys = []
        for v in sim.vehicles:
            st = v.current_street
            x, y = position_on_street(st, v.position_s)
            xs.append(x)
            ys.append(y)

        # In den Scatter "einspielen"
        vehicle_scatter.set_offsets(list(zip(xs, ys)))

        return (vehicle_scatter,)

    # Matplotlib-Animation erstellen
    # frames=200 => 200 Schritte, interval=200 => 200ms pro Frame
    ani = animation.FuncAnimation(
        fig, update, frames=200, init_func=init, interval=200, blit=True
    )

    plt.show()


if __name__ == "__main__":
    main()
