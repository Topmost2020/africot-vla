"""Latent world model (SPEC 5.6), in the style of DreamerV3 and TD-MPC2 (it is
neither): an MLP encoder maps the observation to a 32-d latent, a GRU cell
advances the latent given the action, and an MLP decoder predicts the next
decision's queues per approach, waiting pedestrians per crosswalk and
departures per approach. Multi-step rollout is supported for planning.

Inputs and targets both come from noisy perception: the model only sees what
the deployed controller sees.
"""
import numpy as np
import torch
from torch import nn

from africot import scenarios as sc
from africot import signals

APPROACHES = ("west", "east", "south")
CLASSES = ("car", "danfo", "keke", "okada")
CROSSINGS = ("xE", "xW", "xS")
MOVEMENTS = ("WE", "WS", "EW", "ES", "SE", "SW")
PHASES = signals.PHASES
GREEN_SCALE = 60.0
PHASE_TIME_SCALE = 90.0

TARGET_NAMES = [f"queue_{a}" for a in APPROACHES] + [f"ped_{x}" for x in CROSSINGS] + \
    [f"dep_{a}" for a in APPROACHES]
QUEUE_IDX = [0, 1, 2]
PED_IDX = [3, 4, 5]
DEP_IDX = [6, 7, 8]


def obs_vector(obs):
    """Flatten a perception observation into the model input."""
    v = []
    for a in APPROACHES:
        s = obs["approaches"][a]
        v += [s["queue"]] + [s["counts"][k] for k in CLASSES] + \
            [s["halting_by_class"]["danfo"], s["occupancy"], s["departures"]]
    v += [obs["ped_waiting"][x] for x in CROSSINGS]
    v += [obs["movement_queues"][m] for m in MOVEMENTS]
    v += [1.0 if obs["phase"] == p else 0.0 for p in PHASES]
    v += [obs["time_in_phase"] / PHASE_TIME_SCALE, obs["time"] / sc.END_S]
    return np.asarray(v, dtype=np.float32)


OBS_DIM = 3 * 8 + 3 + 6 + 3 + 2  # 38


def action_vector(phase, green):
    return np.asarray([1.0 if phase == p else 0.0 for p in PHASES] + [green / GREEN_SCALE], dtype=np.float32)


ACT_DIM = 4


def target_vector(next_obs):
    t = [next_obs["approaches"][a]["queue"] for a in APPROACHES]
    t += [next_obs["ped_waiting"][x] for x in CROSSINGS]
    t += [next_obs["approaches"][a]["departures"] for a in APPROACHES]
    return np.asarray(t, dtype=np.float32)


TGT_DIM = 9


class LatentWorldModel(nn.Module):
    def __init__(self, obs_dim=OBS_DIM, act_dim=ACT_DIM, tgt_dim=TGT_DIM, latent=32, hidden=64):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(obs_dim, hidden), nn.ELU(), nn.Linear(hidden, latent), nn.Tanh())
        self.dynamics = nn.GRUCell(act_dim, latent)
        self.decoder = nn.Sequential(nn.Linear(latent, hidden), nn.ELU(), nn.Linear(hidden, tgt_dim))
        self.register_buffer("obs_mean", torch.zeros(obs_dim))
        self.register_buffer("obs_std", torch.ones(obs_dim))
        self.register_buffer("tgt_mean", torch.zeros(tgt_dim))
        self.register_buffer("tgt_std", torch.ones(tgt_dim))
        self.latent = latent

    def set_normalisation(self, obs_mean, obs_std, tgt_mean, tgt_std):
        self.obs_mean.copy_(torch.as_tensor(obs_mean))
        self.obs_std.copy_(torch.as_tensor(np.maximum(obs_std, 1e-3)))
        self.tgt_mean.copy_(torch.as_tensor(tgt_mean))
        self.tgt_std.copy_(torch.as_tensor(np.maximum(tgt_std, 1e-3)))

    def encode(self, obs):
        return self.encoder((obs - self.obs_mean) / self.obs_std)

    def rollout_normalised(self, obs, actions):
        """obs [B, obs_dim], actions [B, H, act_dim] -> normalised predictions [B, H, tgt_dim]."""
        z = self.encode(obs)
        preds = []
        for h in range(actions.shape[1]):
            z = self.dynamics(actions[:, h], z)
            preds.append(self.decoder(z))
        return torch.stack(preds, dim=1)

    def rollout(self, obs, actions):
        """Predictions in real units (vehicles, pedestrians), clipped at zero."""
        p = self.rollout_normalised(obs, actions) * self.tgt_std + self.tgt_mean
        return torch.clamp(p, min=0.0)


def save(model, path, extra=None):
    torch.save({"state_dict": model.state_dict(), "extra": extra or {},
                "dims": [OBS_DIM, ACT_DIM, TGT_DIM, model.latent]}, path)


def load(path):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    obs_dim, act_dim, tgt_dim, latent = ck["dims"]
    m = LatentWorldModel(obs_dim, act_dim, tgt_dim, latent)
    m.load_state_dict(ck["state_dict"])
    m.eval()
    return m, ck["extra"]
