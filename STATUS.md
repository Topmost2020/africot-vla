# Build status

States: todo, building, built, approved, changes_requested, documented. Protocol in `CLAUDE.md`.

| id | stage | state | notes |
|---|---|---|---|
| S0 | Environment and skeleton | built | 2026-10-06 built: requirements pinned (SUMO 1.27.1, torch 2.14.1 CPU, transformers 5.19.0); TraCI smoke test passes; pytest 1 passed |
| S1 | Junction and scenarios | built | 2026-10-06 built: net builds (sim/build_net.sh), phase-conflict tests pass; fixed_time 3900 s on 4 scenarios x tuning seeds 100-104: 0 jam teleports (2 yield teleports, market/outage seed 103); mean AWT normal 43.0 s, market 78.0 s, incident 42.5 s, outage 78.0 s; okada lateral SD 0.84 m vs car 0.26 m (results/s1_scenario_check.json). Demand kept at spec values (no tuning needed). Incident barely raises AWT under fixed_time (one lane still carries the flow). pytest 23 passed. See DEVIATIONS.md |
| S2 | Perception, metrics, baselines | building | 2026-10-06 builder started |
| S3 | Safety shield | todo | |
| S4 | Latent world model | todo | |
| S5 | CEM planner (noslow, nowm) | todo | |
| S6 | Slow loop (renderer, VLAM, validator, coordinator, log) | todo | |
| S7 | Integration | todo | |
| S8 | Experiment tooling, Colab notebook, figures | todo | |
