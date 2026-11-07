"""Figures 10 and 11 of the dissertation, built from the committed result files.

    python analysis/figures_extra.py

Figure 10: paired difference in average waiting time, africot_noslow minus max_pressure.
Figure 11: shield corrections by rule, summed over all reportable evaluation runs
(all six controllers, including africot_full), on a logarithmic scale.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plots

RULES = ["ped_crossing", "max_green", "starvation"]


def main():
    plots.set_style()
    rows = plots.load(os.path.join(ROOT, "results"))
    by = {(d["controller"], d["scenario"], d["seed"]): d for d in rows}
    out = os.path.join(ROOT, "figures")

    scen = [s for s in plots.SCENARIO_ORDER if s != "outage"]
    means, ses = [], []
    for s in scen:
        diff = [by[("africot_noslow", s, k)]["metrics"]["awt"] - by[("max_pressure", s, k)]["metrics"]["awt"]
                for k in range(5)]
        means.append(np.mean(diff))
        ses.append(np.std(diff, ddof=1) / np.sqrt(len(diff)))
    fig, ax = plt.subplots(figsize=(4.5, 3))
    ax.bar(scen, means, yerr=ses, capsize=3, color="#4c72b0", error_kw={"linewidth": 0.8})
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_ylabel("AWT difference (s), noslow minus max-pressure")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "paired_noslow_vs_maxpressure.png"))
    plt.close(fig)

    totals = {r: 0 for r in RULES}
    for d in rows:
        for rule, n in d["info"].get("shield_corrections_by_rule", {}).items():
            totals[rule] = totals.get(rule, 0) + n
    fig, ax = plt.subplots(figsize=(4.5, 3))
    names = list(totals)
    ax.bar(names, [totals[n] for n in names], color="#55a868")
    ax.set_yscale("log")
    ax.set_ylabel("Corrections (all evaluation runs)")
    for i, n in enumerate(names):
        ax.text(i, max(totals[n], 1) * 1.1, str(totals[n]), ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "shield_corrections_by_rule.png"))
    plt.close(fig)
    print("shield totals:", totals)


if __name__ == "__main__":
    main()
