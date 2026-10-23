# Chapter 3: Methodology and System Design

## 3.1 Introduction

This chapter sets out how the AfriCoT-VLA system is designed and how the prototype was built and evaluated. It keeps two things separate: the full design, including parts that are specified but not built, and what was implemented and tested, so that the results in the following chapter can be read against the right scope. The prototype is a single Lagos-style T-junction in the SUMO traffic simulator (Alvarez Lopez et al., 2018), whereas the design addresses a corridor of nearby junctions, tiered communication and a cloud deployment framework. A table near the end of the chapter lists every component, what the design specifies, what was built and tested, and its status. The chapter moves from principles to architecture, then to the deployment framework proposed by Dr. Fasina, and then to the experimental method.
## 3.2 Design principles

The design treats the constraints of Sub-Saharan African cities as inputs to the architecture and not as problems to be solved by better hardware or connectivity. Five principles follow.

First, the real-time control loop must never depend on a network link. Mobile data coverage in the region remains uneven (GSMA, 2024a, 2024b) and access to electricity incomplete (International Energy Agency et al., 2025), so the loop that selects timings is placed on the junction's edge computer and only slow, advisory information crosses the network.

Second, the two kinds of reasoning involved differ in time scale and cost. Predicting queues and choosing a phase timing is fast, narrow and repetitive. Noticing that a market is in progress or that a lane is blocked is slow, broad and occasional, and suits a large vision-language model. Hierarchical designs that separate a slow language-conditioned level from a fast control level have precedent in robotics (Shi et al., 2025; Hafner et al., 2022), and the authors' earlier paper proposed a related two-timescale architecture (Ariyo & Fasina, 2026), which this chapter extends with the reasoning trace, the shield, the audit log and the degradation tiers.

Third, nothing learned may bypass a safety rule. Minimum green, clearance, pedestrian crossing time and the absence of conflicting greens are explicit rules between the planner and the signals, and the slow loop can alter priorities but cannot issue phase commands. Fourth, the system degrades gracefully through four operating tiers, so that loss of connectivity or of a component leads to simpler and not unsafe behaviour.

Fifth, decisions must be explainable to regulators such as the Lagos State Traffic Management Authority (LASTMA) and the state Ministry of Transportation, so every decision is designed to be logged with its triggering conditions and, for slow-loop decisions, the written reasoning behind the subgoal. Chain-of-thought reasoning has been used to expose intermediate steps in robot control (Zawalski et al., 2024; Yang et al., 2025).

Two further choices apply. Only open-weight models are used and none is trained from scratch, because the compute and data available do not support it. And the vision-language-action model and the latent world model are coupled and not fused: they remain separate models linked only by a compact subgoal. Full unification of action generation and world modelling is an open research problem, and coupling is a deliberate choice under limits on compute and connectivity.
## 3.3 The two-timescale architecture

The architecture has an edge perception stage, a fast loop, a slow loop, a subgoal interface between them, a safety shield, an explainability log and a coordinator. The figure below shows how these parts connect. Solid arrows carry control information, and dashed arrows carry supporting information such as keyframes, coordination decisions and log records.

![[figure:architecture_two_timescale.png|The two-timescale architecture: a slow loop (vision-language-action model with chain-of-thought reasoning) sets a subgoal, a fast loop (latent world model with a cross-entropy-method planner) proposes a phase, and a rule-based safety shield corrects the proposal before it reaches the signal controller]]

### 3.3.1 Edge perception

In the design, a lightweight detector on each junction's edge computer classifies vehicles by type (car, danfo, keke, okada) and detects pedestrians, and computes for each approach the queue length, counts by class and occupancy, plus the pedestrians waiting at each crossing. Raw video never leaves the site. The fast loop uses only these summary quantities, and the slow loop uses only occasional keyframes.

In the prototype there is no camera and no detector. Perception is simulated from SUMO ground truth with the noise model described later in this chapter, and the detector is proposed for separate testing on real Lagos footage. Perception also returns halting vehicles per movement, from each vehicle's route, because max-pressure control needs per-movement queues to distinguish phases.

### 3.3.2 The fast loop

The fast loop runs on the junction's edge computer at every signal decision, which in the prototype is the end of each green, about {{decisions_per_run_mean::0}} decisions per run on average. A latent world model predicts how queues, waiting pedestrians and departures evolve under a candidate phase and green time. The planner samples candidate three-step plans, imagines each with the world model, scores them with a cost defined by the current subgoal, and refines its sampling towards the lowest-cost plans (Rubinstein, 1999; de Boer et al., 2005), following the pattern of latent-dynamics planners (Hafner et al., 2019; Chua et al., 2018; Hansen et al., 2024). Only the first step of the best plan is passed to the safety shield. The fast loop runs locally in every operating tier and is never routed elsewhere.

### 3.3.3 The slow loop

The slow loop is designed to run every few minutes, or earlier when something unusual occurs. A vision-language-action model (VLAM) receives a keyframe of the junction and a short context (time of day, any known event such as a market day or incident, current queues and the subgoal in force), reasons step by step and emits a subgoal in a fixed format. The reasoning is stored for audit. The prototype has two backends. A deterministic, rule-based `mock` backend exists only for tests and wiring checks. An `hf` backend loads a Qwen2.5-VL model (Bai et al., 2025) through Hugging Face transformers, with the 3B model for CPU tests and the 7B model intended for a GPU run. Decoding is greedy, so repeated calls return the same text, and the model places reasoning in `<reasoning>` tags and a JSON answer in `<subgoal>` tags. The design does not depend on this model, because the subgoal format is the only contract; manipulation-oriented models such as OpenVLA (Kim et al., 2024) would need adaptation to produce subgoals.

A renderer produces the keyframe in the prototype. It draws a top-down 512 by 512 image from simulator state, with road outlines, crossings, vehicles as shapes coloured by class, waiting pedestrians as dots, the signal state and a legend. It is a simulator view and not a photograph, so the prototype cannot show how a model reads real footage.
### 3.3.4 The subgoal interface

The subgoal is the only interface between the two loops. It is a compact vector of cost weights and constraint bounds that parameterise the planner's cost, so the VLAM's "action" is a statement of priorities and not a phase command. The schema and ranges are in the table below.

Table: The subgoal schema, default values and permitted ranges

| Field | Meaning | Default | Range |
|---|---|---|---|
| `queue_weights` (east, west, south) | Priority of clearing each approach | 1.0 each | 0.2 to 3.0 each |
| `pedestrian_weight` | Priority of reducing pedestrian waiting | 1.0 | 0.0 to 3.0 |
| `max_wait_s` | Longest acceptable wait (seconds) | 120 | 45 to 180 |
| `transit_priority` | Priority of waiting danfos | 1.0 | 0.0 to 2.0 |
| `valid_for_s` | Intended validity (seconds) | 300 | 60 to 900 |

A validator clamps every number to its range. A missing or non-numeric field keeps its previous value, and an unparseable reply leaves the previous subgoal in force, which is intended to tolerate the malformed output that small language models sometimes produce. The `valid_for_s` field is validated but not used by the coordinator, which calls on its own fixed schedule.
### 3.3.5 The safety shield

The safety shield sits between the planner, or any other controller, and the signals. In the prototype every controller, including the baselines, passes through it, and it cannot be disabled in the episode runner. It applies these rules in order to each proposal.

1. Starvation guard: an approach or crossing with observed demand and no green for more than 180 s is served next, longest waiting first.
2. Maximum green: a phase may not exceed 90 s in total; an extension past 90 s is cut and a phase already at 90 s is ended.
3. Minimum green: a new phase lasts at least 10 s.
4. Pedestrian minimum: a phase that gives green to a crossing lasts at least the crossing length divided by 1.2 m/s plus 4 s, rounded up, which is 16 s for the east and west crossings and 10 s for the south crossing.
5. Clearance: every phase change passes through an amber of 3 s and an all-red of 2 s, inserted by the simulation environment, the only code path that changes the signals.

Each correction is returned with its rule and reason so that it can be logged. The shield sees only the noisy perception output and its own signal history. A separate audit class reads simulator ground truth and counts rule violations. Because the audit and the shield share the same rule constants, the audit tests whether the implementation follows the rules and not whether the rules suffice for real-world safety.

Two departures from the design are recorded. The specification required the pedestrian minimum only when pedestrians were observed waiting, but because perception misses pedestrians the prototype applies it on every phase that gives green to a crossing, which is stricter and never less safe. And the design's spillback rule, which forbids releasing traffic towards a full downstream approach, has no meaning at a single junction and is not built.

Each decision produces one JSON line holding the simulation time, controller, scenario and seed; the trigger (scheduled, novelty or none); the connectivity state; the VLAM backend; the reasoning text; the subgoal in force; the planned phases and greens; the shield correction and its reason; the applied phase and green; and the world model's one-step error. The design proposes a frame hash, a predicted-versus-actual outcome record and tamper-evident storage for regulatory audit, none of which is built, and the prototype's log has not been assessed by any regulator.

### 3.3.7 The capability-aware coordinator and the degradation tiers

The design includes a rule-based, non-learned coordinator that routes only slow-loop tasks according to connectivity, available compute and scene novelty. A routine scene goes to a small vision-language model on the edge, an unusual scene goes to a large cloud model when connectivity allows, and an emergency triggers a direct override. A rise in the world model's prediction error signals that heavier reasoning may be needed. Four operating tiers are specified. With full connectivity the slow loop runs a large VLAM in the cloud. With weak connectivity it runs a small VLM on the edge or follows a cached time-of-day subgoal schedule. With no connectivity the fast loop continues on the last subgoal. On a system fault the junction runs a fixed-time plan.

The prototype implements a subset. The coordinator calls the slow loop every 300 simulated seconds and early when a novelty trigger fires, namely when the mean one-step world-model queue error over the last 10 decisions exceeds twice the median of the 30 before them, with at least 120 s between triggers. Connectivity is defined by scenario: during an outage window the coordinator holds the last subgoal, and after more than 600 s offline it switches to a hand-written, untuned time-of-day schedule. Every switch is logged. The slow loop is treated as instantaneous in simulated time and only its wall-clock latency is recorded, an idealisation since one 3B call takes minutes on a four-core CPU.

Much is not built. There is no routing between an edge model and a cloud model, so the same backend serves every call. The weak-connectivity tier is represented only by the cached schedule. The fixed-time baseline can be run as a controller, but no automatic switch to it on a fault exists. An emergency-vehicle override, in which a verified message forces a phase directly while still respecting clearance rules, is described only.
### 3.3.8 Tiered communication

The design arranges five communication tiers in order of preference: 4G or fibre for everything except raw video; SMS over GSM for alerts and subgoals only when data service is down; store-and-forward for logs and training data; a junction-to-junction mesh relay over Wi-Fi or LoRa as the main offline path, since the junctions are close together; and, optionally, satellite for critical alerts only. All incoming messages are to be cryptographically signed, and may change priorities but can never bypass the shield. None of these tiers is implemented. The prototype's outage scenario models connectivity loss only as an on-off window for the slow loop.
### 3.3.9 Multiple junctions

The design also anticipates a corridor of two to three junctions, in which each world model takes its neighbours' outflows as inputs, neighbours share queue and plan data over the mesh so that green waves continue offline, and an optional cluster edge server runs the small vision-language model. The prototype has a single junction, so none of this is built, and it is listed as future work.

## 3.4 The eight-layer deployment framework

### 3.4.1 Origin and content

The layered framework used here originates with the supervisor, Dr. Fasina. During the class session of 27 July 2026 they typed the prompt "Design a cloud-based 8-layer framework for AfriCoT-VLA" into DeepSeek on a shared screen, and the resulting structure is credited to them. The layers are the sensor layer (cameras and actuators for traffic lights); the network connection (compressed video from the cameras over the internet to the cloud); the data store; the model layer (chain-of-thought reasoning, latent world models and the VLAM); the explainability layer; the service layer; the AI agent layer; and the autonomous agentic layer.

The author proposes refinements, which are the author's own and have not yet been confirmed by the supervisor. The data store would hold a hot window and a cold history. The model layer would follow the two-timescale design of this chapter. The service layer would expose decision, query, override and health interfaces. The AI agent layer would handle corridor coordination, and the autonomous agentic layer would produce plan proposals and what-if simulations that a human signs off. Any layer above the model layer could fail with fallback to fixed-time control, the explainability layer would act as a deployment gate, and the network layer is proposed to be the real bottleneck. The figure below shows the layers.

![[figure:eight_layer_framework.png|The eight-layer deployment framework, credited to Dr. Fasina, with the author's proposed refinements (not yet confirmed by the supervisor)]]
### 3.4.2 The cloud versus on-site video tension and a proposed reconciliation

The framework as the supervisor framed it is cloud-based and sends compressed video to the cloud, whereas the architecture of this chapter keeps raw video on site and runs the fast loop locally. The two conflict: with all processing in the cloud, every signal decision depends on a network link and on uplink bandwidth, and with all processing local, the large reasoning model has no place to run.

The author proposes the following reconciliation, offered for discussion and not supervisor-approved. The eight layers are kept as the organising structure. The cloud is treated as the full-connectivity tier, where a large VLAM and the upper layers run when the network allows. The network layer carries compressed keyframes for the slow loop and not continuous video. The sensor layer and the fast loop sit on the edge computer, so that loss of the network leaves the junction running on its edge. The prototype tests none of the framework as a deployment, and the framework serves here as a structure for the design and a map of what remains to be built.
## 3.5 Simulation environment

### 3.5.1 The junction

The experimental environment is a single signalised T-junction in SUMO, built with `netconvert` from committed source files. Traffic drives on the right. The main road runs east to west with two lanes in each direction at 50 km/h, and the side road is the south arm with one lane in each direction at 40 km/h. Every approach is 300 m long, each arm has a sidewalk and a pedestrian crossing, the step is 1 s, and the sublane model with a lateral resolution of 0.8 m lets motorcycles filter between lanes.

### 3.5.2 Phases

Three signal phases serve six movements (west to east through, west to south right, east to west through, east to south left, south to east right, south to west left). Phase A serves the main road with the east left turn permissive and pedestrians crossing the south arm. Phase B gives the east approach a protected left with east through and no crossing. Phase C serves the side road, with turns yielding to pedestrians, and gives green to the east and west crossings. A conflict checker confirms from signal states that no conflicting movements are green together, and a test confirms that it flags a deliberately unsafe state.
### 3.5.3 Vehicle types

Four vehicle types represent informal transport. A car is 4.5 m long with a maximum of 60 km/h. A danfo is a 5.5 m bus-class minibus at 50 km/h that counts as transit. A keke is a 2.7 m tricycle, 1.4 m wide, at 40 km/h. An okada is a 2.0 m motorcycle, 0.8 m wide, at 60 km/h, with arbitrary lateral alignment and a small lateral gap so that it filters between lanes. On tuning seeds the lateral standard deviation of okada positions ranged from {{s1_okada_lateral_sd_range_m.0::2}} m to {{s1_okada_lateral_sd_range_m.1::2}} m, against {{s1_car_lateral_sd_range_m.0::2}} m to {{s1_car_lateral_sd_range_m.1::2}} m for cars, which indicates that filtering is present. These are simulation settings and not measurements of Lagos traffic.
### 3.5.4 Scenarios and demand

Each scenario lasts 3600 s of measured time after a 300 s warm-up that is excluded from every metric, so each run ends at 3900 s. Demand is generated by a seeded Poisson process so that every controller sees the same traffic and pedestrians for a given scenario and seed. The normal scenario represents a typical peak. The market scenario raises pedestrian demand sharply and shifts the mix towards keke and okada. The incident scenario is the normal scenario with the kerb lane of the east approach closed to demand vehicles from 1200 s to 2100 s by a lane permission change, so that all east-approach traffic shares the median lane. The outage scenario carries market demand and makes the slow loop unreachable from 1200 s to 2400 s. Event times are simulation clock times that include the warm-up. Turning shares are 80 and 20 per cent (through and right) from the west, 75 and 25 per cent (through and left) from the east, and 50 per cent each way from the south. The table below gives the parameters.

The parameters of the four scenarios are in the table below.

Table: Scenario parameters (demand per origin arm in vehicles per hour, vehicle mix, pedestrian demand and events)

[[scenario_table]]

Two points matter for interpretation. First, market side-road demand is 200 vehicles per hour and not the 550 specified in the original design. At 550 the south arm gridlocked under fixed-time control on the tuning seeds, with a mean insertion delay of {{demand_tuning.candidates.0.mean_south_depart_delay_s::0}} s and up to {{demand_tuning.candidates.0.max_south_not_inserted::0}} vehicles never inserted. A tuning script tried 550, 300, 275, 250, 225 and 200 on the tuning seeds, requiring at most five uninserted south vehicles on every seed and a mean south insertion delay below 60 s. Only 200 met it, with a mean delay of {{demand_tuning.candidates.5.mean_south_depart_delay_s::1}} s. The market scenario therefore carries less side-road traffic than the normal scenario, and its congestion comes from the vehicle mix, from 900 pedestrians per hour, and from pedestrians on the east and west crossings blocking the yielding turns from the south. Second, the incident scenario raises delay only modestly under fixed-time control, because one lane still carries flow.

### 3.5.5 Seeds and their roles

Three disjoint seed sets serve distinct purposes. Tuning seeds 100 to 104 are used to check scenarios and tune demand, and are the only seeds on which anything was adjusted. Data seeds 200 to 219 are used with the tuning seeds to collect world-model training data. Evaluation seeds 0 to 4 are used for reported results and never for tuning or training; the collection code refuses them and the loader checks again.
### 3.5.6 The perception noise model

Controllers observe the junction only through a noise model that stands in for an imperfect detector. Each vehicle is missed with probability {{perception_config.miss_p::2}}, and Gaussian noise with a standard deviation of {{perception_config.rel_sd::pct1}} per cent of the value, with a minimum of {{perception_config.min_sd::1}}, is added to counts, which are then clipped at zero. The noise is seeded. A clean ground-truth mode is used only for metrics and the audit, never for control. The level is an assumption and not a measured property of any detector.
## 3.6 Controllers

### 3.6.1 Baselines that were built

Three baselines were built, all passing through the shield. **fixed_time** cycles through phases A, B and C with greens of {{fixed_time_params.GREENS.A::0}} s, {{fixed_time_params.GREENS.B::0}} s and {{fixed_time_params.GREENS.C::0}} s, plus amber and all-red, and represents the pre-timed plans common in practice. **count_timer** is a camera-count-plus-timer controller: each green begins at a minimum of {{controller_params.count_timer.MIN_GREEN::0}} s and is extended in steps of {{controller_params.count_timer.STEP::0}} s while the served queue is at least {{controller_params.count_timer.QUEUE_THRESHOLD::0}} vehicles, up to {{controller_params.count_timer.MAX_GREEN::0}} s, with phases cycling A, B, C. **max_pressure** follows the max-pressure principle (Varaiya, 2013), which has been used in learning-based control (Wei et al., 2019a): at each decision it picks the phase whose served movements have the largest total queue, with a fixed green of {{controller_params.max_pressure.GREEN::0}} s. For an isolated junction the downstream queue is treated as empty, so pressure reduces to upstream queue, a simplification that would not hold in a network.
### 3.6.2 Baselines that were not built

Two further baselines were planned and are not built: a deep reinforcement learning controller of the kind applied to traffic signals at scale (Wei et al., 2019b; Chu et al., 2020), and a language-model agent such as LLMLight (Lai et al., 2023). The comparison here is therefore against classical baselines only, and no statement is made about how AfriCoT-VLA compares with learned or language-model controllers. Both are listed as future work.
### 3.6.3 The AfriCoT-VLA variants

Three variants are defined. **africot_noslow** uses the fast loop with a fixed default subgoal (all queue weights 1.0, pedestrian weight 1.0, maximum wait 120 s, transit priority 1.0, validity 300 s) and no slow loop, as the "without slow loop" ablation. **africot_nowm** has no learned world model and scores candidate first steps with a queue-discharge heuristic from current queues, a smoothed arrival-rate estimate and fixed discharge rates, as the "without world model" ablation; its rates are untuned estimates, so it ablates one heuristic and does not bound what a model-free planner could reach. **africot_full** has the slow loop on.

<!--COLAB:method_full-->
The africot_full variant is implemented and has been wiring-tested with the mock backend on all four scenarios and five seeds, and the real `hf` backend has been called once on one snapshot with the 3B model. It has not been evaluated. A grid of africot_full runs with the 7B model on a GPU is prepared as a notebook for separate execution. Until those runs are available, no statement is made in this dissertation about the effect of the slow loop on traffic performance.
<!--/COLAB-->

## 3.7 Metrics

Metrics come from SUMO trip records and per-step sampling, always excluding the warm-up. Average travel time (ATT) and average waiting time (AWT) cover every demand vehicle scheduled to depart after the warm-up and include insertion delay: ATT is departure delay plus trip duration, and AWT is departure delay plus waiting time. A vehicle still in the network at 3900 s, and a vehicle never inserted, is right-censored at 3900 s, and a never-inserted vehicle counts 3900 s minus its scheduled departure for both quantities. The rule is the same for every controller. It was adopted after a review found that with SUMO's plain trip means the delay of vehicles queued outside the network vanished, so a controller that starved the side road could look better. The censoring makes AWT a lower bound for vehicles that did not finish. Completed-trip means (`att_completed`, `awt_completed`) and the count not inserted are also kept.

Average queue length (AQL) is the mean over steps of halting demand vehicles summed over incoming lanes. Throughput is the number of vehicles that arrived, and average pedestrian waiting time is also recorded. Shield interventions, slow-loop calls, parse failures, audit violations and teleports with their reasons are logged. Each result is a mean and sample standard deviation over the five evaluation seeds. Jam teleports are counted separately from other teleports, which are sublane artefacts such as a vehicle blocked while yielding to pedestrians.

### 3.8.1 The world model

The world model is a small recurrent network in the style of the latent world models used for planning, such as DreamerV3 (Hafner et al., 2025) and TD-MPC2 (Hansen et al., 2024). It is neither of them, and no claim is made that it reproduces their methods. An encoder maps the observation to a 32-dimensional latent, a gated recurrent unit takes the latent and the action and gives the next latent, and a decoder predicts the queue per approach, the pedestrians waiting at each crossing and the departures per approach for the next decision. It can be rolled forward for several steps. The observation holds per-approach queues, class counts, halting danfos, occupancy and departures, waiting pedestrians per crossing, movement queues, the phase as a one-hot vector, time in phase and normalised time of day. The action is the next phase as a one-hot vector and the green time divided by 60 s. Inputs and targets both come from the noisy perception output, so the model sees only what a deployed controller would see and its errors are measured against noisy observations.

Training data are transitions logged from fixed_time, count_timer, max_pressure and a seeded random-timing controller, in 300 episodes from the normal, market and incident scenarios on tuning seeds 100 to 104 and data seeds 200 to 219. Outage is omitted because, for controllers without a slow loop, outage episodes would duplicate market episodes exactly. The split is by seed: seeds 100 to 104 and 200 to 209 for training ({{world_model.n_windows.train::0}} three-decision windows), 210 to 214 for validation ({{world_model.n_windows.validation::0}}) and 215 to 219 for testing ({{world_model.n_windows.test::0}}). Training runs on the CPU with mean squared error over a three-step rollout, Adam at a learning rate of {{world_model.hyperparameters.lr::3}}, a batch size of {{world_model.hyperparameters.batch::0}}, a hidden size of {{world_model.hyperparameters.hidden::0}}, early stopping with a patience of {{world_model.hyperparameters.patience::0}} epochs, and a single torch seed.

The acceptance check is that, on held-out data, the one-step mean absolute error of queue prediction must beat a persistence guess ("queues stay the same") by at least 10 per cent, with one-step and three-step errors reported. Persistence is a weak comparator, since a green discharges the served queue, so the threshold is a minimum bar and not a measure of usefulness. The results are reported in the next chapter.

The planner uses the Cross-Entropy Method over plans of three steps. Each step has a phase, drawn from a categorical distribution, and a green time, drawn from a Gaussian clipped to 10 s to 60 s and rounded to whole seconds. The initial green distribution has a mean of {{planner_config.green_mu::0}} s and a standard deviation of {{planner_config.green_sd::0}} s, with the standard deviation floored at 2 s. Each iteration draws {{planner_config.samples::0}} samples, imagines each with the world model, ranks them by cost, and refits the distributions to the {{planner_config.elites::0}} lowest-cost samples, for {{planner_config.iterations::0}} iterations. The random generator is seeded. The cost of an imagined rollout, summed over the horizon, is

cost = Σ_a w_a · queue_a + pedestrian_weight · ped_wait + transit_priority · waiting_danfos + 1000 · max(0, est_wait_a − max_wait_s)

where w_a are the subgoal's queue weights, and the last term is a heavy penalty on any approach whose estimated wait exceeds the subgoal's maximum wait. Only the first step of the best plan is returned, and the shield then corrects it if necessary. Two implementation details are worth stating. The world model does not predict danfos, so the planner approximates waiting danfos as the predicted queue multiplied by the currently observed danfo share of the queue on each approach. And the cost is summed per plan step without weighting by the duration of the step, so a long green is not penalised for the time it covers. No planner parameter was tuned.

## 3.9 Reproducibility

The prototype is designed so that every reported number can be regenerated from committed code. Each run is identified by controller, scenario and seed, and writes a result file with its metrics, full configuration, git hash and VLAM backend. The runner skips existing runs unless forced, and mock-backend results are redirected to a separate directory and marked not reportable. Dependencies are pinned and the code runs headless.

Before this dissertation was written, the repository was checked at the commit under test. The suite of {{tests.pytest_passed_at_start::0}} tests passed, and one run per controller on the normal scenario with seed 0 (SUMO 1.27.1) reproduced the committed metrics apart from wall time and git hash. That verified one scenario and one seed per controller, not all {{n_eval_runs::0}} evaluation runs.

Construct validity concerns whether the simulation and metrics measure what matters. The junction is a plausible Lagos-style layout and not a model of a specific junction, sublane behaviour only approximates informal transport, and perception is ground truth plus an assumed noise model. The metrics treat unfinished vehicles identically for all controllers.

Internal validity concerns whether differences are caused by control. All controllers see the same demand and pass through the same shield, tuning is confined to seeds never used for reporting, and no planner parameter was tuned. However, the world model was trained on four controllers' state distribution and is queried on plans they would rarely produce.

Statistical conclusion validity is limited by five evaluation seeds and by large standard deviations in some cells. Paired by-seed comparisons are exploratory, with n equal to 5 and no correction for multiple comparisons, and the exact two-sided Wilcoxon test cannot give a probability below 0.0625 with five seeds. No superiority is claimed where a gap lies within one standard deviation, and such controllers are described as comparable. Outage equals market for every controller without a slow loop, so it is not an independent scenario for them.

External validity is the weakest. There is one junction, one simulator, simulated traffic and no field trial, so the results say nothing about real roads, cameras or a corridor, and the only real-model slow-loop output so far is one 3B call on one snapshot.

Five ablations are planned and two have been run. Without the slow loop (africot_noslow) and without the world model (africot_nowm) were run on four scenarios and five seeds. Behaviour under connection loss is represented by the outage scenario, which is implemented, but africot_full is not evaluated and the other controllers have no slow loop, so outage equals market for them. The comparison with and without neighbour information is not run because there is a single junction. The comparison of fixed against capability-aware routing is not run because routing between edge and cloud models is not built.
## 3.12 Specified versus built

The table below lists every component of the design, what the design specifies, what was built and tested, and its status. "Built and tested" means that the code exists and that repository tests exercise it, not that its effect on traffic has been shown.

Table: Specified versus built: each component of the design and its status in the prototype

| Component | Specified in design | Built and tested in prototype | Status |
|---|---|---|---|
| Edge perception | Edge detector giving queues, counts, occupancy; raw video stays on site | Simulated from SUMO ground truth plus noise; no detector or camera | Partly built (simulated) |
| Latent world model | Predicts queue evolution; takes neighbour outflows as inputs | GRU latent model (32 dimensions), one junction; one-step error checked against persistence | Built and tested (single junction) |
| CEM planner (fast loop) | Chooses phase timing, always local | Three-step CEM, 64 samples, 4 iterations, 8 elites, subgoal-weighted cost | Built and tested |
| Subgoal interface | Compact vector of cost weights and bounds; emergency override separate | Schema with ranges, clamping validator, parser, default subgoal | Built and tested |
| VLAM with CoT (slow loop) | Reads keyframes and context, outputs subgoal with written justification | Renderer, prompt, `mock` and `hf` backends; one 3B call on one snapshot gave a parseable subgoal | Built; wiring-tested; real-model use limited to one smoke call |
| Safety shield | Minimum and maximum green, amber, all-red, pedestrian time, spillback rule, starvation guard | All rules except spillback (not applicable at one junction); pedestrian minimum stricter than specified; independent audit | Built and tested (spillback not applicable) |
| Explainability log | Timestamped log with CoT trace and triggers; proposed frame hash, tamper-evident store | One JSON line per decision; no frame hash or tamper-evident store | Partly built |
| Capability-aware coordinator | Rule-based routing by connectivity, compute and novelty between edge and cloud | Scheduled and novelty-triggered calls, outage hold and schedule switch, logging; no model routing | Partly built |
| Degradation tiers | Cloud VLAM; edge VLM or cached schedule; last subgoal; fixed-time plan | Hold-last and cached schedule tested with the mock backend; no edge model; no automatic fixed-time fallback | Partly built |
| Cloud VLAM tier | Large VLAM in the cloud at full connectivity | Configurable backend (3B on CPU; 7B prepared for GPU); no cloud deployment | Not built as a tier |
| Tiered communication (SMS, mesh, satellite, store-and-forward) | Five tiers with signed messages | None; outage modelled as an on-off window for the slow loop | Described only |
| Emergency override | Verified emergency message forces a phase, subject to clearance | None | Described only |
| Multi-junction exchange | Neighbour outflows as model inputs; mesh sharing; cluster server | None; single junction | Not built |
| Eight-layer deployment framework | Cloud-based framework credited to Dr. Fasina, with the author's proposed refinements | A design artefact only; nothing deployed | Described only |
| Baselines: fixed_time, count_timer, max_pressure | Reference controllers | Built; evaluated on four scenarios and five seeds (max_pressure in isolated-junction form) | Built and evaluated |
| Baseline: deep RL controller | Reference | Not built | Not built |
| Baseline: LLMLight | Reference | Not built | Not built |
| Variants: africot_noslow, africot_nowm | Ablations without the slow loop and without the world model | Built; evaluated on four scenarios and five seeds | Built and evaluated |
| Variant: africot_full | Full system with slow loop | Implemented; mock-backend wiring tests (20 runs); one 3B smoke call; no evaluation runs | Implemented, wiring-tested, not yet evaluated |
| Hardware-in-the-loop, shadow mode, pilot | Deployment roadmap | None; the detector test on real Lagos footage is also not done | Described only |

The deployment roadmap (Jetson-class edge hardware with hardware-in-the-loop testing, then shadow mode, then a supervised pilot with override, then live operation) is described and not built.

## 3.13 Chapter summary

The chapter has described a design in which a slow, advisory reasoning loop sets priorities and a fast, local planning loop chooses signal timings under a rule-based shield, and the much smaller prototype that tests part of it in simulation. The coordinator's routing, tiered communication, emergency override, multi-junction exchange and the eight-layer framework are described and not built. The next chapter reports what was implemented and what the simulations show.