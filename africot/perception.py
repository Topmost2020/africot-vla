"""Noisy perception of the junction (SPEC 5.2).

Stands in for camera-based detection. From the ground-truth state it keeps, per
approach, the queue (halting vehicles), counts by class, occupancy and
departures since the previous observation; per crossing, the number of waiting pedestrians; and the halting
vehicles per movement (turn lanes and indicators are visible to a camera).

Noise on every count: each vehicle or pedestrian is missed with probability
0.05 (binomial thinning), then Gaussian noise with sd = 10% of the value
(minimum 0.5) is added, and the result is clipped at zero. Seeded.

`clean=True` returns the ground truth with the same layout. It is used only for
metrics and analysis, never for control.
"""
import copy

import numpy as np

MISS_P = 0.05
REL_SD = 0.10
MIN_SD = 0.5

# Fields that never reach a controller (ground truth only).
GROUND_TRUTH_ONLY = ("max_wait", "ped_max_wait", "teleports")


class Perception:
    def __init__(self, seed, clean=False):
        self.clean = clean
        self.rng = np.random.default_rng([int(seed), 31337])
        self._last_dep = {}

    def _noisy(self, value):
        n = int(round(value))
        kept = self.rng.binomial(n, 1.0 - MISS_P) if n > 0 else 0
        sd = max(REL_SD * kept, MIN_SD)
        return float(max(0.0, kept + self.rng.normal(0.0, sd)))

    def __call__(self, state):
        if self.clean:
            obs = copy.deepcopy(state)
            for a, s in obs["approaches"].items():
                cum = s["departures"]
                s["departures"] = float(cum - self._last_dep.get(a, 0))
                self._last_dep[a] = cum
            return obs
        obs = {"time": state["time"], "phase": state["phase"], "time_in_phase": state["time_in_phase"],
               "approaches": {}, "ped_waiting": {}, "movement_queues": {}}
        for a, s in state["approaches"].items():
            obs["approaches"][a] = {
                "queue": self._noisy(s["queue"]),
                "counts": {k: self._noisy(v) for k, v in s["counts"].items()},
                "halting_by_class": {k: self._noisy(v) for k, v in s["halting_by_class"].items()},
                "occupancy": float(s["occupancy"]),
                # vehicles that left this approach since the previous observation
                "departures": self._noisy(s["departures"] - self._last_dep.get(a, 0)),
            }
            self._last_dep[a] = s["departures"]
        for x, n in state["ped_waiting"].items():
            obs["ped_waiting"][x] = self._noisy(n)
        for m, n in state.get("movement_queues", {}).items():
            obs["movement_queues"][m] = self._noisy(n)
        return obs
