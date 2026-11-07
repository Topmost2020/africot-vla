# analysis/

Files used for the dissertation and journal paper, added after the africot_full evaluation.

- `facts.json`: every number used in the documents, built from the committed result files (120 evaluated runs).
- `paired_tests_africot_full.json`: exploratory paired by-seed tests of africot_full against the other controllers (n = 5, no multiplicity correction; exact Wilcoxon and a t-test with 4 degrees of freedom, computed in plain Python and checked against an existing committed test).
- `summarise_results.py`: rebuilds `results/summary.csv` and `results/summary.md` without numpy or matplotlib; it reproduced the committed summary for the original controllers exactly.

The bar-chart figures in `figures/` were regenerated with `python plots.py` after the africot_full runs and now include africot_full.

Added with the orchestrators:

- `figures_extra.py`: builds `figures/paired_noslow_vs_maxpressure.png` and `figures/shield_corrections_by_rule.png` from the committed result files (shield totals 6092, 117 and 2, matching the dissertation text).
- `figure_orchestration.py`: draws `figures/orchestration_hierarchy.png`.
- `compare_runs.py`: compares two result folders and their decision logs, used to show that the junction orchestrator reproduces the earlier coordinator exactly on africot_full (mock backend), normal and outage, seed 0.

`scripts/build_facts.py` is on the `main` branch, not on this one.
