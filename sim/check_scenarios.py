"""S1 'done when' check: every scenario runs 3900 s under fixed_time on the tuning
seeds with zero jam teleports and no growing insertion backlog (at most 5
vehicles never inserted by 3900 s), and okadas filter laterally within lanes.

Writes results/s1_scenario_check.json. Tuning seeds only.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from africot import scenarios as sc  # noqa: E402
from africot.baselines import FixedTime  # noqa: E402
from africot.runner import run_episode  # noqa: E402


class OkadaLateral:
    """Step hook: lateral offsets of okadas on the approach lanes, every 10 s."""

    def __init__(self):
        self.offsets = []
        self.car_offsets = []  # control: cars keep to the lane centre

    def __call__(self, env):
        if int(env.time) % 10:
            return
        c = env.conn
        for lanes in env.lanes.values():
            for lane in lanes:
                for v in c.lane.getLastStepVehicleIDs(lane):
                    vt = c.vehicle.getTypeID(v)
                    if vt == "okada":
                        self.offsets.append(c.vehicle.getLateralLanePosition(v))
                    elif vt == "car":
                        self.car_offsets.append(c.vehicle.getLateralLanePosition(v))


def main():
    out = {"seeds": list(sc.TUNING_SEEDS), "controller": "fixed_time", "runs": []}
    for scenario in sc.SCENARIOS:
        for seed in sc.TUNING_SEEDS:
            lat = OkadaLateral()
            m, info = run_episode(FixedTime(), scenario, seed, step_hooks=[lat])
            offs = np.array(lat.offsets)
            row = {"scenario": scenario, "seed": seed, "teleports": info["teleports"],
                   "jam_teleports": info["teleport_reasons"].get("jam", 0),
                   "teleport_reasons": info["teleport_reasons"],
                   "sim_end": sc.END_S, "awt": m["awt"], "att": m["att"], "aql": m["aql"],
                   "throughput": m["throughput"], "unfinished": m["unfinished"], "ped_wait": m["ped_wait"],
                   "awt_completed": m["awt_completed"], "not_inserted": m["not_inserted"],
                   "not_inserted_by_arm": m["not_inserted_by_arm"],
                   "depart_delay_by_arm": m["depart_delay_by_arm"],
                   "okada_lat_sd": float(offs.std()) if len(offs) else None,
                   "okada_frac_off_centre_0p5m": float(np.mean(np.abs(offs) > 0.5)) if len(offs) else None,
                   "okada_samples": int(len(offs)),
                   "car_lat_sd": float(np.std(lat.car_offsets)) if lat.car_offsets else None, "incident": info["incident"], "demand": info["demand"]}
            out["runs"].append(row)
            print(json.dumps({k: row[k] for k in ("scenario", "seed", "teleports", "jam_teleports", "awt", "not_inserted", "aql",
                                                  "okada_lat_sd", "car_lat_sd")}), flush=True)
    out["all_zero_jam_teleports"] = all(r["jam_teleports"] == 0 for r in out["runs"])
    out["max_not_inserted"] = max(r["not_inserted"] for r in out["runs"])
    out["no_insertion_backlog"] = out["max_not_inserted"] <= 5
    out["total_teleports_any_reason"] = sum(r["teleports"] for r in out["runs"])
    out["git_hash"] = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    os.makedirs("results", exist_ok=True)
    with open("results/s1_scenario_check.json", "w") as f:
        json.dump(out, f, indent=1)
    print("all_zero_jam_teleports", out["all_zero_jam_teleports"],
          "max_not_inserted", out["max_not_inserted"],
          "total_teleports_any_reason", out["total_teleports_any_reason"])


if __name__ == "__main__":
    main()
