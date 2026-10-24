"""Seeded demand generator: writes a SUMO route file for one scenario and seed.

Vehicles arrive as a Poisson process per origin arm; class and destination are
drawn from the scenario mix and the turning shares. Pedestrians arrive as a
Poisson process and each one crosses a single arm.
"""
import numpy as np

from africot import scenarios as sc

EDGE_IN = {"W": "W2C", "E": "E2C", "S": "S2C"}
EDGE_OUT = {"W": "C2W", "E": "C2E", "S": "C2S"}
# Walk from one side of an arm to the other, through that arm's crosswalk.
PED_WALKS = {"xE": ("E2C", "C2E"), "xW": ("W2C", "C2W"), "xS": ("S2C", "C2S")}
APPROACH_LEN = 300.0


def _poisson_times(rng, rate_per_h, end_s):
    times, t = [], 0.0
    if rate_per_h <= 0:
        return times
    mean = 3600.0 / rate_per_h
    while True:
        t += rng.exponential(mean)
        if t >= end_s:
            return times
        times.append(t)


def generate(scenario, seed, path, end_s=sc.END_S, overrides=None):
    """Write routes for (scenario, seed) to `path`. Returns a summary dict.
    `overrides` replaces top-level scenario fields (used only for demand tuning)."""
    cfg = dict(sc.get(scenario), **(overrides or {}))
    rng = np.random.default_rng([seed, 7919])
    classes = list(cfg["mix"])
    probs = np.array([cfg["mix"][c] for c in classes])
    entries = []  # (time, xml)
    counts = {c: 0 for c in classes}
    for arm, rate in cfg["flows"].items():
        dests = list(sc.TURNS[arm])
        dprobs = np.array([sc.TURNS[arm][d] for d in dests])
        for i, t in enumerate(_poisson_times(rng, rate, end_s)):
            vt = classes[rng.choice(len(classes), p=probs)]
            dest = dests[rng.choice(len(dests), p=dprobs)]
            counts[vt] += 1
            lat = ' departPosLat="random"' if vt == "okada" else ""
            entries.append((t, f'    <vehicle id="{arm}{dest}_{i}" type="{vt}" depart="{t:.2f}" '
                               f'departLane="best" departSpeed="max"{lat}>\n'
                               f'        <route edges="{EDGE_IN[arm]} {EDGE_OUT[dest]}"/>\n    </vehicle>'))
    # The incident lane closure is applied through TraCI by africot.env (see JunctionEnv._incident).
    crossings = list(cfg["ped_split"])
    cprobs = np.array([cfg["ped_split"][c] for c in crossings])
    n_ped = 0
    for i, t in enumerate(_poisson_times(rng, cfg["ped_per_h"], end_s)):
        cross = crossings[rng.choice(len(crossings), p=cprobs)]
        a, b = PED_WALKS[cross]
        # also randomise direction across the arm
        if rng.random() < 0.5:
            frm, to, dpos, apos = a, b, APPROACH_LEN - 15.0, 15.0
        else:
            frm, to, dpos, apos = b, a, 15.0, APPROACH_LEN - 15.0
        n_ped += 1
        entries.append((t, f'    <person id="p{cross}_{i}" depart="{t:.2f}" departPos="{dpos:.1f}">\n'
                           f'        <walk from="{frm}" to="{to}" arrivalPos="{apos:.1f}"/>\n    </person>'))
    entries.sort(key=lambda e: e[0])
    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<routes>\n')
        for _, xml in entries:
            f.write(xml + "\n")
        f.write("</routes>\n")
    return {"vehicles": counts, "pedestrians": n_ped, "scenario": scenario, "seed": seed}
