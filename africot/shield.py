"""Safety shield (SPEC 5.5). Sits between every controller and the signals.

Rules, applied in this order to a proposal (phase, green_s):
1. Starvation guard: an approach or crosswalk that has had waiting demand and no
   green for more than 180 s is served next (longest waiting first).
2. Maximum green 90 s: a phase may not run longer than 90 s in total. An
   extension that would pass 90 s is cut, and a phase already at 90 s is ended.
3. Minimum green 10 s for a new phase.
4. Pedestrian minimum: a phase that gives green to a crosswalk lasts at least the
   crossing time (crossing length / 1.2 m/s + 4 s, rounded up). The spec asks for
   this when pedestrians are waiting; the shield applies it on every pedestrian
   phase, because noisy perception can miss a waiting pedestrian (DEVIATIONS.md).
5. Amber 3 s and all-red 2 s on every phase change. The environment inserts them
   in `apply_phase`, which is the only way to change the signals; the shield
   records the transition.

Every correction is returned with its rule and reason so it can be logged.
The shield only uses the controller's observation (noisy perception) and the
signal history it has seen, never ground truth.
"""
import math

from africot import signals
from africot.baselines import PHASE_ORDER

MIN_GREEN = 10
MAX_GREEN = 90
STARVATION_S = 180
PED_SPEED = 1.2
PED_EXTRA_S = 4.0
# observed count at or above this means "someone is waiting"
WAITING_THRESHOLD = 0.5

# Which phases serve each approach / crosswalk.
SERVES = {"west": ("A",), "east": ("A", "B"), "south": ("C",),
          "xS": ("A",), "xE": ("C",), "xW": ("C",)}


def crossing_times(lengths=None):
    if lengths is None:
        from africot.env import crossing_lengths
        lengths = crossing_lengths()
    return {x: int(math.ceil(L / PED_SPEED + PED_EXTRA_S)) for x, L in lengths.items()}


def ped_minimum(phase, ctimes):
    xs = signals.PHASE_CROSSINGS[phase]
    return max((ctimes[x] for x in xs), default=0)


class Shield:
    def __init__(self, ctimes=None):
        self.ctimes = ctimes or crossing_times()
        self.reset()

    def reset(self):
        self.wait_start = {k: 0.0 for k in SERVES}
        self.interventions = 0
        self.transitions = 0
        self.log = []

    def _update_waiting(self, obs):
        """Track how long each approach/crosswalk has had demand without green."""
        now, cur = obs["time"], obs["phase"]
        demand = {a: obs["approaches"][a]["queue"] for a in ("west", "east", "south")}
        demand.update(obs["ped_waiting"])
        for k, served_by in SERVES.items():
            if cur in served_by or demand.get(k, 0.0) < WAITING_THRESHOLD:
                self.wait_start[k] = now  # just served, or nobody waiting
        return {k: now - self.wait_start[k] for k in SERVES}

    def waiting_times(self, obs):
        return {k: obs["time"] - self.wait_start[k] for k in SERVES}

    def check(self, proposal, obs):
        """Return (phase, green_s, corrections) for a proposal made at the end of a green."""
        phase, green = proposal[0], float(proposal[1])
        cur, in_phase = obs["phase"], obs["time_in_phase"]
        corrections = []

        def fix(rule, reason, new_phase, new_green):
            corrections.append({"rule": rule, "reason": reason, "from": [phase, green],
                                "to": [new_phase, new_green]})
            return new_phase, new_green

        if phase not in signals.PHASES:
            phase, green = fix("invalid_phase", f"unknown phase {phase!r}; keep cycle order",
                               PHASE_ORDER[(PHASE_ORDER.index(cur) + 1) % 3], MIN_GREEN)

        # 1. starvation guard
        waits = self._update_waiting(obs)
        starving = sorted((w, k) for k, w in waits.items() if w > STARVATION_S)
        if starving:
            w, k = starving[-1]
            if phase not in SERVES[k]:
                phase, green = fix("starvation", f"{k} waiting {w:.0f} s > {STARVATION_S} s; serve it next",
                                   SERVES[k][0], max(green, MIN_GREEN))

        # 2. maximum green (total time in the phase)
        if phase == cur:
            if in_phase >= MAX_GREEN:
                nxt = self._next_phase(cur, obs)
                phase, green = fix("max_green", f"phase {cur} already green {in_phase:.0f} s; end it",
                                   nxt, MIN_GREEN)
            elif in_phase + green > MAX_GREEN:
                phase, green = fix("max_green", f"extension would reach {in_phase + green:.0f} s > {MAX_GREEN} s",
                                   phase, MAX_GREEN - in_phase)
        if phase != cur and green > MAX_GREEN:
            phase, green = fix("max_green", f"green {green:.0f} s > {MAX_GREEN} s", phase, MAX_GREEN)

        # 3. minimum green for a new phase
        if phase != cur and green < MIN_GREEN:
            phase, green = fix("min_green", f"green {green:.0f} s < {MIN_GREEN} s", phase, MIN_GREEN)
        if green < 1:
            phase, green = fix("min_green", "non-positive extension", phase, 1)

        # 4. pedestrian crossing time for a new pedestrian phase
        if phase != cur:
            pm = ped_minimum(phase, self.ctimes)
            if green < pm:
                phase, green = fix("ped_crossing", f"phase {phase} crosswalk needs {pm} s", phase, pm)

        # 5. amber and all-red are inserted by the environment on every change
        if phase != cur:
            self.transitions += 1
        if corrections:
            self.interventions += 1
        green = int(round(green))
        self.log.append({"time": obs["time"], "proposal": [proposal[0], proposal[1]],
                         "applied": [phase, green], "corrections": corrections})
        return phase, green, corrections

    def _next_phase(self, cur, obs):
        """Phase to switch to when the current one must end: largest observed served queue."""
        from africot.baselines import served_queue
        others = [p for p in PHASE_ORDER if p != cur]
        if "movement_queues" in obs:
            return max(others, key=lambda p: served_queue(obs, p))
        return others[0]


class SafetyAudit:
    """Independent step hook that checks the applied signals against the rules,
    using ground truth from SUMO. Counts violations; it never changes anything."""

    STARVE_BOUND = STARVATION_S + MAX_GREEN + signals.AMBER_S + signals.ALL_RED_S

    def __init__(self, ctimes=None):
        self.ctimes = ctimes or crossing_times()
        self.links = signals.build_states()["links"]
        self.violations = []
        self._seg_kind = None
        self._seg_phase = None
        self._seg_len = 0
        self._seg_ped_waiting = False
        self._prev = None
        self._amber = 0
        self._allred = 0
        self.no_green = {k: 0 for k in SERVES}
        self.max_no_green = {k: 0 for k in SERVES}

    def _close_segment(self, t, end_of_sim=False):
        if self._seg_kind == "green" and not end_of_sim:
            if self._seg_len < MIN_GREEN:
                self.violations.append((t, "min_green", self._seg_phase, self._seg_len))
            if self._seg_len > MAX_GREEN:
                self.violations.append((t, "max_green", self._seg_phase, self._seg_len))
            pm = ped_minimum(self._seg_phase, self.ctimes)
            if self._seg_ped_waiting and self._seg_len < pm:
                self.violations.append((t, "ped_crossing", self._seg_phase, self._seg_len))

    def __call__(self, env):
        t = env.time
        state = env.current_state_string()
        if signals.conflicts_in_state(state, self.links):
            self.violations.append((t, "conflict", state, 0))
        kind, phase = env.signal, env.phase
        if kind == "amber":
            self._amber += 1
        if kind == "all_red":
            self._allred += 1
        key = (kind, phase if kind == "green" else None)
        if key != (self._seg_kind, self._seg_phase if self._seg_kind == "green" else None):
            # new segment
            if self._seg_kind == "green" and kind == "green":
                self.violations.append((t, "no_transition", phase, 0))
            if kind == "green" and self._seg_kind is not None:
                if self._amber != signals.AMBER_S or self._allred != signals.ALL_RED_S:
                    self.violations.append((t, "transition_length", phase, (self._amber, self._allred)))
            self._close_segment(t)
            if kind == "green":
                self._amber = self._allred = 0
                gt = env.get_state()
                self._seg_ped_waiting = any(gt["ped_waiting"][x] > 0 for x in signals.PHASE_CROSSINGS[phase])
            self._seg_kind, self._seg_phase, self._seg_len = kind, phase, 0
        self._seg_len += 1
        # starvation by ground truth: demand present and no green for too long
        if int(t) % 5 == 0:
            gt = env.get_state()
            demand = {a: gt["approaches"][a]["queue"] for a in ("west", "east", "south")}
            demand.update(gt["ped_waiting"])
            for k, served_by in SERVES.items():
                if (kind == "green" and phase in served_by) or demand[k] == 0:
                    self.no_green[k] = 0
                else:
                    self.no_green[k] += 5
                    self.max_no_green[k] = max(self.max_no_green[k], self.no_green[k])
                    if self.no_green[k] == self.STARVE_BOUND + 5:
                        self.violations.append((t, "starvation", k, self.no_green[k]))

    def summary(self):
        by = {}
        for v in self.violations:
            by[v[1]] = by.get(v[1], 0) + 1
        return {"violations": len(self.violations), "by_rule": by,
                "max_no_green_s": dict(self.max_no_green)}
