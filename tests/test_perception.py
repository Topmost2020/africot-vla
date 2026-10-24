"""S2: perception noise model."""
import numpy as np

from africot.perception import Perception


def _state(q=20, peds=4):
    appr = {"queue": q, "counts": {"car": q, "danfo": 5, "keke": 0, "okada": 3},
            "halting_by_class": {"car": q, "danfo": 2, "keke": 0, "okada": 1},
            "occupancy": 12.0, "max_wait": 99.0, "departures": 10}
    return {"time": 500.0, "phase": "A", "time_in_phase": 30.0,
            "approaches": {a: dict(appr) for a in ("west", "east", "south")},
            "ped_waiting": {"xE": peds, "xW": 0, "xS": 1}, "ped_max_wait": {"xE": 50.0, "xW": 0, "xS": 3},
            "movement_queues": {"WE": 10, "WS": 2, "EW": 8, "ES": 3, "SE": 1, "SW": 0}, "teleports": 0}


def test_seeded_and_reproducible():
    a = Perception(3)(_state())
    b = Perception(3)(_state())
    c = Perception(4)(_state())
    assert a == b
    assert a != c


def test_noise_statistics():
    p = Perception(0)
    vals = np.array([p(_state(q=100))["approaches"]["west"]["queue"] for _ in range(3000)])
    # mean ~ 95 (5% missed), sd ~ sqrt(binomial var + (0.1*95)^2) ~ 9.8
    assert abs(vals.mean() - 95) < 1.0
    assert 8.5 < vals.std() < 11.0
    zeros = np.array([p(_state(q=0))["approaches"]["west"]["queue"] for _ in range(3000)])
    assert zeros.min() >= 0.0  # clipped
    assert 0.15 < zeros.mean() < 0.25  # half-normal with sd 0.5 has mean 0.2


def test_no_ground_truth_fields_leak():
    obs = Perception(0)(_state())
    assert "max_wait" not in obs["approaches"]["west"]
    assert "ped_max_wait" not in obs
    assert "teleports" not in obs


def test_clean_mode_returns_truth():
    s = _state()
    obs = Perception(0, clean=True)(s)
    assert obs["approaches"]["west"]["queue"] == 20
    assert obs["ped_waiting"] == s["ped_waiting"]


def test_departures_are_per_interval():
    p = Perception(0, clean=True)
    s = _state()
    assert p(s)["approaches"]["west"]["departures"] == 10
    s["approaches"]["west"] = dict(s["approaches"]["west"], departures=25)
    assert p(s)["approaches"]["west"]["departures"] == 15
