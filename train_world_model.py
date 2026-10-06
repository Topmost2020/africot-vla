"""Collect world-model data and train the latent world model (SPEC 5.6).

    python train_world_model.py collect --jobs 4
    python train_world_model.py train

Splits are by seed, so no episode is shared between them:
  train: tuning seeds 100-104 and data seeds 200-209
  validation (early stopping): data seeds 210-214
  test (held-out check): data seeds 215-219
Evaluation seeds 0-4 are never used.
Outputs: models/world_model.pt, models/wm_training_curve.csv,
models/wm_training_curve.png, models/wm_metrics.json.
"""
import argparse
import glob
import itertools
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import torch

from africot import scenarios as sc
from africot import world_model as wm
from africot import wm_data

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")
TRAIN_SEEDS = tuple(sc.TUNING_SEEDS) + tuple(range(200, 210))
VAL_SEEDS = tuple(range(210, 215))
TEST_SEEDS = tuple(range(215, 220))
HORIZON = 3
SEED = 0


def _collect(job):
    c, s, seed = job
    try:
        return wm_data.collect_episode(c, s, seed), None
    except Exception as e:
        return None, f"{c} {s} {seed}: {type(e).__name__}: {e}"


def collect(jobs):
    combos = list(itertools.product(wm_data.WM_CONTROLLERS, wm_data.WM_SCENARIOS, wm_data.WM_SEEDS))
    errors = []
    with ProcessPoolExecutor(jobs) as ex:
        for f in as_completed([ex.submit(_collect, j) for j in combos]):
            path, err = f.result()
            if err:
                errors.append(err)
                print("FAILED", err, flush=True)
    print(f"collected {len(combos) - len(errors)} episodes, {len(errors)} failed")
    return errors


def load_sequences(seeds, horizon=HORIZON):
    """Windows of `horizon` consecutive decisions: obs[t], actions t..t+H-1, targets t..t+H-1."""
    O, A, T, P = [], [], [], []
    for path in sorted(glob.glob(os.path.join(wm_data.DATA_DIR, "*.npz"))):
        d = np.load(path)
        seed = int(d["seed"])
        assert seed not in sc.EVAL_SEEDS
        if seed not in seeds:
            continue
        obs, act, tgt = d["obs"], d["act"], wm_data.targets_from_obs_vectors(d["next_obs"])
        for t in range(len(obs) - horizon + 1):
            O.append(obs[t])
            A.append(act[t:t + horizon])
            T.append(tgt[t:t + horizon])
            P.append(wm_data.targets_from_obs_vectors(obs[t]))  # current values, for persistence
    return (np.stack(O).astype(np.float32), np.stack(A).astype(np.float32),
            np.stack(T).astype(np.float32), np.stack(P).astype(np.float32))


def evaluate(model, data):
    O, A, T, P = (torch.as_tensor(x) for x in data)
    with torch.no_grad():
        pred = model.rollout(O, A).numpy()
    T, P = T.numpy(), P.numpy()
    out = {}
    for h in range(T.shape[1]):
        err_m = np.abs(pred[:, h] - T[:, h])
        err_p = np.abs(P - T[:, h])
        out[f"{h + 1}step"] = {
            "queue_mae_model": float(err_m[:, wm.QUEUE_IDX].mean()),
            "queue_mae_persistence": float(err_p[:, wm.QUEUE_IDX].mean()),
            "ped_mae_model": float(err_m[:, wm.PED_IDX].mean()),
            "ped_mae_persistence": float(err_p[:, wm.PED_IDX].mean()),
            "dep_mae_model": float(err_m[:, wm.DEP_IDX].mean()),
            "dep_mae_persistence": float(err_p[:, wm.DEP_IDX].mean()),
            "per_target_mae_model": dict(zip(wm.TARGET_NAMES, err_m.mean(0).round(4).tolist())),
        }
        q = out[f"{h + 1}step"]
        q["queue_improvement_vs_persistence"] = 1.0 - q["queue_mae_model"] / q["queue_mae_persistence"]
    return out


def train(epochs=300, patience=20, batch=256, lr=1e-3):
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    tr, va, te = load_sequences(TRAIN_SEEDS), load_sequences(VAL_SEEDS), load_sequences(TEST_SEEDS)
    model = wm.LatentWorldModel()
    tgt_flat = tr[2].reshape(-1, wm.TGT_DIM)
    model.set_normalisation(tr[0].mean(0), tr[0].std(0), tgt_flat.mean(0), tgt_flat.std(0))
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    O, A, T = (torch.as_tensor(x) for x in tr[:3])
    vO, vA, vT = (torch.as_tensor(x) for x in va[:3])

    def norm_t(t):
        return (t - model.tgt_mean) / model.tgt_std

    curve, best, best_state, bad = [], float("inf"), None, 0
    gen = torch.Generator().manual_seed(SEED)
    t0 = time.time()
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(O), generator=gen)
        tot = 0.0
        for i in range(0, len(O), batch):
            idx = perm[i:i + batch]
            loss = torch.mean((model.rollout_normalised(O[idx], A[idx]) - norm_t(T[idx])) ** 2)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        model.eval()
        with torch.no_grad():
            vl = torch.mean((model.rollout_normalised(vO, vA) - norm_t(vT)) ** 2).item()
        curve.append((ep + 1, tot / len(O), vl))
        if vl < best - 1e-5:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
        if (ep + 1) % 10 == 0:
            print(f"epoch {ep + 1}: train {tot / len(O):.4f} val {vl:.4f}", flush=True)
        if bad >= patience:
            break
    model.load_state_dict(best_state)
    model.eval()
    metrics = {
        "split_seeds": {"train": TRAIN_SEEDS, "validation": VAL_SEEDS, "test": TEST_SEEDS},
        "n_windows": {"train": len(tr[0]), "validation": len(va[0]), "test": len(te[0])},
        "horizon": HORIZON, "epochs_run": len(curve), "best_val_loss": best,
        "best_epoch": int(min(curve, key=lambda c: c[2])[0]),
        "hyperparameters": {"latent": 32, "hidden": 64, "lr": lr, "batch": batch, "patience": patience,
                            "max_epochs": epochs, "loss": "MSE on normalised targets, mean over 3-step rollout",
                            "optimiser": "Adam", "torch_seed": SEED},
        "test": evaluate(model, te),
        "validation": evaluate(model, va),
        "controllers": wm_data.WM_CONTROLLERS, "scenarios": wm_data.WM_SCENARIOS,
        "train_wall_s": round(time.time() - t0, 1),
        "git_hash": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                   text=True).stdout.strip(),
    }
    t1 = metrics["test"]["1step"]
    metrics["check_1step_beats_persistence_by_10pct"] = bool(t1["queue_improvement_vs_persistence"] >= 0.10)
    os.makedirs(MODELS, exist_ok=True)
    wm.save(model, os.path.join(MODELS, "world_model.pt"), extra={"metrics_file": "models/wm_metrics.json"})
    with open(os.path.join(MODELS, "wm_training_curve.csv"), "w") as f:
        f.write("epoch,train_loss,val_loss\n")
        for e, a, b in curve:
            f.write(f"{e},{a:.6f},{b:.6f}\n")
    with open(os.path.join(MODELS, "wm_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=1)
    _plot_curve(curve, os.path.join(MODELS, "wm_training_curve.png"))
    print(json.dumps({"1step": {k: v for k, v in t1.items() if k != "per_target_mae_model"},
                      "3step_queue_mae_model": metrics["test"]["3step"]["queue_mae_model"],
                      "3step_queue_mae_persistence": metrics["test"]["3step"]["queue_mae_persistence"],
                      "check": metrics["check_1step_beats_persistence_by_10pct"]}, indent=1))
    return metrics


def _plot_curve(curve, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e, a, b = zip(*curve)
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.plot(e, a, label="train")
    ax.plot(e, b, label="validation")
    ax.set_xlabel("epoch")
    ax.set_ylabel("MSE (normalised)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["collect", "train"])
    p.add_argument("--jobs", type=int, default=4)
    args = p.parse_args(argv)
    if args.cmd == "collect":
        return 1 if collect(args.jobs) else 0
    train()
    return 0


if __name__ == "__main__":
    sys.exit(main())
