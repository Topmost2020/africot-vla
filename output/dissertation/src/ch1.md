# Chapter 1: Introduction

## 1.1 Background

Signalised junctions are among the points at which urban road networks are most easily congested, and the timing of their signals is among the few levers that a city authority can adjust without building new road space. Much of the research on adaptive signal control, surveyed by Wei et al. (2019c), has been developed and tested under assumptions of a comparatively homogeneous vehicle fleet, lane-disciplined behaviour, dependable electricity and continuous network access. Many cities in Sub-Saharan Africa (SSA) differ from this setting on each of these points, and a controller designed for the former cannot be assumed to be suitable for the latter without examination.

### 1.1.1 Urban traffic and informal transit in Sub-Saharan Africa

Road traffic in SSA cities is a mixture of private cars and a large informal public transport sector. In Lagos, minibuses known as danfo carry a large share of passengers, tricycles known as keke fill gaps in the road network, and motorcycle taxis known as okada weave between lanes and through queues. Comparable services operate elsewhere in the region under other names, including matatu minibuses in Kenya and boda-boda motorcycle taxis in East Africa. These descriptions come from the author's own familiarity with the setting rather than from a cited survey, and no vehicle-share statistic is asserted here. What matters for signal control is the behavioural consequence: vehicles of very different length, width and speed share the same approach, motorcycles do not respect lane boundaries, and public transport vehicles stop at irregular points to load passengers. Queue length measured in vehicles is therefore a poor proxy for queue demand, and a controller that counts only cars will misjudge an approach that is full of motorcycles.

Pedestrians add a second source of difficulty. Many junctions have crossing demand that rises sharply around markets, schools and places of worship, and pedestrians in practice cross wherever the gap is largest. A controller that ignores pedestrian waiting time can reduce vehicle delay at the expense of people on foot, which is an outcome that regulators are unlikely to accept. Demand is also strongly time-dependent: market days, public events and incidents change the pattern of arrivals in ways that a signal plan fixed in advance does not anticipate.

### 1.1.2 Connectivity, power and compute limits

The second group of constraints concerns the infrastructure on which an intelligent controller would run. In 2023, 565 million people in SSA lacked access to electricity, which was 85 per cent of the people without access worldwide (International Energy Agency et al., 2025). Roughly 53 per cent of the SSA population had access to electricity, against roughly 92 per cent worldwide (World Bank, 2026). Mobile internet penetration in the region stood at 27 per cent at the end of 2023 (GSMA, 2024a). These regional indicators do not describe any one junction, and urban areas are better served than the regional averages suggest. They do indicate that a control system for the region cannot reasonably assume continuous power, a reliable wide-area link or access to data-centre-scale compute at every site. Data-centre capacity on the continent is also limited (Africa Data Centres Association, 2026), which argues against designs that depend on large remote models being reachable for every decision.

### 1.1.3 The Lagos context and the opportunity

Lagos is the setting that motivates this work. Reports describe a phased deployment of camera- and sensor-based AI traffic systems on selected corridors by the Lagos Metropolitan Area Transport Authority (ITEdgeNews, 2026), the selection of a vendor for an intelligent traffic system (Olomu, 2025) and public discussion of whether such systems can ease the city's congestion (Adeyemo, 2026). Nairobi shows a parallel pattern, with large camera-based programmes announced or tendered (Mumbi, 2026; Nairobi Law Monthly, 2026). The author's reading of these reports is limited to what the sources state: they indicate that investment is under way, not that any particular design performs well.

Three lines of research are relevant to what such investment could be built upon. Latent world models learn a compact predictive model of how a system evolves and allow a controller to plan by imagining outcomes before acting (Hafner et al., 2019; Hafner et al., 2025; Hansen et al., 2024). Vision-language-action models (VLAMs) extend large pretrained vision-language models to produce actions for an embodied agent (Zitkovich et al., 2023; Kim et al., 2024), and chain-of-thought (CoT) reasoning in such models has been explored as a way of making the path from observation to action explicit (Zawalski et al., 2024; Yang et al., 2025). In traffic signal control specifically, reinforcement learning methods are well established (Wei et al., 2019a; Chu et al., 2020), and language-model agents have begun to appear (Lai et al., 2023). The authors' earlier position paper proposed that a slow loop generating compact subgoals, coupled to a fast on-device latent world model planner, is a suitable way of treating SSA infrastructure gaps as design inputs rather than as afterthoughts (Ariyo & Fasina, 2026). The present dissertation applies that architecture to traffic signal control and adds the elements that a regulated public safety function requires.

## 1.2 Problem statement

Adaptive signal controllers designed for well-provisioned cities are not guaranteed to suit SSA junctions. Fixed-time plans cannot respond to market days or incidents. Controllers that rely on continuous cloud access stop adapting when the link fails, and large reasoning models cannot be run at every junction for every decision. Learned controllers are usually opaque, which conflicts with the need for decisions that a traffic authority such as the Lagos State Traffic Management Authority (LASTMA) or the Ministry of Transportation can inspect and audit. Finally, much of the learned-control literature is evaluated on homogeneous traffic that excludes motorcycles that split lanes and pedestrians who dominate some junctions.

The problem addressed here is therefore the absence of a signal control design that (a) keeps basic, safe, locally computed control running when connectivity or power is degraded, (b) can still use context such as time, events and incidents when reasoning capacity is reachable, (c) records every decision in a form that can be audited, and (d) is evaluated under traffic that includes informal transit and pedestrians. Whether the whole design improves control over simpler alternatives is an empirical question, and part of that question remains open in this dissertation for the reasons given in the scope below.

## 1.3 Aim

The aim of the study is to design, implement and evaluate in simulation a prototype of AfriCoT-VLA, a traffic signal control system for SSA cities that is designed to couple a chain-of-thought vision-language-action model with a latent world model through a compact subgoal, and to report honestly what the evidence shows about each component.

## 1.4 Objectives

The objectives are stated so that each can be checked against a built artefact or a recorded result. The prototype is a single T-junction in the SUMO simulator (Alvarez Lopez et al., 2018), driven through its TraCI interface.

1. To specify and build a simulated Lagos-style T-junction with mixed vehicle classes (car, danfo, keke, okada) and pedestrian crossings, and four scenarios (normal, market, incident and outage), each run for 3600 s after a warm-up of 300 s, with evaluation on seeds 0 to 4.
2. To implement a noisy perception layer and metric collection for average travel time, average waiting time, average queue length, throughput and pedestrian waiting time.
3. To implement three baseline controllers, namely fixed-time, camera-count-plus-timer and max-pressure (Varaiya, 2013), and to run them on every scenario and seed.
4. To implement a rule-based safety shield between the planner and the signals that enforces minimum and maximum green, amber and all-red clearance, pedestrian crossing time and a starvation guard, and to test that it corrects unsafe proposals.
5. To train a latent world model of queue evolution on logged transitions and to test whether it beats a persistence guess by at least 10 per cent in one-step queue error on held-out data.
6. To implement a Cross-Entropy Method (CEM) planner (de Boer et al., 2005) that uses the world model to choose signal timings under a subgoal-defined cost, with two ablations, one without the slow loop and one without the world model, and to compare them with the baselines.
7. To implement the slow loop, in which a VLAM with CoT reads a rendered junction snapshot and context and returns a validated subgoal, together with a rule-based coordinator that schedules slow-loop calls, detects novelty from world-model error and handles connectivity loss by holding the last subgoal and then switching to a cached time-of-day schedule.
8. To implement an explainability log that records, for every decision, the trigger, connectivity state, reasoning text, subgoal, plan, shield correction and applied phase, and to test the full controller end to end with a mock backend and once with a small open-weight VLAM (Bai et al., 2025).
9. To describe, as a design contribution, a deployment framework of eight layers, a tiered communication scheme and a path from simulation to field deployment, without building them.

## 1.5 Research questions

The questions are phrased so that the evidence produced by the prototype can address them, and the final question is flagged separately because its evidence does not yet exist.

1. **RQ1.** Can a compact latent world model of junction queues, trained on logged transitions from simple controllers, predict the next decision window's queues better than the assumption that queues remain unchanged?
2. **RQ2.** How does a CEM planner that uses this world model compare, on average waiting time, average travel time, average queue length, throughput and pedestrian waiting, with the fixed-time, count-plus-timer and max-pressure baselines across the normal, market and incident scenarios?
3. **RQ3.** How much of the planner's behaviour depends on the world model, and how much on the subgoal, as indicated by the two ablations?
4. **RQ4.** Does the safety shield hold, in the sense that no conflicting movements are ever green together and no rule violation is recorded across all evaluated runs, and which rules intervene most often?
5. **RQ5.** Does the slow-loop and coordinator machinery behave as specified, in the sense that calls are scheduled, novelty triggers fire, outage windows lead to hold-last and then cached-schedule behaviour, outputs are validated, and every decision is logged?
6. **RQ6.** Does the slow loop with CoT reasoning change control relative to the planner without it, and is a small open-weight VLAM's reasoning reliable enough to use?

RQ1 to RQ5 can be answered from the evidence in this dissertation. RQ6 can be answered only in part. A single smoke test of a small model on one snapshot gives some evidence about the reliability of its reasoning, but the full controller, referred to in the experiments as africot_full, is implemented and wiring-tested and has not yet been evaluated on the scenario grid. The reason is practical: a faithful evaluation calls for a larger open-weight model on a GPU, which was not available in the environment where the prototype was built. The remainder of RQ6 is therefore left open.

<!--COLAB:intro_status-->
The hypothesis behind the slow loop is that a model which can read context unavailable to the planner, such as an incident on one approach or a market day, could shift the planner's cost weights in a useful direction. This is a design intention and not a finding. The evaluation of africot_full on the scenario grid is pending, and no statement about its effect on control is made in this dissertation until it is complete.
<!--/COLAB-->

## 1.6 Scope and delimitations

The study is bounded in the following ways, each of which the reader should keep in mind when interpreting the results.

First, the evaluation is on a single isolated T-junction. The multi-junction corridor that motivates the design, in which neighbouring junctions are close together and exchange queue and plan data, is described but not built or tested. Neighbour information, green waves and mesh relay therefore remain proposals.

Second, the evidence is from simulation only. SUMO traffic, the sublane model for motorcycles and the demand levels are approximations of Lagos traffic and were not calibrated against field counts. Perception is simulated by adding noise to simulator ground truth, so the detector that a real deployment would need is not part of the evaluation. No field trial was carried out.

Third, three of the five planned baselines were built. Fixed-time, count-plus-timer and max-pressure are implemented and evaluated. A deep reinforcement learning controller and the language-model controller LLMLight (Lai et al., 2023) were planned but not built, and the comparisons here do not cover them. This limits any claim about how the planner stands against learned alternatives.

Fourth, africot_full is implemented and wiring-tested with a mock backend, and the real VLAM has been run once on a snapshot as a smoke test with a small model on a CPU. It is not yet evaluated. Mock runs are never reported as VLAM results.

Fifth, some scenario settings were adjusted during construction. The side-road demand in the market scenario was lowered from 550 to 200 vehicles per hour after the specified value produced gridlock under fixed-time control, and the reason is recorded among the deviations. The outage scenario differs from the market scenario only in the slow-loop connectivity window, so for controllers without a slow loop the two scenarios yield identical rows.

Sixth, the emergency-vehicle override, the tiered communication channels (SMS, store-and-forward, mesh relay and satellite), cryptographic message signing and the fixed-time fallback for a system fault are described as design only. With five seeds per cell, the study reports means and standard deviations and treats paired by-seed tests as exploratory. It makes no significance claim where a gap lies within one standard deviation.

Finally, the models are limited to open-source, open-weight systems, and no foundation model is trained from scratch. The world model is a small network in the style of DreamerV3 (Hafner et al., 2025) and TD-MPC2 (Hansen et al., 2024); it is not either of them.

## 1.7 Significance

The study is intended to be useful in four ways. For traffic authorities and researchers in the region, it offers an open, reproducible simulation testbed with informal transit, pedestrians, market and incident scenarios and an outage condition, together with a controller whose every decision can be logged for audit. For the design of embodied AI systems, it offers a worked example of coupling a reasoning model to a fast planner through a small subgoal vector, with a rule-based shield that nothing learned can bypass, and a degradation path intended to keep local control running when the reasoning component is unavailable. For the research community, it reports negative and null results as they were found and records which claims the evidence cannot yet support. For the authors, it provides a concrete base on which a corridor extension, the missing baselines and the GPU evaluation of the full controller can be built.

The study also contributes a deployment framework. The eight layers (sensing, network, data store, models, explainability, services, agents and autonomous operation) were set by the supervisor, Dr. Ebun P. Fasina, in the class session of 27 July 2026, when they typed into DeepSeek on a shared screen the prompt "Design a cloud-based 8-layer framework for AfriCoT-VLA". The framework was cloud-based, with compressed video sent to the cloud, whereas the architecture proposed here keeps raw video on site and runs the fast loop locally. The methodology chapter reconciles the two by keeping the eight layers, treating the cloud as the full-connectivity tier and having the network layer carry compressed keyframes for the slow loop rather than continuous video. The refinements to individual layers are the author's proposals and have not yet been confirmed by the supervisor. They are developed in the methodology chapter and are not evaluated.

## 1.8 Structure of the dissertation

The dissertation has five chapters. This first chapter has set out the background, problem, aim, objectives, research questions, scope and significance. The second chapter reviews the literature on traffic signal control, from fixed-time and actuated plans through max-pressure, reinforcement learning and language-model agents, and then on world models, vision-language-action models and chain-of-thought reasoning for control, explainability and regulation, and the infrastructure constraints of the region. It closes by identifying the gap that the study addresses.

The third chapter presents the methodology and system design. It describes the two-timescale architecture, the subgoal interface, the safety shield, the explainability log, the coordinator and degradation tiers, the tiered communication scheme and the eight-layer deployment framework with its cloud versus on-site tension and reconciliation. It also describes the simulation setup, scenarios, baselines, metrics, seeds and reproducibility measures, and it contains a table that separates what was specified from what was built.

The fourth chapter reports the implementation stage by stage, the accuracy of the world model against persistence, the comparison of controllers across scenarios, the audit of the safety shield, the wiring evidence for the slow loop, the smoke test of the small VLAM and its unreliable reasoning, the negative results, and the threats to validity. The fifth chapter summarises the findings, draws conclusions, makes recommendations and sets out future work, including the corridor extension, neighbour exchange, the missing baselines, the GPU evaluation of the full controller, hardware-in-the-loop testing, shadow mode, a supervised pilot and the deployment roadmap. No submission date is assumed for the timeline. References and appendices follow the final chapter, and the appendices contain reproduction commands, scenario parameters and the full results table.
