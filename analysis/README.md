# analysis/

Files used for the dissertation and journal paper, added after the africot_full evaluation.

- `facts.json`: every number used in the documents, built from the committed result files (120 evaluated runs).
- `paired_tests_africot_full.json`: exploratory paired by-seed tests of africot_full against the other controllers (n = 5, no multiplicity correction; exact Wilcoxon and a t-test with 4 degrees of freedom, computed in plain Python and checked against an existing committed test).
- `summarise_results.py`: rebuilds `results/summary.csv` and `results/summary.md` without numpy or matplotlib; it reproduced the committed summary for the original controllers exactly.

The bar-chart figures in `figures/` were not regenerated with the africot_full runs.
