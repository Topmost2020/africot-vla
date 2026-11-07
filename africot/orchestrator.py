"""Junction orchestrator (SPEC 5.11, formerly the slow-loop coordinator) and network orchestrator.

The junction orchestrator supervises every model that runs at one junction: perception,
the latent world model, the CEM planner, the safety shield and the slow loop. It owns the
slow-loop schedule and the connectivity tiers described below. It never issues phase
commands and it cannot override the shield. The network orchestrator sits above the
junction orchestrators, collects their reports and may send them advisories.

Deployment intent: both orchestrators are meant to be hosted in the cloud. When the link to a
junction is lost, the junction itself must keep running on the edge computer, so the hold-last,
cached-schedule and fixed-time fallback described below has to execute on site. The prototype
simulates the link with scripted outage windows and runs everything in one process; no cloud
deployment exists.

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

# Models and rule layers the junction orchestrator supervises at one junction.
COMPONENTS = ("perception", "world_model", "cem_planner", "safety_shield", "slow_loop")
ADVISORY_KEYS = {"hold_slow_loop"}
TIER_BY_CONNECTIVITY = {"online": "cloud_vlam", "offline_hold_last": "last_subgoal",
                        "offline_cached_schedule": "cached_schedule"}


class JunctionOrchestrator:
    def __init__(self, vlam, scenario_cfg, image_dir=None, keep_images=False, junction_id="J1"):
        self.junction_id = junction_id
        self.parent = None      # set by NetworkOrchestrator.register
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
        self.advisory = {}          # last advisory accepted from the network orchestrator
        self.components = {name: "ok" for name in COMPONENTS}
        self.shield_counts = {}     # corrections seen so far, by rule
        self.status_log = []        # every change of a component status or of the tier
        self.tier = "cloud_vlam"

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
            if trigger != "none" and self.advisory.get("hold_slow_loop"):
                trigger = "suppressed_by_network"
            elif trigger != "none":
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
        self._oversee(t, trigger, rec)
        if self.parent is not None:
            self.parent.poll(t, self.junction_id)
        return copy.deepcopy(self.subgoal)

    # ------------------------------------------------------- oversight
    def _set_status(self, t, name, status):
        if self.components.get(name) != status:
            self.status_log.append({"time": t, "junction": self.junction_id, "component": name,
                                    "from": self.components.get(name), "to": status})
            self.components[name] = status

    def _oversee(self, t, trigger, rec):
        """Update the status of each supervised component after a decision."""
        self.tier = TIER_BY_CONNECTIVITY[self.connectivity]
        slow = "ok"
        if self.connectivity != "online":
            slow = "unreachable"
        elif rec is not None and not rec["parse_ok"]:
            slow = "degraded"
        elif trigger == "suppressed_by_network":
            slow = "held_by_network"
        self._set_status(t, "slow_loop", slow)
        recent_novelty = t - self.last_trigger_time < NOVELTY_MIN_GAP_S
        self._set_status(t, "world_model", "watch" if recent_novelty else "ok")
        self.last_decision["tier"] = self.tier

    def record_shield(self, corrections):
        """Called with the shield's corrections after each decision. The orchestrator only
        observes the shield; it has no way to relax or bypass it."""
        for c in corrections:
            self.shield_counts[c["rule"]] = self.shield_counts.get(c["rule"], 0) + 1

    def accept_advisory(self, advisory):
        """Take an advisory from the network orchestrator. Unknown keys are rejected, and an
        advisory can only hold the slow loop; it cannot change phases or the shield."""
        bad = set(advisory) - ADVISORY_KEYS
        if bad:
            raise ValueError(f"unsupported advisory keys: {sorted(bad)}")
        self.advisory = dict(advisory)

    def report(self):
        return {"junction": self.junction_id, "tier": self.tier, "components": dict(self.components),
                "subgoal_source": self.source, "slow_loop_calls": len(self.calls),
                "parse_failures": self.parse_failures, "shield_corrections": dict(self.shield_counts),
                "advisory": dict(self.advisory)}


class NetworkOrchestrator:
    """Oversees the junction orchestrators of a corridor or network.

    It collects one report per junction after each of that junction's decisions, derives a
    network state, and may send an advisory to one or all junctions. It sits above the
    junction orchestrators and has no path to any signal controller or shield. The
    prototype registers a single junction; the multi-junction behaviour is exercised only
    by unit tests with scripted junctions.
    """

    def __init__(self, network_id="N1"):
        self.network_id = network_id
        self.junctions = {}
        self.reports = {}
        self.state = "nominal"
        self.log = []

    def register(self, junction):
        if junction.junction_id in self.junctions:
            raise ValueError(f"junction {junction.junction_id!r} already registered")
        self.junctions[junction.junction_id] = junction
        junction.parent = self

    def poll(self, t, junction_id):
        self.reports[junction_id] = self.junctions[junction_id].report()
        state = "nominal"
        for rep in self.reports.values():
            if rep["tier"] != "cloud_vlam" or any(v in ("unreachable", "degraded")
                                                   for v in rep["components"].values()):
                state = "degraded"
                break
        if state != self.state:
            self.log.append({"time": t, "network": self.network_id, "from": self.state, "to": state,
                             "reported_by": junction_id})
            self.state = state

    def advise(self, advisory, junction_id=None):
        """Send an advisory to one junction, or to all when `junction_id` is None."""
        targets = [self.junctions[junction_id]] if junction_id else list(self.junctions.values())
        for j in targets:
            j.accept_advisory(advisory)
        self.log.append({"event": "advisory", "advisory": dict(advisory), "to": junction_id or "all"})

    def summary(self):
        return {"network": self.network_id, "state": self.state, "junctions": self.reports, "log": self.log}
