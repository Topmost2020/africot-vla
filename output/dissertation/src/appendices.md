# Appendix A: Reproduction Commands

All commands are run from the root of the prototype repository. The code is designed so that every reported number can be regenerated from committed files, and an independent check at the third gate reproduced the normal-scenario, seed 0 results of the five non-VLAM controllers exactly, apart from wall time, git hash and a float difference of the order of 1e-8 in the world-model error. Install and test with the same interpreter, for example through `python -m pip`.

**A.1 Environment.** SUMO is installed from the pinned pip packages, so no separate system installation is required. The requirements file pins eclipse-sumo, traci and sumolib at version 1.27.1, numpy 2.4.6, matplotlib 3.11.2, pytest 9.1.1, torch 2.14.1 (CPU wheel index), torchvision 0.29.1, transformers 5.19.0, accelerate 1.15.0, pillow 12.3.0 and qwen-vl-utils 0.0.14. The helper in the package locates the SUMO binaries and sets `SUMO_HOME`; the graphical interface is never used.

- `python -m pip install -r requirements.txt`
- `sh sim/build_net.sh` (rebuilds `sim/junction.net.xml` with netconvert; the committed network is already built)

**A.2 Tests.** The test suite passed with {{tests.pytest_passed_at_start::0}} tests at the start of the documentation work and takes roughly {{tests.pytest_runtime_s::0}} s.

- `python -m pytest -q`

**A.3 Single runs and grids.** One controller on one scenario and seed writes `results/<controller>__<scenario>__<seed>.json`; existing results are skipped unless `--force` is given. The scenarios are normal, market, incident and outage; the controllers are fixed_time, count_timer, max_pressure, africot_noslow, africot_nowm and africot_full. The default VLAM backend is the mock, whose runs are written for wiring checks only and are never reported.

- `python run_experiment.py --controller max_pressure --scenario normal --seed 0`
- `python run_grid.py --controllers fixed_time count_timer max_pressure --seeds 0 1 2 3 4 --jobs 4`
- `python run_grid.py --controllers africot_noslow africot_nowm --seeds 0 1 2 3 4 --jobs 4`

**A.4 World model.** Data are collected on tuning seeds 100 to 104 and data seeds 200 to 219, never on evaluation seeds 0 to 4, and the model is then trained.

- `python train_world_model.py collect --jobs 4`
- `python train_world_model.py train`

**A.5 Tables, figures and facts.** The plotting script uses only reportable runs on evaluation seeds 0 to 4 and writes `results/summary.csv`, `results/summary.md` and the figures. The facts file from which every number in this document is filled is built from committed files only.

- `python plots.py`
- `python scripts/build_facts.py`

**A.6 The africot_full evaluation on a GPU (Colab).** This step has not yet been executed. The notebook `colab_experiments.ipynb` mounts Google Drive, clones the build branch, installs the requirements while keeping Colab's own CUDA build of PyTorch, runs two test files, and then runs the resumable grid with the Qwen2.5-VL-7B-Instruct backend. The 7B model in bfloat16 needs about 17 GB of GPU memory. The grid cell is:

- `python run_grid.py --controllers africot_full --scenarios normal market incident outage --seeds 0 1 2 3 4 --vlam-backend hf --vlam-model Qwen/Qwen2.5-VL-7B-Instruct --results-dir <Drive results folder> --jobs 1`

The notebook then prints the backend, model, slow-loop calls, parse failures and mean latency per run, and the final cell copies the result files into `results/` and reruns `python plots.py`. The smoke test of the 3B model on a CPU used the same hf backend and took {{vlam_smoke_test.latency_s::0}} s for one call.

# Appendix B: Scenario and Shield Parameters

Table: Scenario parameters (demand in vehicles per hour, pedestrians per hour, vehicle mix and event windows)

[[scenario_table]]

The measured period is {{measure_s::0}} s after a warm-up of {{warmup_s::0}} s. Scenario event times are simulation clock times that include the warm-up. Perception is designed to add noise to SUMO ground truth, with a miss probability of {{perception_config.miss_p::2}} per object, a relative standard deviation of {{perception_config.rel_sd::2}} and a minimum standard deviation of {{perception_config.min_sd::1}}.

Table: Safety shield and controller parameters

| Parameter | Value |
|---|---|
| Minimum green | {{shield_config.min_green::0}} s |
| Maximum green | {{shield_config.max_green::0}} s |
| Starvation limit | {{shield_config.starvation_s::0}} s |
| Pedestrian crossing time, east and west arms | {{shield_config.crossing_times.xE::0}} s |
| Pedestrian crossing time, south arm | {{shield_config.crossing_times.xS::0}} s |
| Amber | 3 s |
| All-red clearance | 2 s |
| Fixed-time greens (phases A, B, C) | {{fixed_time_params.GREENS.A::0}} s, {{fixed_time_params.GREENS.B::0}} s, {{fixed_time_params.GREENS.C::0}} s |
| max_pressure green | {{controller_params.max_pressure.GREEN::0}} s |
| count_timer minimum, step and maximum green | {{controller_params.count_timer.MIN_GREEN::0}} s, {{controller_params.count_timer.STEP::0}} s, {{controller_params.count_timer.MAX_GREEN::0}} s |
| Planner horizon, samples, iterations, elites | {{planner_config.horizon::0}}, {{planner_config.samples::0}}, {{planner_config.iterations::0}}, {{planner_config.elites::0}} |
| Default subgoal: max wait, validity | {{default_subgoal.max_wait_s::0}} s, {{default_subgoal.valid_for_s::0}} s |

# Appendix C: Full Results

The table gives, for every scenario and controller, the mean over five evaluation seeds of average waiting time (AWT), average travel time (ATT), average queue length (AQL), throughput and pedestrian waiting time. The `africot_full` controller has no row because it has not been evaluated. Outage rows equal market rows for every controller shown, because those controllers have no slow loop.

Table: Full results by scenario and controller (mean and standard deviation over five seeds)

[[results_table:full]]

# Appendix D: Deviations from the Specification

The table summarises the entries of the deviation record kept during the build. Dates are those of the record, and all fall on 6 October 2026.

Table: Deviations from the build specification

| Stage | Deviation | Reason |
|---|---|---|
| S1 | The first incident was a broken-down vehicle on the kerb lane. It was superseded the same day by the lane closure below. | Traffic passed the vehicle and used the kerb lane downstream, so the lane was not blocked. |
| S1 | Incident: the kerb lane of the east approach is closed to passenger, bus and motorcycle demand with a TraCI permission change from 1200 s to 2100 s, then restored. Vehicles already on the lane at 1200 s may clear it. | This blocks the whole lane up to the stop line, so east-approach traffic shares the median lane. |
| S1 | Event times (incident 1200 to 2100 s, outage 1200 to 2400 s) are read as simulation clock times, including the 300 s warm-up. | The specification does not say which clock; both windows fall inside the measured period either way. |
| S1 | The zero-teleport check counts only teleports with reason jam. Two teleports with reason yield occurred in the tuning runs (market and outage, seed 103) and none with reason jam. | A yield teleport is a junction-blocking artefact of the sublane model with dense pedestrian flow, not a congestion jam. |
| S1 | Market and outage side-road demand is 200 vehicles per hour instead of 550. Other market values are as specified, and normal keeps 300. | At 550 the south arm gridlocked under fixed-time. Of the values tried (550, 300, 275, 250, 225, 200) only 200 met the criterion on the tuning seeds. The side road therefore carries less in market than in normal. |
| S1 and S2 | ATT and AWT include insertion delay and are right-censored at 3900 s for vehicles still in the network or never inserted. Completed-trip means are kept separately. | Without censoring, delay of vehicles queued outside the network vanished, so a controller that starved the side road looked better. |
| S2 | Perception also returns halting vehicles per movement, taken from each vehicle's route, with the same noise as other counts. | Max-pressure needs per-movement queues to distinguish its phases. |
| S3 | The shield enforces the pedestrian crossing time on every phase that gives green to a crosswalk, not only when pedestrians are observed waiting. | Perception can miss a waiting pedestrian, so the unconditional minimum is stricter than specified and never less safe. |
| S3 | The baseline results were rerun through the shield and overwritten, so all reported runs pass through it. | The shield is meant to apply to every controller and cannot be bypassed. |
| S4 | World-model data cover normal, market and incident, not outage. | Outage differs from market only in the slow-loop connectivity window, so the data controllers would produce exact copies of market episodes. |
| S4 | World-model inputs and targets both come from noisy perception, and the persistence baseline uses the noisy current queue. | The model may only see what the deployed controller sees, so errors are measured against noisy observations for both. |

Two further points are recorded in the stage notes and the status file rather than the deviation table. The danfo term in the planner cost is approximated from the current danfo share, and the third-gate reproduction used torch 2.12.1 (CPU) because the pinned version was not installable on that machine.
