"""Run one controller on one scenario and seed and save the metrics (SPEC 5.13).

    python run_experiment.py --controller max_pressure --scenario normal --seed 0

Writes results/<controller>__<scenario>__<seed>.json with the metrics, the full
config, the code git hash and the VLAM backend. Existing results are skipped
unless --force.
"""
import argparse
import json
import os
import subprocess
import sys
import time

from africot import scenarios as sc
from africot import shield
from africot.perception import Perception
from africot.log import ExplainLog
from africot.runner import run_episode

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(ROOT, "results")
MOCK_RESULTS_DIR = os.path.join(ROOT, "results", "mock_wiring")


def git_hash():
    try:
        h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        return h + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def seed_role(seed):
    if seed in sc.EVAL_SEEDS:
        return "evaluation"
    if seed in sc.TUNING_SEEDS:
        return "tuning"
    if seed in sc.DATA_SEEDS:
        return "data"
    return "other"


def build_controller(name, args):
    from africot.baselines import BASELINES
    if name in BASELINES:
        return BASELINES[name](), {"vlam_backend": None}
    if name in ("africot_noslow", "africot_nowm"):
        from africot import planner_cem
        from africot import subgoal as sg
        use_wm = name == "africot_noslow"
        ctrl = planner_cem.CEMPlanner(args.seed, use_world_model=use_wm, name=name)
        extra = {"vlam_backend": None, "planner": dict(planner_cem.CEM), "subgoal": "fixed default",
                 "default_subgoal": sg.DEFAULT_SUBGOAL}
        if use_wm:
            extra["world_model"] = os.path.relpath(planner_cem.DEFAULT_WM, ROOT)
        return ctrl, extra
    if name == "africot_full":
        from africot import planner_cem
        from africot.coordinator import Coordinator
        from africot.vlam import make_vlam
        backend = getattr(args, "vlam_backend", None) or "mock"
        vlam = make_vlam(backend, getattr(args, "vlam_model", None))
        coord = Coordinator(vlam, sc.get(args.scenario))
        ctrl = planner_cem.CEMPlanner(args.seed, use_world_model=True, subgoal_source=coord, name=name)
        return ctrl, {"vlam_backend": backend, "vlam_model": vlam.model_id, "planner": dict(planner_cem.CEM),
                      "world_model": os.path.relpath(planner_cem.DEFAULT_WM, ROOT),
                      "reportable": backend != "mock"}
    raise SystemExit(f"unknown controller {name!r}")


def result_path(controller, scenario, seed, results_dir=RESULTS_DIR):
    return os.path.join(results_dir, f"{controller}__{scenario}__{seed}.json")


def run(controller, scenario, seed, force=False, results_dir=RESULTS_DIR, args=None, quiet=False):
    args = args or argparse.Namespace()
    backend = getattr(args, "vlam_backend", None)
    if controller == "africot_full" and (backend or "mock") == "mock" and results_dir == RESULTS_DIR:
        # mock-VLAM runs are wiring checks only and are never reported as VLAM results
        results_dir = MOCK_RESULTS_DIR
    path = result_path(controller, scenario, seed, results_dir)
    if os.path.exists(path) and not force:
        if not quiet:
            print(f"skip (exists): {path}")
        return path
    args.seed = seed
    args.scenario = scenario
    ctrl, extra = build_controller(controller, args)
    perception = Perception(seed)
    run_id = f"{controller}__{scenario}__{seed}" + (f"__{extra['vlam_backend']}" if extra.get("vlam_backend") else "")
    log = ExplainLog(run_id, controller, scenario, seed, vlam_backend=extra.get("vlam_backend"), ctrl=ctrl)
    try:
        metrics, info = run_episode(ctrl, scenario, seed, observe=perception, decision_hook=log)
    finally:
        log.close()
    info["log_file"] = os.path.relpath(log.path, ROOT)
    coord = getattr(ctrl, "subgoal_source", None)
    if coord is not None and hasattr(coord, "calls"):
        metrics["slow_loop_calls"] = len(coord.calls)
        metrics["vlam_parse_failures"] = coord.parse_failures
        metrics["novelty_triggers"] = sum(1 for ev in coord.events if ev["event"] == "novelty_trigger")
        info["coordinator_events"] = coord.events
        lat = [c["latency_s"] for c in coord.calls]
        info["vlam_latency_mean_s"] = float(sum(lat) / len(lat)) if lat else None
    out = {
        "controller": controller,
        "scenario": scenario,
        "seed": seed,
        "seed_role": seed_role(seed),
        "vlam_backend": extra.get("vlam_backend"),
        "reportable": extra.get("reportable", True),
        "metrics": metrics,
        "info": info,
        "config": {
            "scenario": sc.get(scenario),
            "warmup_s": sc.WARMUP_S,
            "measure_s": sc.MEASURE_S,
            "controller_params": {k: v for k, v in vars(type(ctrl)).items()
                                  if k.isupper() and isinstance(v, (int, float, str, dict, tuple))},
            "perception": {"miss_p": 0.05, "rel_sd": 0.10, "min_sd": 0.5, "clean": False},
            "shield": {"enabled": True, "min_green": shield.MIN_GREEN, "max_green": shield.MAX_GREEN,
                       "starvation_s": shield.STARVATION_S, "crossing_times": shield.crossing_times()},
            **{k: v for k, v in extra.items() if k != "vlam_backend"},
        },
        "git_hash": git_hash(),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    os.makedirs(results_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    if not quiet:
        m = metrics
        print(f"{controller} {scenario} {seed}: AWT {m['awt']:.1f} ATT {m['att']:.1f} AQL {m['aql']:.1f} "
              f"thr {m['throughput']} ped {m['ped_wait']:.1f} teleports {m['teleports']} "
              f"shield {m['shield_interventions']} violations {m.get('safety_violations')} -> {path}")
    return path


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--controller", required=True)
    p.add_argument("--scenario", required=True, choices=list(sc.SCENARIOS))
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--vlam-backend", default="mock", choices=["mock", "hf"])
    p.add_argument("--vlam-model", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--results-dir", default=RESULTS_DIR)
    args = p.parse_args(argv)
    run(args.controller, args.scenario, args.seed, force=args.force, results_dir=args.results_dir, args=args)


if __name__ == "__main__":
    sys.exit(main())
