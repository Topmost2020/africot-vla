# Build status

States: todo, building, built, approved, changes_requested, documented. Protocol in `CLAUDE.md`.

| id | stage | state | notes |
|---|---|---|---|
| S0 | Environment and skeleton | built | 2026-10-06 built: requirements pinned (SUMO 1.27.1, torch 2.14.1 CPU, transformers 5.19.0); TraCI smoke test passes; pytest 1 passed |
| S1 | Junction and scenarios | building | 2026-10-06 builder started |
| S2 | Perception, metrics, baselines | todo | |
| S3 | Safety shield | todo | |
| S4 | Latent world model | todo | |
| S5 | CEM planner (noslow, nowm) | todo | |
| S6 | Slow loop (renderer, VLAM, validator, coordinator, log) | todo | |
| S7 | Integration | todo | |
| S8 | Experiment tooling, Colab notebook, figures | todo | |
