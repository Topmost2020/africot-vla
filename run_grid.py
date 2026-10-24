"""Run a grid of (controller, scenario, seed) combinations. Resumable: existing
result files are skipped unless --force (SPEC 5.13).

    python run_grid.py --controllers fixed_time count_timer max_pressure --seeds 0 1 2 3 4 --jobs 4
"""
import argparse
import itertools
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from africot import scenarios as sc
import run_experiment


def _one(job):
    controller, scenario, seed, force, results_dir, extra = job
    args = argparse.Namespace(**extra)
    try:
        return run_experiment.run(controller, scenario, seed, force=force, results_dir=results_dir,
                                  args=args, quiet=True), None
    except Exception as e:  # keep the grid going; report at the end
        return None, f"{controller} {scenario} {seed}: {type(e).__name__}: {e}"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--controllers", nargs="+", required=True)
    p.add_argument("--scenarios", nargs="+", default=list(sc.SCENARIOS))
    p.add_argument("--seeds", nargs="+", type=int, default=list(sc.EVAL_SEEDS))
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--force", action="store_true")
    p.add_argument("--results-dir", default=run_experiment.RESULTS_DIR)
    p.add_argument("--vlam-backend", default="mock", choices=["mock", "hf"])
    p.add_argument("--vlam-model", default=None)
    args = p.parse_args(argv)
    extra = {"vlam_backend": args.vlam_backend, "vlam_model": args.vlam_model}
    jobs = [(c, s, seed, args.force, args.results_dir, extra)
            for c, s, seed in itertools.product(args.controllers, args.scenarios, args.seeds)]
    errors = []
    if args.jobs <= 1:
        for j in jobs:
            path, err = _one(j)
            print(path or err, flush=True)
            if err:
                errors.append(err)
    else:
        with ProcessPoolExecutor(args.jobs) as ex:
            futs = [ex.submit(_one, j) for j in jobs]
            for f in as_completed(futs):
                path, err = f.result()
                print(path or err, flush=True)
                if err:
                    errors.append(err)
    print(f"done: {len(jobs) - len(errors)} ok, {len(errors)} failed")
    for e in errors:
        print("FAILED", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
