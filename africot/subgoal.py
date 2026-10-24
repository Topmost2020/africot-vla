"""Subgoal schema, ranges and validator (SPEC 5.8).

The subgoal is the compact interface from the slow loop (VLAM) to the fast loop
(world model and CEM planner). Values outside their range are clamped; an
unparseable response keeps the previous subgoal.
"""
import copy
import json
import re

DEFAULT_SUBGOAL = {
    "queue_weights": {"east": 1.0, "west": 1.0, "south": 1.0},
    "pedestrian_weight": 1.0,
    "max_wait_s": 120,
    "transit_priority": 1.0,
    "valid_for_s": 300,
}

RANGES = {
    "queue_weights": (0.2, 3.0),
    "pedestrian_weight": (0.0, 3.0),
    "max_wait_s": (45, 180),
    "transit_priority": (0.0, 2.0),
    "valid_for_s": (60, 900),
}

# Cached time-of-day schedule, used in long outages (SPEC 5.11). Keys are the
# hour of day the schedule entry starts. The simulated hour runs from 07:00
# (sim clock 0 s) to 08:05 (3900 s), see clock_hour().
TIME_OF_DAY_SCHEDULE = {
    0: dict(DEFAULT_SUBGOAL, pedestrian_weight=0.5, max_wait_s=150),
    6: dict(DEFAULT_SUBGOAL, queue_weights={"east": 1.3, "west": 1.3, "south": 1.0},
            transit_priority=1.5, max_wait_s=120, valid_for_s=900),
    10: dict(DEFAULT_SUBGOAL, queue_weights={"east": 1.0, "west": 1.0, "south": 1.3},
             pedestrian_weight=1.5, max_wait_s=120, valid_for_s=900),
    16: dict(DEFAULT_SUBGOAL, queue_weights={"east": 1.3, "west": 1.3, "south": 1.0},
             transit_priority=1.5, max_wait_s=120, valid_for_s=900),
    20: dict(DEFAULT_SUBGOAL, pedestrian_weight=0.8, max_wait_s=150, valid_for_s=900),
}
SIM_START_HOUR = 7.0


def clock_hour(sim_time):
    """Simulated time of day in hours (sim clock 0 s is 07:00)."""
    return (SIM_START_HOUR + sim_time / 3600.0) % 24


def scheduled_subgoal(sim_time):
    h = clock_hour(sim_time)
    start = max(k for k in TIME_OF_DAY_SCHEDULE if k <= h)
    return copy.deepcopy(TIME_OF_DAY_SCHEDULE[start])


def _clamp(v, lo, hi):
    return min(max(float(v), lo), hi)


def validate(candidate, previous=None):
    """Return (subgoal, notes). Missing or non-numeric fields fall back to the
    previous subgoal (or the default); numeric fields are clamped to range."""
    base = copy.deepcopy(previous or DEFAULT_SUBGOAL)
    notes = []
    if not isinstance(candidate, dict):
        return base, ["not an object; kept previous subgoal"]
    out = copy.deepcopy(base)
    qw = candidate.get("queue_weights")
    if isinstance(qw, dict):
        lo, hi = RANGES["queue_weights"]
        for a in ("east", "west", "south"):
            if a in qw:
                try:
                    v = _clamp(qw[a], lo, hi)
                    if v != float(qw[a]):
                        notes.append(f"queue_weights.{a} clamped {qw[a]} -> {v}")
                    out["queue_weights"][a] = v
                except (TypeError, ValueError):
                    notes.append(f"queue_weights.{a} not numeric; kept {out['queue_weights'][a]}")
    elif qw is not None:
        notes.append("queue_weights not an object; kept previous")
    for k in ("pedestrian_weight", "max_wait_s", "transit_priority", "valid_for_s"):
        if k not in candidate:
            notes.append(f"{k} missing; kept {out[k]}")
            continue
        lo, hi = RANGES[k]
        try:
            v = _clamp(candidate[k], lo, hi)
        except (TypeError, ValueError):
            notes.append(f"{k} not numeric; kept {out[k]}")
            continue
        if v != float(candidate[k]):
            notes.append(f"{k} clamped {candidate[k]} -> {v}")
        out[k] = v
    return out, notes


def parse_response(text):
    """Extract (reasoning, subgoal dict or None) from a VLAM response with
    <reasoning>...</reasoning> and <subgoal>{json}</subgoal>."""
    reasoning = ""
    m = re.search(r"<reasoning>(.*?)</reasoning>", text or "", re.S)
    if m:
        reasoning = m.group(1).strip()
    m = re.search(r"<subgoal>(.*?)</subgoal>", text or "", re.S)
    if not m:
        return reasoning, None
    body = m.group(1).strip()
    body = re.sub(r"^```(?:json)?|```$", "", body.strip()).strip()
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        mm = re.search(r"\{.*\}", body, re.S)
        if not mm:
            return reasoning, None
        try:
            obj = json.loads(mm.group(0))
        except json.JSONDecodeError:
            return reasoning, None
    return reasoning, obj if isinstance(obj, dict) else None
