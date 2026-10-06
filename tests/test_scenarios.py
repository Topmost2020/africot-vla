"""S1: demand generation and short scenario runs through the environment."""
import xml.etree.ElementTree as ET

import pytest

from africot import scenarios as sc
from africot import signals
from africot.baselines import FixedTime
from africot.env import JunctionEnv
from africot.runner import run_episode
from sim import demand


def test_demand_is_seeded(tmp_path):
    a, b, c = tmp_path / "a.xml", tmp_path / "b.xml", tmp_path / "c.xml"
    demand.generate("normal", 100, a)
    demand.generate("normal", 100, b)
    demand.generate("normal", 101, c)
    assert a.read_text() == b.read_text()
    assert a.read_text() != c.read_text()


def test_demand_rates_and_turns(tmp_path):
    p = tmp_path / "r.xml"
    demand.generate("market", 100, p)
    root = ET.parse(p).getroot()
    vehs = root.findall("vehicle")
    from_s = [v for v in vehs if v.find("route").get("edges").startswith("S2C")]
    # 550 veh/h over 3900 s, Poisson: within 15%
    assert abs(len(from_s) - 550 * 3900 / 3600) < 0.15 * 550 * 3900 / 3600
    from_w = [v for v in vehs if v.find("route").get("edges").startswith("W2C")]
    right = sum(v.find("route").get("edges").endswith("C2S") for v in from_w)
    assert 0.15 < right / len(from_w) < 0.25
    peds = root.findall("person")
    assert abs(len(peds) - 900 * 3900 / 3600) < 0.15 * 900 * 3900 / 3600


def test_tuning_and_eval_seeds_disjoint():
    assert not set(sc.TUNING_SEEDS) & set(sc.EVAL_SEEDS)
    assert not set(sc.DATA_SEEDS) & set(sc.EVAL_SEEDS)


def test_signal_states_never_conflict_during_run():
    env = JunctionEnv()
    env.reset("normal", 100, end_s=400)
    seen = set()
    hook = lambda e: seen.add(e.current_state_string())  # noqa: E731
    env.step_hooks.append(hook)
    try:
        for p, g in (("B", 12), ("C", 25), ("A", 35), ("C", 20)):
            env.apply_phase(p, g)
    finally:
        env.close()
    links = signals.build_states()["links"]
    assert len(seen) >= 5  # greens, ambers, all-red
    for s in seen:
        assert signals.conflicts_in_state(s, links) == []


def test_amber_and_all_red_inserted():
    env = JunctionEnv()
    env.reset("normal", 100, end_s=200)
    log = []
    env.step_hooks.append(lambda e: log.append((e.time, e.signal)))
    try:
        env.apply_phase("A", 10)
        env.apply_phase("C", 10)
    finally:
        env.close()
    kinds = [k for _, k in log]
    assert kinds.count("amber") == 3 and kinds.count("all_red") == 2


@pytest.mark.parametrize("scenario", list(sc.SCENARIOS))
def test_short_run_each_scenario(scenario):
    m, info = run_episode(FixedTime(), scenario, 100, end_s=900)
    assert info["teleport_reasons"].get("jam", 0) == 0
    assert m["throughput"] > 0


def test_incident_blocker_stops_on_east_kerb_lane():
    env = JunctionEnv()
    env.reset("incident", 100, end_s=1300)
    try:
        cyc = FixedTime()
        phase = "A"
        while not env.done():
            env.apply_phase(phase, cyc.GREENS[phase])
            phase = {"A": "B", "B": "C", "C": "A"}[phase]
        c = env.conn
        assert env.incident_log["inserted"] == 1200
        assert env.incident_log["stopped"] is not None and env.incident_log["stopped"] <= 1215
        assert c.vehicle.getLaneID("incident_blocker") == "E2C_1"
        assert c.vehicle.isStopped("incident_blocker")
    finally:
        env.close()
