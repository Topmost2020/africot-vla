"""S7 'done when' check: africot_full runs end to end with the MOCK backend on all
scenarios (wiring only, never reported), the outage log shows hold-last then the
cached-schedule switch, and the novelty trigger is checked in the incident scenario.

    python sim/check_integration.py --seeds 0 1 2 3 4 --jobs 4

Runs go to results/mock_wiring/ (reportable=false). Writes
results/mock_wiring/s7_integration_check.json.
"""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from africot import scenarios as sc  # noqa: E402
import run_experiment as rx  # noqa: E402


def _one(job):
    scenario, seed = job
    args = argparse.Namespace(vlam_backend="mock", vlam_model=None)
    return rx.run("africot_full", scenario, seed, force=True, args=args, quiet=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", nargs="+", type=int, default=list(sc.EVAL_SEEDS))
    p.add_argument("--jobs", type=int, default=4)
    a = p.parse_args()
    jobs = [(s, seed) for s in sc.SCENARIOS for seed in a.seeds]
    with ProcessPoolExecutor(a.jobs) as ex:
        paths = list(ex.map(_one, jobs))
    runs = []
    for (scenario, seed), path in zip(jobs, paths):
        d = json.load(open(path))
        log = [json.loads(line) for line in open(os.path.join(ROOT, d["info"]["log_file"]))]
        conn = [(r["sim_time"], r["connectivity"]) for r in log]
        switches = [(t, c) for i, (t, c) in enumerate(conn) if i == 0 or c != conn[i - 1][1]]
        m = d["metrics"]
        runs.append({
            "scenario": scenario, "seed": seed, "vlam_backend": d["vlam_backend"], "reportable": d["reportable"],
            "completed": d["metrics"]["aql_steps"] == sc.MEASURE_S, "awt": m["awt"],
            "safety_violations": m["safety_violations"], "slow_loop_calls": m["slow_loop_calls"],
            "parse_failures": m["vlam_parse_failures"], "novelty_triggers": m["novelty_triggers"],
            "novelty_trigger_times": [r["sim_time"] for r in log if r["trigger"] == "novelty"],
            "connectivity_switches_in_log": switches, "coordinator_events": d["info"]["coordinator_events"],
            "log_file": d["info"]["log_file"],
        })
    out = {"backend": "mock", "note": "wiring check only; mock-VLAM runs are never reported as VLAM results",
           "runs": runs}
    outage = [r for r in runs if r["scenario"] == "outage"]
    out["outage_hold_then_cached_all_seeds"] = all(
        [c for _, c in r["connectivity_switches_in_log"]][:4] ==
        ["online", "offline_hold_last", "offline_cached_schedule", "online"] for r in outage)
    inc = [r for r in runs if r["scenario"] == "incident"]
    out["incident_novelty_trigger_seeds"] = [r["seed"] for r in inc if r["novelty_triggers"] > 0]
    out["incident_novelty_triggers_in_window"] = {
        r["seed"]: [t for t in r["novelty_trigger_times"] if 1200 <= t <= 2400] for r in inc}
    out["all_completed"] = all(r["completed"] for r in runs)
    out["total_safety_violations"] = sum(r["safety_violations"] for r in runs)
    out["git_hash"] = rx.git_hash()
    path = os.path.join(rx.MOCK_RESULTS_DIR, "s7_integration_check.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "runs"}, indent=1))


if __name__ == "__main__":
    main()
