# Deviations from SPEC.md

Record every deviation with the date, the stage, what changed and why.

| date | stage | deviation | reason |
|---|---|---|---|
| 2026-10-06 | S1 | Incident block is a broken-down vehicle inserted through TraCI at 1200 s at the first free position on the kerb lane of the east approach (`E2C_1`), then stopped there until 2100 s. On tuning seeds it stops between 1203 s and 1206 s, usually about 5 m from the start of the approach, so the kerb lane is blocked for the length of the approach downstream of it. | The spec allows "a stopped vehicle". A vehicle preloaded in the route file at a fixed position near the stop line was either teleported by a collision on insertion or reached its stop only 30 to 110 s late behind the queue. Inserting at a free spot gives a reliable start within a few seconds. |
| 2026-10-06 | S1 | Scenario event times (incident 1200 to 2100 s, outage 1200 to 2400 s) are read as simulation clock times, which include the 300 s warm-up. | The spec does not say which clock. Both windows fall inside the measured period either way. |
| 2026-10-06 | S1 | The "zero jam teleports" check counts teleports whose SUMO reason is `jam`. Across the 20 tuning runs there were 2 teleports with reason `yield` (market and outage, seed 103, the same okada turning S to W waiting to yield to pedestrians) and 0 with reason `jam`. | A yield teleport is a junction-blocking artefact of the sublane model with dense pedestrian flow, not a congestion jam. Both counts are recorded in `results/s1_scenario_check.json`. |
