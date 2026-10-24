"""Signal phases of the T-junction, built from the link indices in junction.net.xml.

Movements (right-hand traffic):
    WE  W->E through        WS  W->S right
    EW  E->W through        ES  E->S left
    SE  S->E right          SW  S->W left
Pedestrian crossings: xE (east arm), xW (west arm), xS (south arm).

Phases (SPEC 4):
    A main road: WE, WS, EW green; ES permissive (yields). Pedestrians cross south arm.
    B east protected left: ES, EW green. No pedestrians.
    C side road: SE, SW green. Pedestrians cross east and west arms.
Turning vehicles whose path crosses a green crosswalk get 'g' (yield to pedestrians).
"""
import os
import xml.etree.ElementTree as ET

SIM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim")
NET_FILE = os.path.join(SIM_DIR, "junction.net.xml")
TLS_ID = "C"

PHASES = ("A", "B", "C")
AMBER_S = 3
ALL_RED_S = 2

EDGE_TO_ARM_IN = {"W2C": "W", "E2C": "E", "S2C": "S"}
EDGE_TO_ARM_OUT = {"C2W": "W", "C2E": "E", "C2S": "S"}
CROSSING_ARM = {frozenset({"C2E", "E2C"}): "xE", frozenset({"C2W", "W2C"}): "xW",
                frozenset({"C2S", "S2C"}): "xS"}

# Signal per movement in each green phase. Missing movement means red.
PHASE_SIGNALS = {
    "A": {"WE": "G", "WS": "g", "EW": "G", "ES": "g", "xS": "G"},
    "B": {"ES": "G", "EW": "G"},
    "C": {"SE": "g", "SW": "g", "xE": "G", "xW": "G"},
}

# Movements each phase serves, by approach (used by baselines and perception).
PHASE_APPROACHES = {"A": ("west", "east"), "B": ("east",), "C": ("south",)}
PHASE_MOVEMENTS = {p: tuple(m for m in sig if not m.startswith("x")) for p, sig in PHASE_SIGNALS.items()}
PHASE_CROSSINGS = {p: tuple(m for m in sig if m.startswith("x")) for p, sig in PHASE_SIGNALS.items()}

# Movements each phase serves with right of way (permissive E->S in A is not counted).
PHASE_SERVED = {"A": ("WE", "WS", "EW"), "B": ("ES", "EW"), "C": ("SE", "SW")}

# Geometric conflicts between movements (vehicle-vehicle and vehicle-crossing).
VEHICLE_CONFLICTS = {
    frozenset({"WE", "ES"}), frozenset({"WE", "SW"}), frozenset({"WE", "SE"}),
    frozenset({"WS", "ES"}), frozenset({"EW", "SW"}),
    frozenset({"ES", "SE"}), frozenset({"ES", "SW"}),
}
CROSSING_CONFLICTS = {
    "xS": {"WS", "ES", "SE", "SW"},
    "xE": {"WE", "SE", "EW", "ES"},
    "xW": {"EW", "SW", "WE", "WS"},
}
# Permissive pairs allowed together if the first one shows lowercase 'g' (yields).
PERMISSIVE = {("ES", "WE"), ("ES", "WS")}


def load_links(net_file=NET_FILE):
    """Return {link_index: movement name} for the junction's traffic light."""
    root = ET.parse(net_file).getroot()
    crossings = {}
    for edge in root.findall("edge"):
        if edge.get("function") == "crossing":
            crossings[edge.get("id")] = CROSSING_ARM[frozenset(edge.get("crossingEdges").split())]
    links = {}
    for c in root.findall("connection"):
        if c.get("tl") != TLS_ID:
            continue
        idx = int(c.get("linkIndex"))
        frm, to = c.get("from"), c.get("to")
        if to in crossings:
            links[idx] = crossings[to]
        elif frm in EDGE_TO_ARM_IN:
            links[idx] = EDGE_TO_ARM_IN[frm] + EDGE_TO_ARM_OUT[to]
        else:
            raise ValueError(f"unexpected tl connection {frm}->{to}")
        if c.get("linkIndex2") is not None:
            links[int(c.get("linkIndex2"))] = links[idx]
    return links


def build_states(net_file=NET_FILE):
    """Signal state strings: green[p], amber[p] (leaving p), and all_red."""
    links = load_links(net_file)
    n = max(links) + 1
    green, amber = {}, {}
    for p, sig in PHASE_SIGNALS.items():
        g = ["r"] * n
        for idx, mov in links.items():
            g[idx] = sig.get(mov, "r")
        green[p] = "".join(g)
        amber[p] = "".join("y" if ch in "Gg" else "r" for ch in g)
    return {"green": green, "amber": amber, "all_red": "r" * n, "links": links}


def green_movements(state, links):
    """{movement: signal char} for every link that shows green (G or g)."""
    out = {}
    for idx, mov in links.items():
        ch = state[idx]
        if ch in "Gg":
            # several links per movement: keep the strongest
            if out.get(mov) != "G":
                out[mov] = ch
    return out


def conflicts_in_state(state, links):
    """List of conflicting movement pairs green together in a state string."""
    greens = green_movements(state, links)
    bad = []
    for pair in VEHICLE_CONFLICTS:
        a, b = sorted(pair)
        if a in greens and b in greens:
            ok = any((x, y) in PERMISSIVE and greens[x] == "g" for x, y in ((a, b), (b, a)))
            if not ok:
                bad.append((a, b))
    for cross, movs in CROSSING_CONFLICTS.items():
        if cross in greens:
            for m in movs:
                if m in greens and greens[m] != "g":
                    bad.append((cross, m))
    return bad
