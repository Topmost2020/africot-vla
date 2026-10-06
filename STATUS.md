# Build status

States: todo, building, built, approved, changes_requested, documented. Protocol in `CLAUDE.md`.

| id | stage | state | notes |
|---|---|---|---|
| S0 | Environment and skeleton | approved | 2026-10-06 reviewer: approved (pytest 23 passed on rerun; see reviews/S0.md). 2026-10-06 built: requirements pinned (SUMO 1.27.1, torch 2.14.1 CPU, transformers 5.19.0); TraCI smoke test passes; pytest 1 passed |
| S1 | Junction and scenarios | changes_requested | 2026-10-06 reviewer: changes requested (reviews/S1.md): incident blocker does not block the kerb lane downstream of it; market/outage south arm gridlocked under fixed_time (insertion delay mean 1228 s, seed 100); metrics exclude insertion delay and never-inserted vehicles. Results reproduce exactly. 2026-10-06 built: net builds (sim/build_net.sh), phase-conflict tests pass; fixed_time 3900 s on 4 scenarios x tuning seeds 100-104: 0 jam teleports (2 yield teleports, market/outage seed 103); mean AWT normal 43.0 s, market 78.0 s, incident 42.5 s, outage 78.0 s; okada lateral SD 0.84 m vs car 0.26 m (results/s1_scenario_check.json). Demand kept at spec values (no tuning needed). Incident barely raises AWT under fixed_time (one lane still carries the flow). pytest 23 passed. See DEVIATIONS.md |
| S2 | Perception, metrics, baselines | changes_requested | 2026-10-06 reviewer: changes requested (reviews/S2.md): market AWT ranking is an artefact of metrics excluding insertion delay (fixed_time leaves ~455 veh/run unserved vs 279-323); market scenario gridlocked (S1); result git_hash 434f552 not in repo. Results reproduce exactly. 2026-10-06 built: 3 baselines x 4 scenarios x eval seeds 0-4 (60 runs, no shield yet, noisy perception) in results/. Mean AWT normal: fixed_time 34.8 s, count_timer 42.4 s, max_pressure 17.5 s (max_pressure < fixed_time: yes). Market: fixed_time 73.5 s, count_timer 112.8 s, max_pressure 83.9 s, so both adaptive baselines lose to fixed_time on AWT under market demand while raising throughput (1592 vs 1734/1687). 0 jam teleports; 2 non-jam teleports. Outage equals market for baselines (no slow loop). pytest 32 passed |
| S3 | Safety shield | building | 2026-10-06 builder started |
| S4 | Latent world model | todo | |
| S5 | CEM planner (noslow, nowm) | todo | |
| S6 | Slow loop (renderer, VLAM, validator, coordinator, log) | todo | |
| S7 | Integration | todo | |
| S8 | Experiment tooling, Colab notebook, figures | todo | |
