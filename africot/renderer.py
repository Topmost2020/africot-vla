"""Top-down junction image (SPEC 5.9). Stands in for a camera keyframe.

`snapshot(env)` captures what is needed from SUMO (vehicle and pedestrian
positions, signal state); `render(snap, path)` draws a 512x512 PNG with road
outlines, crosswalks, vehicles as shapes coloured by class, waiting
pedestrians as dots, the current signal state and a legend.
"""
import math
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

from africot import signals  # noqa: E402

CLASS_COLOURS = {"car": "#7f7f7f", "danfo": "#f2b705", "keke": "#2ca02c", "okada": "#d62728"}
VIEW_HALF = 90.0  # metres shown either side of the junction centre
SIGNAL_COLOURS = {"G": "#2ca02c", "g": "#98df8a", "y": "#ffbf00", "r": "#d62728"}

_GEOM = None


def _geometry():
    """Lane and crossing polygons plus junction centre from the network file."""
    global _GEOM
    if _GEOM is None:
        root = ET.parse(signals.NET_FILE).getroot()
        lanes, crossings, walks = [], [], []
        for e in root.findall("edge"):
            fn = e.get("function")
            for lane in e.findall("lane"):
                pts = [tuple(map(float, p.split(","))) for p in lane.get("shape").split()]
                width = float(lane.get("width", 3.2))
                if fn == "crossing":
                    crossings.append((pts, width))
                elif fn == "walkingarea":
                    walks.append(pts)
                elif fn is None:
                    lanes.append((pts, width, lane.get("allow") == "pedestrian"))
        junction = next(j for j in root.findall("junction") if j.get("id") == signals.TLS_ID)
        jshape = [tuple(map(float, p.split(","))) for p in junction.get("shape").split()]
        centre = (float(junction.get("x")), float(junction.get("y")))
        _GEOM = {"lanes": lanes, "crossings": crossings, "walks": walks, "junction": jshape,
                 "centre": centre}
    return _GEOM


def snapshot(env):
    """Capture positions and signals from a running JunctionEnv."""
    c = env.conn
    vehicles = []
    for v in c.vehicle.getIDList():
        x, y = c.vehicle.getPosition(v)
        vehicles.append({"x": x, "y": y, "angle": c.vehicle.getAngle(v), "type": c.vehicle.getTypeID(v),
                         "length": c.vehicle.getLength(v), "width": c.vehicle.getWidth(v)})
    peds = []
    for p in c.person.getIDList():
        x, y = c.person.getPosition(p)
        peds.append({"x": x, "y": y, "waiting": c.person.getSpeed(p) < 0.1})
    return {"time": env.time, "phase": env.phase, "signal": env.signal,
            "state": env.current_state_string(), "links": env.links,
            "vehicles": vehicles, "pedestrians": peds}


def _rect(x, y, angle_deg, length, width):
    """Vehicle footprint; SUMO position is the front bumper, angle 0 = north, clockwise."""
    a = math.radians(angle_deg)
    dx, dy = math.sin(a), math.cos(a)        # heading
    px, py = dy, -dx                          # right-hand normal
    bx, by = x - dx * length, y - dy * length  # rear centre
    hw = width / 2
    return [(x + px * hw, y + py * hw), (x - px * hw, y - py * hw),
            (bx - px * hw, by - py * hw), (bx + px * hw, by + py * hw)]


def render(snap, path, size_px=512):
    g = _geometry()
    cx, cy = g["centre"]
    dpi = 128
    fig = plt.figure(figsize=(size_px / dpi, size_px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(cx - VIEW_HALF, cx + VIEW_HALF)
    ax.set_ylim(cy - VIEW_HALF, cy + VIEW_HALF)
    ax.set_aspect("equal")
    ax.axis("off")
    # metres to points, so line widths match lane widths
    m2pt = (size_px / (2 * VIEW_HALF)) * 72.0 / dpi
    ax.add_patch(Rectangle((cx - VIEW_HALF, cy - VIEW_HALF), 2 * VIEW_HALF, 2 * VIEW_HALF,
                           color="#dfe8d8", zorder=0))
    for pts, width, sidewalk in g["lanes"]:
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color="#c8c8c8" if sidewalk else "#4a4a4a", linewidth=width * m2pt,
                solid_capstyle="butt", zorder=1)
    for pts in g["walks"]:
        if len(pts) >= 3:
            ax.add_patch(Polygon(pts, closed=True, color="#c8c8c8", zorder=1))
    ax.add_patch(Polygon(g["junction"], closed=True, color="#4a4a4a", zorder=1))
    for pts, width in g["crossings"]:
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color="white", linewidth=width * m2pt, linestyle=(0, (0.12, 0.12)),
                solid_capstyle="butt", zorder=2)
    for v in snap["vehicles"]:
        col = CLASS_COLOURS.get(v["type"], "#9467bd")
        ax.add_patch(Polygon(_rect(v["x"], v["y"], v["angle"], v["length"], v["width"]), closed=True,
                             facecolor=col, edgecolor="black", linewidth=0.3, zorder=3))
    wx = [p["x"] for p in snap["pedestrians"] if p["waiting"]]
    wy = [p["y"] for p in snap["pedestrians"] if p["waiting"]]
    ax.scatter(wx, wy, s=9, color="#1f77b4", edgecolor="black", linewidth=0.3, zorder=4)
    # signal state panel: one lamp per movement
    strength = {"G": 3, "g": 2, "y": 1, "r": 0}
    greens = {}
    for idx, mov in snap["links"].items():
        ch = snap["state"][idx]
        if strength.get(ch, 0) >= strength.get(greens.get(mov, "r"), 0):
            greens[mov] = ch
    movs = ["WE", "WS", "EW", "ES", "SE", "SW", "xE", "xW", "xS"]
    x0, y0 = cx - VIEW_HALF + 4, cy + VIEW_HALF - 8
    ax.text(x0, y0 + 3.5, f"t={snap['time']:.0f}s  phase {snap['phase']} ({snap['signal']})",
            fontsize=6, zorder=6, family="serif")
    for i, m in enumerate(movs):
        ch = greens.get(m, "r")
        ax.add_patch(Rectangle((x0 + i * 9, y0 - 5), 7.5, 4.5, color=SIGNAL_COLOURS.get(ch, "#d62728"), zorder=6))
        ax.text(x0 + i * 9 + 0.6, y0 - 4.2, m, fontsize=4.5, zorder=7, family="serif")
    # legend
    lx, ly = cx + VIEW_HALF - 42, cy - VIEW_HALF + 4
    items = list(CLASS_COLOURS.items()) + [("waiting pedestrian", "#1f77b4")]
    ax.add_patch(Rectangle((lx - 2, ly - 2), 42, 6 * len(items) + 2, color="white", alpha=0.85, zorder=5))
    for i, (name, col) in enumerate(items):
        yy = ly + i * 6
        if name == "waiting pedestrian":
            ax.scatter([lx + 2], [yy + 1.5], s=9, color=col, edgecolor="black", linewidth=0.3, zorder=6)
        else:
            ax.add_patch(Rectangle((lx, yy), 4, 3, color=col, zorder=6))
        ax.text(lx + 6, yy + 0.3, name, fontsize=5, zorder=6, family="serif")
    for label, (ox, oy) in (("west", (-VIEW_HALF + 4, -14)), ("east", (VIEW_HALF - 16, -14)),
                            ("south", (6, -VIEW_HALF + 4))):
        ax.text(cx + ox, cy + oy, label, fontsize=6, zorder=6, family="serif")
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path
