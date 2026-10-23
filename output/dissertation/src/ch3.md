# Chapter 3: Methodology and System Design

## 3.1 Introduction

This chapter sets out how the AfriCoT-VLA system is designed and how the prototype was built and evaluated, keeping separate the full design, including parts specified but not built, and what was implemented and tested. The system is intended to be hosted on the cloud, with an on-site fast loop and safety shield as a resilience tier. The prototype is a single Lagos-style T-junction in the SUMO traffic simulator (Alvarez Lopez et al., 2018), whereas the design addresses a corridor of nearby junctions, tiered communication and a cloud deployment. A table near the end lists the status of every component.

The design treats the constraints of Sub-Saharan African cities as inputs to the architecture. Five principles follow.

First, the real-time control loop must never depend on a network link. Mobile data coverage in the region remains uneven (GSMA, 2024a, 2024b) and access to electricity incomplete (International Energy Agency et al., 2025). The reasoning and management layers are therefore intended to be hosted on the cloud, where a large model can run, while the loop that selects timings stays on the junction's edge computer as a resilience tier.

Second, the two kinds of reasoning involved differ in time scale and cost. Predicting queues and choosing a phase timing is fast and repetitive, whereas noticing that a market is in progress or that a lane is blocked is slow and occasional, and suits a large vision-language model. Hierarchical designs with a slow language-conditioned level and a fast control level have precedent in robotics (Shi et al., 2025; Hafner et al., 2022), and the authors' earlier paper proposed a related architecture (Ariyo & Fasina, 2026), which this chapter extends.

Third, nothing learned may bypass a safety rule: minimum green, clearance and pedestrian crossing time are explicit rules between the planner and the signals, and the slow loop can alter priorities but cannot issue phase commands. Fourth, the system degrades gracefully through four operating tiers, so that loss of connectivity or of a component leads to simpler and not unsafe behaviour.

Fifth, decisions must be explainable to regulators such as the Lagos State Traffic Management Authority (LASTMA) and the state Ministry of Transportation, so every decision is designed to be logged with its triggering conditions and, for slow-loop decisions, the written reasoning behind the subgoal. Chain-of-thought reasoning has been used to expose intermediate steps in robot control (Zawalski et al., 2024; Yang et al., 2025).

Two further choices apply. Only open-weight models are used, none trained from scratch. And the vision-language-action model and the latent world model are coupled and not fused, linked only by a compact subgoal, because full unification of action generation and world modelling is an open research problem.
## 3.3 The two-timescale architecture

The architecture has an edge perception stage, a fast loop, a slow loop, a subgoal interface between them, a safety shield, an explainability log and a coordinator. Edge perception, the fast loop and the shield form the on-site resilience tier, and the slow loop with the upper management layers is intended to be hosted on the cloud. In the figure below, solid arrows carry control information and dashed arrows carry keyframes, coordination decisions and log records.

![[figure:architecture_two_timescale.png|The two-timescale architecture: a slow loop (vision-language-action model with chain-of-thought reasoning) sets a subgoal, a fast loop (latent world model with a cross-entropy-method planner) proposes a phase, and a rule-based safety shield corrects the proposal before it reaches the signal controller]]

### 3.3.1 Edge perception

In the design, a lightweight detector on each junction's edge computer classifies vehicles by type (car, danfo, keke, okada), detects pedestrians, and computes for each approach the queue length, counts by class and occupancy, plus the pedestrians waiting at each crossing. Raw video never leaves the site; the fast loop uses only these summaries and the slow loop only occasional keyframes.

In the prototype there is no camera and no detector. Perception is simulated from SUMO ground truth with the noise model described later, and the detector is proposed for separate testing on real Lagos footage.

### 3.3.2 The fast loop

The fast loop runs on the junction's edge computer at every signal decision, which in the prototype is the end of each green, about {{decisions_per_run_mean::0}} decisions per run on average. A latent world model predicts how queues, waiting pedestrians and departures evolve under a candidate phase and green time. The planner samples candidate three-step plans, imagines each with the world model, scores them with a cost defined by the current subgoal, and refines its sampling towards the lowest-cost plans (Rubinstein, 1999; de Boer et al., 2005; Hafner et al., 2019; Chua et al., 2018; Hansen et al., 2024). The fast loop runs locally in every operating tier and is never routed to the cloud.

### 3.3.3 The slow loop

The slow loop is designed to run every few minutes, or earlier when something unusual occurs, and in the intended deployment it runs in the cloud. A vision-language-action model (VLAM) receives a keyframe of the junction and a short context (time of day, any known event such as a market day or incident, current queues and the subgoal in force), reasons step by step and emits a subgoal in a fixed format. The prototype has two backends: a deterministic, rule-based `mock` backend used only for tests and wiring checks, and an `hf` backend that loads a Qwen2.5-VL model (Bai et al., 2025) through Hugging Face transformers, with the 3B model for CPU tests and the 7B model intended for a GPU run. Reasoning and answer are placed in `<reasoning>` and `<subgoal>` tags. The subgoal format is the only contract, so the design does not depend on this model, although manipulation-oriented models such as OpenVLA (Kim et al., 2024) would need adaptation.

A renderer produces the keyframe in the prototype. It draws a top-down 512 by 512 image from simulator state, with vehicles as shapes coloured by class, waiting pedestrians as dots, the signal state and a legend. It is a simulator view and not a photograph, so the prototype cannot show how a model reads real footage.
### 3.3.4 The subgoal interface

The subgoal is the only interface between the two loops: a compact vector of cost weights and constraint bounds that parameterise the planner's cost, so the VLAM's "action" is a statement of priorities and not a phase command. The schema is in the table below.

Table: The subgoal schema, default values and permitted ranges

| Field | Meaning | Default | Range |
|---|---|---|---|
| `queue_weights` (east, west, south) | Priority of clearing each approach | 1.0 each | 0.2 to 3.0 each |
| `pedestrian_weight` | Priority of reducing pedestrian waiting | 1.0 | 0.0 to 3.0 |
| `max_wait_s` | Longest acceptable wait (seconds) | 120 | 45 to 180 |
| `transit_priority` | Priority of waiting danfos | 1.0 | 0.0 to 2.0 |
| `valid_for_s` | Intended validity (seconds) | 300 | 60 to 900 |

A validator clamps every number to its range. A missing field keeps its previous value, and an unparseable reply leaves the previous subgoal in force.

The safety shield sits between the planner, or any other controller, and the signals. In the prototype every controller, including the baselines, passes through it. It applies these rules in order.

1. Starvation guard: an approach or crossing with observed demand and no green for over 180 s is served next.
2. Maximum green: a phase may not exceed 90 s in total.
3. Minimum green: a new phase lasts at least 10 s.
4. Pedestrian minimum: a phase that gives green to a crossing lasts at least the crossing length divided by 1.2 m/s plus 4 s, which is 16 s for the east and west crossings and 10 s for the south crossing.
5. Clearance: every phase change passes through an amber of 3 s and an all-red of 2 s, inserted by the simulation environment.

Each correction is returned with its rule and reason for logging. The shield sees only the noisy perception output and its own signal history, while a separate audit class reads simulator ground truth and counts rule violations. Because both share the same rule constants, the audit tests the implementation and not whether the rules suffice for real-world safety.

Two departures from the design are recorded. Because perception misses pedestrians, the prototype applies the pedestrian minimum on every phase that gives green to a crossing and not only when pedestrians are observed, which is stricter and never less safe. And the spillback rule, which forbids releasing traffic towards a full downstream approach, has no meaning at a single junction and is not built.

### 3.3.6 The explainability log

Each decision produces one JSON line holding the simulation time, controller, scenario and seed; the trigger (scheduled, novelty or none); the connectivity state; the VLAM backend; the reasoning text; the subgoal in force; the planned phases and greens; the shield correction and its reason; the applied phase and green; and the world model's one-step error. A frame hash, a predicted-versus-actual record and tamper-evident storage are proposed and not built, and no regulator has assessed the log.

### 3.3.7 The capability-aware coordinator and the degradation tiers

The design includes a rule-based, non-learned coordinator that routes only slow-loop tasks according to connectivity, available compute and scene novelty. A routine scene goes to a small vision-language model on the edge, an unusual scene to a large cloud model when connectivity allows, and an emergency triggers a direct override. The four operating tiers (cloud VLAM; edge VLM or cached schedule; last subgoal; fixed-time plan) are mapped to cloud behaviour in the cloud deployment architecture below.

The prototype implements a subset. The coordinator calls the slow loop every 300 simulated seconds and early when a novelty trigger fires, namely when the mean one-step world-model queue error over the last 10 decisions exceeds twice the median of the 30 before them, with at least 120 s between triggers. During an outage window it holds the last subgoal, and after more than 600 s offline it switches to a hand-written, untuned time-of-day schedule. The slow loop is treated as instantaneous in simulated time, an idealisation since one 3B call takes minutes on a four-core CPU.

Much is not built. There is no routing between an edge model and a cloud model, the weak-connectivity tier is represented only by the cached schedule, and no automatic switch to the fixed-time plan on a fault exists. An emergency-vehicle override, in which a verified message forces a phase directly while still respecting clearance rules, is described only.
### 3.3.8 Tiered communication

The design arranges five communication tiers in order of preference: 4G or fibre for everything except raw video; SMS over GSM for alerts and subgoals when data service is down; store-and-forward for logs and training data; a junction-to-junction mesh over Wi-Fi or LoRa as the main offline path, since the junctions are close together; and, optionally, satellite for critical alerts. All incoming messages are to be cryptographically signed, and may change priorities but never bypass the shield. None of these tiers is implemented.

The design also anticipates a corridor of two to three junctions, in which each world model takes its neighbours' outflows as inputs, neighbours share queue and plan data over the mesh so that green waves continue offline, and an optional cluster edge server runs the small vision-language model. The prototype has a single junction, so none of this is built.

## 3.4 The eight-layer deployment framework

### 3.4.1 Origin and content

The layered framework used here originates with the supervisor, Dr. Fasina, and is the organising structure of the intended cloud deployment. During the class session of 27 July 2026 they typed the prompt "Design a cloud-based 8-layer framework for AfriCoT-VLA" into DeepSeek on a shared screen, and the structure is credited to them. The layers are the sensor layer (cameras and actuators for traffic lights); the network connection (compressed video from the cameras over the internet to the cloud); the data store; the model layer (chain-of-thought reasoning, latent world models and the VLAM); the explainability layer; the service layer; the AI agent layer; and the autonomous agentic layer.

The author proposes refinements, which are the author's own and have not yet been confirmed by the supervisor. The data store would hold a hot window and a cold history. The model layer would follow the two-timescale design of this chapter. The service layer would expose decision, query, override and health interfaces. The AI agent layer would handle corridor coordination, and the autonomous agentic layer would produce plan proposals and what-if simulations that a human signs off. Any layer above the model layer could fail with fallback to fixed-time control, the explainability layer would act as a deployment gate, and the network layer is proposed to be the real bottleneck.

![[figure:eight_layer_framework.png|The eight-layer deployment framework, credited to Dr. Fasina, with the author's proposed refinements (not yet confirmed by the supervisor)]]
### 3.4.2 The cloud versus on-site video tension and its reconciliation

The framework as the supervisor framed it is cloud-based and sends compressed video to the cloud, whereas keeping raw video on site and running the fast loop locally appears to conflict with it. With all processing in the cloud, every signal decision would depend on a network link.

The author proposes the following reconciliation, built on the supervisor's framing and not supervisor-approved. The eight layers are kept. The cloud is the primary tier for the data store, the model layer with the VLAM and its reasoning, the explainability layer, the service layer, the AI agent layer and the autonomous agentic layer. The network layer carries compressed keyframes for the slow loop and not continuous video, and raw video never leaves the site. The sensor layer, the fast loop and the safety shield remain on the edge computer as the resilience tier, so that loss of the network leaves the junction running.

## 3.5 Cloud deployment architecture

### 3.5.1 Hosting and placement

The deployed system is intended to be hosted on the cloud, following the supervisor's framework. The cloud is the primary tier for the data store, the model layer, the explainability layer, the service layer, the AI agent layer and the autonomous agentic layer. The junction hosts the sensor layer, edge perception, the fast loop and the safety shield, which form the resilience tier that keeps the signals operating whenever the link weakens or fails. The network layer carries compressed keyframes, summary state, subgoals and log records between them. The cloud region is a design question: a region near Lagos would shorten round trips, a distant one may offer more mature managed services, and the choice interacts with data residency. Components are intended to be packaged as containers, with managed services where available, and no vendor is assumed.

### 3.5.2 Latency and cost

The slow loop is designed to run every few minutes, so a round trip of several seconds, covering keyframe upload, model inference and return of the subgoal, is tolerable, because the fast loop continues on the subgoal in force while a call is pending. Latency matters for emergency messages and subgoal freshness, not signal timing. Keyframes are single compressed images sent occasionally, which is intended to keep uplink demand small compared with continuous video, although their size and data cost have not been measured. The only latency figure in this work is the wall-clock time of one 3B model call on a four-core local CPU, which is not a cloud figure. No cost has been estimated.

### 3.5.3 Security and data residency

Every message between an edge node and the cloud is designed to be cryptographically signed, with each edge node authenticated to the cloud and the cloud to each edge node. A message may change priorities and never bypass the shield, so a spoofed message could at worst degrade efficiency and not safety. Components are to run with least privilege: the cloud holds no credentials that can write to the signal controller, which is reached only through the edge computer and the shield. Raw video stays on site.

Data residency is an open question for the supervisor and for the regulators. Whether keyframes, decision logs and reasoning traces may be stored outside Nigeria, and in which region, has to be settled with LASTMA and the Ministry of Transportation, and the answer may constrain the choice of cloud region.

### 3.5.4 Behaviour across the degradation tiers

With full connectivity the cloud runs the large VLAM for the slow loop and hosts the upper layers. With weak connectivity the cloud is called less often or not at all: the junction uses a small VLM on the edge or the cached time-of-day schedule, alerts and subgoals may travel by SMS or the junction mesh, and logs wait for store-and-forward. With no connectivity the fast loop continues on the last subgoal and logs are queued locally. On a system fault the junction runs a fixed-time plan, which the cloud layers cannot affect. The prototype's outage scenario simulates only the last two connectivity behaviours, through a scripted window in which the coordinator holds the last subgoal and later switches to a hand-written schedule.

No part of this cloud deployment has been built or tested. The prototype simulates the control logic and the outage behaviour with a mock or scripted backend, plus a single smoke test of a 3B model on a local machine. No measurement of latency, availability, cost, security or data residency exists, and this section states design intent for a staged evaluation described in the final chapter.

## 3.6 Simulation environment

### 3.6.1 The junction

The experimental environment is a single signalised T-junction in SUMO. The main road runs east to west with two lanes in each direction at 50 km/h, and the side road is the south arm with one lane in each direction at 40 km/h. Every approach is 300 m long, each arm has a sidewalk and a pedestrian crossing, the step is 1 s, and the sublane model with a lateral resolution of 0.8 m lets motorcycles filter between lanes.

### 3.6.2 Phases

Three signal phases serve six movements. Phase A serves the main road with the east left turn permissive and pedestrians crossing the south arm. Phase B gives the east approach a protected left with east through and no crossing. Phase C serves the side road, with turns yielding to pedestrians, and gives green to the east and west crossings. A conflict checker confirms that no conflicting movements are green together.

Four vehicle types represent informal transport. A car is 4.5 m long (60 km/h maximum), a danfo is a 5.5 m minibus (50 km/h) that counts as transit, a keke is a 2.7 m tricycle (40 km/h), and an okada is a 2.0 m motorcycle (60 km/h) with arbitrary lateral alignment so that it filters between lanes. On tuning seeds the lateral standard deviation of okada positions ranged from {{s1_okada_lateral_sd_range_m.0::2}} m to {{s1_okada_lateral_sd_range_m.1::2}} m, against {{s1_car_lateral_sd_range_m.0::2}} m to {{s1_car_lateral_sd_range_m.1::2}} m for cars, which indicates that filtering is present. These are simulation settings, not Lagos measurements.

Each scenario lasts 3600 s of measured time after a 300 s warm-up excluded from every metric, so each run ends at 3900 s. Demand is a seeded Poisson process, so every controller sees the same traffic for a given scenario and seed. The normal scenario represents a typical peak. The market scenario raises pedestrian demand and shifts the mix towards keke and okada. The incident scenario is the normal scenario with the kerb lane of the east approach closed to demand vehicles from 1200 s to 2100 s. The outage scenario carries market demand and makes the slow loop unreachable from 1200 s to 2400 s. Turning shares are 80 and 20 per cent (through and right) from the west, 75 and 25 (through and left) from the east, and 50 each way from the south. The parameters are in the table below.

Table: Scenario parameters (demand per origin arm in vehicles per hour, vehicle mix, pedestrian demand and events)

[[scenario_table]]

Two points matter for interpretation. First, market side-road demand is 200 vehicles per hour and not the 550 specified originally. At 550 the south arm gridlocked under fixed-time control on the tuning seeds, with a mean insertion delay of {{demand_tuning.candidates.0.mean_south_depart_delay_s::0}} s and up to {{demand_tuning.candidates.0.max_south_not_inserted::0}} vehicles never inserted. A tuning script tried 550, 300, 275, 250, 225 and 200, requiring at most five uninserted south vehicles on every seed and a mean south insertion delay below 60 s. Only 200 met it, with a mean delay of {{demand_tuning.candidates.5.mean_south_depart_delay_s::1}} s. Market congestion therefore comes from the vehicle mix, from 900 pedestrians per hour, and from pedestrians blocking the yielding turns from the south. Second, the incident scenario raises delay only modestly under fixed-time control, because one lane still carries flow.

### 3.6.5 Seeds and their roles

Three disjoint seed sets serve distinct purposes. Tuning seeds 100 to 104 are used to check scenarios and tune demand. Data seeds 200 to 219 are used with them to collect world-model training data. Evaluation seeds 0 to 4 are used for reported results and never for tuning or training; the collection code refuses them and the loader checks again.

Controllers observe the junction only through a noise model that stands in for an imperfect detector. Each vehicle is missed with probability {{perception_config.miss_p::2}}, and Gaussian noise with a standard deviation of {{perception_config.rel_sd::pct1}} per cent of the value, with a minimum of {{perception_config.min_sd::1}}, is added to counts, which are then clipped at zero. A clean ground-truth mode is used only for metrics and the audit. The level is an assumption, not a measured detector property.

### 3.7.1 Baselines that were built

Three baselines were built, all passing through the shield. **fixed_time** cycles through phases A, B and C with greens of {{fixed_time_params.GREENS.A::0}} s, {{fixed_time_params.GREENS.B::0}} s and {{fixed_time_params.GREENS.C::0}} s, plus amber and all-red, representing common pre-timed plans. **count_timer** is a camera-count-plus-timer controller: each green begins at a minimum of {{controller_params.count_timer.MIN_GREEN::0}} s and is extended in steps of {{controller_params.count_timer.STEP::0}} s while the served queue is at least {{controller_params.count_timer.QUEUE_THRESHOLD::0}} vehicles, up to {{controller_params.count_timer.MAX_GREEN::0}} s, with phases cycling A, B, C. **max_pressure** follows the max-pressure principle (Varaiya, 2013), which has been used in learning-based control (Wei et al., 2019a): at each decision it picks the phase whose served movements have the largest total queue, with a fixed green of {{controller_params.max_pressure.GREEN::0}} s. For an isolated junction the downstream queue is treated as empty, a simplification that would not hold in a network.

Two further baselines were planned and are not built: a deep reinforcement learning controller of the kind applied to traffic signals at scale (Wei et al., 2019b; Chu et al., 2020), and a language-model agent such as LLMLight (Lai et al., 2023). The comparison is therefore against classical baselines only.

Three variants are defined. **africot_noslow** uses the fast loop with a fixed default subgoal (all queue weights 1.0, pedestrian weight 1.0, maximum wait 120 s, transit priority 1.0, validity 300 s) and no slow loop. **africot_nowm** has no learned world model and scores candidate first steps with a queue-discharge heuristic from current queues, a smoothed arrival-rate estimate and fixed discharge rates; its rates are untuned, so it does not bound what a model-free planner could reach. **africot_full** has the slow loop on.

<!--COLAB:method_full-->
The africot_full variant is implemented and has been wiring-tested with the mock backend on all four scenarios and five seeds, and the real `hf` backend has been called once on one snapshot with the 3B model. It has not been evaluated. A grid of africot_full runs with the 7B model on a GPU is prepared as a notebook for separate execution. Until those runs are available, no statement is made in this dissertation about the effect of the slow loop on traffic performance.
<!--/COLAB-->

## 3.8 Metrics

Metrics come from SUMO trip records and per-step sampling, always excluding the warm-up. Average travel time (ATT) and average waiting time (AWT) cover every demand vehicle scheduled to depart after the warm-up and include insertion delay: ATT is departure delay plus trip duration, and AWT is departure delay plus waiting time. A vehicle still in the network at 3900 s, or never inserted, is right-censored at 3900 s, a never-inserted vehicle counting 3900 s minus its scheduled departure. The rule is the same for every controller and was adopted because with SUMO's plain trip means the delay of vehicles queued outside the network vanished, so a controller that starved the side road could look better. The censoring makes AWT a lower bound for vehicles that did not finish.

Average queue length (AQL) is the mean over steps of halting demand vehicles summed over incoming lanes. Throughput is the number of vehicles that arrived, and average pedestrian waiting time is also recorded. Shield interventions, slow-loop calls, parse failures, audit violations and teleports are logged. Each result is a mean and sample standard deviation over the five evaluation seeds.

## 3.9 The world model and planner

The world model is a small recurrent network in the style of latent world models used for planning, such as DreamerV3 (Hafner et al., 2025) and TD-MPC2 (Hansen et al., 2024), though it is neither of them. An encoder maps the observation to a 32-dimensional latent, a gated recurrent unit takes the latent and the action and gives the next latent, and a decoder predicts the queue per approach, the pedestrians waiting at each crossing and the departures per approach for the next decision. The observation holds per-approach queues, class counts, halting danfos, occupancy and departures, waiting pedestrians per crossing, movement queues, the phase, time in phase and normalised time of day. The action is the next phase and the green time divided by 60 s. Inputs and targets both come from the noisy perception output, so errors are measured against noisy observations.

Training data are transitions logged from fixed_time, count_timer, max_pressure and a seeded random-timing controller, in 300 episodes from the normal, market and incident scenarios. Outage is omitted because, for controllers without a slow loop, it would duplicate market episodes. The split is by seed: seeds 100 to 104 and 200 to 209 for training ({{world_model.n_windows.train::0}} three-decision windows), 210 to 214 for validation ({{world_model.n_windows.validation::0}}) and 215 to 219 for testing ({{world_model.n_windows.test::0}}). Training uses mean squared error over a three-step rollout, Adam at a learning rate of {{world_model.hyperparameters.lr::3}}, a batch size of {{world_model.hyperparameters.batch::0}}, a hidden size of {{world_model.hyperparameters.hidden::0}}, early stopping with a patience of {{world_model.hyperparameters.patience::0}} epochs, and a single torch seed.

The acceptance check is that, on held-out data, the one-step mean absolute error of queue prediction must beat a persistence guess ("queues stay the same") by at least 10 per cent, with one-step and three-step errors reported. Persistence is a weak comparator, so the threshold is a minimum bar.

The planner uses the Cross-Entropy Method over plans of three steps. Each step has a phase, drawn from a categorical distribution, and a green time, drawn from a Gaussian clipped to 10 s to 60 s and rounded to whole seconds, with an initial mean of {{planner_config.green_mu::0}} s and a standard deviation of {{planner_config.green_sd::0}} s floored at 2 s. Each iteration draws {{planner_config.samples::0}} samples, imagines each with the world model, ranks them by cost, and refits the distributions to the {{planner_config.elites::0}} lowest-cost samples, for {{planner_config.iterations::0}} iterations. The cost of an imagined rollout, summed over the horizon, is

cost = Σ_a w_a · queue_a + pedestrian_weight · ped_wait + transit_priority · waiting_danfos + 1000 · max(0, est_wait_a − max_wait_s)

where w_a are the subgoal's queue weights, and the last term is a heavy penalty on any approach whose estimated wait exceeds the subgoal's maximum wait. The world model does not predict danfos, so the planner approximates waiting danfos as the predicted queue multiplied by the observed danfo share on each approach. The cost is summed per plan step without weighting by step duration, so a long green is not penalised for the time it covers. No planner parameter was tuned.

## 3.10 Reproducibility and validity

Every reported number is designed to be regenerable from committed code. Each run writes a result file identified by controller, scenario and seed, with its metrics, configuration, git hash and VLAM backend, and mock-backend results are marked not reportable.

The suite of {{tests.pytest_passed_at_start::0}} tests passed, and one run per controller on the normal scenario with seed 0 (SUMO 1.27.1) reproduced the committed metrics apart from wall time and git hash. That verified one scenario and seed per controller, not all {{n_eval_runs::0}} evaluation runs.

Construct validity is limited because the junction is a plausible Lagos-style layout and not a specific junction, sublane behaviour only approximates informal transport, and perception is ground truth plus assumed noise. Internal validity is supported because all controllers see the same demand and shield and tuning is confined to other seeds, but the world model was trained on four controllers' states and is queried on plans they rarely produce.

Statistical conclusion validity is limited by five evaluation seeds and by large standard deviations in some cells. Paired by-seed comparisons are exploratory, with n equal to 5 and no multiplicity correction, and the exact two-sided Wilcoxon test cannot give a probability below 0.0625 with five seeds. No superiority is claimed where a gap lies within one standard deviation, and such controllers are described as comparable.

External validity is the weakest: one junction, one simulator and no field trial mean the results say nothing about real roads, cameras, a corridor or a cloud deployment.

Five ablations are planned and two have been run: without the slow loop and without the world model, on four scenarios and five seeds. Behaviour under connection loss is represented by the outage scenario, but africot_full is not evaluated. The neighbour-information and routing comparisons are not run, because there is a single junction and no edge-cloud routing.

The table below lists every component of the design, what it specifies, what was built and tested, and its status. "Built and tested" means that the code exists and repository tests exercise it, not that its effect on traffic has been shown.

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
| Cloud hosting of layers 3 to 8 | Data store, model, explainability, service, agent and agentic layers hosted on the cloud | None; nothing deployed | Not built |
| Data residency | Region and storage rules agreed with LASTMA and the Ministry of Transportation | None; open question for the supervisor and regulators | Not built; open question |
| Signed-message security | Signed messages, authenticated edge nodes, least privilege | None; no signing or authentication code | Not built |
| Latency and cost measurement | Round-trip, availability and cost figures for a cloud deployment | None; only one 3B call timed on a local CPU, not a cloud figure | Not measured |
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

The deployment roadmap (Jetson-class edge hardware with hardware-in-the-loop testing, then shadow mode, then a supervised pilot with override, then live operation) is described and not built; cloud hosting and its measurement would be staged within it.

## 3.12 Chapter summary

The chapter has described a design in which a slow, advisory reasoning loop, intended to be hosted on the cloud, sets priorities, and a fast, local planning loop chooses signal timings under a rule-based shield that keeps the junction running when the link fails. It has also described the much smaller prototype that tests part of the design in simulation. The cloud deployment, routing, tiered communication, emergency override, multi-junction exchange and the eight-layer framework are described and not built. The next chapter reports what was implemented and what the simulations show.