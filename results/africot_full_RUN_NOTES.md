# africot_full evaluation run

- Controller: africot_full (slow loop, latent world model, CEM planner, safety shield).
- VLAM: Hugging Face backend, Qwen/Qwen2.5-VL-3B-Instruct, greedy decoding, float16.
- Hardware: Google Colab, one NVIDIA T4 GPU. The 7B model named in the original plan does not fit a free T4.
- Grid: 4 scenarios (normal, market, incident, outage) x seeds 0 to 4 = 20 runs, all completed, 0 failed.
- Code: commit cf3e7ed on claude/africot-build, with one runtime change made in the notebook after cloning:
  `dtype="bfloat16"` replaced by `dtype="float16"` in africot/vlam.py (the T4 has no native bfloat16).
  The `-dirty` suffix on `git_hash` in each result file comes from that change; no repository file was edited.
- Result files: `africot_full__<scenario>__<seed>.json`, copied unchanged from Google Drive.
- Not yet done: summary.csv, summary.md and the figures have not been regenerated with these runs.
