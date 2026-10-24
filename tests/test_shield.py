"""S3: the shield corrects deliberately unsafe proposals, and the audit catches unsafe signals."""
import pytest

from africot.env import JunctionEnv
from africot.shield import MAX_GREEN, MIN_GREEN, SafetyAudit, Shield, crossing_times

CT = crossing_times()


def obs(t=100.0, phase="A", in_phase=20.0, queues=(5, 5, 5), peds=(0, 0, 0)):
    appr = {a: {"queue": q} for a, q in zip(("west", "east", "south"), queues)}
    mq = {"WE": queues[0], "WS": 0, "EW": queues[1], "ES": 1, "SE": queues[2], "SW": 0}
    return {"time": t, "phase": phase, "time_in_phase": in_phase, "approaches": appr,
            "ped_waiting": dict(zip(("xE", "xW", "xS"), peds)), "movement_queues": mq}


def rules(corr):
    return [c["rule"] for c in corr]


def test_crossing_times_from_network():
    # east/west arms: 14 m / 1.2 + 4 = 15.7 -> 16 s; south: 7 m -> 9.8 -> 10 s
    assert CT == {"xE": 16, "xW": 16, "xS": 10}


def test_short_green_raised_to_min():
    s = Shield(CT)
    p, g, c = s.check(("B", 3), obs())
    assert (p, g) == ("B", MIN_GREEN) and rules(c) == ["min_green"]
    assert c[0]["reason"]


def test_long_green_capped():
    s = Shield(CT)
    p, g, c = s.check(("B", 200), obs())
    assert (p, g) == ("B", MAX_GREEN) and "max_green" in rules(c)


def test_extension_cut_at_max_total():
    s = Shield(CT)
    p, g, c = s.check(("A", 30), obs(phase="A", in_phase=75))
    assert (p, g) == ("A", 15) and rules(c) == ["max_green"]


def test_phase_at_max_is_ended():
    s = Shield(CT)
    p, g, c = s.check(("A", 15), obs(phase="A", in_phase=90))
    assert p != "A" and g >= MIN_GREEN and "max_green" in rules(c)


def test_pedestrian_phase_gets_crossing_time():
    s = Shield(CT)
    p, g, c = s.check(("C", 10), obs(peds=(3, 2, 0)))
    assert (p, g) == ("C", 16) and rules(c) == ["ped_crossing"]


def test_starvation_guard_serves_waiting_approach():
    s = Shield(CT)
    s.check(("A", 30), obs(t=300, phase="C"))  # south served at t=300
    # south keeps a queue and is not served for 200 s; a proposal ignoring it is corrected
    p, g, c = s.check(("B", 15), obs(t=501, phase="A", queues=(9, 9, 4)))
    assert p == "C" and "starvation" in rules(c)
    assert "south" in c[0]["reason"]


def test_starvation_clock_resets_when_nobody_waits():
    s = Shield(CT)
    s.check(("A", 30), obs(t=300, phase="C"))
    s.check(("A", 30), obs(t=400, phase="A", queues=(9, 9, 0)))  # south empty
    p, g, c = s.check(("B", 15), obs(t=501, phase="A", queues=(9, 9, 2)))
    assert p == "B" and c == []


def test_invalid_phase_corrected():
    s = Shield(CT)
    p, g, c = s.check(("Z", 20), obs(phase="A"))
    assert p in ("A", "B", "C") and "invalid_phase" in rules(c)


def test_safe_proposal_untouched_and_logged():
    s = Shield(CT)
    p, g, c = s.check(("B", 20), obs())
    assert (p, g, c) == ("B", 20, [])
    assert s.log[-1]["applied"] == ["B", 20]
    assert s.interventions == 0


@pytest.mark.parametrize("bad", [("C", 5), ("B", 4)])
def test_audit_detects_unsafe_signals_without_shield(bad):
    audit = SafetyAudit(CT)
    env = JunctionEnv(step_hooks=[audit])
    env.reset("market", 100, end_s=400)
    try:
        env.apply_phase("A", 20)
        env.apply_phase(*bad)   # bypasses the shield on purpose
        env.apply_phase("A", 20)
    finally:
        env.close()
    assert "min_green" in audit.summary()["by_rule"]
