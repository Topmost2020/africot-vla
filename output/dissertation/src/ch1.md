# Chapter 1: Introduction

## 1.1 Background

Signal timing is among the few levers that a city authority can adjust without building new road space. Much of the research on adaptive signal control, surveyed by Wei et al. (2019c), has been developed under assumptions of a comparatively homogeneous vehicle fleet, lane-disciplined behaviour, dependable electricity and continuous network access. Many cities in Sub-Saharan Africa (SSA) differ on each of these points, so a controller designed for the former cannot be assumed to suit the latter.

### 1.1.1 Urban traffic and informal transit in Sub-Saharan Africa

Road traffic in SSA cities mixes private cars with a large informal public transport sector. In Lagos, minibuses known as danfo carry a large share of passengers, tricycles known as keke fill gaps in the road network, and motorcycle taxis known as okada weave between lanes and through queues. Comparable services operate elsewhere, including matatu minibuses in Kenya and boda-boda motorcycle taxis in East Africa. These descriptions come from the author's familiarity with the setting, not a cited survey, and no vehicle-share statistic is asserted. What matters for signal control is the behavioural consequence: vehicles of very different length, width and speed share the same approach, motorcycles do not respect lane boundaries, and public transport vehicles stop at irregular points. Queue length in vehicles is therefore a poor proxy for queue demand.

Pedestrians add a second difficulty, since a controller that ignores their waiting can reduce vehicle delay at their expense. Demand is also time-dependent: market days, events and incidents change arrivals in ways a fixed plan does not anticipate.

### 1.1.2 Connectivity, power and compute limits

The second group of constraints concerns the infrastructure beneath an intelligent controller. In 2023, 565 million people in SSA lacked access to electricity, which was 85 per cent of the people without access worldwide (International Energy Agency et al., 2025). Roughly 53 per cent of the SSA population had access to electricity, against roughly 92 per cent worldwide (World Bank, 2026). Mobile internet penetration in the region stood at 27 per cent at the end of 2023 (GSMA, 2024a). These regional figures do not describe any one junction, and cities are better served than the averages, but a control system cannot assume continuous power or a reliable wide-area link at every site. Data-centre capacity on the continent is also limited (Africa Data Centres Association, 2026), so where large models are hosted is itself a design question. These limits argue for a cloud-hosted reasoning tier paired with an on-site tier that keeps working when the link fails.

### 1.1.3 The Lagos context and the opportunity

Lagos is the setting that motivates this work. Reports describe a phased deployment of AI traffic systems on selected corridors by the Lagos Metropolitan Area Transport Authority (ITEdgeNews, 2026), the selection of a vendor (Olomu, 2025) and public discussion of whether such systems can ease congestion (Adeyemo, 2026). Nairobi shows a parallel pattern (Mumbi, 2026; Nairobi Law Monthly, 2026). These sources indicate that investment is under way, not that any particular design performs well.

Three lines of research are relevant. Latent world models learn a compact predictive model of how a system evolves and allow a controller to plan by imagining outcomes before acting (Hafner et al., 2019; Hafner et al., 2025; Hansen et al., 2024). Vision-language-action models (VLAMs) extend large pretrained vision-language models to produce actions for an embodied agent (Zitkovich et al., 2023; Kim et al., 2024), and chain-of-thought (CoT) reasoning in such models has been explored as a way of making the path from observation to action explicit (Zawalski et al., 2024; Yang et al., 2025). In signal control, reinforcement learning is well established (Wei et al., 2019a; Chu et al., 2020) and language-model agents have begun to appear (Lai et al., 2023). The authors' earlier position paper proposed that a slow loop generating compact subgoals, coupled to a fast on-device latent world model planner, treats SSA infrastructure gaps as design inputs (Ariyo & Fasina, 2026). This dissertation applies that architecture to signal control, intends it to be cloud-hosted, and adds the elements that a regulated public safety function requires.

## 1.2 Problem statement

Adaptive controllers designed for well-provisioned cities are not guaranteed to suit SSA junctions. Fixed-time plans cannot respond to market days or incidents, controllers that rely on continuous cloud access stop adapting when the link fails, and large reasoning models cannot be run at every junction. Learned controllers are usually opaque, which conflicts with the need for decisions that the Lagos State Traffic Management Authority (LASTMA) or the Ministry of Transportation can audit. Finally, much of the learned-control literature is evaluated on homogeneous traffic that excludes lane-splitting motorcycles and pedestrians.

The problem addressed here is therefore the absence of a cloud-based signal control design that (a) keeps basic, safe, locally computed control running when connectivity or power is degraded, (b) uses context such as time, events and incidents through reasoning hosted in the cloud when it is reachable, (c) records every decision in a form that can be audited, and (d) is evaluated under traffic that includes informal transit and pedestrians. Whether the design improves control over simpler alternatives is empirical, and part of that question remains open here.

## 1.3 Aim

The aim is to design, implement and evaluate in simulation a prototype of AfriCoT-VLA, a cloud-based traffic signal control system for SSA cities that pairs cloud-hosted chain-of-thought vision-language-action reasoning with an on-site latent world model through a compact subgoal, and to report honestly what the evidence shows about each component.

## 1.4 Objectives

The prototype is a single T-junction in the SUMO simulator (Alvarez Lopez et al., 2018), driven through its TraCI interface.

1. To build a simulated Lagos-style T-junction with mixed vehicle classes (car, danfo, keke, okada), pedestrian crossings and four scenarios (normal, market, incident and outage), each run for 3600 s after a warm-up of 300 s, with evaluation on seeds 0 to 4.
2. To implement a noisy perception layer and metrics for average travel time, waiting time, queue length, throughput and pedestrian waiting.
3. To implement fixed-time, camera-count-plus-timer and max-pressure (Varaiya, 2013) baselines and run them on every scenario and seed.
4. To implement a rule-based safety shield between the planner and the signals, and test that it corrects unsafe proposals.
5. To train a latent world model of queue evolution and test whether it beats a persistence guess by at least 10 per cent in one-step queue error on held-out data.
6. To implement a Cross-Entropy Method (CEM) planner (de Boer et al., 2005) that uses the world model under a subgoal-defined cost, with ablations without the slow loop and without the world model.
7. To implement the slow loop, in which a VLAM with CoT reads a rendered snapshot and context and returns a validated subgoal, with a rule-based coordinator that schedules calls, detects novelty and handles connectivity loss by holding the last subgoal and then a cached schedule. The cloud link is represented in simulation by a scripted backend and outage windows.
8. To implement an explainability log of every decision, and test the full controller with a mock backend and once with a small open-weight VLAM (Bai et al., 2025).
9. To describe, without building them, the cloud-based eight-layer framework, the cloud deployment architecture, tiered communication and a path to field deployment.

## 1.5 Research questions

1. **RQ1.** Can a compact latent world model of junction queues, trained on logged transitions from simple controllers, predict the next decision window's queues better than the assumption that queues remain unchanged?
2. **RQ2.** How does a CEM planner that uses this world model compare with the fixed-time, count-plus-timer and max-pressure baselines across the normal, market and incident scenarios?
3. **RQ3.** How much of the planner's behaviour depends on the world model, and how much on the subgoal, as indicated by the two ablations?
4. **RQ4.** Does the safety shield hold, in the sense that no conflicting movements are ever green together and no rule violation is recorded across all evaluated runs, and which rules intervene most often?
5. **RQ5.** Does the slow-loop and coordinator machinery behave as specified, in that calls are scheduled, novelty triggers fire, outages lead to hold-last and then cached-schedule behaviour, and every decision is logged?
6. **RQ6.** Does the slow loop with CoT reasoning change control relative to the planner without it, and is a small open-weight VLAM's reasoning reliable enough to use?

RQ1 to RQ5 can be answered from the evidence here. RQ6 can be answered only in part: a single smoke test of a small model gives some evidence about the reliability of its reasoning, but the full controller, africot_full, is implemented and wiring-tested and has not been evaluated on the scenario grid. A faithful evaluation calls for a larger open-weight model on a GPU, which was not available.

<!--COLAB:intro_status-->
The hypothesis behind the slow loop is that a model which can read context unavailable to the planner, such as an incident on one approach or a market day, could shift the planner's cost weights in a useful direction. This is a design intention and not a finding. The evaluation of africot_full on the scenario grid is pending, and no statement about its effect on control is made in this dissertation until it is complete.
<!--/COLAB-->

## 1.6 Scope and delimitations

First, the system is intended to be cloud-hosted, but no cloud deployment has been built or tested. The prototype simulates the control logic and outage behaviour only, with a scripted backend and one CPU smoke test of a 3B model on a local machine. No latency, cost, availability, security or data-residency measurement exists.

Second, the evaluation covers one isolated T-junction; the multi-junction corridor, neighbour information, green waves and mesh relay remain proposals.

Third, the evidence is from simulation only. SUMO traffic and demand approximate Lagos traffic and were not calibrated against field counts, and perception is simulated by adding noise to ground truth, so no real detector is evaluated. No field trial was carried out.

Fourth, three of the five planned baselines were built. A deep reinforcement learning controller and LLMLight (Lai et al., 2023) were not, which limits any comparison with learned alternatives.

Fifth, africot_full is implemented and wiring-tested with a mock backend, and a small VLAM has been run once on a CPU. It is not evaluated, and mock runs are never reported as VLAM results.

Sixth, the market side-road demand was lowered from 550 to 200 vehicles per hour after the specified value produced gridlock under fixed-time control. The outage scenario differs from market only in the slow-loop connectivity window, so controllers without a slow loop yield identical rows for the two.

Seventh, the emergency override, the tiered communication channels, cryptographic message signing and the fixed-time fallback for a system fault are design only. With five seeds per cell, paired by-seed tests are exploratory, and no significance claim is made where a gap lies within one standard deviation.

Finally, the models are open-weight and none is trained from scratch. The world model is a small network in the style of DreamerV3 (Hafner et al., 2025) and TD-MPC2 (Hansen et al., 2024), not either of them.

## 1.7 Significance

The study is intended to be useful in four ways. For traffic authorities and researchers in the region, it offers an open, reproducible simulation testbed with informal transit, pedestrians, market and incident scenarios and an outage condition, with every controller decision logged for audit. For embodied AI design, it offers a worked example of coupling a cloud-hosted reasoning model to a fast on-site planner through a small subgoal vector, behind a shield that nothing learned can bypass. For the research community, it reports negative and null results as found. For the authors, it provides a base for the corridor extension, the missing baselines, the GPU evaluation and the measurement of a real cloud deployment.

The eight layers were set by the supervisor, Dr. Ebun P. Fasina, in the class session of 27 July 2026, when they typed into DeepSeek on a shared screen the prompt "Design a cloud-based 8-layer framework for AfriCoT-VLA". The framework is cloud-based, with compressed video sent to the cloud. The system proposed here is intended to follow it: the cloud is the primary tier for the data store, model, explainability, service, agent and autonomous layers, and the network layer carries compressed keyframes for the slow loop rather than continuous raw video, which never leaves the site. The fast loop and the safety shield stay on site as the resilience tier, so the junction keeps operating when the link drops. The methodology chapter develops this reconciliation. Its details and the refinements to individual layers are the author's proposals, not yet confirmed by the supervisor, and are not evaluated.

## 1.8 Structure of the dissertation

The dissertation has five chapters. The second chapter reviews the literature on traffic signal control, from fixed-time plans through max-pressure, reinforcement learning and language-model agents, then on world models, vision-language-action models and chain-of-thought reasoning, explainability and regulation, and regional infrastructure constraints, and identifies the gap addressed.

The third chapter presents the methodology and system design: the two-timescale architecture, the subgoal interface, the safety shield, the explainability log, the coordinator and degradation tiers, the tiered communication scheme, the eight-layer framework and the cloud deployment architecture. It also describes the simulation setup, scenarios, baselines, metrics and reproducibility measures, and contains a table separating what was specified from what was built.

The fourth chapter reports the implementation, the world model against persistence, the controller comparison, the shield audit, the wiring evidence for the slow loop, the smoke test, the negative results and the threats to validity. The fifth chapter summarises the findings, draws conclusions, makes recommendations and sets out future work, including cloud deployment and measurement, the corridor extension, the missing baselines and the staged deployment roadmap. References and appendices follow.
