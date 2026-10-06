"""Baseline controllers (SPEC 5.4).

A controller is called at the end of each green with the observed state and
returns (next_phase, green_seconds).
"""
from africot import signals

PHASE_ORDER = ("A", "B", "C")


def _next_in_cycle(phase):
    return PHASE_ORDER[(PHASE_ORDER.index(phase) + 1) % len(PHASE_ORDER)]


class FixedTime:
    """Cycle A 35 s, B 12 s, C 25 s (amber and all-red added by the environment)."""
    name = "fixed_time"
    GREENS = {"A": 35, "B": 12, "C": 25}

    def reset(self):
        self._started = False

    def first(self):
        return "A", self.GREENS["A"]

    def decide(self, obs):
        nxt = _next_in_cycle(obs["phase"])
        return nxt, self.GREENS[nxt]
