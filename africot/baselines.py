"""Baseline controllers (SPEC 5.4).

A controller is called at the end of each green with the (noisy) observation
and returns (next_phase, green_seconds). Returning the current phase extends
its green without amber.
"""
from africot import signals

PHASE_ORDER = ("A", "B", "C")


def next_in_cycle(phase):
    return PHASE_ORDER[(PHASE_ORDER.index(phase) + 1) % len(PHASE_ORDER)]


def served_queue(obs, phase):
    """Observed halting vehicles on the movements a phase serves with right of way."""
    return sum(obs["movement_queues"][m] for m in signals.PHASE_SERVED[phase])


class FixedTime:
    """Cycle A 35 s, B 12 s, C 25 s (amber and all-red added by the environment)."""
    name = "fixed_time"
    GREENS = {"A": 35, "B": 12, "C": 25}

    def reset(self):
        pass

    def first(self):
        return "A", self.GREENS["A"]

    def decide(self, obs):
        nxt = next_in_cycle(obs["phase"])
        return nxt, self.GREENS[nxt]


class CountTimer:
    """Camera count plus timer (actuated). Green starts at 10 s and extends in 5 s
    steps while the served queue is at least 3, up to 60 s. Phases cycle A, B, C."""
    name = "count_timer"
    MIN_GREEN, STEP, MAX_GREEN, QUEUE_THRESHOLD = 10, 5, 60, 3

    def reset(self):
        pass

    def first(self):
        return "A", self.MIN_GREEN

    def decide(self, obs):
        phase, elapsed = obs["phase"], obs["time_in_phase"]
        if served_queue(obs, phase) >= self.QUEUE_THRESHOLD and elapsed + self.STEP <= self.MAX_GREEN:
            return phase, self.STEP
        return next_in_cycle(phase), self.MIN_GREEN


class MaxPressure:
    """Pick the phase whose served movements have the largest total queue
    (downstream treated as empty for an isolated junction). Fixed green 15 s.
    Ties keep the current phase, then follow cycle order."""
    name = "max_pressure"
    GREEN = 15

    def reset(self):
        pass

    def first(self):
        return "A", self.GREEN

    def decide(self, obs):
        cur = obs["phase"]
        order = [cur] + [p for p in PHASE_ORDER if p != cur]
        best = max(order, key=lambda p: served_queue(obs, p))  # max keeps the first on ties
        return best, self.GREEN


BASELINES = {c.name: c for c in (FixedTime, CountTimer, MaxPressure)}
