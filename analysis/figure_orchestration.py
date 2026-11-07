"""Orchestration hierarchy figure (dissertation Chapter 3). python analysis/figure_orchestration.py

Both orchestrators and the slow loop are drawn in the cloud tier (intended hosting);
perception, the world model, the CEM planner and the safety shield are drawn on site.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def box(ax, x, y, w, h, text, fc, fs=7.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="#333333", lw=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle=style, lw=0.8, color="#333333"))


fig, ax = plt.subplots(figsize=(6.8, 4.8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.2)
ax.axis("off")

ax.add_patch(Rectangle((0.05, 3.55), 9.9, 3.55, fill=False, ls="--", ec="#4a6fa5", lw=1))
ax.text(0.15, 6.85, "Cloud tier (intended hosting of the orchestrators and the slow loop)", fontsize=7,
        color="#4a6fa5", style="italic")
box(ax, 2.8, 5.7, 4.4, 0.8, "Network orchestrator\nreports from every junction; advisories", "#d9e4f5", 8, True)

for i, x in enumerate((0.25, 5.25)):
    jid = i + 1
    box(ax, x, 4.0, 3.0, 0.85, "Junction orchestrator J%d\nsupervises this junction's models" % jid, "#e3f1df", 7.5, True)
    box(ax, x + 3.2, 4.0, 1.3, 0.85, "Slow loop\n(VLAM)", "#f3f3f3", 7)
    arrow(ax, 5.0, 5.7, x + 1.5, 4.85, "<->")
    arrow(ax, x + 3.0, 4.42, x + 3.2, 4.42, "<->")
    ax.add_patch(Rectangle((x - 0.1, 1.55), 4.7, 1.55, fill=False, ls=":", ec="#8a5a3a", lw=1))
    ax.text(x, 1.65, "On site: edge computer at junction J%d" % jid, fontsize=6.5, color="#8a5a3a", style="italic")
    comps = ["Percep-\ntion", "World\nmodel", "CEM\nplanner", "Safety\nshield"]
    for j, c in enumerate(comps):
        cx = x + j * 1.12
        fc = "#f9e0d0" if c.startswith("Safety") else "#f3f3f3"
        box(ax, cx, 2.0, 1.0, 0.95, c, fc, 7)
        arrow(ax, x + 1.5, 4.0, cx + 0.5, 2.95, "<->")

ax.text(5.0, 0.75, "J2 is drawn to show the intended multi-junction case; the prototype runs one junction, in one process.\n"
        "Neither orchestrator can issue a phase command or relax the safety shield. If the cloud link fails,\n"
        "the on-site fallback (last subgoal, cached schedule, fixed-time plan) keeps the junction running.",
        ha="center", fontsize=6.8, style="italic")
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "figures", "orchestration_hierarchy.png"), dpi=200)
