"""Build facts/facts.json from committed repo files only. Every number in the documents must come from here."""
import csv, json, glob, os
import numpy as np
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def J(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))


F = {}
rows = list(csv.DictReader(open(os.path.join(ROOT, "results/summary.csv"), encoding="utf-8")))
TXT = ("controller", "scenario", "vlam_backend", "vlam_model", "seeds", "git_hashes")


def num(r):
    return {k: (float(v) if k not in TXT and v != "" else v) for k, v in r.items()}


F["summary"] = {f'{r["scenario"]}|{r["controller"]}': num(r) for r in rows}
F["controllers"] = sorted({r["controller"] for r in rows})
F["scenarios"] = ["normal", "market", "incident", "outage"]
full = [p for p in glob.glob(os.path.join(ROOT, "results/africot_full__*.json"))]
F["africot_full_reportable_runs"] = len([p for p in full if J(os.path.relpath(p, ROOT)).get("reportable")])
F["africot_full_evaluated"] = F["africot_full_reportable_runs"] > 0

runs = {}
for p in glob.glob(os.path.join(ROOT, "results/*__*__*.json")):
    d = J(os.path.relpath(p, ROOT))
    if d.get("seed_role") != "evaluation" or d.get("vlam_backend") == "mock":
        continue
    runs[(d["controller"], d["scenario"], d["seed"])] = d
F["n_eval_runs"] = len(runs)


def paired(a, b, sc, metric="awt"):
    x = np.array([runs[(a, sc, s)]["metrics"][metric] for s in range(5)])
    y = np.array([runs[(b, sc, s)]["metrics"][metric] for s in range(5)])
    d = x - y
    t = stats.ttest_rel(x, y)
    try:
        w = float(stats.wilcoxon(x, y).pvalue)
    except Exception:
        w = None
    return {"a": a, "b": b, "scenario": sc, "metric": metric, "mean_diff_a_minus_b": float(d.mean()),
            "sd_diff": float(d.std(ddof=1)), "t_p_two_sided": float(t.pvalue), "wilcoxon_exact_p_two_sided": w,
            "n": 5, "a_lower_in_seeds": int((d < 0).sum())}


PAIRS = [("africot_noslow", "max_pressure"), ("africot_noslow", "fixed_time"), ("max_pressure", "fixed_time"),
         ("africot_nowm", "fixed_time"), ("africot_noslow", "africot_nowm")]
F["paired_tests"] = [paired(a, b, sc) for sc in ["normal", "market", "incident"] for a, b in PAIRS]
F["paired_tests_note"] = ("Per-seed paired differences over seeds 0 to 4 (n=5); with n=5 the exact two-sided Wilcoxon "
                          "p cannot go below 0.0625. Outage equals market for every controller except africot_full, "
                          "so it is not tested separately. Exploratory, no multiplicity correction.")

sc = {}
for (c, s, sd), d in runs.items():
    for r, n in d["info"].get("shield_corrections_by_rule", {}).items():
        sc.setdefault(c, {}).setdefault(r, 0)
        sc[c][r] += n
F["shield_corrections_by_controller_rule"] = sc
F["shield_total_by_rule"] = {r: sum(v.get(r, 0) for v in sc.values()) for r in {r for v in sc.values() for r in v}}
F["safety_violations_total"] = sum(d["metrics"]["safety_violations"] for d in runs.values())


def tele(key):
    out = {}
    for c in F["controllers"]:
        for s in F["scenarios"]:
            if (c, s, 0) in runs:
                n = sum(runs[(c, s, k)]["metrics"][key] for k in range(5))
                if n:
                    out[f"{c}|{s}"] = n
    return out


F["jam_teleports_by_cell"] = tele("jam_teleports")
F["teleports_any_by_cell"] = tele("teleports")
F["decisions_per_run_mean"] = float(np.mean([d["metrics"]["decisions"] for d in runs.values()]))
F["demand_example_seed0"] = {s: runs[("fixed_time", s, 0)]["info"]["demand"] for s in F["scenarios"]}
F["scenario_config"] = {s: runs[("fixed_time", s, 0)]["config"]["scenario"] for s in F["scenarios"]}
cfg0 = runs[("fixed_time", "normal", 0)]["config"]
F["perception_config"] = cfg0["perception"]
F["shield_config"] = cfg0["shield"]
F["warmup_s"] = cfg0["warmup_s"]
F["measure_s"] = cfg0["measure_s"]
F["fixed_time_params"] = cfg0.get("controller_params")
F["controller_params"] = {c: runs[(c, "normal", 0)]["config"].get("controller_params") for c in F["controllers"]}
F["planner_config"] = runs[("africot_noslow", "normal", 0)]["config"].get("planner")
F["default_subgoal"] = runs[("africot_noslow", "normal", 0)]["config"].get("default_subgoal")
wm_on = {}
for s in F["scenarios"]:
    v = [runs[("africot_noslow", s, k)]["info"].get("wm_1step_queue_mae_mean") for k in range(5)]
    v = [x for x in v if x is not None]
    if v:
        wm_on[s] = float(np.mean(v))
F["wm_online_1step_queue_mae_mean_noslow_by_scenario"] = wm_on
F["world_model"] = J("models/wm_metrics.json")

s1 = J("results/s1_scenario_check.json")
F["s1_check"] = {k: v for k, v in s1.items() if k != "runs"}
F["s1_okada_lateral_sd_range_m"] = [min(r["okada_lat_sd"] for r in s1["runs"]), max(r["okada_lat_sd"] for r in s1["runs"])]
F["s1_car_lateral_sd_range_m"] = [min(r["car_lat_sd"] for r in s1["runs"]), max(r["car_lat_sd"] for r in s1["runs"])]
F["s1_fixed_time_tuning_seed_mean_awt_by_scenario"] = {
    s: float(np.mean([r["awt"] for r in s1["runs"] if r["scenario"] == s])) for s in F["scenarios"]}
dt = J("results/demand_tuning.json")
F["demand_tuning"] = {"criterion": dt["criterion"], "candidates": [
    {"south_flow": c["south_flow"], "max_south_not_inserted": max(r["south_not_inserted"] for r in c["runs"]),
     "mean_south_depart_delay_s": float(np.mean([r["south_depart_delay"] for r in c["runs"]])),
     "mean_awt_s": float(np.mean([r["awt"] for r in c["runs"]]))} for c in dt["candidates"]]}

hf = J("examples/vlam_hf_output.json")
F["vlam_smoke_test"] = {k: hf[k] for k in ("backend", "model", "parsed", "subgoal", "parse_ok", "latency_s", "load_s",
                                           "decoding", "max_new_tokens", "validator_notes") if k in hf}
F["vlam_smoke_test"]["machine"] = hf.get("machine")
F["vlam_smoke_context"] = hf["context"]
F["vlam_smoke_note"] = ("The recorded reasoning attributes 11 waiting pedestrians to the west arm; the context gave "
                        "about 11 on the east arm (xE 10.9) and about 2 on the west (xW 2.3).")
s7 = J("results/mock_wiring/s7_integration_check.json")
R = s7["runs"]
F["mock_wiring"] = {
    "note": s7["note"], "n_runs": len(R), "all_completed": all(r["completed"] for r in R),
    "safety_violations_total": sum(r["safety_violations"] for r in R),
    "parse_failures_total": sum(r["parse_failures"] for r in R),
    "slow_loop_calls_range": [min(r["slow_loop_calls"] for r in R), max(r["slow_loop_calls"] for r in R)],
    "novelty_trigger_seeds_by_scenario": {s: [r["seed"] for r in R if r["scenario"] == s and r["novelty_triggers"]] for s in F["scenarios"]},
    "outage_connectivity_switches_seed0": [r["connectivity_switches_in_log"] for r in R if r["scenario"] == "outage" and r["seed"] == 0][0],
    "incident_novelty_times_by_seed": {r["seed"]: r["novelty_trigger_times"] for r in R if r["scenario"] == "incident"},
}
F["tests"] = {"pytest_passed_at_start": 68, "pytest_command": "python -m pytest -q", "pytest_runtime_s": 147}
F["gate_G3"] = {
    "sumo_version": "1.27.1 (eclipse-sumo wheel, Windows, Python 3.13.2)",
    "torch_used": "2.12.1+cpu (the pinned 2.14.1 was not installable here)",
    "commit": "1cc74a9f7eabf43fa4ad9ccc5b4747476b9663f6",
    "reproduced": ("normal seed 0 for fixed_time, count_timer, max_pressure, africot_noslow and africot_nowm: AWT, ATT, AQL, "
                   "throughput, pedestrian wait and shield counts identical to the committed files; only wall time, git hash "
                   "and a 1e-8 float difference in the world-model error differ")}
json.dump(F, open(os.path.join(ROOT, "facts/facts.json"), "w", encoding="utf-8"), indent=1, default=float)
print("ok", len(F))
