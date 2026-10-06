"""Slow-loop coordinator (SPEC 5.11).

- Calls the slow loop (renderer + VLAM + validator) every 300 simulated seconds,
  and early when the novelty trigger fires.
- Connectivity: during a scenario outage window the slow loop is unreachable.
  Offline, the last subgoal is held; after more than 600 s offline the cached
  time-of-day subgoal is used. Every switch is logged.
- Novelty trigger: rolling 1-step world-model error over the last 10 decisions;
  fires when it exceeds 2x the rolling median of the previous 30, with at least
  120 s between triggers.
- The slow loop is treated as instantaneous in simulated time; its wall-clock
  latency is recorded.
"""
import copy
import os
import tempfile

import numpy as np

from africot import renderer
from africot import subgoal as sg

CALL_PERIOD_S = 300
OFFLINE_SWITCH_S = 600
NOVELTY_WINDOW = 10
NOVELTY_HISTORY = 30
NOVELTY_FACTOR = 2.0
NOVELTY_MIN_GAP_S = 120


class Coordinator:
    def __init__(self, vlam, scenario_cfg, image_dir=None, keep_images=False):
        self.vlam = vlam
        self.cfg = scenario_cfg
        self.image_dir = image_dir or tempfile.mkdtemp(prefix="africot_img_")
        self.keep_images = keep_images
        self.env = None
        self.reset()

    def reset(self):
        self.subgoal = copy.deepcopy(sg.DEFAULT_SUBGOAL)
        self.source = "default"
        self.last_call = None
        self.last_trigger_time = -1e9
        self.offline_since = None
        self.connectivity = "online"
        self.events = []        # connectivity switches and triggers
        self.calls = []         # slow-loop call records
        self.parse_failures = 0
        self.errors = []        # world-model 1-step errors, one per decision
        self.last_decision = {"trigger": "none", "connectivity": "online", "reasoning": None, "call": None}

    def bind_env(self, env):
        self.env = env

    # ------------------------------------------------------------ helpers
    def scenario_context(self, t):
        parts = []
        if self.cfg.get("context") and "incident" not in self.cfg["context"]:
            parts.append(self.cfg["context"])
        inc = self.cfg.get("incident")
        if inc and inc["start"] <= t < inc["end"]:
            parts.append("incident reported on east approach")
        return "; ".join(parts)

    def online(self, t):
        out = self.cfg.get("outage")
        return not (out and out["start"] <= t < out["end"])

    def novelty(self, t):
        e = self.errors
        if len(e) < NOVELTY_WINDOW + NOVELTY_HISTORY:
            return False
        recent = float(np.mean(e[-NOVELTY_WINDOW:]))
        base = float(np.median(e[-(NOVELTY_WINDOW + NOVELTY_HISTORY):-NOVELTY_WINDOW]))
        if recent > NOVELTY_FACTOR * base and t - self.last_trigger_time >= NOVELTY_MIN_GAP_S:
            self.last_trigger_time = t
            self.events.append({"time": t, "event": "novelty_trigger", "recent_error": recent, "median_prev": base})
            return True
        return False

    def _call(self, obs, trigger):
        t = obs["time"]
        path = os.path.join(self.image_dir, f"snap_{int(t)}.png")
        renderer.render(renderer.snapshot(self.env), path)
        context = {
            "clock": "%02d:%02d" % divmod(int(sg.clock_hour(t) * 60), 60),
            "scenario_context": self.scenario_context(t),
            "queues": {a: obs["approaches"][a]["queue"] for a in ("east", "west", "south")},
            "ped_waiting": obs["ped_waiting"],
            "danfos": {a: obs["approaches"][a]["halting_by_class"]["danfo"] for a in ("east", "west", "south")},
            "subgoal": self.subgoal,
        }
        rec = self.vlam.query(path, context)
        if not self.keep_images:
            try:
                os.remove(path)
            except OSError:
                pass
        rec.update({"time": t, "trigger": trigger, "context": context})
        self.calls.append(rec)
        if not rec["parse_ok"]:
            self.parse_failures += 1
        else:
            self.subgoal = rec["subgoal"]
            self.source = "vlam"
        self.last_call = t
        return rec

    # ------------------------------------------------------- per decision
    def __call__(self, obs, wm_error=None):
        """Subgoal source for the planner; called once per decision."""
        t = obs["time"]
        if wm_error is not None:
            self.errors.append(wm_error)
        trigger, rec = "none", None
        if self.online(t):
            if self.connectivity != "online":
                self.events.append({"time": t, "event": "connectivity", "from": self.connectivity, "to": "online"})
                self.connectivity = "online"
                self.offline_since = None
            novel = self.novelty(t)
            if self.last_call is None or t - self.last_call >= CALL_PERIOD_S:
                trigger = "scheduled"
            elif novel:
                trigger = "novelty"
            if trigger != "none":
                rec = self._call(obs, trigger)
        else:
            if self.offline_since is None:
                self.offline_since = t
                self.events.append({"time": t, "event": "connectivity", "from": self.connectivity,
                                    "to": "offline_hold_last"})
                self.connectivity = "offline_hold_last"
            if self.connectivity == "offline_hold_last" and t - self.offline_since > OFFLINE_SWITCH_S:
                self.events.append({"time": t, "event": "connectivity", "from": self.connectivity,
                                    "to": "offline_cached_schedule"})
                self.connectivity = "offline_cached_schedule"
            if self.connectivity == "offline_cached_schedule":
                self.subgoal = sg.scheduled_subgoal(t)
                self.source = "cached_schedule"
        self.last_decision = {"trigger": trigger, "connectivity": self.connectivity,
                              "reasoning": rec["reasoning"] if rec else None, "call": rec}
        return copy.deepcopy(self.subgoal)
