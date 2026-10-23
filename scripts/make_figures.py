"""Extra figures for the dissertation and paper. Data from facts/facts.json and committed results. No figure numbers in images."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT, exist_ok=True)
F = json.load(open(os.path.join(ROOT, "facts", "facts.json"), encoding="utf-8"))
names = {f.name for f in font_manager.fontManager.ttflist}
fam = "Times New Roman" if "Times New Roman" in names else "serif"
plt.rcParams.update({"font.family": fam, "font.size": 9, "savefig.dpi": 200, "axes.spines.top": False, "axes.spines.right": False})
print("font:", fam)


def box(ax, x, y, w, h, text, fc="#e8eef7", ec="#335", fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p, q, text=None, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9, lw=0.9, color="#333", linestyle=ls))
    if text:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.12, text, ha="center", fontsize=7, style="italic")


def architecture():
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis("off")
    box(ax, 0.2, 5.6, 2.6, 1.0, "Camera keyframes\nand context\n(time, event, queues)", "#f4efe2")
    box(ax, 3.6, 5.6, 3.0, 1.0, "Slow loop (minutes)\nVLAM with CoT reasoning", "#dfeadf", bold=True)
    box(ax, 7.4, 5.6, 2.4, 1.0, "Subgoal\ncost weights and bounds", "#f6e3e3")
    arrow(ax, (2.8, 6.1), (3.6, 6.1)); arrow(ax, (6.6, 6.1), (7.4, 6.1))
    box(ax, 0.2, 3.3, 2.6, 1.1, "Edge perception\nqueues, counts,\noccupancy (noisy)", "#f4efe2")
    box(ax, 3.6, 3.3, 3.0, 1.1, "Fast loop (every decision)\nlatent world model +\nCEM planner", "#dfeadf", bold=True)
    box(ax, 7.4, 3.3, 2.4, 1.1, "Safety shield\n(rule-based,\nnot bypassable)", "#f6e3e3", bold=True)
    arrow(ax, (2.8, 3.85), (3.6, 3.85)); arrow(ax, (6.6, 3.85), (7.4, 3.85), "proposal")
    arrow(ax, (8.6, 5.6), (6.0, 4.4), "weights")
    arrow(ax, (1.5, 5.6), (1.5, 4.4), "keyframe", ls="--")
    box(ax, 7.4, 1.4, 2.4, 1.0, "Signal controller\n(amber, all-red)", "#e8eef7")
    arrow(ax, (8.6, 3.3), (8.6, 2.4), "safe phase")
    box(ax, 3.6, 1.4, 3.0, 1.0, "Explainability log\ntimestamp, CoT, subgoal,\nplan, shield correction", "#ececec")
    arrow(ax, (7.4, 1.9), (6.6, 1.9), style="<|-", ls="--")
    box(ax, 0.2, 1.4, 2.6, 1.0, "Coordinator\nconnectivity, novelty", "#fff3cc")
    arrow(ax, (1.5, 2.4), (1.5, 3.3), ls="--")
    arrow(ax, (2.8, 1.9), (3.6, 1.9), ls="--")
    ax.text(5.0, 0.55, "Degradation: full connectivity, hold last subgoal, cached time-of-day schedule, fixed-time plan on fault", ha="center", fontsize=7.5, style="italic")
    fig.savefig(os.path.join(OUT, "architecture_two_timescale.png"), bbox_inches="tight"); plt.close(fig)


def layers():
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 9); ax.axis("off")
    L = ["1 Sensor layer (cameras, signal actuators)", "2 Network connection (keyframes, not continuous video)", "3 Data store (hot window, cold history)",
         "4 Model layer (CoT, LWM, VLAM)", "5 Explainability layer (audit log, deployment gate)", "6 Service layer (decision, query, override, health APIs)",
         "7 AI agent layer (corridor coordination)", "8 Autonomous agentic layer (plans, what-if, human sign-off)"]
    for i, t in enumerate(L):
        y = i * 1.05 + 0.3
        fc = "#dfeadf" if i < 4 else "#e8eef7"
        box(ax, 0.3, y, 7.2, 0.85, t, fc, fs=8)
    ax.annotate("", xy=(8.2, 8.5), xytext=(8.2, 0.4), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(8.45, 4.5, "layers above 4 may fail;\nfast loop and shield\nkeep running, fixed-time\nplan on fault", fontsize=7, va="center")
    fig.savefig(os.path.join(OUT, "eight_layer_framework.png"), bbox_inches="tight"); plt.close(fig)


def outage_timeline():
    ev = F["mock_wiring"]["outage_connectivity_switches_seed0"]
    fig, ax = plt.subplots(figsize=(6.5, 1.8))
    cols = {"online": "#55a868", "offline_hold_last": "#dd8452", "offline_cached_schedule": "#c44e52"}
    lab = {"online": "online (scheduled slow loop)", "offline_hold_last": "offline: hold last subgoal", "offline_cached_schedule": "offline: cached schedule"}
    end = 3900
    for i, (t, s) in enumerate(ev):
        t2 = ev[i + 1][0] if i + 1 < len(ev) else end
        ax.barh(0, t2 - t, left=t, color=cols[s], edgecolor="white", label=lab[s] if lab[s] not in ax.get_legend_handles_labels()[1] else None)
    ax.set_yticks([]); ax.set_xlabel("Simulation clock (s)"); ax.set_xlim(0, end)
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.5))
    fig.savefig(os.path.join(OUT, "outage_degradation_timeline.png"), bbox_inches="tight"); plt.close(fig)


def shield_bar():
    t = F["shield_total_by_rule"]
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    k = ["ped_crossing", "max_green", "starvation"]
    ax.bar(k, [t.get(x, 0) for x in k], color="#4c72b0")
    ax.set_yscale("log"); ax.set_ylabel("Corrections (count, log scale)")
    for i, x in enumerate(k):
        ax.text(i, t.get(x, 0) * 1.1, str(t.get(x, 0)), ha="center", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "shield_corrections_by_rule.png")); plt.close(fig)


def wm_bars():
    T = F["world_model"]["test"]
    steps = ["1step", "2step", "3step"]
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    x = np.arange(3)
    ax.bar(x - 0.2, [T[s]["queue_mae_model"] for s in steps], 0.4, label="World model", color="#55a868")
    ax.bar(x + 0.2, [T[s]["queue_mae_persistence"] for s in steps], 0.4, label="Persistence", color="#999999")
    ax.set_xticks(x); ax.set_xticklabels(["1 step", "2 steps", "3 steps"]); ax.set_ylabel("Queue MAE, held-out (veh)")
    ax.legend(frameon=False, fontsize=8); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "world_model_vs_persistence.png")); plt.close(fig)


def paired():
    P = [p for p in F["paired_tests"] if p["a"] == "africot_noslow" and p["b"] == "max_pressure"]
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    sc = [p["scenario"] for p in P]
    ax.bar(sc, [p["mean_diff_a_minus_b"] for p in P], yerr=[p["sd_diff"] / np.sqrt(5) for p in P], capsize=3, color="#8172b3")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("AWT difference, no-slow minus\nmax pressure (s, mean and SE)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "paired_noslow_vs_maxpressure.png")); plt.close(fig)


for f in (architecture, layers, outage_timeline, shield_bar, wm_bars, paired):
    f()
print(sorted(os.listdir(OUT)))
