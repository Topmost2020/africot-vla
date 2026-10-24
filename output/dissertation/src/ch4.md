# Chapter 4: Implementation, Results and Discussion

This chapter describes how the prototype specified in the methodology chapter was built, what the committed result files show, and what can be concluded from them. The build proceeded in nine stages, S0 to S8, each ending with passing tests and an independent review whose findings are reported because they changed the evaluation in several places. One point governs everything that follows. The full controller, africot_full, is implemented and wiring-tested with a rule-based mock backend and smoke-tested once with a small vision-language model, but it has not been evaluated. No result in this chapter is a result of the complete system.

## 4.1 Implementation, stage by stage

### 4.1.1 Environment and skeleton (S0)

The prototype is written in Python and drives the SUMO traffic simulator headlessly through its TraCI interface (Alvarez Lopez et al., 2018). A pinned requirements file fixes SUMO 1.27.1, a CPU build of PyTorch for the world model, and the transformers library for the vision-language backend. This stage built no controller; it produced the environment, the directory layout and a smoke test that launches SUMO through TraCI, and the reviewer reinstalled the pinned packages and reran the suite without a required fix.

### 4.1.2 Junction and scenarios (S1)

The second stage built the experimental environment: a signalised T-junction with a two-lane main road in each direction, a single-lane side road to the south, sidewalks, three crossings, and three signal phases as specified. Each phase change passes through an amber of 3 s and an all-red of 2 s. The fleet has four vehicle types (car, danfo, keke and okada), and okadas are configured with arbitrary lateral alignment and a small lateral gap so that they filter between lanes under the sublane model. Across the tuning runs, the lateral standard deviation of okada positions ranged from {{s1_okada_lateral_sd_range_m.0::2}} m to {{s1_okada_lateral_sd_range_m.1::2}} m, against {{s1_car_lateral_sd_range_m.0::2}} m to {{s1_car_lateral_sd_range_m.1::2}} m for cars, the intended lane filtering. Demand is a seeded Poisson process, so every controller meets the same traffic for a given scenario and seed (see the table below).

Table: Scenario parameters as implemented (vehicles per hour per origin arm; pedestrians per hour in total)
[[scenario_table]]

Three reviewer-driven changes altered this stage, and each is recorded as a deviation. First, the initial incident, a broken-down vehicle on the kerb lane of the east approach, did not block the lane, because traffic used the lane downstream. The incident is now a closure of that lane to all demand vehicle classes from 1200 s to 2100 s of simulation clock time. Vehicles already on the lane may clear it, and a test confirms that no other demand vehicle enters it during the window.

Second, at the specified side-road demand of 550 vehicles per hour the south arm gridlocked under fixed-time control (mean insertion delay {{demand_tuning.candidates.0.mean_south_depart_delay_s::0}} s, up to {{demand_tuning.candidates.0.max_south_not_inserted::0}} south-arm vehicles never inserted on a tuning seed). A tuning script tried six side-road flows on the tuning seeds only, with the criterion of at most five uninserted south-arm vehicles on every seed and a mean south insertion delay below 60 s. Only 200 vehicles per hour met it, (mean south insertion delay {{demand_tuning.candidates.5.mean_south_depart_delay_s::1}} s, fixed-time mean AWT {{demand_tuning.candidates.5.mean_awt_s::1}} s). The market scenario therefore carries less side-road traffic than the normal scenario (200 against 300 vehicles per hour). Its congestion comes from the vehicle mix and 900 pedestrians per hour. This demand was tuned against fixed-time control (see the threats to validity).

Third, with SUMO's plain trip statistics the delay of vehicles queued outside the network vanishes, so a controller that starved the side road could appear better. Average travel time and average waiting time now include insertion delay, and vehicles still in the network at 3900 s, or never inserted, are right-censored at 3900 s with the same rule for every controller. After these fixes, the fixed-time check on the tuning seeds recorded no jam teleports and at most {{s1_check.max_not_inserted::0}} vehicles never inserted in a run.

### 4.1.3 Perception, metrics and baselines (S2)

Controllers observe the junction only through a seeded perception model. Per approach it reports the queue, counts by class, halting vehicles (also per movement, because max-pressure control must distinguish the through phase from the protected-left phase), occupancy and departures, and per crossing it reports waiting pedestrians. Each vehicle or pedestrian is missed with probability 0.05, Gaussian noise with a standard deviation of 10 percent of the value (minimum 0.5) is added, and the result is clipped at zero. Ground-truth fields exist for metrics only, and a test checks that they never reach a controller.

Three baselines were built: a fixed-time plan with greens of {{fixed_time_params.GREENS.A::0}} s, {{fixed_time_params.GREENS.B::0}} s and {{fixed_time_params.GREENS.C::0}} s for phases A, B and C; a count-and-timer controller that starts each green at {{controller_params.count_timer.MIN_GREEN::0}} s and extends it in {{controller_params.count_timer.STEP::0}} s steps while the observed served queue is at least {{controller_params.count_timer.QUEUE_THRESHOLD::0}}, up to {{controller_params.count_timer.MAX_GREEN::0}} s; and max-pressure control (Varaiya, 2013), which selects the phase with the largest observed queue on its served movements, treats the downstream as empty because the junction is isolated, and uses a fixed green of {{controller_params.max_pressure.GREEN::0}} s. The stage condition that max-pressure beats fixed-time on waiting time in the normal scenario holds. The first review requested changes, because the market ranking, in which both adaptive baselines appeared worse than fixed-time, was an artefact of metrics that excluded insertion delay; the runs were regenerated after the S1 fixes and the re-review approved the stage. Most result files carry a dirty-tree code hash suffix, but the reviewer verified that the code reproduces them exactly.

### 4.1.4 Safety shield and its audit (S3)

The shield sits between every controller and the signals and applies its rules to each proposal in a fixed order: a starvation guard that serves next any approach or crossing with observed demand and no green for more than {{shield_config.starvation_s::0}} s; a maximum green of {{shield_config.max_green::0}} s; a minimum green of {{shield_config.min_green::0}} s for every new phase; and, for any phase that serves a crosswalk, at least the crossing time, which the network gives as {{shield_config.crossing_times.xE::0}} s on the east and west crossings and {{shield_config.crossing_times.xS::0}} s on the south crossing. Amber and all-red are inserted by the only function that changes the signals, each correction is logged, and the run loop offers no way to disable the shield.

An independent audit class reads simulator ground truth and counts violations of conflicting greens, transition lengths, minimum and maximum green, the pedestrian minimum, and a starvation bound. Thirteen tests exercise the shield and the audit, including deliberately unsafe proposals and a bypassed shield. The audit and the shield share the same rule constants, so the audit shows that the implementation follows the rules, not that the rules suffice for real safety.

One deviation matters for the results below. The specification applies the pedestrian crossing minimum when pedestrians are waiting; the implementation applies it on every phase that gives green to a crosswalk, because perception can miss a waiting pedestrian. In practice this only lifts phase C greens shorter than {{shield_config.crossing_times.xE::0}} s. It is stricter than the specification and never less safe, but it makes the correction counts large.

### 4.1.5 Latent world model (S4)

The world model follows the specification. A multilayer-perceptron encoder maps the noisy perception vector to a {{world_model.hyperparameters.latent::0}}-dimensional latent, a GRU cell advances the latent given the action (phase and green time), and a decoder predicts, for the next decision, the queue per approach, the waiting pedestrians per crossing and the departures per approach. It supports multi-step rollout and is written in the style of DreamerV3 (Hafner et al., 2025) and TD-MPC2 (Hansen et al., 2024) without being either.

Training data are 300 simulated episodes from four controllers (fixed-time, count-and-timer, max-pressure and a seeded random-timing controller) in the normal, market and incident scenarios. The split is by seed: training uses seeds 100 to 104 and 200 to 209, validation uses 210 to 214 and testing uses 215 to 219, giving {{world_model.n_windows.train::0}}, {{world_model.n_windows.validation::0}} and {{world_model.n_windows.test::0}} windows. Evaluation seeds 0 to 4 are refused by the collection code. Training used Adam with batch size {{world_model.hyperparameters.batch::0}} and early stopping with patience {{world_model.hyperparameters.patience::0}}, and stopped after {{world_model.epochs_run::0}} epochs. Outage episodes were omitted because they would duplicate market episodes for the data controllers, and inputs and targets both come from noisy perception, so all errors are measured against what the controller observes, not ground truth.

### 4.1.6 CEM planner (S5)

The planner uses the Cross-Entropy Method (Rubinstein, 1999; de Boer et al., 2005) over three-step plans. Each step is a phase drawn from a categorical distribution and a green time drawn from a Gaussian and clipped to 10 s to 60 s, using 64 samples, 4 iterations and 8 elites with a seeded generator. The cost of an imagined rollout is the weighted predicted queue, plus the pedestrian weight times predicted pedestrian waiting, plus the transit priority times predicted waiting danfos, plus a large penalty for any estimated wait that exceeds the subgoal's maximum wait. Only the first step is executed, after the shield. Because the world model does not predict danfos, the danfo term is approximated by the predicted queue multiplied by the observed danfo share of the queue, an interpretation the reviewer asked to be stated. The cost is summed per plan step and not weighted by step duration, so a long green is not penalised for the time it covers.

Two variants were run. The africot_noslow variant uses the default subgoal and the trained world model and serves as the without-slow-loop ablation. The africot_nowm variant loads no world model and scores the first step only, using current queues, a smoothed arrival-rate estimate and untuned fixed discharge rates. No planner parameter was tuned on any seed.

### 4.1.7 Slow loop (S6)

The slow loop has five parts. A renderer draws a 512 by 512 top-down image of the junction from a simulator snapshot, standing in for a camera keyframe. A subgoal module defines the schema and ranges, clamps out-of-range values, and keeps the previous subgoal when a reply cannot be parsed. A VLAM module offers a deterministic mock backend, for tests and wiring only, and a Hugging Face backend defaulting to Qwen2.5-VL-3B-Instruct (Bai et al., 2025) with greedy decoding, configurable to the 7B model for a GPU; the model is asked to reason inside reasoning tags and answer with JSON inside subgoal tags. A coordinator calls the slow loop every 300 simulated seconds or when a novelty trigger fires, holds the last subgoal while the loop is unreachable, and switches to a cached time-of-day schedule after more than 600 s offline. Every decision is written to an explainability log. The reviewer noted that the slow loop is treated as instantaneous in simulated time, so its wall-clock latency has no effect on control, and that the subgoal validity field is unused.

### 4.1.8 Integration (S7)

The integration stage assembled africot_full, which couples the coordinator, renderer, VLAM and validator to the planner through the subgoal, and checked the wiring with the mock backend on all four scenarios and five seeds. Mock results go to a separate directory flagged as not reportable.

### 4.1.9 Experiment tooling (S8)

The last stage built a resumable grid runner, the plotting script and a Colab notebook intended to run the africot_full grid with the 7B model on a GPU. The plotting script reads only evaluation-seed runs, drops any mock-backend file, and reports means with the sample standard deviation over five seeds, covering {{n_eval_runs::0}} runs (five controllers by four scenarios by five seeds). The notebook has not been executed, because no GPU was available, so it is untested until its first run.

## 4.2 Reproduction evidence

The repository's test suite has {{tests.pytest_passed_at_start::0}} tests, all passing. During preparation of this dissertation the evidence was checked on a Windows machine with PyTorch 2.12.1 in place of the pinned 2.14.1, which could not be installed there. The full suite passed in {{tests.pytest_runtime_s::0}} s. This reproduction check (gate G3 in the project records) re-ran the normal scenario on seed 0 for fixed-time, count-and-timer, max-pressure, africot_noslow and africot_nowm, and for all five the waiting time, travel time, queue length, throughput, pedestrian waiting time and shield correction counts were identical to the committed files. Only wall time, the recorded code hash and a difference of the order of 1e-8 in the world-model error differed.

The scope is limited to one scenario and one seed per controller. The stage reviewers had separately re-executed a sample of runs with identical metrics, and the world-model reviewer collected the 300 training episodes from scratch and obtained bit-identical weights and metrics.

## 4.3 World-model accuracy

The world model was evaluated on the held-out test seeds 215 to 219 against a persistence baseline that predicts that queues stay unchanged. The specification required the one-step queue error to beat persistence by at least 10 percent. The model passes this check by a wide margin: the one-step queue mean absolute error (MAE) is {{world_model.test.1step.queue_mae_model::2}} vehicles against {{world_model.test.1step.queue_mae_persistence::2}} for persistence, an improvement of {{world_model.test.1step.queue_improvement_vs_persistence::pct1}} percent. The advantage persists at two steps ({{world_model.test.2step.queue_mae_model::2}} against {{world_model.test.2step.queue_mae_persistence::2}}) and three steps ({{world_model.test.3step.queue_mae_model::2}} against {{world_model.test.3step.queue_mae_persistence::2}}, {{world_model.test.3step.queue_improvement_vs_persistence::pct1}} percent), and one-step errors for waiting pedestrians ({{world_model.test.1step.ped_mae_model::2}} against {{world_model.test.1step.ped_mae_persistence::2}}) and departures ({{world_model.test.1step.dep_mae_model::2}} against {{world_model.test.1step.dep_mae_persistence::2}}) show the same pattern.

![[figure:world_model_vs_persistence.png|Queue prediction error of the world model and of the persistence baseline on held-out seeds 215 to 219, at one, two and three steps]]

The figure above shows the model error rising slowly with horizon while persistence stays near five vehicles. Three cautions apply. First, persistence is a weak baseline, because decisions are 15 s to 90 s apart and a green discharges the served queue, so the 10 percent check is a minimum bar and does not show that the model is a strong predictor. Second, both inputs and targets are noisy perception outputs, so the errors are not errors against ground truth. Third, the model was trained once with a single torch seed, so no variability across training runs is available, and it was trained on the state distribution of four controllers whereas the planner queries it on plans none of them would produce.

The online one-step queue error in the africot_noslow evaluation runs has a mean of {{wm_online_1step_queue_mae_mean_noslow_by_scenario.normal::2}} vehicles in the normal scenario, {{wm_online_1step_queue_mae_mean_noslow_by_scenario.market::2}} in market and {{wm_online_1step_queue_mae_mean_noslow_by_scenario.incident::2}} in the incident scenario, lower than the offline test error, although the incident value is the highest; these too are measured against noisy observations.

![[figure:world_model_training_curve.png|Training and validation loss of the world model by epoch]]

The training curve above shows the loss used for early stopping, with the best validation loss of {{world_model.best_val_loss::3}} at epoch {{world_model.best_epoch::0}}.

## 4.4 Controller comparison

### 4.4.1 Average waiting time

The main comparison covers five controllers in four scenarios, each cell being the mean and sample standard deviation over evaluation seeds 0 to 4. The outage scenario carries market demand and its window only affects the slow loop, so the outage rows of every controller except africot_full equal the market rows; it is not an independent fourth test for these controllers.

Table: Average waiting time in seconds, mean and standard deviation over five evaluation seeds
[[results_table:awt]]

![[figure:awt_by_scenario.png|Average waiting time by scenario and controller, mean over five evaluation seeds with sample standard deviation as error bars; the outage group duplicates the market group for every controller shown]]

In the normal scenario, max-pressure has the lowest mean waiting time ({{summary.normal|max_pressure.awt_mean::1}} s, standard deviation {{summary.normal|max_pressure.awt_sd::1}} s), followed closely by africot_noslow ({{summary.normal|africot_noslow.awt_mean::1}} s, {{summary.normal|africot_noslow.awt_sd::1}} s). Fixed-time ({{summary.normal|fixed_time.awt_mean::1}} s), count-and-timer ({{summary.normal|count_timer.awt_mean::1}} s) and africot_nowm ({{summary.normal|africot_nowm.awt_mean::1}} s) are about twice as high, and fixed-time and africot_nowm are much more variable. In the market scenario, africot_noslow has the lowest mean ({{summary.market|africot_noslow.awt_mean::1}} s, standard deviation {{summary.market|africot_noslow.awt_sd::1}} s) but max-pressure is close ({{summary.market|max_pressure.awt_mean::1}} s) with a standard deviation of {{summary.market|max_pressure.awt_sd::1}} s, so the lead is inside one standard deviation. In the incident scenario max-pressure again has the lowest mean ({{summary.incident|max_pressure.awt_mean::1}} s) and africot_noslow is slightly higher ({{summary.incident|africot_noslow.awt_mean::1}} s), while africot_nowm is the worst of the five ({{summary.incident|africot_nowm.awt_mean::1}} s, standard deviation {{summary.incident|africot_nowm.awt_sd::1}} s). The incident scenario raises waiting only modestly under fixed-time (from {{summary.normal|fixed_time.awt_mean::1}} s to {{summary.incident|fixed_time.awt_mean::1}} s), because the median east lane still carries flow.

On market, max-pressure is lower than fixed-time on average waiting time in the summary as it now stands ({{summary.market|max_pressure.awt_mean::1}} s against {{summary.market|fixed_time.awt_mean::1}} s), and count-and-timer is about level with it ({{summary.market|count_timer.awt_mean::1}} s). An earlier, un-fixed version of the metrics showed both adaptive baselines losing to fixed-time on market, traced by the reviewer to the exclusion of insertion delay and to a gridlocked side road; only the current results are reported.

Table: Average waiting time, average travel time, average queue length, throughput and pedestrian waiting time per scenario and controller, mean and standard deviation over five evaluation seeds
[[results_table:full]]

### 4.4.2 Other metrics

The other metrics follow the pattern of the waiting time. Throughput differs little between controllers within a scenario: in the normal scenario it ranges only from {{summary.normal|fixed_time.throughput_mean::0}} to {{summary.normal|max_pressure.throughput_mean::0}} vehicles, so all controllers serve essentially the same demand. Pedestrian waiting in the normal scenario is lowest for count-and-timer, max-pressure and africot_noslow and highest for fixed-time and africot_nowm.

![[figure:att_by_scenario.png|Average travel time by scenario and controller, mean over five evaluation seeds with sample standard deviation as error bars; the outage group duplicates the market group]]

![[figure:aql_by_scenario.png|Average queue length by scenario and controller, mean over five evaluation seeds with sample standard deviation as error bars; the outage group duplicates the market group]]

![[figure:throughput_by_scenario.png|Throughput by scenario and controller, mean over five evaluation seeds with sample standard deviation as error bars; the outage group duplicates the market group]]

![[figure:ped_wait_by_scenario.png|Average pedestrian waiting time by scenario and controller, mean over five evaluation seeds with sample standard deviation as error bars; the outage group duplicates the market group]]

### 4.4.3 Paired by-seed tests

Because every controller meets the same traffic for a given seed, differences can be examined seed by seed. The paired tests take the difference in average waiting time between two controllers on each of the five evaluation seeds. They are exploratory: with five seeds the exact two-sided Wilcoxon signed-rank test cannot return a p-value below 0.0625, the t-test rests on five differences, and no correction for multiple comparisons was applied. The count of seeds in which the first-named controller was lower is the more robust summary at this sample size.

Table: Paired by-seed differences in average waiting time (first controller minus second), with two-sided p-values; exploratory, five seeds, no multiplicity correction
[[paired_table]]

The comparison with max-pressure matters most. In the normal scenario, africot_noslow is higher than max-pressure by {{paired_tests.0.mean_diff_a_minus_b::1}} s on average (standard deviation of the differences {{paired_tests.0.sd_diff::1}} s), and it was lower in {{paired_tests.0.a_lower_in_seeds::0}} of the five seeds, so max-pressure was lower in all five seeds. In the incident scenario the mean difference is {{paired_tests.10.mean_diff_a_minus_b::1}} s in favour of max-pressure, but the standard deviation of the differences is {{paired_tests.10.sd_diff::1}} s and africot_noslow was lower in {{paired_tests.10.a_lower_in_seeds::0}} of five seeds, so the two controllers are comparable there (Wilcoxon p = {{paired_tests.10.wilcoxon_exact_p_two_sided::3}}). In the market scenario the mean difference is {{paired_tests.5.mean_diff_a_minus_b::1}} s with a standard deviation of {{paired_tests.5.sd_diff::1}} s, africot_noslow was lower in {{paired_tests.5.a_lower_in_seeds::0}} of five seeds, and the p-values ({{paired_tests.5.t_p_two_sided::2}} for the t-test, {{paired_tests.5.wilcoxon_exact_p_two_sided::3}} for Wilcoxon) give no basis to separate them. The market and incident results are therefore described as comparable. The paired data do not support a claim that the planner without the slow loop beats max-pressure in any scenario, and they support the opposite on normal demand.

![[figure:paired_noslow_vs_maxpressure.png|Paired difference in average waiting time, africot_noslow minus max-pressure, per scenario, mean over five seeds with standard error as error bars; positive values mean max-pressure is lower]]

The figure above shows the same pattern.

Against fixed-time, both africot_noslow and max-pressure have lower waiting time in all five seeds in every scenario, with mean differences between {{paired_tests.7.mean_diff_a_minus_b::1}} s and {{paired_tests.12.mean_diff_a_minus_b::1}} s and exact Wilcoxon p-values that sit at the floor of {{paired_tests.1.wilcoxon_exact_p_two_sided::4}}. Adaptive control that uses current queues thus has lower waiting time than a fixed plan in these simulations, including the planner with the world model, but this does not separate the planner from max-pressure.

## 4.5 The contribution of the world model

The ablation without the world model is the clearest result among the variants. In the paired tests, africot_noslow has lower waiting time than africot_nowm in all five seeds in each of the three scenarios, with mean differences of {{paired_tests.4.mean_diff_a_minus_b::1}} s (normal), {{paired_tests.9.mean_diff_a_minus_b::1}} s (market) and {{paired_tests.14.mean_diff_a_minus_b::1}} s (incident), and exact Wilcoxon p-values at the floor of {{paired_tests.4.wilcoxon_exact_p_two_sided::4}} in all three. In the means, africot_nowm is also no better than fixed-time, being higher in every scenario ({{summary.normal|africot_nowm.awt_mean::1}} s against {{summary.normal|fixed_time.awt_mean::1}} s in normal, {{summary.market|africot_nowm.awt_mean::1}} s against {{summary.market|fixed_time.awt_mean::1}} s in market and {{summary.incident|africot_nowm.awt_mean::1}} s against {{summary.incident|fixed_time.awt_mean::1}} s in incident). The paired tests against fixed-time do not separate them: africot_nowm was lower in {{paired_tests.3.a_lower_in_seeds::0}}, {{paired_tests.8.a_lower_in_seeds::0}} and {{paired_tests.13.a_lower_in_seeds::0}} of five seeds in the three scenarios, with small differences relative to their spread. In summary, africot_nowm is comparable to fixed-time and clearly worse than the planner that uses the learned model.

This result needs a caveat. The africot_nowm variant is not a matched ablation of equal strength. It replaces a three-step imagination planner with a one-step queue-discharge heuristic that uses fixed, untuned discharge rates, so the learned predictor and the planning horizon change at once. A world-model-free controller built with comparable care could narrow or remove the gap. The result is evidence that the learned model with three-step planning is better than this particular heuristic, not of how much of the benefit comes from learning as such. On the incident scenario africot_nowm left a mean of {{summary.incident|africot_nowm.not_inserted_mean::1}} vehicles uninserted per run, with a waiting-time standard deviation of {{summary.incident|africot_nowm.awt_sd::1}} s.

## 4.6 Safety shield audit

The independent audit recorded {{safety_violations_total::0}} safety violations across all {{n_eval_runs::0}} evaluation runs. The shield was active in every run and its corrections are summarised below.

Table: Shield corrections by controller and rule, summed over all evaluation runs of that controller
[[shield_table]]

Across all runs the shield made {{shield_total_by_rule.ped_crossing::0}} pedestrian-crossing corrections, {{shield_total_by_rule.max_green::0}} maximum-green corrections and {{shield_total_by_rule.starvation::0}} starvation corrections.

![[figure:shield_corrections_by_rule.png|Shield corrections by rule summed over all evaluation runs, on a logarithmic scale]]

Most corrections are the pedestrian crossing minimum, a consequence of the deviation described earlier: any phase C green shorter than {{shield_config.crossing_times.xE::0}} s is lifted to that value, so the count reflects how often controllers propose short side-road greens, not frequent unsafe actions. The maximum-green corrections are concentrated in the africot_nowm runs ({{shield_corrections_by_controller_rule.africot_nowm.max_green::0}} of the {{shield_total_by_rule.max_green::0}}), where the heuristic repeatedly reselects the same phase, and the two starvation corrections both come from max-pressure. The shield thus acts as a backstop against a weak controller, as intended, and the africot_nowm results are reported after its corrections. A zero audit count concerns the implemented rules, which the audit and shield share, and makes no claim about real-world safety.

Jam teleports, in which SUMO removes a vehicle stuck for too long, occurred in only two cells: {{jam_teleports_by_cell.africot_nowm|normal::0}} in africot_nowm on the normal scenario and {{jam_teleports_by_cell.max_pressure|market::0}} each in max-pressure on market and outage, which are the same runs counted twice because outage equals market. The reviewer traced the max-pressure case to vehicles held inside the junction while yielding to dense pedestrian flow, a sublane artefact that the shield cannot reach, and the audit found no signal violation there. Teleports of other kinds were recorded in several cells (up to {{teleports_any_by_cell.africot_nowm|incident::0}}, in africot_nowm on the incident scenario).

## 4.7 Slow-loop evidence

### 4.7.1 Wiring checks with the mock backend

All wiring checks used the mock backend, which is rule-based and is not the VLAM. They show that the software paths work and say nothing about reasoning quality or traffic performance. The mock africot_full controller completed all {{mock_wiring.n_runs::0}} runs with {{mock_wiring.safety_violations_total::0}} safety violations and {{mock_wiring.parse_failures_total::0}} parse failures.

In the outage scenario the coordinator log shows the intended degradation sequence on every seed. On seed 0 the state is online at the start, switches to holding the last subgoal at {{mock_wiring.outage_connectivity_switches_seed0.1.0::0}} s, switches to the cached time-of-day schedule at {{mock_wiring.outage_connectivity_switches_seed0.2.0::0}} s, which is more than 600 s into the outage, and returns online at {{mock_wiring.outage_connectivity_switches_seed0.3.0::0}} s. The return to online is logged slightly after the end of the outage window at 2400 s, consistent with connectivity being checked at decision times, although the code was not inspected to confirm it.

![[figure:outage_degradation_timeline.png|Connectivity state of the coordinator over the simulation clock in the outage scenario on seed 0 with the mock backend: online, holding the last subgoal, using the cached schedule, and online again]]

The novelty trigger fired inside the incident window (1200 s to 2100 s) on all five seeds in the mock runs, which was the stage condition. The trigger is not specific to the incident, however. The same check records novelty events in the normal scenario (seeds {{mock_wiring.novelty_trigger_seeds_by_scenario.normal.0::0}} and {{mock_wiring.novelty_trigger_seeds_by_scenario.normal.1::0}}), market (seeds {{mock_wiring.novelty_trigger_seeds_by_scenario.market.0::0}}, {{mock_wiring.novelty_trigger_seeds_by_scenario.market.1::0}} and {{mock_wiring.novelty_trigger_seeds_by_scenario.market.2::0}}) and outage (seed {{mock_wiring.novelty_trigger_seeds_by_scenario.outage.0::0}}), and some incident triggers fall outside the incident window (for example seed 0 at {{mock_wiring.incident_novelty_times_by_seed.0.1::0}} s and seed 3 at {{mock_wiring.incident_novelty_times_by_seed.3.0::0}} s). Trigger events can also coincide with scheduled calls, so distinct novelty-driven calls are fewer than the event count in some runs. The trigger responds to rises in world-model error generally and cannot be described as an incident detector.

### 4.7.2 The 3B smoke test

The Hugging Face backend was run once, on the committed renderer snapshot (market scenario, tuning seed 100, 226 s), with Qwen2.5-VL-3B-Instruct on a four-core CPU. The prompt gave a clock time of 07:03, queues of about {{vlam_smoke_context.queues.east::1}}, {{vlam_smoke_context.queues.west::1}} and {{vlam_smoke_context.queues.south::1}} on the east, west and south approaches, and about {{vlam_smoke_context.ped_waiting.xE::0}} waiting pedestrians at the east crossing against about {{vlam_smoke_context.ped_waiting.xW::0}} at the west.

![[figure:renderer_snapshot_market_100.png|Renderer keyframe used for the smoke test: market scenario, tuning seed 100, 226 s into the simulation; waiting pedestrians appear as dots at the crossings, and the signal state per movement is shown at the top left]]

The reply was parseable and the validator accepted it without notes. The subgoal kept all queue weights at {{vlam_smoke_test.subgoal.queue_weights.east::1}}, raised the pedestrian weight to {{vlam_smoke_test.subgoal.pedestrian_weight::1}}, and left the other fields at their defaults. The recorded latency was {{vlam_smoke_test.latency_s::1}} s on an idle machine, about half of the 300 s call interval.

The reasoning text is the more important finding. The model states that 11 pedestrians are waiting on the west arm, but the context gave about 11 at the east crossing and about 2 at the west, so the reasoning is wrong about which arm has the pedestrians. The resulting subgoal (a higher pedestrian weight) is plausible for a market-day scene, but it is not supported by correct reasoning. The call shows that the pipeline from image and context to a validated subgoal works; it is not evidence of sound reasoning and supports no claim about 7B or larger models, which have not been run.

<!--COLAB:results_full-->
**Pending (not yet evaluated).** The africot_full grid (slow loop on, Qwen2.5-VL-7B-Instruct, four scenarios, evaluation seeds 0 to 4) is prepared in the Colab notebook and has not been run. No africot_full results are reported in this chapter, and the summary tables contain no africot_full row. When run, this block is to be replaced by the africot_full rows, a paired by-seed comparison with africot_noslow and max-pressure, and a report of parse failures and call latency.
<!--/COLAB-->

## 4.8 Negative results and threats to validity

The unfavourable results are stated above and not softened: the planner without the slow loop loses to max-pressure on normal demand (lower in five of five seeds), africot_nowm is no better than fixed-time, the novelty trigger is not incident-specific, the 3B reasoning was wrong, and the slow loop has no evaluation. The main threats to validity follow. First, the evaluation covers a single isolated junction, whereas the design targets a corridor of close junctions, so no result bears on neighbour exchange, green waves or mesh communication. Second, perception is simulator ground truth with seeded noise and missed detections, without occlusion, lighting or class confusion, and no detector was tested on real footage. Third, demand is synthetic Poisson traffic, and the market side-road demand was lowered from 550 to 200 vehicles per hour, tuned against fixed-time control on the tuning seeds. Fourth, there are only five evaluation seeds, so the paired tests are exploratory. Fifth, the outage scenario is not independent of market for any controller without a slow loop. Sixth, africot_nowm is a weaker comparator than a carefully built world-model-free planner. Seventh, the censoring rule makes waiting and travel time a lower bound for unfinished vehicles, applied equally to every controller. Eighth, the planner and baselines were not tuned, so the results may understate tuned versions. Ninth, the slow loop is treated as instantaneous in simulated time, so latency, about {{vlam_smoke_test.latency_s::0}} s per call for the 3B model on a CPU, has no effect on control in any run. Tenth, no cloud deployment was built, tested or measured: the simulation covers the control logic and the outage behaviour only, and no latency, availability, cost, security or data-residency figure exists for a cloud-hosted system.

The deviations from the specification that are recorded in the project log are summarised in the table below.

Table: Deviations from the specification recorded during the build
| Stage | Deviation | Reason |
|---|---|---|
| S1 | Incident implemented as closure of the east kerb lane to demand classes from 1200 s to 2100 s, replacing a stopped vehicle | The stopped vehicle did not block the lane downstream (reviewer finding) |
| S1 | Event times read as simulation clock times, including the warm-up | The specification does not say which clock |
| S1 | Market and outage side-road demand 200 veh/h instead of 550 veh/h | At 550 the south arm gridlocked under fixed-time; 200 passed the tuning criterion |
| S1, S2 | ATT and AWT include insertion delay, with right-censoring at 3900 s | Plain trip statistics hid the delay of vehicles never inserted |
| S2 | Perception also returns halting vehicles per movement | Max-pressure needs per-movement queues |
| S3 | Pedestrian crossing minimum applied on every pedestrian phase | Perception can miss waiting pedestrians; stricter than the specification |
| S4 | World-model data omit the outage scenario; inputs, targets and persistence use noisy perception | Outage duplicates market for the data controllers; ground truth must not be used for control |
| S5 | Danfo cost term approximated from the observed danfo share of the queue | The world model does not predict danfos |

## 4.9 Discussion

The evidence answers some of the research questions and leaves others open.

The first question is whether a small latent world model can learn useful short-horizon dynamics of a junction with mixed informal transit. The evidence says yes in a limited sense: on held-out seeds the one-step queue error is {{world_model.test.1step.queue_mae_model::2}} vehicles against {{world_model.test.1step.queue_mae_persistence::2}} for persistence, rising to {{world_model.test.3step.queue_mae_model::2}} at three steps. Transfer to real counts is not shown.

The second question is whether planning with the world model beats simpler control, and the answer is mixed. The planner has lower waiting time than fixed-time and than the one-step heuristic variant in all five seeds in each scenario. It is not better than max-pressure in any scenario: it is worse on normal demand by a small and consistent margin and comparable on market and incident, so a simple adaptive rule with a fixed green matches or beats a three-step planner with a learned model here. The planner was not tuned.

The third question is whether the shield keeps every controller within its rules. In simulation the audit recorded no violations in any evaluation run, which supports the structural claim that nothing learned can bypass the shield, not a claim about physical safety.

The fourth question is whether the degradation tiers behave as designed when connectivity is lost. The wiring evidence shows the designed sequence of holding the last subgoal and then switching to the cached schedule after ten minutes. It does not show that the cached schedule is a good one, what degradation costs in traffic terms, or how a cloud deployment would behave.

Several questions cannot be answered. Whether chain-of-thought reasoning improves the subgoals, and through them the traffic outcomes, is untested, because no africot_full result exists, and the single 3B call gives reason for caution about small models. Corridor behaviour, performance on real footage, regulatory acceptance of the explainability log and the behaviour of a cloud-hosted deployment are outside this evaluation.

<!--COLAB:discussion_full-->
**Pending (not yet evaluated).** The central hypothesis of the design, that a slow loop with chain-of-thought reasoning can steer the fast loop through the subgoal to lower delay when conditions are unusual, is intended to be tested by the africot_full grid with the 7B model. Until that grid has been run, this chapter makes no claim that the slow loop helps, hurts or has no effect. This block is to be rewritten with the paired by-seed comparison of africot_full against africot_noslow and max-pressure in all four scenarios, including outage.
<!--/COLAB-->

Taken together, the results are best read as a working, reproducible prototype with an honest baseline. The fast loop with a learned world model has lower waiting time than fixed-time and than a one-step heuristic in these simulations, does not beat the strongest classical baseline, and the slow loop with chain-of-thought reasoning remains to be evaluated.
