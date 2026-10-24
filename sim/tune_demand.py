"""Tune the market side-road demand on tuning seeds 100-104 only (SPEC 4).

Target: congested but not gridlocked under fixed_time, i.e. the south-arm
insertion backlog does not grow without bound. For each candidate side-road
flow this records the fixed_time AWT (insertion delay included), the south-arm
mean insertion delay, and the vehicles never inserted by 3900 s.
Writes results/demand_tuning.json.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from africot import scenarios as sc  # noqa: E402
from africot.baselines import FixedTime  # noqa: E402
from africot.runner import run_episode  # noqa: E402

CANDIDATES = [550, 300, 275, 250, 225, 200]


def _one(job):
    s_flow, seed = job
    flows = dict(sc.get("market")["flows"], S=s_flow)
    m, info = run_episode(FixedTime(), "market", seed, overrides={"flows": flows}, audit=False)
    return {"seed": seed, "awt": m["awt"], "awt_completed": m["awt_completed"],
            "south_depart_delay": m["depart_delay_by_arm"].get("south"),
            "south_not_inserted": m["not_inserted_by_arm"].get("south", 0),
            "not_inserted": m["not_inserted"], "jam_teleports": m["jam_teleports"]}


def main():
    out = {"scenario": "market", "controller": "fixed_time", "seeds": list(sc.TUNING_SEEDS),
           "criterion": "south-arm vehicles never inserted at 3900 s <= 5 on every tuning seed, "
                        "and mean south insertion delay < 60 s",
           "candidates": []}
    jobs = [(s_flow, seed) for s_flow in CANDIDATES for seed in sc.TUNING_SEEDS]
    with ProcessPoolExecutor(int(os.environ.get("JOBS", "4"))) as ex:
        results = dict(zip(jobs, ex.map(_one, jobs)))
    for s_flow in CANDIDATES:
        rows = [results[(s_flow, seed)] for seed in sc.TUNING_SEEDS]
        ok = all(r["south_not_inserted"] <= 5 for r in rows) and \
            float(np.mean([r["south_depart_delay"] for r in rows])) < 60
        cand = {"south_flow": s_flow, "runs": rows, "meets_criterion": ok,
                "mean_awt": float(np.mean([r["awt"] for r in rows])),
                "mean_south_depart_delay": float(np.mean([r["south_depart_delay"] for r in rows])),
                "max_south_not_inserted": int(max(r["south_not_inserted"] for r in rows))}
        out["candidates"].append(cand)
        print(json.dumps({k: cand[k] for k in ("south_flow", "meets_criterion", "mean_awt",
                                               "mean_south_depart_delay", "max_south_not_inserted")}),
              flush=True)
    passing = [c["south_flow"] for c in out["candidates"] if c["meets_criterion"]]
    out["selected_south_flow"] = max(passing) if passing else None
    out["git_hash"] = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    os.makedirs("results", exist_ok=True)
    with open("results/demand_tuning.json", "w") as f:
        json.dump(out, f, indent=1)
    print("selected", out["selected_south_flow"])


if __name__ == "__main__":
    main()
