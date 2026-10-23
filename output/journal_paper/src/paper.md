% AfriCoT-VLA: Coupling Chain-of-Thought Vision-Language Reasoning with a Latent World Model for Infrastructure-Constrained Traffic Signal Control in Sub-Saharan Africa
% Authors: Temitope W. Ariyo, Ebun P. Fasina

# Abstract

Traffic signal control in Sub-Saharan African cities has to cope with mixed informal transit, intermittent connectivity and power, sparse sensing and a need for decisions that regulators can audit. This paper proposes AfriCoT-VLA, a two-timescale design in which a vision-language-action model with chain-of-thought reasoning, the slow loop, occasionally turns a junction keyframe and its context into a compact subgoal with a written justification, while an on-site latent world model and a cross-entropy method planner, the fast loop, choose phase timings against that subgoal. A rule-based safety shield stands between planner and signals, a capability-aware coordinator governs degradation when connectivity is lost, and every decision is written to an explainability log. The paper extends the authors' earlier position paper with the reasoning slow loop, the shield and audit, the coordinator and simulation evidence. The system was examined in a single SUMO T-junction with cars, minibuses, tricycles and motorcycles, over five seeds in four scenarios. On held-out data the world model lowered one-step queue error against a persistence guess by {{world_model.test.1step.queue_improvement_vs_persistence::pct1}} percent. The fast loop with a default subgoal was behind max-pressure control in the means on normal and incident demand and comparable with it on market demand, and the variant without the world model was no better than fixed-time control. The shield recorded {{safety_violations_total::0}} safety violations in {{n_eval_runs::0}} evaluation runs. Negative results are reported in full.
<!--COLAB:abstract_status-->
The full system with the vision-language slow loop is implemented and wiring-tested but not yet evaluated.
<!--/COLAB-->
All findings come from one simulated junction and are exploratory.

# Keywords

traffic signal control; chain-of-thought reasoning; vision-language-action models; latent world models; explainability; Sub-Saharan Africa

# Introduction

## 1.1 Background and motivation

Cities in Sub-Saharan Africa (SSA) are beginning to equip junctions with cameras and software-controlled signals. Lagos has been reported to have selected a vendor for an intelligent traffic system (Olomu, 2025), the Lagos Metropolitan Area Transport Authority has been reported to be deploying AI-supported systems on selected roads (ITEdgeNews, 2026), and Nairobi has announced camera-equipped, centrally coordinated signals in phases (Kenya Urban Roads Authority, 2023; Kinyanjui, 2024; Mumbi, 2026). The conditions under which such controllers must run are demanding (Adeyemo, 2026). Hundreds of millions of people in the region still lack electricity (International Energy Agency et al., 2025), mobile internet adoption remains well below the world average (GSMA, 2024a, 2024b), and the compute available at a roadside cabinet is small. A junction controller for these settings has to treat power, bandwidth and compute as design inputs.

The traffic itself is also different from the conditions assumed by most signal-control research. Motorcycle taxis (okadas), tricycles (kekes) and minibuses (danfos, matatus) share the carriageway with cars, motorcycles filter between lanes, and pedestrians cross at the same junctions in large numbers on market days. Demand changes with the calendar and with incidents, and a controller tuned for a typical peak may serve a market day poorly. Finally, public authorities such as the Lagos State Traffic Management Authority and the Ministry of Transportation are expected to be able to ask why a signal behaved as it did. A controller that cannot give a reviewable account of its decisions is difficult to adopt, however well it performs.

Two families of models are attractive for this problem for complementary reasons. Vision-language-action (VLA) models extend pretrained vision-language models so that images and text can be mapped to actions (Kim et al., 2024; Zitkovich et al., 2023), and several have been trained to write out intermediate reasoning before they act (Yang et al., 2025; Zawalski et al., 2024). Such models can read context that numerical sensors do not capture, and the reasoning is text that a person can read. Latent world models, on the other hand, learn a compact predictive model of an environment and let a planner imagine the consequences of candidate actions cheaply (Hafner et al., 2019; Hafner et al., 2025; Hansen et al., 2024). A large reasoning model is too slow and too connectivity-dependent to set signal timings every few seconds, whereas a small world model is cheap enough to do so on site but has no access to semantic context. The design studied here couples the two.

## 1.2 Relation to the authors' earlier work

This paper is an offshoot of a position paper by the same authors (Ariyo & Fasina, 2026), which argued that a slow, infrequent subgoal generator and a fast, on-device world-model planner should be linked through a narrow interface, and which compared candidate interfaces using a toy two-dimensional study. That paper contained no traffic domain, no chain-of-thought reasoning, no safety layer and no simulation of a real control problem. The present paper keeps the two-timescale idea and the cross-entropy planner, and adds the following.

1. A slow loop based on chain-of-thought reasoning that produces a subgoal together with a written justification, and a log that records both for audit.
2. A rule-based safety shield and an independent safety audit, which together define what the learned components may and may not do.
3. A capability-aware coordinator and explicit degradation tiers, including the behaviour when the slow loop is unreachable.
4. A SUMO prototype of one Lagos-style T-junction, with results for the parts that have been evaluated and an explicit account of the results that are negative.

The paper does not claim that the full system improves traffic control: the slow loop is implemented and wiring-tested, but its evaluation with a real vision-language model has not yet been run.

## 1.3 Research questions and contributions

Three questions guide the work. First, can a small latent world model trained on simulated perception output predict short-horizon queue evolution well enough to support planning? Second, how does a world-model planner with a fixed default subgoal compare with fixed-time, actuated and max-pressure control at one junction under four demand conditions, and which of its parts matter? Third, can the safety, audit and degradation machinery around the learned components be specified so that it can be tested independently of them? The contributions are the architecture and its interfaces, and the prototype with the evidence for the parts that were evaluated, including what failed.

# Related Work

## 2.1 Traffic signal control

A survey by Wei et al. (2019c) organises the fixed-time, actuated, adaptive and learning-based approaches to signal control. Max-pressure control selects the phase that relieves the largest pressure between upstream and downstream queues, and was shown to be throughput-optimal under stated assumptions for a network of signalised intersections (Varaiya, 2013). It needs no model of demand, which makes it a demanding baseline and the one against which the present prototype is mainly compared. Reinforcement-learning controllers include PressLight, which learns a max-pressure-inspired reward for arterial coordination (Wei et al., 2019a), CoLight, which uses graph attention for network-level cooperation (Wei et al., 2019b), and multi-agent methods for large networks (Chu et al., 2020). They typically assume dependable sensing and communication. LLMLight casts a large language model as a signal-control agent that reads textual descriptions of traffic (Lai et al., 2023). It is the closest existing work to the slow loop in motivation, but it places the language model directly in the control path, whereas the present design lets it set priorities only.

## 2.2 Latent world models and sampling-based planning

Planning in a learned latent space was popularised by PlaNet, which used the cross-entropy method to search over action sequences (Hafner et al., 2019). The cross-entropy method repeatedly refits a sampling distribution to the best-scoring candidates (de Boer et al., 2005; Rubinstein, 1999), and sampling-based planning with learned dynamics has been used in sample-efficient model-based reinforcement learning (Chua et al., 2018). Later systems trained policies in imagination (Hafner et al., 2025) or combined learned latent models with model predictive control (Hansen et al., 2024), and joint-embedding predictive models have been scaled to video (Assran et al., 2025). The world model used here is a small recurrent latent model in their general style, not an implementation of any of them, trained on noisy per-approach summaries and not on pixels.

## 2.3 Vision-language-action models and chain-of-thought reasoning

OpenVLA, Octo and π0 are generalist policies for manipulation (Black et al., 2025; Kim et al., 2024; Octo Model Team et al., 2024), RT-2 showed that web knowledge can transfer to robot control (Zitkovich et al., 2023), and a survey covers the area (Sapkota et al., 2025). Embodied chain-of-thought training teaches a policy to write intermediate reasoning steps before it acts (Zawalski et al., 2024), and InstructVLA combines multimodal reasoning with action generation through instruction tuning (Yang et al., 2025). These works address manipulation, where the action is a low-level robot command. In the present design the model's action is a subgoal, a small vector of cost weights, and the reasoning text is stored as the justification of the decision.

## 2.4 Hierarchical and dual-system designs

Splitting a slow semantic component from a fast control component is an established pattern. Hi Robot has a vision-language model issue language commands to a lower-level policy (Shi et al., 2025), GR00T N1 and Helix pair a slower vision-language module with a faster action module (Figure AI, 2025; NVIDIA et al., 2025), and Director learns goals in a latent space for a worker policy (Hafner et al., 2022). The authors' earlier paper compared several of these in detail (Ariyo & Fasina, 2026). What distinguishes the present design is the combination of a narrow cost-weight interface, an explicit planner with a learned model in the fast loop, a rule-based shield that no learned part can bypass, and degradation rules written for unreliable connectivity.

## 2.5 Safety, explainability and constrained deployment

Benchmarks and frameworks for the safety of embodied agents that are driven by language models have started to appear (Yin et al., 2024; Zhang et al., 2024), and they motivate keeping learned components away from the final actuation decision. Liu et al. (2026) argue for an infrastructure-first approach to embodied AI in the Global South, and foundation models carry risks that systems built on them inherit (Bommasani et al., 2021; Feng et al., 2025). None of this literature gives a signal-control design in which the infrastructure limits, the audit trail and the safety rules are first-order inputs, which is the gap the present paper addresses.

# System Design

The design is described in full, including parts that the prototype does not implement. A table in the experimental section lists what was built and what is only specified.

## 3.1 Two-timescale architecture

At each junction, an edge computer is connected to the existing signal controller. Edge perception converts camera input into per-approach queue length, counts by vehicle class, occupancy and the number of waiting pedestrians at each crossing. Raw video is intended to stay on site. The fast loop runs on the same edge computer at every signal decision, which in the prototype is about {{decisions_per_run_mean::0}} decisions per simulated run, and it is never routed elsewhere. The slow loop runs every few minutes, or earlier on unusual events, and it may run on the edge computer, on a cluster server or in the cloud, depending on connectivity.

![[figure:architecture_two_timescale.png|The two-timescale architecture. Solid arrows show the main data flow, dashed arrows show keyframes, coordination and logging. The subgoal is the only interface between the slow and fast loops, and the shield stands between the planner and the signal controller]]

The figure above summarises the data flow. The slow loop receives a keyframe and a context block (clock time, known events such as a market day or a reported incident, the current queues and the current subgoal). A vision-language-action model (VLAM) is asked to reason step by step and then to emit a subgoal. The fast loop receives the subgoal as the weights of its cost function. A latent world model predicts the consequences of candidate signal plans, a cross-entropy method (CEM) planner searches for the plan with the lowest cost, and only the first step of the best plan is passed to the shield. The VLAM and the world model are deliberately kept as separate models that are linked only by the subgoal. Unifying them in one model is an open research problem, and coupling is a design choice made under the compute and connectivity limits described above, not a claim that a unified model would be inferior.

### 3.1.1 Fast loop: latent world model and CEM planner

The observation vector contains the noisy perception output, the current phase, the time in phase and the normalised time of day. An encoder maps it to a latent state of {{world_model.hyperparameters.latent::0}} dimensions, a recurrent cell advances the latent given an action (the next phase and a green duration), and a decoder predicts the queues per approach, the pedestrians waiting at each crossing and the departures at the next decision. Multi-step rollout is supported so that the planner can imagine several decisions ahead.

The planner searches over plans of {{planner_config.horizon::0}} steps. Each step has a phase drawn from a categorical distribution and a green time drawn from a Gaussian that is clipped to 10 to 60 s. At each decision it draws {{planner_config.samples::0}} candidate plans, keeps the best {{planner_config.elites::0}} and refits the distribution, for {{planner_config.iterations::0}} iterations. The cost of an imagined rollout adds a weighted sum of predicted queues, a pedestrian-waiting term, a term for waiting minibuses and a steep penalty on the estimated wait of any approach beyond the maximum wait set by the subgoal. The minibus term is approximated from the world model's queue prediction and the currently observed minibus share of each queue, because the world model does not predict vehicle classes. The prototype was run only on a general-purpose CPU.

### 3.1.2 Slow loop: reasoning that produces a subgoal and a justification

The slow loop is designed to turn what a camera and a clock show into a statement of priorities. Its output is written as reasoning text followed by a JSON subgoal. The reasoning is kept as the justification that goes to the audit log. In the prototype the keyframe is a rendered top-down image of the simulated junction, which stands in for a camera frame. The VLAM backend is configurable, and the open-weight Qwen2.5-VL family (Bai et al., 2025) is used, the 3B model on a CPU for a smoke test and the 7B model planned for a GPU run. Decoding is greedy so that a call can be reproduced.

## 3.2 The subgoal interface

The subgoal is a compact vector with queue weights for each approach, a pedestrian weight, a maximum wait, a transit priority and a validity period. The permitted ranges are 0.2 to 3.0 for each queue weight, 0.0 to 3.0 for the pedestrian weight, 45 to 180 s for the maximum wait, 0.0 to 2.0 for transit priority and 60 to 900 s for validity. A validator clamps any value outside its range, keeps the previous value when a field is missing or not numeric, and keeps the whole previous subgoal when the reply cannot be parsed. The default subgoal has all weights at 1.0, a maximum wait of 120 s and a validity of 300 s.

This interface has three properties that the design relies on. It is narrow, so it can be sent over a poor link, including a short message. It is bounded, so that a wrong or adversarial value cannot move the cost function outside a fixed region. And it is not a phase command, so even a total failure of the slow loop cannot by itself switch a signal. The one exception is an emergency-vehicle override, which is described but not built and would still pass through the shield.

## 3.3 The safety shield and the audit

The shield is a rule layer between the planner and the signal controller. Nothing learned can bypass it, and every controller in the evaluation, including the baselines, is routed through it. It enforces a minimum green of {{shield_config.min_green::0}} s and a maximum green of {{shield_config.max_green::0}} s, inserts an amber of 3 s and an all-red clearance of 2 s at every phase change, gives every pedestrian phase at least the crossing time ({{shield_config.crossing_times.xE::0}} s for the east and west crossings and {{shield_config.crossing_times.xS::0}} s for the south crossing, from the crossing length at 1.2 m/s plus a 4 s margin), and serves next any approach that has waited longer than {{shield_config.starvation_s::0}} s. The design also includes a spillback rule for corridors, which withholds green from a movement whose downstream approach is full and is not exercised at a single junction. Each correction is returned with the rule that caused it and is logged.

The pedestrian minimum is applied to every phase that gives green to a crosswalk, not only when waiting pedestrians are observed, because perception misses some pedestrians. This is stricter than a rule conditioned on detection and is recorded as a deviation from the specification. An independent audit, which reads ground-truth signal and pedestrian state and not the perception output, checks the signal states of every run against the same rules, and it was tested to flag unshielded short greens. The shield is not a proof of road safety, and its parameters have not been checked against Nigerian signal-timing guidance.

## 3.4 The explainability log

Every decision is written as one JSON line containing the simulated time, controller, scenario and seed, the trigger (scheduled, novelty or none), the connectivity state, the VLAM backend, the reasoning text, the subgoal, the CEM plan, any shield correction with its reason, the applied phase and green, and the world model's one-step error. The log is intended to let a regulator ask why an approach was favoured at a given time and be shown the subgoal, its justification and the triggering conditions. A log records what the model wrote and does not prove that the text caused the weights, so the reasoning is treated as an audit artefact whose reliability must itself be tested, as the smoke test below shows.

## 3.5 Capability-aware coordinator and degradation tiers

The coordinator is rule-based and not learned. It routes only slow-loop work. In the full design it would send a routine scene to a small edge model, an unusual scene to a large model in the cloud when a link is available, and would treat a rise in the world model's prediction error as a sign that heavier reasoning is needed. An emergency-vehicle alert triggers a direct override.

The prototype implements a subset. It calls the slow loop every 300 simulated seconds and early when a novelty trigger fires. The trigger compares the mean one-step world-model queue error over the last 10 decisions with twice the median of the 30 decisions before them, with at least 120 s between triggers. When the scenario marks the slow loop as unreachable, the coordinator holds the last subgoal, and after more than 600 s offline it switches to a cached time-of-day schedule that was written by hand and not tuned. Each switch is logged. The routing of work between an edge and a cloud model is specified and not implemented.

Table: Degradation tiers. The prototype implements the hold-last and cached-schedule behaviours and the scenario-defined outage window. The remaining rows are specified, not exercised
| Condition | Behaviour |
|---|---|
| Full connectivity | The slow loop runs a large VLAM in the cloud |
| Weak connectivity | A small VLM on the edge, or a cached time-of-day subgoal schedule |
| No connectivity | The fast loop continues on the last subgoal |
| System fault | A fixed-time signal plan |

## 3.6 Tiered communication

Five channels are planned. Fibre or fourth-generation mobile data carries everything except raw video, short messages over GSM carry alerts and subgoals when data is down, store-and-forward carries logs and training data later, a junction-to-junction mesh over Wi-Fi or LoRa is the main offline path because neighbouring junctions are close, and optional satellite links carry critical alerts only. All incoming messages are intended to be cryptographically signed, and messages may change priorities but can never bypass the shield. This tiering is part of the specified design and is not simulated in the prototype, where connectivity is a binary window in the outage scenario.

## 3.7 The eight-layer deployment framework

The layer structure used to organise deployment comes from the second author, Dr. Fasina. During the class session of 27 July 2026, they typed the prompt "Design a cloud-based 8-layer framework for AfriCoT-VLA" into DeepSeek on a shared screen, and the layers below are credited to them. The layers are: the sensor layer (cameras and actuators for traffic lights), the network connection (compressed video from cameras over the internet to the cloud), the data store, the model layer (chain-of-thought reasoning, latent world models and the VLAM), the explainability layer, the service layer, the AI agent layer, and an autonomous agentic layer.

There is a tension between this framework and the architecture above. The framework is cloud-based and sends compressed video to the cloud, whereas the architecture keeps raw video on site and runs the fast loop locally. The proposed reconciliation keeps all eight layers, treats the cloud as the full-connectivity tier, and has the network layer carry compressed keyframes for the slow loop and not continuous video. The remaining refinements are the first author's proposals and have not yet been confirmed by the second author. The data store would hold a hot window plus cold history. The model layer would implement the two-timescale design. The service layer would offer decision, query, override and health interfaces. The agent layer would coordinate a corridor, and the autonomous layer would offer plan proposals, what-if simulations and human sign-off. In this reading, any layer above the model layer can fail and the junction falls back to fixed-time control, the network layer is the real bottleneck, and the explainability layer acts as a deployment gate. The framework is not implemented in the prototype beyond the sensing, model and logging functions that the simulation exercises.

# Experimental Setup

## 4.1 The simulated junction

The prototype uses the SUMO traffic simulator (Alvarez Lopez et al., 2018) with traffic driving on the right, as in Nigeria. The network is one signalised T-junction with an east and west main road of two lanes each way, a south side road of one lane each way, approaches of 300 m, speed limits of 50 km/h on the main road and 40 km/h on the side road, and pedestrian crossings with sidewalks on all three arms. There are three signal phases. Phase A serves the main road through and right-turn movements together with the permissive east-to-south left turn, with pedestrians crossing the south arm. Phase B is a protected east-to-south left turn with the east-to-west through movement. Phase C serves the side road, with pedestrians crossing the east and west arms. Every change passes through an amber of 3 s and an all-red of 2 s, and a test confirms that no conflicting movements are ever green together.

Four vehicle types are simulated: cars, minibuses (danfos, which count as transit), tricycles (kekes) and motorcycles (okadas). The sublane model lets motorcycles filter between lanes. In the tuning runs the lateral position of okadas had a standard deviation of {{s1_okada_lateral_sd_range_m.0::2}} to {{s1_okada_lateral_sd_range_m.1::2}} m, against {{s1_car_lateral_sd_range_m.0::2}} to {{s1_car_lateral_sd_range_m.1::2}} m for cars, which is the evidence used here that lane-splitting is represented.

## 4.2 Scenarios and demand

Each run simulates one hour of measurement after a warm-up of {{warmup_s::0}} s that is excluded from every metric. Four scenarios are used and are given in the table below. The normal scenario has 700 vehicles per hour per main-road direction and 300 vehicles per hour on the side road. The market scenario raises pedestrian demand and shifts the vehicle mix towards tricycles and motorcycles. The incident scenario closes the kerb lane of the east approach to all demand vehicles from 1200 s to 2100 s of the simulation clock. The outage scenario has market demand and makes the slow loop unreachable from 1200 s to 2400 s.

Table: Scenario definitions. Flows are vehicles per hour per source, the mix is the share of cars, minibuses, tricycles and motorcycles, and pedestrian demand is in pedestrians per hour in total
[[scenario_table]]

Market side-road demand is {{scenario_config.market.flows.S::0}} vehicles per hour, not the 550 first specified, and this is a deviation that matters for interpretation. At 550 vehicles per hour the south arm gridlocked under fixed-time control on the tuning seeds, with a mean insertion delay of {{demand_tuning.candidates.0.mean_south_depart_delay_s::0}} s and up to {{demand_tuning.candidates.0.max_south_not_inserted::0}} vehicles never inserted. Candidate values from 550 down to 200 were tried on tuning seeds only, and only 200 passed the criterion of at most five uninserted south vehicles on every seed and a mean south insertion delay below 60 s (at 225 vehicles per hour, up to {{demand_tuning.candidates.4.max_south_not_inserted::0}} remained uninserted). The side road therefore carries less traffic in the market scenario than in the normal one. The incident scenario raises waiting only modestly under fixed-time control because one lane of the east approach still carries flow. Seeds 100 to 104 were used for tuning, 200 to 219 for world-model data, and seeds 0 to 4 are the only seeds used for reported evaluation.

## 4.3 Perception and metrics

Perception in the simulation is derived from the simulator and then degraded: Gaussian noise on counts with a standard deviation of {{perception_config.rel_sd::pct1}} percent of the value (minimum {{perception_config.min_sd::1}}), and each vehicle missed with a probability of {{perception_config.miss_p::pct1}} percent. Controllers see only this noisy output. Per-movement queues are also derived from each halting vehicle's route, with the same noise, because a controller such as max-pressure needs to tell the through and left-turn phases apart. No detector is trained, so the paper says nothing about detection accuracy on real footage.

The metrics are average waiting time (AWT), average travel time (ATT), average queue length (AQL, the mean number of halting vehicles over the incoming lanes), throughput (vehicles arrived) and average pedestrian waiting time. AWT and ATT include insertion delay and cover every vehicle scheduled to depart after the warm-up. Vehicles still in the network or never inserted at the end of the run are right-censored at 3900 s, which makes AWT a lower bound for those vehicles under the same rule for every controller. The rule was introduced after a review found that excluding insertion delay rewarded a controller that starved the side road. Jam teleports are counted as a check on gridlock, and AWT is the primary metric.

## 4.4 Controllers

Three baselines are built. Fixed-time uses greens of {{fixed_time_params.GREENS.A::0}} s, {{fixed_time_params.GREENS.B::0}} s and {{fixed_time_params.GREENS.C::0}} s for phases A, B and C. The camera-count-plus-timer controller (count-timer) starts each green at 10 s and extends it in 5 s steps while the served queue is at least 3, up to 60 s, cycling A, B, C. Max-pressure picks the phase whose served movements have the largest total queue, with a fixed green of {{controller_params.max_pressure.GREEN::0}} s, and treats the downstream as empty because the junction is isolated. This single-junction form lacks the downstream term that gives max-pressure its network properties.

Two ablations of the fast loop are built. The first, `africot_noslow`, runs the world model and CEM planner with the default subgoal at all times, which is the ablation without the slow loop. The second, `africot_nowm`, replaces the world model by a one-step queue-discharge heuristic that uses smoothed arrival rates and fixed discharge rates, which are untuned engineering estimates. A third variant, `africot_full`, adds the slow loop. No planner parameter was tuned on any seed.

The world model was trained on windows from fixed-time, count-timer, max-pressure and random-timing controllers in the normal, market and incident scenarios over 25 data seeds, with {{world_model.n_windows.train::0}} training, {{world_model.n_windows.validation::0}} validation and {{world_model.n_windows.test::0}} test windows split by seed. The outage scenario was skipped because, for controllers without a slow loop, it would duplicate market episodes. Training used the Adam optimiser with early stopping on the validation split, and the test seeds are 215 to 219.

Table: Specified compared with built. A component is built if it exists in the prototype and has been run, and wiring-tested if it was run only with a rule-based stand-in for the model
| Component | Status |
|---|---|
| Edge perception with noise | Built, simulated from SUMO state, no detector |
| Latent world model and CEM planner | Built and evaluated |
| Safety shield and independent audit | Built and evaluated |
| Explainability log | Built, one line per decision |
| Subgoal validator | Built and tested |
| Coordinator (schedule, novelty, hold-last, cached schedule) | Built, wiring-tested |
| VLAM slow loop (africot_full) | Implemented, wiring-tested with a mock backend, one 3B smoke test, not yet evaluated |
| Capability-aware routing between edge and cloud models | Specified, not built |
| Emergency-vehicle override | Specified, not built |
| Tiered communication and signed messages | Specified, not built |
| Eight-layer service, agent and autonomous layers | Specified, not built |
| Deep reinforcement-learning baseline | Not built |
| LLMLight baseline | Not built |
| Multi-junction corridor and neighbour exchange | Specified, not built |

## 4.5 Reproducibility and statistics

Every run writes a result file with its metrics, configuration, backend and code revision, and the reported tables are regenerated from these files by script. The test suite of 68 tests passed in a clean reproduction, and re-running the five built controllers on one scenario and seed gave metrics identical to the committed files. Means and standard deviations are over seeds 0 to 4. Because five seeds give little power, a per-seed paired comparison is added for selected pairs, reporting the mean difference, the number of seeds in which the first controller is lower, a paired t-test and an exact Wilcoxon signed-rank test. With five pairs the smallest possible exact two-sided Wilcoxon p-value is 0.0625, and no correction for multiple comparisons is applied, so these tests are exploratory and a gap that lies within one standard deviation is not described as a difference.

# Results

## 5.1 The world model against persistence

The world model was checked on seeds that were never used for training or validation. The figure below compares its error with that of the persistence guess that queues stay unchanged, which is the natural reference for a planner that needs to predict how queues will change.

![[figure:world_model_vs_persistence.png|Held-out mean absolute error of the latent world model and of the persistence guess for one-, two- and three-step predictions]]

At one step ahead the mean absolute queue error was {{world_model.test.1step.queue_mae_model::2}} vehicles for the model and {{world_model.test.1step.queue_mae_persistence::2}} for persistence, an improvement of {{world_model.test.1step.queue_improvement_vs_persistence::pct1}} percent, and the advantage remained at three steps ({{world_model.test.3step.queue_mae_model::2}} against {{world_model.test.3step.queue_mae_persistence::2}}, {{world_model.test.3step.queue_improvement_vs_persistence::pct1}} percent). The specified check, a one-step improvement of at least 10 percent, was passed by a wide margin. Errors are measured against noisy observations, as the deployed controller would see, so they are not errors against the true queue. Persistence is a weak reference when the signal changes between decisions, so the model's value for planning is tested only through the controller results below.

Table: World-model errors on held-out data, with the persistence guess for comparison
[[wm_table]]

Inside the controller runs, the world model's online one-step queue error for `africot_noslow` averaged {{wm_online_1step_queue_mae_mean_noslow_by_scenario.normal::2}} vehicles in the normal scenario, {{wm_online_1step_queue_mae_mean_noslow_by_scenario.market::2}} in market and {{wm_online_1step_queue_mae_mean_noslow_by_scenario.incident::2}} in incident, which is higher than on the held-out set. One plausible reason is that the planner visits states that differ from those of the data-collecting controllers, which is also why the novelty trigger is based on this error.

## 5.2 Controller comparison

The next table gives the mean and standard deviation of AWT over the five evaluation seeds for the five controllers in four scenarios, and the figure below shows the same data.

Table: Average waiting time (s), mean and standard deviation over seeds 0 to 4
[[results_table:awt]]

![[figure:awt_by_scenario.png|Average waiting time by scenario and controller, mean over seeds 0 to 4 with standard deviation as error bars]]

On normal demand, max-pressure had the lowest mean AWT ({{summary.normal|max_pressure.awt_mean::1}} s), `africot_noslow` was close behind ({{summary.normal|africot_noslow.awt_mean::1}} s), and fixed-time ({{summary.normal|fixed_time.awt_mean::1}} s), count-timer ({{summary.normal|count_timer.awt_mean::1}} s) and `africot_nowm` ({{summary.normal|africot_nowm.awt_mean::1}} s) were well behind. In the paired by-seed comparison, `africot_noslow` was higher than max-pressure by {{paired_tests.0.mean_diff_a_minus_b::1}} s on average, and was lower in only {{paired_tests.0.a_lower_in_seeds::0}} of {{paired_tests.0.n::0}} seeds, so max-pressure was lower in every seed. The planner with a default subgoal was lower than fixed-time in every seed ({{paired_tests.1.a_lower_in_seeds::0}} of {{paired_tests.1.n::0}}, mean difference {{paired_tests.1.mean_diff_a_minus_b::1}} s).

On market demand, max-pressure had a mean AWT of {{summary.market|max_pressure.awt_mean::1}} s with a standard deviation of {{summary.market|max_pressure.awt_sd::1}} s and `africot_noslow` had {{summary.market|africot_noslow.awt_mean::1}} s with a standard deviation of {{summary.market|africot_noslow.awt_sd::1}} s. The lead of `africot_noslow` in the means is {{paired_tests.5.mean_diff_a_minus_b::1}} s, well inside one standard deviation, and it was lower than max-pressure in only {{paired_tests.5.a_lower_in_seeds::0}} of {{paired_tests.5.n::0}} seeds, so the two are described as comparable. Both were lower than fixed-time ({{summary.market|fixed_time.awt_mean::1}} s) in every seed.

On incident demand, the mean AWT was {{summary.incident|max_pressure.awt_mean::1}} s for max-pressure and {{summary.incident|africot_noslow.awt_mean::1}} s for `africot_noslow`. The planner with a default subgoal was higher in the means, was lower than max-pressure in only {{paired_tests.10.a_lower_in_seeds::0}} of {{paired_tests.10.n::0}} seeds, and the mean difference of {{paired_tests.10.mean_diff_a_minus_b::1}} s is smaller than the spread between seeds ({{paired_tests.10.sd_diff::1}} s), so the data do not separate the two with confidence, but they offer no support for an advantage of the planner. Both were lower than fixed-time ({{summary.incident|fixed_time.awt_mean::1}} s) in every seed.

The outage rows equal the market rows for every controller without a slow loop, because the outage window changes nothing when no slow loop exists, so outage is not an independent scenario for them and is not tested separately.

Table: All reported metrics per scenario and controller (mean and standard deviation over seeds 0 to 4)
[[results_table:full]]

Throughput barely separates the controllers: in the normal scenario it ranged from {{summary.normal|fixed_time.throughput_mean::0}} to {{summary.normal|max_pressure.throughput_mean::0}} vehicles per run across controllers, with standard deviations of up to {{summary.normal|fixed_time.throughput_sd::0}}, so AWT, ATT and AQL carry the information. The average pedestrian waiting time was lower for two of the adaptive controllers than for fixed-time on normal demand ({{summary.normal|africot_noslow.ped_wait_mean::1}} s for `africot_noslow` and {{summary.normal|max_pressure.ped_wait_mean::1}} s for max-pressure, against {{summary.normal|fixed_time.ped_wait_mean::1}} s), although the shield's pedestrian minimum applies to every controller.

Table: Exploratory paired by-seed comparisons of AWT over seeds 0 to 4 (n = 5), without correction for multiple comparisons
[[paired_table]]

## 5.3 Ablations and negative results

Removing the world model did not produce a competitive controller. The `africot_nowm` variant was worse than fixed-time in the means on all three scenarios (normal by {{paired_tests.3.mean_diff_a_minus_b::1}} s, market by {{paired_tests.8.mean_diff_a_minus_b::1}} s and incident by {{paired_tests.13.mean_diff_a_minus_b::1}} s), although none of these differences was consistent across seeds (it was lower than fixed-time in {{paired_tests.3.a_lower_in_seeds::0}}, {{paired_tests.8.a_lower_in_seeds::0}} and {{paired_tests.13.a_lower_in_seeds::0}} of {{paired_tests.3.n::0}} seeds). The variant with the world model was lower than the one without it in every seed in every scenario tested (mean difference {{paired_tests.4.mean_diff_a_minus_b::1}} s on normal). The discharge rates of the heuristic are untuned guesses, so this is an ablation of one specific heuristic and not a bound on what a world-model-free planner can reach, and the heuristic variant also produced the only jam teleport among the planner runs ({{jam_teleports_by_cell.africot_nowm|normal::0}}, on normal demand) as well as vehicles that were never inserted in some runs.

The planner with a default subgoal did not beat the strongest classical baseline. No deeper investigation was carried out. Candidate explanations that are untested include the cost being summed per plan step and not weighted by the duration of each step, the short horizon, the approximation of the minibus term, the noisy observations, and the use of an untuned default subgoal. All comparisons are between shielded controllers.

Further observations temper the tables. Count-timer was not better than fixed-time on normal or market demand in the means, and the gap in each case lies within one standard deviation. An earlier version of the metrics, which excluded insertion delay, ranked the adaptive baselines differently from fixed-time on market demand, and the ranking above is the one that remains after the correction described in the setup. Max-pressure shows a large spread on market demand ({{summary.market|max_pressure.awt_sd::1}} s), which makes its market result less certain than its normal result. Max-pressure had {{jam_teleports_by_cell.max_pressure|market::0}} jam teleport on market demand, with additional non-jam teleports in several cells.

## 5.4 Shield audit

All {{n_eval_runs::0}} evaluation runs passed through the shield, and the independent audit found {{safety_violations_total::0}} safety violations. The shield was nonetheless active. Across the runs, it made {{shield_total_by_rule.ped_crossing::0}} pedestrian-crossing corrections, {{shield_total_by_rule.max_green::0}} maximum-green corrections and {{shield_total_by_rule.starvation::0}} starvation corrections.

![[figure:shield_corrections_by_rule.png|Shield corrections by controller and rule, summed over all evaluation runs]]

Table: Shield corrections by controller and rule, summed over the evaluation runs
[[shield_table]]

Most corrections were pedestrian-crossing minima, which lift side-road greens that were shorter than the crossing time, and which were issued to max-pressure ({{shield_corrections_by_controller_rule.max_pressure.ped_crossing::0}}), `africot_noslow` ({{shield_corrections_by_controller_rule.africot_noslow.ped_crossing::0}}) and count-timer ({{shield_corrections_by_controller_rule.count_timer.ped_crossing::0}}). The `africot_nowm` variant received {{shield_corrections_by_controller_rule.africot_nowm.max_green::0}} maximum-green corrections, more than any other, and max-pressure received {{shield_corrections_by_controller_rule.max_pressure.max_green::0}} and {{shield_corrections_by_controller_rule.max_pressure.starvation::0}} starvation corrections. Fixed-time received none. The counts show that the planners propose timings that the rules reject and that the shield changes what is applied. They do not show that the rules themselves are the right ones.

## 5.5 Slow-loop wiring and the 3B smoke test

The integrated controller was run with a mock backend on all four scenarios and five seeds, giving {{mock_wiring.n_runs::0}} runs. The mock backend is deterministic and rule-based, it is not a vision-language model, and its outputs are not VLAM results. The purpose was to check the wiring. All runs completed, with {{mock_wiring.safety_violations_total::0}} safety violations and {{mock_wiring.parse_failures_total::0}} parse failures, and with {{mock_wiring.slow_loop_calls_range.0::0}} to {{mock_wiring.slow_loop_calls_range.1::0}} slow-loop calls per run.

![[figure:outage_degradation_timeline.png|Connectivity states of one integration run in the outage scenario with the mock backend (seed 0). The timeline shows scripted behaviour and is not a VLAM result]]

In the outage scenario, the log shows the intended sequence on every seed. The slow loop was online until {{mock_wiring.outage_connectivity_switches_seed0.1.0::0}} s, the last subgoal was held, the cached schedule was used from about {{mock_wiring.outage_connectivity_switches_seed0.2.0::0}} s, and connectivity returned at about {{mock_wiring.outage_connectivity_switches_seed0.3.0::0}} s. The novelty trigger fired inside the incident window on all five seeds, but it is not specific to incidents. It also fired in the normal scenario on seeds 3 and 4, in the market scenario on seeds 1, 3 and 4, and in the outage scenario on seed 4. The trigger therefore indicates that the world model's error rises at times, and not that an incident has occurred.

A single call to Qwen2.5-VL-3B (Bai et al., 2025) was made on a rendered market-day snapshot on a four-core CPU with greedy decoding. The reply parsed and validated, with a pedestrian weight of {{vlam_smoke_test.subgoal.pedestrian_weight::1}} and all other values at their defaults, and the call took {{vlam_smoke_test.latency_s::1}} s on an idle machine. The context gave about {{vlam_smoke_context.ped_waiting.xE::1}} waiting pedestrians at the east crossing and about {{vlam_smoke_context.ped_waiting.xW::1}} at the west crossing. The model's reasoning attributed the waiting pedestrians to the west arm, so its chain of thought is unreliable at this size. This single call shows that the pipeline from image to validated subgoal runs, and it is no evidence of sound reasoning. It also shows that a logged justification can be wrong while the resulting subgoal is plausible. A re-run on a separate download gave identical text, consistent with deterministic decoding.

<!--COLAB:results_full-->
No evaluation of the full controller with a vision-language model is reported in this version. The results of the planned GPU grid with the 7B model are to be added here, in the same scenarios and seeds as the table above.
<!--/COLAB-->

# Discussion

The most secure findings concern the parts that were evaluated. The small world model predicts queue changes at the next few decisions much better than a persistence guess, the planner built on it is lower than fixed-time control in every seed in the normal, market and incident scenarios and lower than the same planner with a crude heuristic in place of the world model, and the shield produced no violations while correcting thousands of proposals. Taken together, these results support the narrower claim that a learned world model can be used inside a shielded planner at a single junction without the safety record being damaged by the learned parts. They do not support the stronger claim that this planner is the best available controller, because max-pressure is lower in the means on normal and incident demand and comparable on market demand.

That result does not dismiss the architecture, but it repositions the question. If the fast loop alone is not ahead of a simple actuated rule at one isolated junction, the case for the architecture cannot rest on average delay in ordinary conditions. It would have to rest on situations in which a rule that sees only queues is blind, such as an event that changes priorities in a way queue counts do not show, or the need for an audit trail. The prototype's scenarios contain such situations only weakly, and the market scenario was made less demanding on the side road to avoid gridlock, so they are a limited test of what the slow loop is meant to address.

<!--COLAB:discussion_full-->
The working hypothesis for the slow loop is that context a camera and a calendar supply, such as a market day or a blocked lane, could be translated into subgoal weights that the fast loop alone cannot infer, and that the written justification could make such changes reviewable. This hypothesis has not been tested. It would be supported only if the full controller shows lower waiting than the planner with a default subgoal in paired by-seed comparisons, with the log showing sensible reasoning, and it would be weakened if the reasoning of the larger model were also unreliable.
<!--/COLAB-->

The smoke test carries a methodological lesson whatever the later experiment finds. The 3B model's reasoning was fluent and wrong about where pedestrians were waiting, and a log that stores such text would mislead an auditor who took it at face value. The design therefore asks for two further safeguards that are not yet built: comparing the claims in the reasoning with the perception output that was available to the model, and flagging decisions for manual review when the two disagree. The shield and the subgoal bounds limit the harm that a wrong rationale can cause, but they do not make the rationale correct.

The degradation tiers work as wired, but the prototype does not show how much control quality is lost when they are used, because the controller they would protect has not been evaluated. The ablations under connection loss, with and without neighbour information, and with fixed and capability-aware routing remain to be run.

Finally, the cloud orientation of the eight-layer framework sits uneasily with sites where connectivity is the main constraint. Treating the cloud as the full-connectivity tier preserves the layer structure, and it is a proposal for confirmation by the second author and not a settled design.

# Limitations

The evidence has several limits that readers should keep in mind.

- A single simulated junction is used. The corridor and neighbour exchange that the design describes for close junctions are not built, so claims about coordination and green waves are outside the evidence.
- The evaluation is in simulation with perception derived from simulator state plus noise. No detector was trained or tested on real footage, and the renderer used as the slow-loop keyframe is a simulator view and not a camera image.
- Five evaluation seeds give low power. The paired tests are exploratory and uncorrected, and many cells have a large standard deviation.
- The full system has not been evaluated. The only real-model evidence is one call of a 3B model, and the integration runs used a rule-based mock backend. The slow loop is treated as instantaneous in simulated time, although the measured call time of the 3B model on an idle four-core CPU was {{vlam_smoke_test.latency_s::0}} s and a larger model on the same hardware would take longer. The validity period in the subgoal is validated but not used by the coordinator.
- The deep reinforcement-learning and LLMLight baselines are not built, so the paper makes no comparison with learned traffic controllers or language-model controllers. The max-pressure baseline is its isolated single-junction form.
- Market side-road demand was lowered from 550 to 200 vehicles per hour to avoid gridlock, which changes the character of that scenario. The incident scenario is mild under fixed-time control, and the outage scenario duplicates market for every controller without a slow loop.
- The novelty trigger fires without an incident, and the cached schedule, the heuristic discharge rates and the minibus cost term are untuned or approximate.
- The communication tiers, capability-aware routing, emergency override and the upper framework layers are specified and not built. The explainability log was not assessed with regulators.
- The hardware roadmap (hardware-in-the-loop testing, shadow mode, supervised pilot) is described and not carried out.

# Conclusion

This paper proposed AfriCoT-VLA, a two-timescale traffic signal design for infrastructure-constrained cities, in which a chain-of-thought vision-language slow loop sets a bounded subgoal and a justification, an on-site latent world model and CEM planner choose timings against it, a rule-based shield limits what any learned component can do, and a capability-aware coordinator and tiered communication govern degradation. Relative to the authors' earlier position paper, the contribution is the reasoning slow loop with its justification log, the shield and audit, the coordinator and degradation tiers, and simulation evidence that includes negative results.

In one simulated junction and five seeds, the world model predicted short-horizon queues much better than persistence and the shield produced no violations, but the planner with a default subgoal was not better than max-pressure control, and removing the world model gave a controller no better than fixed-time control. The evidence supports the use of the fast loop inside a shield as a basis for further work, and it does not support a claim that the system improves on simple actuated control.

<!--COLAB:conclusion_full-->
The full controller, africot_full, is implemented and wiring-tested with a mock backend and has had one smoke test with a 3B model, but it has not been evaluated, so no conclusion about the benefit of the slow loop is drawn. Its evaluation with a 7B model on a GPU, in the same scenarios and seeds, is the next step.
<!--/COLAB-->

Further work comprises the missing deep reinforcement-learning and LLMLight baselines, a corridor of two to three junctions with neighbour information, tests of the reasoning against the perception it was given, and hardware-in-the-loop trials before any supervised pilot.
