"""Performance metrics (SPEC 5.3). The warm-up is excluded from every metric.

Vehicle delay metrics are computed over every demand vehicle *scheduled* to
depart after the warm-up (scheduled depart = depart - departDelay), and include
the time spent waiting to enter the network (insertion delay):

- ATT = departDelay + travel duration
- AWT = departDelay + waitingTime (time at speed < 0.1 m/s in the network)

Vehicles still in the network at the end, and vehicles never inserted, are
right-censored at the end of the run: they contribute the time accrued up to
then (a never-inserted vehicle contributes end - scheduled depart to both).
So a controller cannot look better by letting demand back up outside the
network. The completed-trip, in-network-only versions are kept as
`att_completed` and `awt_completed` for reference (DEVIATIONS.md).

- AQL: mean over post-warm-up steps of halting demand vehicles summed over
  incoming lanes.
- throughput: demand vehicles arrived between the end of the warm-up and the end.
- pedestrian waiting: mean walk waitingTime from personinfo for persons that
  departed after the warm-up.
"""
import xml.etree.ElementTree as ET

import numpy as np

from africot import scenarios as sc

DEMAND_TYPES = {"car", "danfo", "keke", "okada"}
ARM_OF_ID = {"W": "west", "E": "east", "S": "south"}


class StepSampler:
    """Step hook: samples the summed halting demand vehicles on incoming lanes after the warm-up."""

    def __init__(self, warmup=sc.WARMUP_S):
        self.warmup = warmup
        self.queue_samples = []

    def __call__(self, env):
        if env.time <= self.warmup:
            return
        c = env.conn
        q = 0
        for lanes in env.lanes.values():
            for lane in lanes:
                for v in c.lane.getLastStepVehicleIDs(lane):
                    if c.vehicle.getSpeed(v) < 0.1 and c.vehicle.getTypeID(v) in DEMAND_TYPES:
                        q += 1
        self.queue_samples.append(q)


def scheduled_vehicles(route_file):
    """{vehicle id: (scheduled depart, vType)} for demand vehicles in a route file."""
    out = {}
    for v in ET.parse(route_file).getroot().findall("vehicle"):
        if v.get("type") in DEMAND_TYPES:
            out[v.get("id")] = (float(v.get("depart")), v.get("type"))
    return out


def parse_tripinfo(path, route_file=None, warmup=sc.WARMUP_S, end=sc.END_S):
    root = ET.parse(path).getroot()
    att, awt, att_c, awt_c = [], [], [], []
    by_class, by_arm = {}, {}
    arrived = unfinished = 0
    seen = set()
    for ti in root.findall("tripinfo"):
        vt = ti.get("vType")
        if vt not in DEMAND_TYPES:
            continue
        vid = ti.get("id")
        seen.add(vid)
        depart = float(ti.get("depart"))
        delay = float(ti.get("departDelay", 0.0))
        arrival = float(ti.get("arrival"))
        if arrival >= 0 and warmup <= arrival <= end:
            arrived += 1
        if depart - delay < warmup:
            continue
        dur, wait = float(ti.get("duration")), float(ti.get("waitingTime"))
        att.append(delay + dur)
        awt.append(delay + wait)
        arm = ARM_OF_ID.get(vid[0], "other")
        by_arm.setdefault(arm, {"awt": [], "depart_delay": []})
        by_arm[arm]["awt"].append(delay + wait)
        by_arm[arm]["depart_delay"].append(delay)
        by_class.setdefault(vt, []).append(delay + wait)
        if arrival < 0:
            unfinished += 1
        else:
            att_c.append(dur)
            awt_c.append(wait)
    not_inserted = 0
    not_inserted_by_arm = {}
    if route_file:
        for vid, (dep, vt) in scheduled_vehicles(route_file).items():
            if vid in seen or dep < warmup or dep >= end:
                continue
            not_inserted += 1
            censored = end - dep
            att.append(censored)
            awt.append(censored)
            arm = ARM_OF_ID.get(vid[0], "other")
            not_inserted_by_arm[arm] = not_inserted_by_arm.get(arm, 0) + 1
            by_arm.setdefault(arm, {"awt": [], "depart_delay": []})
            by_arm[arm]["awt"].append(censored)
            by_arm[arm]["depart_delay"].append(censored)
            by_class.setdefault(vt, []).append(censored)
    ped_wait = []
    for pi in root.findall("personinfo"):
        if float(pi.get("depart")) < warmup:
            continue
        ped_wait.append(sum(float(w.get("waitingTime", 0)) for w in pi.findall("walk")))

    def mean(x):
        return float(np.mean(x)) if len(x) else float("nan")

    return {
        "att": mean(att),
        "awt": mean(awt),
        "att_completed": mean(att_c),
        "awt_completed": mean(awt_c),
        "awt_by_class": {k: mean(v) for k, v in sorted(by_class.items())},
        "awt_by_arm": {k: mean(v["awt"]) for k, v in sorted(by_arm.items())},
        "depart_delay_by_arm": {k: mean(v["depart_delay"]) for k, v in sorted(by_arm.items())},
        "throughput": arrived,
        "vehicles_measured": len(att),
        "completed_trips": len(att_c),
        "unfinished": unfinished,
        "not_inserted": not_inserted,
        "not_inserted_by_arm": not_inserted_by_arm,
        "ped_wait": mean(ped_wait),
        "ped_count": len(ped_wait),
    }


def compute(tripinfo_path, sampler, counters=None, route_file=None):
    m = parse_tripinfo(tripinfo_path, route_file=route_file)
    m["aql"] = float(np.mean(sampler.queue_samples)) if sampler.queue_samples else float("nan")
    m["aql_steps"] = len(sampler.queue_samples)
    for k, v in (counters or {}).items():
        m[k] = v
    return m
