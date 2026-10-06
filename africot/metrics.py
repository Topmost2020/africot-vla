"""Performance metrics (SPEC 5.3). The warm-up is excluded from every metric.

- ATT, AWT: from SUMO tripinfo, over vehicles that departed after the warm-up and
  arrived before the end. Vehicles still in the network at the end are counted
  separately as `unfinished`.
- AQL: mean over post-warm-up steps of halting vehicles summed over incoming lanes.
- throughput: vehicles arrived between the end of the warm-up and the end.
- pedestrian waiting: mean walk waitingTime from personinfo for persons that
  departed after the warm-up.
"""
import xml.etree.ElementTree as ET

import numpy as np

from africot import scenarios as sc

DEMAND_TYPES = {"car", "danfo", "keke", "okada"}


class StepSampler:
    """Step hook: samples the summed halting count on incoming lanes after the warm-up."""

    def __init__(self, warmup=sc.WARMUP_S):
        self.warmup = warmup
        self.queue_samples = []
        self.ped_wait_samples = []

    def __call__(self, env):
        if env.time <= self.warmup:
            return
        c = env.conn
        q = 0
        for lanes in env.lanes.values():
            for lane in lanes:
                q += c.lane.getLastStepHaltingNumber(lane)
        self.queue_samples.append(q)


def parse_tripinfo(path, warmup=sc.WARMUP_S, end=sc.END_S):
    root = ET.parse(path).getroot()
    tt, wt, by_class = [], [], {}
    arrived, unfinished = 0, 0
    for ti in root.findall("tripinfo"):
        vt = ti.get("vType")
        if vt not in DEMAND_TYPES:
            continue
        depart = float(ti.get("depart"))
        arrival = float(ti.get("arrival"))
        if arrival >= 0 and warmup <= arrival <= end:
            arrived += 1
        if depart < warmup:
            continue
        if arrival < 0:
            unfinished += 1
            continue
        tt.append(float(ti.get("duration")))
        wt.append(float(ti.get("waitingTime")))
        by_class.setdefault(vt, []).append(float(ti.get("waitingTime")))
    ped_wait = []
    for pi in root.findall("personinfo"):
        if float(pi.get("depart")) < warmup:
            continue
        w = sum(float(walk.get("waitingTime", 0)) for walk in pi.findall("walk"))
        ped_wait.append(w)
    return {
        "att": float(np.mean(tt)) if tt else float("nan"),
        "awt": float(np.mean(wt)) if wt else float("nan"),
        "awt_by_class": {k: float(np.mean(v)) for k, v in sorted(by_class.items())},
        "throughput": arrived,
        "completed_trips": len(tt),
        "unfinished": unfinished,
        "ped_wait": float(np.mean(ped_wait)) if ped_wait else float("nan"),
        "ped_count": len(ped_wait),
    }


def compute(tripinfo_path, sampler, counters=None):
    m = parse_tripinfo(tripinfo_path)
    m["aql"] = float(np.mean(sampler.queue_samples)) if sampler.queue_samples else float("nan")
    m["aql_steps"] = len(sampler.queue_samples)
    for k, v in (counters or {}).items():
        m[k] = v
    return m
