"""Junction orchestrator oversight and network orchestrator."""
import pytest

from africot import orchestrator as co
from africot import scenarios as sc
from africot.vlam import MockVLAM
from tests.test_slow_loop import FakeEnv, _obs


def _junction(jid, scenario, tmp_path):
    j = co.JunctionOrchestrator(MockVLAM(), sc.get(scenario), image_dir=str(tmp_path), junction_id=jid)
    j.bind_env(FakeEnv())
    return j


def test_report_lists_every_supervised_component(tmp_path):
    j = _junction("J1", "normal", tmp_path)
    j(_obs(0))
    rep = j.report()
    assert set(rep["components"]) == set(co.COMPONENTS)
    assert rep["tier"] == "cloud_vlam" and rep["junction"] == "J1"


def test_outage_moves_tier_and_network_state(tmp_path):
    net = co.NetworkOrchestrator("N1")
    j = _junction("J1", "outage", tmp_path)
    net.register(j)
    j(_obs(0))
    assert net.state == "nominal"
    j(_obs(1300))
    assert j.tier == "last_subgoal" and net.state == "degraded"
    j(_obs(1950))
    assert j.tier == "cached_schedule"
    j(_obs(2500))
    assert j.tier == "cloud_vlam" and net.state == "nominal"
    assert [e["to"] for e in net.log] == ["degraded", "nominal"]


def test_network_orchestrator_oversees_two_junctions(tmp_path):
    net = co.NetworkOrchestrator("N1")
    a, b = _junction("J1", "normal", tmp_path), _junction("J2", "outage", tmp_path)
    net.register(a)
    net.register(b)
    a(_obs(0))
    b(_obs(1300))
    assert net.state == "degraded"
    assert net.reports["J1"]["tier"] == "cloud_vlam" and net.reports["J2"]["tier"] == "last_subgoal"
    with pytest.raises(ValueError):
        net.register(_junction("J1", "normal", tmp_path))


def test_advisory_holds_slow_loop_but_nothing_else(tmp_path):
    net = co.NetworkOrchestrator("N1")
    j = _junction("J1", "normal", tmp_path)
    net.register(j)
    net.advise({"hold_slow_loop": True})
    j(_obs(0))
    assert j.last_decision["trigger"] == "suppressed_by_network" and not j.calls
    net.advise({"hold_slow_loop": False}, junction_id="J1")
    j(_obs(10))
    assert j.last_decision["trigger"] == "scheduled" and len(j.calls) == 1
    with pytest.raises(ValueError):
        net.advise({"force_phase": "A"})


def test_default_behaviour_matches_unorchestrated_run(tmp_path):
    """With no advisory and no parent, the subgoal sequence is the one the coordinator produced."""
    solo = _junction("J1", "outage", tmp_path)
    net = co.NetworkOrchestrator("N1")
    managed = _junction("J1", "outage", tmp_path)
    net.register(managed)
    for t in (0, 100, 310, 700, 1300, 1950, 2500):
        assert solo(_obs(t)) == managed(_obs(t))
