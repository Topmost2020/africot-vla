"""S6: renderer, mock VLAM wiring, validator path, coordinator and log."""
import json

import numpy as np
from PIL import Image

from africot import coordinator as co
from africot import renderer
from africot import scenarios as sc
from africot import subgoal as sg
from africot.env import JunctionEnv
from africot.vlam import MockVLAM, build_prompt


def _obs(t, q=(5, 5, 5)):
    appr = {a: {"queue": float(x), "halting_by_class": {"danfo": 1.0}} for a, x in zip(("west", "east", "south"), q)}
    return {"time": float(t), "phase": "A", "time_in_phase": 20, "approaches": appr,
            "ped_waiting": {"xE": 1.0, "xW": 0.0, "xS": 2.0}}


class FakeEnv:
    """Stands in for the simulator when only the coordinator logic is tested."""
    time, phase, signal = 0.0, "A", "green"
    links = {0: "WE"}

    def current_state_string(self):
        return "G"

    class conn:  # noqa: N801
        class vehicle:  # noqa: N801
            @staticmethod
            def getIDList():
                return []

        class person:  # noqa: N801
            @staticmethod
            def getIDList():
                return []


def _coord(scenario, tmp_path):
    c = co.Coordinator(MockVLAM(), sc.get(scenario), image_dir=str(tmp_path))
    c.bind_env(FakeEnv())
    return c


def test_render_real_snapshot_is_512_png(tmp_path):
    env = JunctionEnv()
    env.reset("market", 100, end_s=400)
    try:
        env.apply_phase("A", 35)
        env.apply_phase("C", 25)
        snap = renderer.snapshot(env)
    finally:
        env.close()
    p = renderer.render(snap, tmp_path / "s.png")
    im = Image.open(p)
    assert im.size == (512, 512) and im.format == "PNG"
    assert len(snap["vehicles"]) > 0


def test_mock_vlam_output_parses_and_validates():
    ctx = {"clock": "07:30", "scenario_context": "market day", "queues": {"east": 10, "west": 2, "south": 4},
           "ped_waiting": {"xE": 3}, "subgoal": sg.DEFAULT_SUBGOAL}
    rec = MockVLAM().query("unused.png", ctx)
    assert rec["parse_ok"] and rec["backend"] == "mock"
    assert rec["subgoal"]["pedestrian_weight"] == 1.5
    assert "<reasoning>" in rec["raw"] and rec["reasoning"]
    out, notes = sg.validate(rec["subgoal"])
    assert notes == []
    assert "market day" in build_prompt(ctx) and "[45, 180]" in build_prompt(ctx)


def test_unparseable_response_keeps_previous_subgoal(tmp_path):
    class Broken(MockVLAM):
        def query(self, image_path, context):
            from africot.vlam import _finish
            return _finish(self, "I am not sure.", context, 0.1)
    c = co.Coordinator(Broken(), sc.get("normal"), image_dir=str(tmp_path))
    c.bind_env(FakeEnv())
    c.subgoal = dict(sg.DEFAULT_SUBGOAL, max_wait_s=77)
    goal = c(_obs(400))
    assert goal["max_wait_s"] == 77 and c.parse_failures == 1


def test_scheduled_calls_every_300_s(tmp_path):
    c = _coord("normal", tmp_path)
    for t in range(300, 1600, 50):
        c(_obs(t))
    times = [r["time"] for r in c.calls]
    assert times == [300, 600, 900, 1200, 1500]
    assert all(r["trigger"] == "scheduled" for r in c.calls)


def test_outage_holds_last_then_switches_to_cached_schedule(tmp_path):
    c = _coord("outage", tmp_path)
    for t in range(300, 2600, 50):
        c(_obs(t))
    ev = [(e["time"], e["to"]) for e in c.events if e["event"] == "connectivity"]
    assert ev[0] == (1200, "offline_hold_last")
    assert ev[1][1] == "offline_cached_schedule" and 1800 < ev[1][0] <= 1850
    assert ev[2] == (2400, "online")
    assert not [r for r in c.calls if 1200 <= r["time"] < 2400]


def test_novelty_trigger_fires_with_gap(tmp_path):
    c = _coord("normal", tmp_path)
    c.last_call = 0
    errs = [1.0] * 40 + [5.0] * 12
    fired = []
    for i, e in enumerate(errs):
        t = 100 + 10 * i
        c.last_call = t  # suppress scheduled calls
        c(_obs(t), wm_error=e)
        if c.last_decision["trigger"] == "novelty":
            fired.append(t)
    # rolling mean of the last 10 exceeds 2x the median of the previous 30 after 3 high errors
    assert fired and fired[0] == 100 + 10 * 42
    assert all(b - a >= co.NOVELTY_MIN_GAP_S for a, b in zip(fired, fired[1:]))


def test_incident_context_only_inside_window(tmp_path):
    c = _coord("incident", tmp_path)
    assert c.scenario_context(1000) == ""
    assert c.scenario_context(1500) == "incident reported on east approach"
    assert _coord("market", tmp_path).scenario_context(100) == "market day"


def test_full_controller_end_to_end_mock_short(tmp_path):
    """africot_full with the mock backend runs through runner, shield and log (wiring only)."""
    import argparse
    import run_experiment as rx
    args = argparse.Namespace(vlam_backend="mock", vlam_model=None)
    path = rx.run("africot_full", "incident", 100, results_dir=str(tmp_path), args=args, quiet=True)
    d = json.load(open(path))
    assert d["vlam_backend"] == "mock" and d["reportable"] is False
    assert d["metrics"]["slow_loop_calls"] >= 12
    log = [json.loads(line) for line in open(rx.ROOT + "/" + d["info"]["log_file"])]
    keys = {"sim_time", "controller", "scenario", "seed", "trigger", "connectivity", "vlam_backend",
            "cot_reasoning", "subgoal", "cem_plan", "shield_corrections", "shield_reason",
            "applied_phase", "applied_green", "wm_1step_error"}
    assert keys <= set(log[0])
    assert any(r["trigger"] == "scheduled" and r["cot_reasoning"] for r in log)
    assert np.isfinite(d["metrics"]["awt"])
