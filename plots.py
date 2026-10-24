"""Figures and tables from the committed results (SPEC 5.13).

    python plots.py [--results-dir results] [--figures-dir figures]

Uses only reportable runs on evaluation seeds 0-4. Mock-VLAM runs
(results/mock_wiring, or any file with vlam_backend == "mock" or
reportable == false) are excluded. Writes results/summary.csv,
results/summary.md and figures/*.png. No figure numbers are baked into images.
"""
import argparse
import csv
import glob
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from africot import scenarios as sc  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTROLLER_ORDER = ["fixed_time", "count_timer", "max_pressure", "africot_nowm", "africot_noslow", "africot_full"]
LABELS = {"fixed_time": "Fixed time", "count_timer": "Count + timer", "max_pressure": "Max pressure",
          "africot_nowm": "AfriCoT (no WM)", "africot_noslow": "AfriCoT (no slow loop)",
          "africot_full": "AfriCoT (full)"}
SCENARIO_ORDER = list(sc.SCENARIOS)
METRICS = [("awt", "Average waiting time (s)"), ("att", "Average travel time (s)"),
           ("aql", "Average queue length (veh)"), ("throughput", "Throughput (veh)"),
           ("ped_wait", "Average pedestrian waiting time (s)")]
COLOURS = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3", "#937860"]


def set_style():
    names = {f.name for f in font_manager.fontManager.ttflist}
    family = "Times New Roman" if "Times New Roman" in names else "serif"
    plt.rcParams.update({"font.family": family, "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 200})
    return family


def load(results_dir):
    rows = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*__*__*.json"))):
        d = json.load(open(path))
        if d.get("vlam_backend") == "mock" or d.get("reportable") is False:
            continue
        if d.get("seed_role") != "evaluation":
            continue
        rows.append(d)
    return rows


def summarise(rows):
    groups = {}
    for d in rows:
        key = (d["controller"], d["scenario"], d.get("vlam_backend") or "none", (d["config"].get("vlam_model") or ""))
        groups.setdefault(key, []).append(d)
    out = []
    for (c, s, b, model), ds in groups.items():
        rec = {"controller": c, "scenario": s, "vlam_backend": b, "vlam_model": model, "n_seeds": len(ds),
               "seeds": " ".join(str(d["seed"]) for d in sorted(ds, key=lambda x: x["seed"]))}
        for k in ["awt", "att", "aql", "throughput", "ped_wait", "not_inserted", "awt_completed",
                  "shield_interventions", "safety_violations", "jam_teleports"]:
            vals = np.array([d["metrics"].get(k, np.nan) for d in ds], dtype=float)
            rec[f"{k}_mean"] = float(np.mean(vals))
            rec[f"{k}_sd"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        rec["git_hashes"] = " ".join(sorted({d["git_hash"][:8] for d in ds}))
        out.append(rec)
    order = {c: i for i, c in enumerate(CONTROLLER_ORDER)}
    sorder = {s: i for i, s in enumerate(SCENARIO_ORDER)}
    out.sort(key=lambda r: (sorder.get(r["scenario"], 99), order.get(r["controller"], 99)))
    return out


def write_tables(summary, results_dir):
    path = os.path.join(results_dir, "summary.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    md = os.path.join(results_dir, "summary.md")
    with open(md, "w") as f:
        f.write("Mean (SD) over evaluation seeds 0-4. AWT and ATT include insertion delay (see DEVIATIONS.md).\n\n")
        f.write("| scenario | controller | n | AWT (s) | ATT (s) | AQL (veh) | throughput | ped wait (s) | safety violations |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in summary:
            f.write(f"| {r['scenario']} | {r['controller']} | {r['n_seeds']} | "
                    f"{r['awt_mean']:.1f} ({r['awt_sd']:.1f}) | {r['att_mean']:.1f} ({r['att_sd']:.1f}) | "
                    f"{r['aql_mean']:.1f} ({r['aql_sd']:.1f}) | {r['throughput_mean']:.0f} ({r['throughput_sd']:.0f}) | "
                    f"{r['ped_wait_mean']:.1f} ({r['ped_wait_sd']:.1f}) | {r['safety_violations_mean']:.0f} |\n")
    return path, md


def bar_figure(summary, metric, ylabel, path):
    controllers = [c for c in CONTROLLER_ORDER if any(r["controller"] == c for r in summary)]
    scenarios = [s for s in SCENARIO_ORDER if any(r["scenario"] == s for r in summary)]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    width = 0.8 / len(controllers)
    x = np.arange(len(scenarios))
    for i, c in enumerate(controllers):
        means, sds = [], []
        for s in scenarios:
            r = next((r for r in summary if r["controller"] == c and r["scenario"] == s), None)
            means.append(r[f"{metric}_mean"] if r else np.nan)
            sds.append(r[f"{metric}_sd"] if r else 0)
        ax.bar(x + (i - (len(controllers) - 1) / 2) * width, means, width, yerr=sds, capsize=2,
               label=LABELS.get(c, c), color=COLOURS[i % len(COLOURS)], error_kw={"linewidth": 0.7})
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def wm_curve_figure(path):
    f = os.path.join(ROOT, "models", "wm_training_curve.csv")
    if not os.path.exists(f):
        return None
    data = np.genfromtxt(f, delimiter=",", names=True)
    fig, ax = plt.subplots(figsize=(4.5, 3))
    ax.plot(data["epoch"], data["train_loss"], label="training")
    ax.plot(data["epoch"], data["val_loss"], label="validation")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE (normalised targets)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", default=os.path.join(ROOT, "results"))
    p.add_argument("--figures-dir", default=os.path.join(ROOT, "figures"))
    a = p.parse_args(argv)
    family = set_style()
    rows = load(a.results_dir)
    if not rows:
        print("no reportable evaluation results found")
        return 1
    summary = summarise(rows)
    csv_path, md_path = write_tables(summary, a.results_dir)
    os.makedirs(a.figures_dir, exist_ok=True)
    made = []
    for m, label in METRICS:
        path = os.path.join(a.figures_dir, f"{m}_by_scenario.png")
        bar_figure(summary, m, label, path)
        made.append(path)
    wm_fig = wm_curve_figure(os.path.join(a.figures_dir, "world_model_training_curve.png"))
    if wm_fig:
        made.append(wm_fig)
    print(f"font: {family}; {len(rows)} runs; wrote {csv_path}, {md_path}")
    for m in made:
        print(" ", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
