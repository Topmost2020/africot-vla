"""World-model data collection (SPEC 5.6, Data).

Transitions are logged from fixed_time, count_timer, max_pressure and a
random-timing controller, through the shield, with noisy perception, on
tuning seeds 100-104 and data seeds 200-219. Evaluation seeds are refused.
Each episode is saved as an .npz of per-decision observation vectors, applied
actions and next-decision targets.
"""
import os

import numpy as np

from africot import scenarios as sc
from africot import world_model as wm
from africot.baselines import BASELINES, PHASE_ORDER
from africot.perception import Perception
from africot.runner import run_episode

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wm")
WM_SEEDS = tuple(sc.TUNING_SEEDS) + tuple(sc.DATA_SEEDS)
WM_CONTROLLERS = ("fixed_time", "count_timer", "max_pressure", "random_timing")
# Outage traffic is identical to market for controllers without a slow loop, so
# outage episodes would duplicate market episodes exactly (DEVIATIONS.md).
WM_SCENARIOS = ("normal", "market", "incident")


class RandomTiming:
    """Random phase and random green in [10, 60] s. Seeded."""
    name = "random_timing"

    def __init__(self, seed):
        self.seed = seed

    def reset(self):
        self.rng = np.random.default_rng([self.seed, 4242])

    def first(self):
        return "A", 30

    def decide(self, obs):
        return PHASE_ORDER[self.rng.integers(3)], int(self.rng.integers(10, 61))


def make_controller(name, seed):
    if name == "random_timing":
        return RandomTiming(seed)
    return BASELINES[name]()


def episode_path(controller, scenario, seed, data_dir=DATA_DIR):
    return os.path.join(data_dir, f"{controller}__{scenario}__{seed}.npz")


def collect_episode(controller, scenario, seed, data_dir=DATA_DIR, end_s=sc.END_S):
    if seed in sc.EVAL_SEEDS:
        raise ValueError("evaluation seeds must never be used for world-model data")
    path = episode_path(controller, scenario, seed, data_dir)
    if os.path.exists(path):
        return path
    obs_list, act_list = [], []

    def hook(env, obs, proposal, applied, corrections):
        obs_list.append(wm.obs_vector(obs))
        act_list.append(wm.action_vector(*applied))

    perception = Perception(seed)
    run_episode(make_controller(controller, seed), scenario, seed, observe=perception,
                decision_hook=hook, audit=False, end_s=end_s)
    # the hook sees the observation at each decision; the target of decision i is
    # the observation at decision i+1
    tgt = []
    for i in range(1, len(obs_list)):
        tgt.append(obs_list[i])
    obs = np.stack(obs_list[:-1])
    act = np.stack(act_list[:-1])
    nxt = np.stack(tgt)
    os.makedirs(data_dir, exist_ok=True)
    np.savez_compressed(path, obs=obs, act=act, next_obs=nxt, seed=seed)
    return path


def targets_from_obs_vectors(next_obs):
    """Pick the target fields (queues, waiting pedestrians, departures) out of observation vectors."""
    idx = []
    for i in range(3):  # queue of each approach
        idx.append(i * 8)
    idx += [24, 25, 26]  # ped waiting xE, xW, xS
    for i in range(3):  # departures of each approach
        idx.append(i * 8 + 7)
    return next_obs[..., idx]
