"""S4: world-model shapes, feature layout and seed hygiene."""
import numpy as np
import pytest
import torch

from africot import world_model as wm
from africot import wm_data


def _obs(q=(4, 6, 2), peds=(1, 0, 3), dep=(5, 7, 1), phase="B", t=1000.0):
    appr = {}
    for a, qq, d in zip(wm.APPROACHES, q, dep):
        appr[a] = {"queue": qq, "counts": {"car": 3, "danfo": 2, "keke": 1, "okada": 1},
                   "halting_by_class": {"car": 1, "danfo": 1, "keke": 0, "okada": 0},
                   "occupancy": 10.0, "departures": d}
    return {"time": t, "phase": phase, "time_in_phase": 15.0, "approaches": appr,
            "ped_waiting": dict(zip(wm.CROSSINGS, peds)),
            "movement_queues": {m: 1.0 for m in wm.MOVEMENTS}}


def test_obs_vector_layout_and_targets_agree():
    o = _obs()
    v = wm.obs_vector(o)
    assert v.shape == (wm.OBS_DIM,)
    # target fields picked from the observation vector equal target_vector()
    np.testing.assert_allclose(wm_data.targets_from_obs_vectors(v), wm.target_vector(o))
    assert list(v[33:36]) == [0.0, 1.0, 0.0]  # phase B one-hot


def test_rollout_shapes_and_nonnegative():
    m = wm.LatentWorldModel()
    obs = torch.randn(5, wm.OBS_DIM)
    act = torch.randn(5, 3, wm.ACT_DIM)
    out = m.rollout(obs, act)
    assert out.shape == (5, 3, wm.TGT_DIM)
    assert (out >= 0).all()
    assert m.encode(obs).shape == (5, 32)


def test_save_load_roundtrip(tmp_path):
    m = wm.LatentWorldModel()
    m.set_normalisation(np.ones(wm.OBS_DIM), 2 * np.ones(wm.OBS_DIM), np.zeros(wm.TGT_DIM), np.ones(wm.TGT_DIM))
    p = tmp_path / "m.pt"
    wm.save(m, p)
    m2, _ = wm.load(p)
    x, a = torch.randn(2, wm.OBS_DIM), torch.randn(2, 2, wm.ACT_DIM)
    torch.testing.assert_close(m.eval().rollout(x, a), m2.rollout(x, a))


def test_eval_seeds_refused():
    with pytest.raises(ValueError):
        wm_data.collect_episode("fixed_time", "normal", 0)
    assert not set(wm_data.WM_SEEDS) & {0, 1, 2, 3, 4}


def test_split_seeds_disjoint():
    import train_world_model as t
    assert not set(t.TRAIN_SEEDS) & set(t.VAL_SEEDS)
    assert not set(t.TRAIN_SEEDS) & set(t.TEST_SEEDS)
    assert not set(t.VAL_SEEDS) & set(t.TEST_SEEDS)
    assert not (set(t.TRAIN_SEEDS) | set(t.VAL_SEEDS) | set(t.TEST_SEEDS)) & {0, 1, 2, 3, 4}
