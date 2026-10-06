"""CEM planner over 3-step signal plans (SPEC 5.7).

Each plan step is a phase (categorical) and a green time (Gaussian, clipped to
10-60 s). 64 samples, 4 iterations, 8 elites, seeded. The world model imagines
each plan; the cost of an imagined rollout, summed over the horizon, is

    sum_a w_a * queue_a + pedestrian_weight * ped_wait
        + transit_priority * waiting_danfos + 1000 * max(0, est_wait_a - max_wait_s)

with the weights from the current subgoal. Only the first step is executed,
after the shield.

Controller variants:
- africot_full: subgoal from the slow loop (coordinator, S7)
- africot_noslow: fixed default subgoal
- africot_nowm: no world model; scores candidate first steps with a simple
  queue-discharge heuristic from the current queues
"""
import copy
import os

import numpy as np
import torch

from africot import signals
from africot import subgoal as sg
from africot import world_model as wm
from africot.baselines import PHASE_ORDER
from africot.shield import SERVES, WAITING_THRESHOLD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WM = os.path.join(ROOT, "models", "world_model.pt")
APPROACHES = ("east", "west", "south")
TRANSITION_S = signals.AMBER_S + signals.ALL_RED_S
GREEN_MIN, GREEN_MAX = 10.0, 60.0

CEM = {"horizon": 3, "samples": 64, "iterations": 4, "elites": 8, "green_mu": 30.0, "green_sd": 15.0}
# Saturation discharge (veh/s) per approach while its phase is green, used by the
# no-world-model heuristic only: about 1800 veh/h per lane.
DISCHARGE = {"A": {"west": 1.0, "east": 0.5}, "B": {"east": 1.0}, "C": {"south": 0.5}}


class WaitTracker:
    """Estimated time each approach/crosswalk has had demand without green,
    from the observations alone (same rule as the shield's starvation clock)."""

    def __init__(self):
        self.start = {k: 0.0 for k in SERVES}

    def update(self, obs):
        now, cur = obs["time"], obs["phase"]
        demand = {a: obs["approaches"][a]["queue"] for a in ("west", "east", "south")}
        demand.update(obs["ped_waiting"])
        for k, served in SERVES.items():
            if cur in served or demand.get(k, 0.0) < WAITING_THRESHOLD:
                self.start[k] = now
        return {k: now - self.start[k] for k in SERVES}


def _cost_terms(q, ped, danfo_share, waits0, phases, greens, cur_phase, subgoal):
    """Vectorised plan cost. q [N,H,3] (west,east,south), ped [N,H,3], phases [N,H] int,
    greens [N,H]. Returns cost [N]."""
    n, h = phases.shape
    qw = np.array([subgoal["queue_weights"][a] for a in ("west", "east", "south")])
    cost = np.zeros(n)
    wait = np.tile(np.array([waits0[a] for a in ("west", "east", "south")]), (n, 1)).astype(float)
    prev = np.full(n, PHASE_ORDER.index(cur_phase))
    serves = np.zeros((3, 3), dtype=bool)  # [phase, approach]
    for pi, p in enumerate(PHASE_ORDER):
        for ai, a in enumerate(("west", "east", "south")):
            serves[pi, ai] = p in SERVES[a]
    for k in range(h):
        dur = greens[:, k] + np.where(phases[:, k] != prev, TRANSITION_S, 0.0)
        served = serves[phases[:, k]]  # [N,3]
        wait = np.where(served, 0.0, wait + dur[:, None])
        cost += (q[:, k] * qw).sum(1)
        cost += subgoal["pedestrian_weight"] * ped[:, k].sum(1)
        cost += subgoal["transit_priority"] * (q[:, k] * danfo_share).sum(1)
        cost += 1000.0 * np.maximum(0.0, wait - subgoal["max_wait_s"]).sum(1)
        prev = phases[:, k]
    return cost


class CEMPlanner:
    """Fast-loop controller. `subgoal_source(obs)` returns the subgoal in force
    (None means the fixed default subgoal, i.e. africot_noslow)."""

    def __init__(self, seed, use_world_model=True, wm_path=DEFAULT_WM, subgoal_source=None, name=None):
        self.seed = seed
        self.use_wm = use_world_model
        self.subgoal_source = subgoal_source
        self.name = name or ("africot_noslow" if use_world_model else "africot_nowm")
        self.model = None
        if use_world_model:
            self.model, _ = wm.load(wm_path)
            torch.set_num_threads(1)
        self.last_plan = None
        self.last_wm_error = None

    def reset(self):
        self.rng = np.random.default_rng([self.seed, 999])
        self.waits = WaitTracker()
        self._prev_obs = None
        self._prev_pred = None
        self.last_plan = None
        self.last_wm_error = None
        self.wm_errors = []

    def first(self):
        return "A", 30

    def current_subgoal(self, obs):
        if self.subgoal_source is None:
            return copy.deepcopy(sg.DEFAULT_SUBGOAL)
        return self.subgoal_source(obs)

    def _danfo_share(self, obs):
        out = []
        for a in ("west", "east", "south"):
            s = obs["approaches"][a]
            out.append(s["halting_by_class"]["danfo"] / s["queue"] if s["queue"] >= 1 else 0.0)
        return np.clip(np.array(out), 0.0, 1.0)

    def decide(self, obs):
        waits = self.waits.update(obs)
        goal = self.current_subgoal(obs)
        # world-model 1-step error of the previous decision's prediction (novelty signal)
        if self._prev_pred is not None:
            actual = np.array([obs["approaches"][a]["queue"] for a in ("west", "east", "south")])
            self.last_wm_error = float(np.abs(self._prev_pred - actual).mean())
            self.wm_errors.append(self.last_wm_error)
        if self.use_wm:
            phase, green, plan = self._cem(obs, waits, goal)
        else:
            phase, green, plan = self._heuristic(obs, waits, goal)
        self.last_plan = plan
        self.last_subgoal = goal
        return phase, green

    def note_applied(self, obs, phase, green):
        """Record the world model's 1-step queue prediction for the action actually applied."""
        if not self.use_wm:
            self._prev_pred = None
            return
        o = torch.as_tensor(wm.obs_vector(obs))[None]
        a = torch.as_tensor(wm.action_vector(phase, green))[None, None]
        with torch.no_grad():
            p = self.model.rollout(o, a)[0, 0].numpy()
        self._prev_pred = p[wm.QUEUE_IDX]

    # ------------------------------------------------------------------ CEM
    def _cem(self, obs, waits, goal):
        H, N, E = CEM["horizon"], CEM["samples"], CEM["elites"]
        probs = np.full((H, 3), 1.0 / 3)
        mu = np.full(H, CEM["green_mu"])
        sd = np.full(H, CEM["green_sd"])
        o = torch.as_tensor(wm.obs_vector(obs))[None].repeat(N, 1)
        share = self._danfo_share(obs)
        best = (np.inf, None, None)
        for _ in range(CEM["iterations"]):
            phases = np.stack([self.rng.choice(3, size=N, p=probs[k]) for k in range(H)], axis=1)
            greens = np.clip(self.rng.normal(mu, sd, size=(N, H)), GREEN_MIN, GREEN_MAX).round()
            act = np.zeros((N, H, wm.ACT_DIM), dtype=np.float32)
            act[np.arange(N)[:, None], np.arange(H)[None], phases] = 1.0
            act[..., 3] = greens / wm.GREEN_SCALE
            with torch.no_grad():
                pred = self.model.rollout(o, torch.as_tensor(act)).numpy()
            # model target order: queues west, east, south; peds xE, xW, xS
            q = pred[..., wm.QUEUE_IDX]
            ped = pred[..., wm.PED_IDX]
            cost = _cost_terms(q, ped, share, waits, phases, greens, obs["phase"], goal)
            el = np.argsort(cost)[:E]
            if cost[el[0]] < best[0]:
                best = (float(cost[el[0]]), phases[el[0]].copy(), greens[el[0]].copy())
            for k in range(H):
                counts = np.bincount(phases[el, k], minlength=3) + 1e-3
                probs[k] = counts / counts.sum()
            mu = greens[el].mean(0)
            sd = np.maximum(greens[el].std(0), 2.0)
        _, ph, gr = best
        plan = [{"phase": PHASE_ORDER[int(p)], "green": int(g)} for p, g in zip(ph, gr)]
        return plan[0]["phase"], plan[0]["green"], {"steps": plan, "cost": best[0]}

    # ----------------------------------------------------------- heuristic
    def _heuristic(self, obs, waits, goal):
        """No world model: one-step queue-discharge estimate for each candidate first step."""
        t = obs["time"]
        q0 = np.array([obs["approaches"][a]["queue"] for a in ("west", "east", "south")])
        dep = np.array([obs["approaches"][a]["departures"] for a in ("west", "east", "south")])
        if self._prev_obs is not None and t > self._prev_obs[0]:
            dt = t - self._prev_obs[0]
            arr = np.maximum(0.0, (q0 - self._prev_obs[1]) + dep) / dt
            self._arr = 0.7 * getattr(self, "_arr", arr) + 0.3 * arr
        elif not hasattr(self, "_arr"):
            self._arr = np.zeros(3)
        self._prev_obs = (t, q0)
        ped0 = np.array([obs["ped_waiting"][x] for x in ("xE", "xW", "xS")])
        cands = [(pi, g) for pi in range(3) for g in range(10, 61, 5)]
        phases = np.array([[c[0]] for c in cands])
        greens = np.array([[float(c[1])] for c in cands])
        q = np.zeros((len(cands), 1, 3))
        ped = np.zeros((len(cands), 1, 3))
        for i, (pi, g) in enumerate(cands):
            p = PHASE_ORDER[pi]
            dur = g + (TRANSITION_S if p != obs["phase"] else 0)
            dis = np.array([DISCHARGE[p].get(a, 0.0) for a in ("west", "east", "south")]) * g
            q[i, 0] = np.maximum(0.0, q0 + self._arr * dur - dis)
            served_x = signals.PHASE_CROSSINGS[p]
            ped[i, 0] = [0.0 if x in served_x else v for x, v in zip(("xE", "xW", "xS"), ped0)]
        cost = _cost_terms(q, ped, self._danfo_share(obs), waits, phases, greens, obs["phase"], goal)
        i = int(np.argmin(cost))
        p, g = PHASE_ORDER[cands[i][0]], cands[i][1]
        return p, g, {"steps": [{"phase": p, "green": g}], "cost": float(cost[i])}
