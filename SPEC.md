# AfriCoT-VLA Prototype: Build Specification

This is the single source of truth for the build. Every agent (builder, reviewer, documenter) works from this file. The visual version is `docs/design.html`.

Author: Temitope W. Ariyo, Machine Learning Research Group, Department of Artificial Intelligence and Robotics, University of Lagos. Supervisor: Dr. Ebun P. Fasina.

## 1. Goal

Build and test a single-junction prototype of AfriCoT-VLA in SUMO. The prototype couples a vision-language-action model (VLAM) with Chain-of-Thought (CoT) reasoning to a latent world model (LWM) through a compact subgoal. It runs one Lagos-style T-junction with mixed informal transit.

- **Slow loop:** the VLAM reads a junction snapshot plus context, reasons step by step, and outputs a subgoal.
- **Fast loop:** the LWM predicts queues and a CEM planner picks signal timings that minimise the subgoal-defined cost.
- **Safety shield:** a rule layer sits between the planner and the signals and cannot be bypassed.

This is a dissertation prototype. Results feed Chapter 4, so **correctness and honesty matter more than impressive numbers**.

## 2. Integrity rules (non-negotiable)

1. Never fabricate, estimate or hand-edit a result. Every number in `results/` must come from a run that the committed code can reproduce.
2. Tuning uses seeds 100 to 104. Reported evaluation uses seeds 0 to 4. Never tune on evaluation seeds.
3. If a component underperforms (for example the planner loses to max-pressure), report it as it is. Do not quietly change the test to make it pass. Record it in `STATUS.md` notes.
4. The mock VLAM backend exists only for unit tests and wiring checks. Never report mock-VLAM runs as VLAM results. Result files must record which backend produced them.
5. Any deviation from this spec must be written in `DEVIATIONS.md` with the reason.

## 3. Environment

- Python 3.10 or newer. Dependencies pinned in `requirements.txt`.
- SUMO through pip: `eclipse-sumo`, `traci`, `sumolib`. Set `SUMO_HOME` from the `sumo` package if needed (`import sumo; sumo.SUMO_HOME`).
- PyTorch on CPU for the world model.
- `transformers` and `accelerate` for the VLAM backend (Qwen2.5-VL family).
- `pytest` for tests. Every stage adds tests under `tests/`.
- The code must run headless (no `sumo-gui`).

## 4. Junction and traffic

**Traffic drives on the right (Nigeria).**

### Network
- T-junction, signalised. Arms: **east**, **west** (main road) and **south** (side road).
- Main road: 2 lanes each way. Side road: 1 lane each way. Approach length 300 m on every arm.
- Speed limit 50 km/h on the main road, 40 km/h on the side road.
- Pedestrian crossings on all three arms, with sidewalks.
- Build from `.nod.xml` / `.edg.xml` (and `.con.xml` if needed) with `netconvert`. Commit both the sources and the generated `.net.xml`.
- Use the sublane model (`--lateral-resolution 0.8`) so motorcycles can filter between lanes.

### Movements and phases
- Movements: W→E through, W→S right, E→W through, E→S left, S→E right, S→W left.
- Three signal phases:
  - **A, main road:** W→E, W→S, E→W green; E→S permissive (yields). Pedestrians cross the **south** arm.
  - **B, east protected left:** E→S and E→W green (W→E red). No pedestrian crossing.
  - **C, side road:** S→E, S→W green. Pedestrians cross the **east** and **west** arms.
- Every phase change goes through **amber 3 s** then **all-red 2 s**.
- No conflicting movements may ever be green together. Write a test that checks this from the signal states.

### Vehicle types (`vtypes.add.xml`)
| id | vClass | length (m) | max speed (km/h) | notes |
|---|---|---|---|---|
| car | passenger | 4.5 | 60 | |
| danfo | bus | 5.5 | 50 | minibus, counts as transit |
| keke | passenger (or custom) | 2.7 | 40 | tricycle, narrow (width 1.4 m) |
| okada | motorcycle | 2.0 | 60 | width 0.8 m, lane-splitting through sublane settings (`latAlignment="arbitrary"`, low `minGapLat`) |

Pedestrians use the default `ped_pedestrian` type.

### Scenarios
One simulated hour each (3600 s), after a 300 s warm-up that is excluded from metrics.

| scenario | main road per direction | side road | mix car/danfo/keke/okada | pedestrians | event |
|---|---|---|---|---|---|
| normal | 700 veh/h | 300 veh/h | 45/20/15/20 | 300 ped/h total | none |
| market | 700 veh/h | 550 veh/h | 30/20/25/25 | 900 ped/h total, mostly crossing east and west arms | none |
| incident | as normal | as normal | as normal | as normal | right lane of the east approach blocked 1200 s to 2100 s (for example through `traci.lane.setDisallowed` or a stopped vehicle) |
| outage | as market | as market | as market | as market | slow loop unreachable 1200 s to 2400 s |

Turning shares: from west, 80% through and 20% right to south. From east, 75% through and 25% left to south. From south, 50/50.

Demand should be generated with randomness that depends on the seed. Tune demand on tuning seeds only, so that the scenario is congested but not gridlocked under fixed-time. The target is fixed-time average waiting time well above free-flow, with no teleports caused by jams. Record the final demand values.

## 5. Components

### 5.1 `env.py` (TraCI wrapper)
- `reset(scenario, seed)`, `step_until(t)`, `apply_phase(phase, green_s)` (inserts amber and all-red), `get_state()`, `close()`.
- Decisions happen at the end of each green. The controller returns `(next_phase, green_seconds)`.

### 5.2 `perception.py`
- Per approach (east, west, south):
  - queue length (halting vehicles)
  - counts by class (car, danfo, keke, okada)
  - occupancy
  - waiting pedestrians at each crossing
- Noise: Gaussian on counts (sd = 10% of value, minimum 0.5), and each vehicle missed with probability 0.05. Clip to zero. Seeded.
- An option to return clean ground truth, used only for metrics and never for control.

### 5.3 `metrics.py`
- From SUMO `tripinfo` output and per-step sampling:
  - average travel time (ATT)
  - average waiting time (AWT)
  - average queue length (AQL, the mean over steps of halting vehicles summed over incoming lanes)
  - throughput (vehicles arrived)
  - average pedestrian waiting time
- Also logged: shield interventions, slow-loop calls and VLAM parse failures.
- Exclude the warm-up from every metric.

### 5.4 `baselines.py`
- **fixed_time:** cycle A 35 s, B 12 s, C 25 s (plus amber and all-red). Tune only if the scenario fails to run, and record it if so.
- **count_timer** (camera count plus timer, actuated): green starts at minimum 10 s and extends in 5 s steps while the served queue is at least 3, up to 60 s. The phases cycle in order A, B, C.
- **max_pressure:** at each decision, pick the phase whose served movements have the largest total queue. For a single isolated junction, downstream is treated as empty. Fixed green of 15 s. The shield still applies.

### 5.5 `shield.py`
- Minimum green 10 s and maximum green 90 s.
- Amber 3 s and all-red 2 s are always inserted.
- A pedestrian phase must give at least the crossing time (crossing length / 1.2 m/s + 4 s) when pedestrians are waiting.
- Starvation guard: any approach waiting longer than 180 s gets served next.
- Every correction is returned with a reason so it can be logged.
- Tests feed deliberately unsafe proposals and check that each is corrected.

### 5.6 `world_model.py` (latent world model)
- **Observation vector:**
  - perception output (noisy)
  - current phase (one-hot)
  - time in phase
  - time of day (normalised)
- **Action:** next phase (one-hot) and green duration (normalised).
- **Model:**
  - an MLP encoder maps the observation to a 32-dimensional latent
  - a GRU cell takes the latent and the action and gives the next latent
  - an MLP decoder predicts the next-decision queues per approach, pedestrian waiting and departures
  - multi-step rollout is supported, for planning
- **Data:**
  - transitions logged from fixed_time, count_timer, max_pressure and random-timing controllers
  - all scenarios
  - tuning seeds plus extra data seeds 200 to 219
  - never evaluation seeds
- **Training:** CPU, MSE loss, Adam, early stopping on a held-out split. Save the weights and the training curve.
- **Check:** on held-out data, the 1-step MAE of queue prediction must beat the persistence guess ("queues stay the same") by at least 10%. Report 1-step and 3-step errors.
- It is "in the style of" DreamerV3 and TD-MPC2. Do not claim it is either.

### 5.7 `planner_cem.py`
- Cross-Entropy Method over 3-step plans. Each step is a phase (categorical) and a green time (Gaussian, clipped to 10 to 60 s).
- 64 samples, 4 iterations, 8 elites. Seeded.
- **Cost** of an imagined rollout, summed over the horizon:
  `sum_a w_a * queue_a + pedestrian_weight * ped_wait + transit_priority * waiting_danfos + 1000 * max(0, est_wait_a - max_wait_s)`
- Only the first step is executed, after the shield.
- **Controller variants:**
  - `africot_full`: slow loop on
  - `africot_noslow`: fixed default subgoal (the "without slow loop" ablation)
  - `africot_nowm`: no world model; scores candidate first steps with a simple queue-discharge heuristic from current queues (the "without world model" ablation)

### 5.8 `subgoal.py`
Schema and ranges. Clamp any value outside its range. An unparseable response keeps the previous subgoal.

```json
{
  "queue_weights": {"east": 1.0, "west": 1.0, "south": 1.0},
  "pedestrian_weight": 1.0,
  "max_wait_s": 120,
  "transit_priority": 1.0,
  "valid_for_s": 300
}
```

| field | range |
|---|---|
| queue_weights.* | 0.2 to 3.0 |
| pedestrian_weight | 0.0 to 3.0 |
| max_wait_s | 45 to 180 |
| transit_priority | 0.0 to 2.0 |
| valid_for_s | 60 to 900 |

The block above is the default subgoal. The file also holds a **cached time-of-day schedule** (a small table of subgoals by hour), used in long outages.

### 5.9 `renderer.py`
- matplotlib top-down image of the junction: road outlines, crossings, vehicles drawn as shapes coloured by class, waiting pedestrians as dots, and the current signal state.
- Includes a legend.
- 512×512 PNG. It stands in for a camera keyframe.

### 5.10 `vlam.py`
Backends:
- `mock`: deterministic rules. **Only for tests and wiring.**
- `hf`: Hugging Face transformers with `Qwen/Qwen2.5-VL-3B-Instruct` (CPU tests) or `Qwen/Qwen2.5-VL-7B-Instruct` (GPU, Colab). The model id is configurable.

Prompt contents:
- the image
- a context block: simulated clock time, scenario context such as "market day" or "incident reported on east approach" when known, the current queues and the current subgoal
- the subgoal schema with its ranges

The model is asked to reason step by step inside `<reasoning>...</reasoning>`, then output JSON inside `<subgoal>...</subgoal>`.

Handling the output:
- Parse it and pass it to the subgoal validator.
- Record the raw text, the parsed subgoal, the latency and any parse failure.
- Use greedy decoding (temperature 0) for reproducibility.

### 5.11 `coordinator.py`
- Calls the slow loop every 300 simulated seconds, and early when the novelty trigger fires.
- **Connectivity:**
  - scenario-defined outage windows
  - when offline, hold the last subgoal
  - if offline for more than 600 s, switch to the cached time-of-day subgoal
  - log every switch
- **Novelty trigger:**
  - rolling 1-step world-model error over the last 10 decisions
  - fires when the error exceeds 2× the rolling median of the previous 30
  - at least 120 s between triggers
- An emergency override is described in the dissertation, not built.

### 5.12 `log.py` (explainability log)
- One JSON line per decision, with these fields:
  - sim time, controller, scenario, seed
  - trigger (scheduled / novelty / none)
  - connectivity state
  - VLAM backend
  - CoT reasoning text
  - subgoal
  - CEM plan
  - shield correction and its reason
  - applied phase and green
  - world-model 1-step error
- Written to `logs/<run_id>.jsonl`.

### 5.13 Running and plotting
- `run_experiment.py --controller X --scenario Y --seed N [--vlam-backend mock|hf] [--vlam-model ID]`
  - writes `results/<controller>__<scenario>__<seed>.json` with the metrics plus the full config, code git hash and backend
  - skips runs that already exist unless `--force`
- `run_grid.py`: runs a list of combinations, resumable.
- `plots.py`: matplotlib figures and tables. No figure numbers baked into images. Times New Roman where available, serif fallback.
- `colab_experiments.ipynb`:
  - installs requirements
  - mounts Google Drive and writes results there
  - runs the `africot_full` grid with the 7B model on GPU
  - resumable

## 6. Stages

Each stage ends with its checks passing, the tests committed and `STATUS.md` updated. Run the full test suite (`pytest -q`) at the end of every stage.

| id | stage | done when |
|---|---|---|
| S0 | Environment and skeleton | `pip install -r requirements.txt` works; a smoke test runs a tiny SUMO sim through TraCI; package layout as in section 7 |
| S1 | Junction and scenarios | network builds; the phase-conflict test passes; all 4 scenarios run 3900 s under fixed_time on tuning seeds with zero jam teleports; okadas observed lane-filtering (lateral positions vary within lanes) |
| S2 | Perception, metrics, baselines | all 3 baselines run all 4 scenarios on eval seeds 0–4, results saved; max_pressure AWT is lower than fixed_time on `normal` (if not, investigate and record) |
| S3 | Safety shield | unsafe-proposal tests pass; baselines rerun through the shield show no rule violations |
| S4 | Latent world model | data collected, model trained, beats persistence by ≥10% 1-step MAE on held-out data; weights, curve and metrics committed |
| S5 | CEM planner (`africot_noslow`, `africot_nowm`) | both run all scenarios on eval seeds; results saved; comparison against max_pressure recorded honestly |
| S6 | Slow loop | renderer image committed as an example; the mock backend passes wiring tests; the `hf` backend with the smallest model that fits the machine (3B preferred, `HuggingFaceTB/SmolVLM-256M-Instruct` acceptable for a wiring smoke test if memory is short) produces a parseable subgoal on at least one real snapshot, with the output saved to `examples/`; validator tests pass |
| S7 | Integration | `africot_full` runs end to end with the mock backend on all scenarios (wiring only, not reported); the outage scenario shows hold-last then the cached-schedule switch in the log; the novelty trigger fires in the incident scenario (if not, record it) |
| S8 | Experiment tooling | `run_grid.py`, `plots.py` and the Colab notebook are done; figures produced from all real results available so far (baselines, noslow, nowm); a results table is written to `results/summary.csv` |

## 7. Layout

```
africot-vla/
  SPEC.md  STATUS.md  DEVIATIONS.md  CLAUDE.md  README.md  requirements.txt
  sim/            network sources, net.xml, vtypes, routes, sumocfg, demand generator
  africot/        env, perception, metrics, baselines, shield, world_model, planner_cem,
                  subgoal, renderer, vlam, coordinator, log
  tests/
  models/         world model weights and training curve
  results/        one JSON per run, summary.csv
  logs/           explainability logs (JSONL)
  figures/
  examples/       sample snapshot, sample VLAM output
  reviews/        reviewer reports, one per stage
  docs/           design.html, stages/ (documenter write-ups)
  run_experiment.py  run_grid.py  plots.py  colab_experiments.ipynb
```

Large or bulky outputs (big logs, model downloads) must not be committed. Use `.gitignore`. Commit small, representative examples instead.
