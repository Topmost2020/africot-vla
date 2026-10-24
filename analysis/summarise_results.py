"""Rebuild results/summary.csv and results/summary.md in plain Python (same method as the repository's plots.py,
without numpy or matplotlib). Usage: python summarise_results.py [results_dir]"""
import csv, glob, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results")
CONTROLLER_ORDER = ["fixed_time", "count_timer", "max_pressure", "africot_nowm", "africot_noslow", "africot_full"]
SCENARIO_ORDER = ["normal", "market", "incident", "outage"]
KEYS = ["awt", "att", "aql", "throughput", "ped_wait", "not_inserted", "awt_completed", "shield_interventions", "safety_violations", "jam_teleports"]

rows = []
for p in sorted(glob.glob(os.path.join(RD, "*__*__*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    if d.get("vlam_backend") == "mock" or d.get("reportable") is False or d.get("seed_role") != "evaluation":
        continue
    rows.append(d)
groups = {}
for d in rows:
    groups.setdefault((d["controller"], d["scenario"], d.get("vlam_backend") or "none", d["config"].get("vlam_model") or ""), []).append(d)
out = []
for (c, s, b, model), ds in groups.items():
    rec = {"controller": c, "scenario": s, "vlam_backend": b, "vlam_model": model, "n_seeds": len(ds),
           "seeds": " ".join(str(d["seed"]) for d in sorted(ds, key=lambda x: x["seed"]))}
    for k in KEYS:
        v = [float(d["metrics"].get(k, float("nan"))) for d in ds]
        rec[f"{k}_mean"] = statistics.fmean(v)
        rec[f"{k}_sd"] = statistics.stdev(v) if len(v) > 1 else 0.0
    rec["git_hashes"] = " ".join(sorted({d["git_hash"][:8] for d in ds}))
    out.append(rec)
co = {c: i for i, c in enumerate(CONTROLLER_ORDER)}
so = {s: i for i, s in enumerate(SCENARIO_ORDER)}
out.sort(key=lambda r: (so.get(r["scenario"], 99), co.get(r["controller"], 99)))
with open(os.path.join(RD, "summary.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
with open(os.path.join(RD, "summary.md"), "w", encoding="utf-8") as f:
    f.write("Mean (SD) over evaluation seeds 0-4. AWT and ATT include insertion delay (see DEVIATIONS.md).\n\n")
    f.write("| scenario | controller | n | AWT (s) | ATT (s) | AQL (veh) | throughput | ped wait (s) | safety violations |\n")
    f.write("|---|---|---|---|---|---|---|---|---|\n")
    for r in out:
        f.write(f"| {r['scenario']} | {r['controller']} | {r['n_seeds']} | {r['awt_mean']:.1f} ({r['awt_sd']:.1f}) | {r['att_mean']:.1f} ({r['att_sd']:.1f}) | "
                f"{r['aql_mean']:.1f} ({r['aql_sd']:.1f}) | {r['throughput_mean']:.0f} ({r['throughput_sd']:.0f}) | "
                f"{r['ped_wait_mean']:.1f} ({r['ped_wait_sd']:.1f}) | {r['safety_violations_mean']:.0f} |\n")
print("wrote", len(out), "rows")
