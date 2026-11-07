"""Compare two result folders run with different code (for example the old coordinator and the new
orchestrators) on the same controller, scenario and seed.

    python analysis/compare_runs.py <results_dir_A> <results_dir_B> <log_dir_A> <log_dir_B>

Checks, for every result file present in both folders:
  1. every number in "metrics" is identical;
  2. the explainability logs have the same decisions: same proposal, applied phase and green,
     subgoal, shield corrections, trigger and connectivity at every decision.
Fields that legitimately differ (git hash, timestamps, wall time, the new junction_tier log field,
the new orchestrator report in "info") are ignored. Exit code 0 = identical, 1 = differences.
"""
import glob
import json
import os
import sys

LOG_KEYS = ["sim_time", "trigger", "connectivity", "subgoal", "cem_plan", "proposal",
            "shield_corrections", "applied_phase", "applied_green", "wm_1step_error"]


def load_log(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def main(a, b, la, lb):
    bad = 0
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(a, "*.json")))
    if not files:
        print("no result files in", a)
        return 1
    for name in files:
        pa, pb = os.path.join(a, name), os.path.join(b, name)
        if not os.path.exists(pb):
            print("MISSING in B:", name)
            bad += 1
            continue
        ra, rb = json.load(open(pa)), json.load(open(pb))
        same_metrics = ra["metrics"] == rb["metrics"]
        run_id = name[:-5] + "__mock"
        loga = load_log(os.path.join(la, run_id + ".jsonl"))
        logb = load_log(os.path.join(lb, run_id + ".jsonl"))
        diffs = 0
        if len(loga) != len(logb):
            diffs = abs(len(loga) - len(logb))
        for x, y in zip(loga, logb):
            if any(x.get(k) != y.get(k) for k in LOG_KEYS):
                diffs += 1
        ok = same_metrics and diffs == 0
        print("%-40s metrics identical: %-5s  decisions: %d vs %d, differing: %d  -> %s" %
              (name, same_metrics, len(loga), len(logb), diffs, "SAME" if ok else "DIFFERENT"))
        bad += 0 if ok else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
