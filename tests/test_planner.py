"""S5: CEM planner and the no-world-model heuristic."""
import numpy as np

from africot import planner_cem as pc
from africot import subgoal as sg
from africot import world_model as wm


def _obs(q=(3, 3, 3), t=600.0, phase="A", peds=(0, 0, 0)):
    appr = {}
    for a, qq in zip(("west", "east", "south"), q):
        appr[a] = {"queue": float(qq), "counts": {"car": qq, "danfo": 0, "keke": 0, "okada": 0},
                   "halting_by_class": {"car": qq, "danfo": 0.0, "keke": 0, "okada": 0},
                   "occupancy": 5.0, "departures": 2.0}
    return {"time": t, "phase": phase, "time_in_phase": 20.0, "approaches": appr,
            "ped_waiting": dict(zip(("xE", "xW", "xS"), peds)),
            "movement_queues": {m: 1.0 for m in wm.MOVEMENTS}}


def _model(tmp_path):
    m = wm.LatentWorldModel()
    p = tmp_path / "wm.pt"
    wm.save(m, p)
    return p


def test_cost_penalises_exceeding_max_wait():
    goal = dict(sg.DEFAULT_SUBGOAL, max_wait_s=60)
    q = np.zeros((2, 1, 3))
    ped = np.zeros((2, 1, 3))
    waits = {"west": 0.0, "east": 0.0, "south": 50.0}
    phases = np.array([[0], [2]])  # A leaves south waiting, C serves it
    greens = np.array([[30.0], [30.0]])
    c = pc._cost_terms(q, ped, np.zeros(3), waits, phases, greens, "A", goal)
    assert c[0] > 1000 * 20 - 1 and c[1] == 0.0


def test_cost_uses_subgoal_weights():
    q = np.ones((1, 1, 3))
    ped = np.ones((1, 1, 3))
    waits = {"west": 0.0, "east": 0.0, "south": 0.0}
    g1 = dict(sg.DEFAULT_SUBGOAL, pedestrian_weight=0.0, transit_priority=0.0)
    g2 = dict(g1, queue_weights={"east": 3.0, "west": 1.0, "south": 1.0})
    a = pc._cost_terms(q, ped, np.zeros(3), waits, np.array([[0]]), np.array([[20.0]]), "A", g1)
    b = pc._cost_terms(q, ped, np.zeros(3), waits, np.array([[0]]), np.array([[20.0]]), "A", g2)
    assert a[0] == 3.0 and b[0] == 5.0


def test_cem_is_seeded_and_in_range(tmp_path):
    p = _model(tmp_path)
    outs = []
    for _ in range(2):
        c = pc.CEMPlanner(7, wm_path=p)
        c.reset()
        outs.append([c.decide(_obs(t=600 + 30 * i)) for i in range(3)])
    assert outs[0] == outs[1]
    for phase, green in outs[0]:
        assert phase in ("A", "B", "C") and 10 <= green <= 60
    assert len(c.last_plan["steps"]) == 3


def test_heuristic_serves_long_queue():
    c = pc.CEMPlanner(0, use_world_model=False)
    c.reset()
    phase, green = c.decide(_obs(q=(0, 0, 30), phase="A"))
    assert phase == "C"
