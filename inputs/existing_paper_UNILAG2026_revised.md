Towards a Unified Framework of Vision-Language-Action Models and Latent World Models for Low-Resource, Infrastructure-Constrained Environments in Sub-Saharan Africa

Temitope W. Ariyo1* and Ebun P. Fasina1

1Machine Learning Research Group, Department of Artificial Intelligence and Robotics, Faculty of Computing and Informatics, University of Lagos, Akoka, Lagos, Nigeria

temitopeariyo6@gmail.com, efasina@unilag.edu.ng

Abstract

Vision-language-action (VLA) models and latent world models are mostly built assuming dependable connectivity, compute and power, all scarce in Sub-Saharan Africa, where 53% of people had electricity in 2023 and 27% used mobile internet. This position paper argues for a two-loop design. A VLA-derived subgoal generator runs occasionally, on the device or remotely, and sends a compact subgoal to an on-device latent world model planner that plans with the cross-entropy method at every control step. Because hierarchical and dual-system designs already exist, the contribution is narrow: a low-resource design rationale, an explicit narrow-interface constraint, a deployment and fallback analysis, and a comparison of three subgoal interfaces. The method combines a narrative review, conceptual framework design and an illustrative two-dimensional toy study with analytic estimates. In the toy, remote per-step control needed 868 kbit/s at 10 Hz, against 87 kbit/s with a keyframe every ten steps; under bursty outages an expiry-then-cached-goal fallback kept toy success at 100%, a result the static toy nearly guarantees, while remote per-step control fell to 28–84% (50% outage, 5 s mean). Compute savings depended on model sizes. On-device fast control and explicit fallback appear to matter most; the design remains a testable hypothesis.

Keywords: Edge computing, Embodied artificial intelligence, Latent world models, Sub-Saharan Africa, Vision-language-action models

1. Introduction

1.1 Background and Problem

Artificial intelligence (AI) is moving from systems that describe the world towards systems that act in it. Two families of models carry much of this shift. Vision-language-action (VLA) models extend pretrained vision-language models (VLMs) so that a camera image and a natural-language instruction can be mapped to robot actions (Driess et al., 2023; Kim et al., 2025; Zitkovich et al., 2023). Latent world models learn a compact model of how an environment evolves and use it to imagine the consequences of candidate actions before acting (Hafner et al., 2019; Hafner et al., 2025). The two are complementary: VLA models bring broad semantic grounding from web-scale pretraining, while world models bring short-horizon prediction and planning at low cost per step.

Almost all of this work assumes dependable connectivity, abundant compute and stable power, which rarely hold across Sub-Saharan Africa (SSA). In 2023, 565 million people in the region lacked electricity, 85 percent of everyone without access worldwide (International Energy Agency [IEA] et al., 2025). About 53% of the SSA population had access to electricity against about 92% worldwide (World Bank, 2026a), 32.3% used the Internet against 69.2% worldwide (World Bank, 2026b), and mobile internet penetration, as measured by the GSMA (the global association of mobile network operators), reached 27% at the end of 2023 (GSMA Intelligence, 2024) against 57% globally (GSMA, 2024). Figure 1 sets these indicators against the world average. Cities in the region are nonetheless investing in camera-based intelligent infrastructure. In Nairobi, the Kenya Urban Roads Authority has announced camera-equipped, centrally coordinated traffic signals, beginning with 25 junctions (Mwita, 2025), with a second phase of 60 junctions at the procurement stage (Kenya Engineer, 2026), alongside a separately announced programme for 125 intersections (Mburu, 2024), and engineering commentary on the project names unstable roadside power and dependence on single communication links as design risks (Kenya Engineer, 2026). In Lagos, the Lagos Metropolitan Area Transport Authority (LAMATA) has begun a phased deployment of camera- and sensor-based AI traffic systems on selected corridors (ITEdgeNews, 2026). Any embodied AI system proposed for such settings therefore has to treat bandwidth, latency, compute and power as design inputs rather than as details to be settled after deployment.

Figure 1. Sub-Saharan Africa compared with the world average on three infrastructure indicators (data year 2023), drawn from the World Bank World Development Indicators (WDI) for electricity access and Internet use (World Bank, 2026a, 2026b) and from GSMA for mobile internet users (GSMA Intelligence, 2024; GSMA, 2024); in the axis labels, SDG7 is the Sustainable Development Goal 7 tracking data and ITU the International Telecommunication Union. Source: Adapted from World Bank (2026a, 2026b), GSMA Intelligence (2024) and GSMA (2024); chart by the authors

1.2 Related Work and Positioning

Pairing a slow high-level model with a fast low-level planner or controller is not new, and Table 1 compares the closest systems with the present proposal. PlaNet (Hafner et al., 2019) planned online in a learned latent space with the cross-entropy method (CEM), a sampling-based optimiser that repeatedly refits a Gaussian over action sequences to the best-scoring samples (de Boer et al., 2005). DreamerV3 (Hafner et al., 2025) does not plan with CEM; it trains an actor and a critic in imagination. TD-MPC2 (Hansen et al., 2024) uses model predictive control (MPC) with model predictive path integral (MPPI) sampling. Director (Hafner et al., 2022) learns a manager that picks a latent goal every eight steps and a worker that reaches it; it is the closest precedent for a shared-latent subgoal but is not language-conditioned. UniPi (Du et al., 2023), HiP (Hierarchical Planning; Ajay et al., 2023) and SuSIE (Black, Nakamoto, et al., 2024) use predicted videos or goal images as subgoals; SuSIE is essentially the predicted-observation interface studied here, with a learned policy in place of a world-model planner. 3D-VLA (Zhen et al., 2024) predicts goal images and point clouds within one generative model. SayCan (Ahn et al., 2022) lets a large language model choose among pretrained skills, and Hi Robot (Shi et al., 2025) has a VLM issue atomic language commands to a π0 policy (Black, Brown, et al., 2024). Dual-system VLA models split a slow VLM from a fast action module: GR00T N1 (NVIDIA et al., 2025) runs a VLM at 10 Hz and an action module at 120 Hz, and Helix (Figure AI, 2025) runs a 7-billion-parameter VLM at 7–9 Hz that passes a single latent vector to an 80-million-parameter policy at 200 Hz. Helix is the closest existing design to the narrow interface proposed here; it differs in having no learned world model or explicit planner in the fast loop and in assuming an industrial onboard budget rather than intermittent connectivity.

Table 1. Comparison of hierarchical and dual-system approaches with the proposed framework

Source: Authors' compilation (2026) from the cited works; MPC = model predictive control; MPPI = model predictive path integral; LWM = latent world model; 80M = 80 million parameters. A, B and C = the subgoal options (shared latent, learned mapping and predicted goal observation) defined in the framework description.

Few of these systems were designed for constrained deployment. The 55-billion-parameter RT-2 ran at 1–3 Hz from cloud-hosted inference (Zitkovich et al., 2023), whereas smaller models exist, such as Octo at 27 and 93 million parameters (Octo Model Team et al., 2024), SmolVLA at 450 million (Shukor et al., 2025) and TinyVLA at 422 million to 1.3 billion (Wen et al., 2025). Liu et al. (2026) argue for an infrastructure-first approach to embodied AI for science in the Global South, under limits of manpower, power and connectivity. What the reviewed systems leave largely implicit are the questions that dominate such deployment: which component must see pixels and where it runs, how many bytes cross each interface, what happens when the slow component becomes unreachable, and which subgoal representation is cheapest to transmit and consume. This is a position paper: it argues for a design built around those questions and supports the argument with a narrative review and a small illustrative toy study, not with a trained or deployed system.

1.3 Research Objectives

The aim is to propose and examine a two-loop framework that couples a VLA-derived subgoal generator with a latent world model planner for low-resource, infrastructure-constrained settings in SSA. The specific objectives are:

• O1: to derive a two-loop design rationale from the bandwidth, latency, compute and power constraints documented for SSA;

• O2: to define an explicit narrow-interface constraint and three candidate subgoal interfaces, and to compare them on message size, on-device compute, training needs and interpretability;

• O3: to analyse deployment configurations and fallback behaviour when the slow loop is remote, unreachable or unpowered;

• O4: to propose a staged training scheme for the slow loop based on a task-completion signal;

• O5: to illustrate O1 to O3 quantitatively with a toy feasibility study of communication cost, link outages, interface choice, memory, latency and compute overhead.

2. Methodology

2.1 Study Design

The study combines three components. The first is a narrative literature review, used because this is a position paper; no counts of screened records were kept. Sources were identified from the authors' original reading and, during revision, by searches of arXiv and Crossref, of the proceedings of the main robot-learning and machine-learning venues (through the Proceedings of Machine Learning Research (PMLR) and OpenReview), of publisher pages and of the web, and by following reference lists. Search terms combined "vision-language-action", "world model", "latent dynamics", "model predictive control", "cross-entropy method", "hierarchical planning", "subgoal", "dual-system", "edge deployment" and "efficient VLA", and paired "embodied AI" with "low-resource", "Global South" or "Africa". Recent VLA and hybrid systems were drawn mainly from 2023 to 2026 and latent world models from 2019 onwards. Works were included if they proposed, analysed or surveyed VLA models, latent world models, planners for learned models or hierarchical controllers with architectural details usable in a comparison; official statistics and dated reports on Nairobi and Lagos were included for context. Works that could not be located in a bibliographic database or on a publisher's page were excluded, and in October 2026 every scholarly reference was checked against its digital object identifier (DOI), arXiv record, proceedings page or OpenReview entry, and every report, data set and news item against its publisher's page. The second component is conceptual framework design, in which the architecture, interface, planner, training scheme and fallback policy are specified from the review and the constraints above. The third is an illustrative toy feasibility study with analytic estimates, designed to make the framework's quantitative claims concrete, not to validate it.

2.2 The Proposed Framework

2.2.1 Architecture and Naming

The framework has two loops (Figure 2). VLA here denotes a model that maps vision and language to robot-relevant outputs. Because the slow loop outputs subgoals rather than motor commands, it is not a VLA policy in the strict sense; we call it a VLA-derived subgoal generator to signal that it reuses a pretrained VLA or VLM backbone with a subgoal head in place of the action head. The fast loop is the latent world model (LWM) planner. The slow loop runs every K control steps, or earlier when a new instruction arrives or the scene changes beyond a threshold; given an instruction l and a keyframe ot, it outputs a subgoal g. The fast loop runs at every control step: it encodes the current observation into a latent state zt, rolls out candidate action sequences with a learned latent dynamics model, scores them against g, and executes the first action of the best sequence before re-planning.

Figure 2. The proposed two-loop framework. The VLA-derived subgoal generator (slow loop) may run on the device or remotely; the subgoal channel is the only path from the slow loop to the LWM planner (fast loop), and a subgoal watchdog handles expiry and fallback. Source: Authors' creation (2026)

2.2.2 Subgoal Interface and Options A, B and C

Definition. The subgoal interface is the message m = (g, τ, v) sent from the slow loop to the fast loop, where g is the subgoal payload, τ the time at which it was produced and v an optional confidence or validity horizon. The fast loop minimises, over a horizon H, the cost J = Σh [ δ(ẑt+h, φ(g)) + λa‖at+h‖² + λq Q(ẑt+h) ], where ẑ are latent states predicted by the world model, φ converts the payload into a latent target, δ is a latent distance, a are actions and Q penalises constraint violations such as predicted collisions. The narrow-interface constraint requires that m has a bounded size and that no image, text or intermediate activation from the slow loop reaches the fast loop by any other path. The slow loop produces m and the fast loop consumes it.

Option A, shared latent. The slow loop outputs a vector directly in the world model's latent space, so φ is the identity. It is the cheapest to consume but couples the two components: the slow loop must be retrained whenever the world model changes. Here g has d values, where d is the latent dimension of the world model (d = 32 in the toy study).

Option B, learned mapping. The slow loop outputs a compact code of smaller dimension, and a small learned network φ on the device maps it to a latent target (written gφ(c) in Figure 2, with c the compact code). This decouples the two loops at the cost of extra parameters and paired training data. Here c has k values with k smaller than d (k = 8 in the toy study).

Option C, predicted goal observation. The slow loop outputs a predicted image of the goal, and φ is the fast loop's own observation encoder, as in SuSIE (Black, Nakamoto, et al., 2024) and UniPi (Du et al., 2023). It is the most interpretable option but has the largest message and needs a generative model on the slow side. Here g is an image, 64 × 64 in the toy study and 224 × 224 at realistic resolution.

2.2.3 Fast-Loop Planning With the Cross-Entropy Method

At each step the LWM planner samples N action sequences of length H from a Gaussian, rolls them out through the latent dynamics, evaluates J, refits the Gaussian to the best sequences and repeats for I iterations, following PlaNet (Hafner et al., 2019). Learned latent dynamics are differentiable, so CEM is not chosen because gradients are unavailable, and gradient-based and hybrid planners exist (Bharadhwaj et al., 2020; Srinivas et al., 2018). CEM is chosen because it is gradient-free with respect to the cost, so non-smooth terms such as collision indicators can be used directly; because sampling copes with multimodal costs better than local gradient descent; because the N rollouts parallelise well on small accelerators; and because it has few hyperparameters. A learned actor, as in DreamerV3, or MPPI with a value function, as in TD-MPC2, could replace CEM behind the same interface.

2.2.4 Staged Training

Training is proposed in two stages. First, the world model is trained on logged transitions with the usual reconstruction or self-prediction and reward terms (Hafner et al., 2019; Hafner et al., 2025), giving a stable latent space. Second, the slow loop is trained against the frozen world model. In a supervised step, hindsight relabelling (Andrychowicz et al., 2017; Ghosh et al., 2021; Mendonca et al., 2021) makes the latent state actually reached after K steps the target subgoal for the instruction and keyframe at the start of the segment, so no reward is required. In a fine-tuning step, the fast loop tries to reach proposed subgoals and each subgoal is weighted by the binary task-completion signal or a return, in the manner of reward-weighted or advantage-weighted regression (Peng et al., 2019; Peters & Schaal, 2007). The staging is intended to avoid jointly optimising two components with different rates; it is a proposal and is not verified here.

2.2.5 Deployment Configurations and Fallback

Where the slow loop runs determines what crosses the network. In configuration M1, a unified VLA runs remotely and every control step needs an uplinked frame and a downlinked action. In M2, the slow loop runs remotely and the fast loop on the device, so a keyframe goes up every K steps and a subgoal comes down; pixels still cross the network, only K times less often. In M3, both loops run on the device, and the cost moves to memory and compute. Because the slow loop may become unreachable, or its host may lose power, the fast loop includes a subgoal watchdog. While a valid subgoal exists, the fast loop keeps planning towards the last one received. Each subgoal carries an expiry time Texp, after which the fast loop switches to a safe default such as braking and holding position or, where a coarse final goal is cached locally, continues towards it at reduced speed (graceful degradation). A power drop that affects the fast loop itself has to be covered by hardware fail-safes.

2.3 Data Generation: Toy Simulation

All data were generated by a toy simulation written in Python with NumPy and matplotlib, with a fixed random seed (20261015); assumed quantities are stated as assumptions. The code, output files and figure scripts are openly available under the MIT licence at https://github.com/Topmost2020/vla-lwm-toy-simulation. It has five parts.

E1, communication. Network traffic of M1, M2 and M3 is computed analytically at an assumed 10 Hz control rate. A 224 × 224 colour keyframe is 150,528 bytes raw; a natural photograph (the sample portrait supplied with matplotlib) resized to that resolution and compressed with the Joint Photographic Experts Group (JPEG) codec at quality 75 gave a measured 10,479 bytes. Actions have seven degrees of freedom in 16-bit floating point (fp16), and the default subgoal is Option A with 32 fp16 values (64 bytes). Link capacities of 64 kbit/s to 5 Mbit/s and round-trip times (RTTs) of 100 to 1,000 ms are illustrative assumptions. Transmitted bytes include an assumed 40-byte header for every 1,460-byte segment and a 40-byte header on each reply, and the round-trip latency in the Results includes an assumed 50 ms of remote processing.

E2, outages. A two-dimensional point mass travels through a 10 m × 10 m arena with four to six static circular obstacles from (1, 1) to (9, 9); success means ending within 0.4 m of the goal within 400 steps at 10 Hz. The world model is a fixed random linear encoder into a 32-dimensional latent space with linear latent dynamics fitted on 4,000 random transitions (1,216 parameters). The planner is CEM with N = 64, H = 12 and I = 4. The slow loop is an oracle path planner, with no language or perception, that proposes a waypoint 2 m ahead every K = 10 steps with a delay of 5 steps. The link follows a two-state Gilbert-Elliott model of bursty channels (Elliott, 1963; Gilbert, 1960), with outage fractions of 10%, 30% and 50% and mean outage durations of 1, 5 and 20 s, plus slow-loop power drops of 10 and 20 s. Four policies are run on 100 random seeds per condition: P1, remote per-step control with zero network latency (an optimistic assumption for P1), which on link loss holds its last action or outputs zero; P2, keep the last subgoal; P3, let it expire after 3 s and brake; and P4, let it expire and plan towards a locally cached final goal at 0.5 m/s. The planner evaluates the goal cost in closed form because the latent model is linear, refits to the best 10% of samples, and the slow loop also issues a new request when the link recovers.

E3, interfaces. The three options run the same task without outages. Option A sends the 32-dimensional latent target, Option B an 8-dimensional code (16 bytes) mapped on the device by a small learned map, and Option C a 64 × 64 single-channel goal image. E3 also tests quantisation to 8-bit integers (int8) and added noise.

E4 and E5, compute, memory and overhead. Toy planner latencies were measured on a cloud processor (Intel Xeon at 2.80 GHz, four virtual cores), which is not an edge device. Memory and compute were then estimated for slow loops of 0.03 to 7 billion parameters and world models of 5, 50 and 200 million parameters, against assumed edge tiers of 4 and 8 GB of memory (2.5 and 6.5 GB assumed usable) and 0.5, 5 and 20 tera floating-point operations per second (TFLOP/s) of assumed sustained throughput. E5 compares a unified VLA that runs at every step (U) with the two-loop design (T) in floating-point operations (FLOPs) per step over 180 combinations (five slow-loop sizes, three world-model sizes, K of 5, 10, 20 and 50, and three CEM budgets). The small, medium and large CEM budgets are N = 64, H = 10, I = 3; N = 256, H = 12, I = 4; and N = 1,000, H = 15, I = 5, which is 1,920, 12,288 and 75,000 latent rollout steps per control step. The slow loop is assumed to process 256 image tokens and 32 text tokens per call, the unified VLA to decode seven action tokens per step, and the world model to hold 50% of its parameters in the encoder (applied at 64 positions) and 10% in the latent dynamics. The latency measurement timed the toy linear latent model with H of 10 and 15 and four iterations, and a stand-in with a tanh MLP dynamics network (hidden width 256 or 1,024) with the three budgets above. For scale, PlaNet used N = 1,000, H = 12 and I = 10, or 120,000 rollout steps (Hafner et al., 2019), and TD-MPC2 uses 512 samples, 6 iterations and a horizon of 3, or about 9,200 (Hansen et al., 2024), so the large budget here is of the same order as published settings. Memory need is the parameter count of the slow loop and the world model times the bytes per parameter times an assumed 1.2 runtime-overhead multiplier, and usable memory is the device total less an assumed 1.5 GB reserved for the operating system and camera pipeline. The unified VLA is assumed to process the full 288-token prompt at every step without cache reuse.

2.4 Analysis

The analysis is descriptive. For E1, traffic is reported in bytes per step, kbit/s and as a share of an assumed link. For E2, the toy success, collision and timeout rates over 100 seeds are reported per policy and condition. For E3, the message size, fast-side FLOPs, extra parameters and mean subgoal error are compared. For E4 and E5, memory need and latency are set against the assumed tiers, with a 100 ms deadline for the 10 Hz fast loop, and the two-loop cost is expressed as a ratio T/U. No inferential statistics are used, because the toy is meant to make claims measurable, not to test them. Every number in the Results comes from the simulation's output files.

3. Results

All results are from the toy study and analytic estimates; they are illustrative and depend on the stated assumptions.

3.1 Communication Cost

Remote per-step control (M1) needs about 12.4 Mbit/s with raw frames and 868 kbit/s with JPEG frames, which is 339% of a 256 kbit/s link (Table 2, Figure 3). With the slow loop remote and the fast loop on the device (M2), traffic falls in proportion to K: 87 kbit/s at K = 10, about a tenth of M1. With both loops on the device (M3), only instructions cross the network. The keyframe uplink dominates every remote configuration; Option C with a full predicted 224 × 224 frame costs as much downlink as a keyframe uplink. Latency compounds the problem: at an assumed 100 ms RTT on a 256 kbit/s link, an M1 action arrives 489 ms after its frame and closed-loop control falls to 2.04 Hz, whereas under M2 the fast loop keeps its 10 Hz rate and the cost appears as subgoal staleness of 0.74 s at a 100 ms round trip and 1.64 s at 1,000 ms on that link, including an assumed 0.3 s of remote slow-loop inference.

Table 2. Network traffic per deployment configuration at an assumed 10 Hz control rate

Source: Authors' creation (2026); JPEG at quality 75 on a photograph stand-in; values above 100% mean that the link cannot carry the stream.

Figure 3. Network traffic against the slow-loop period K at 10 Hz: (a) total traffic of remote per-step control (M1) and of a remote slow loop (M2), with assumed link capacities as dotted lines; (b) downlink traffic by subgoal option; in the legend, PNG is Portable Network Graphics and JPEG is Joint Photographic Experts Group, and d is the subgoal latent dimension (32 in the toy study, 1,024 as a larger case). Source: Authors' creation (2026)

3.2 Link Outages, Power Drops and Fallback

Remote per-step control that holds its last action degrades fastest: its toy success falls to 28% at 50% outage with a 5 s mean, and a 20 s power drop of the remote host leaves it at 1% (Table 3, Figure 4). Outputting zero on link loss is safer in this static toy (79% to 100%) but still fails under long outages.

Table 3. Toy success rate (%) under link outages and slow-loop power drops (100 seeds per cell)

Source: Authors' creation (2026); P1 is given zero network latency, which favours it; obstacles are static and sensed locally.

P2 and P3 reach 100% under short outages and under both power drops, because the fast loop either keeps planning towards the last subgoal (P2) or stops safely after expiry and resumes when the link returns (P3), within the 40 s episode limit, but fall to 82–83% at 50% outage with a 5 s mean; their failures are timeouts, not collisions, which were 0% for every two-loop policy in every condition. Under heavy or long outages, P2 and P3 were no better than remote control that outputs zero (83% and 82% against 84% at 50% outage with a 5 s mean). P4 succeeded in all 1,200 toy episodes, but this is close to guaranteed by the toy: with an exact cached final goal and local obstacle sensing, the fast loop can reach the goal without the slow loop at all. Without outages, the two-loop policies sent about 148 kB per episode against about 1,348 kB for P1, over mean times to the goal of 14.2 s and 12.4 s.

Figure 4. Toy success rate against the fraction of time the link is down, for mean outage durations of 1, 5 and 20 s, under remote per-step control (P1) and the two-loop fallback policies (P2 to P4). Source: Authors' creation (2026)

3.3 Comparison of Subgoal Interfaces

All three options reached 100% toy success with the same final distance to the goal (0.38 m), so the toy does not separate them on task outcome; the differences lie in message size, on-device cost, training needs and robustness (Table 4). Option B gave the smallest message (16 bytes) but needs a learned map with 2,080 parameters; its mean error fell from 0.886 m with 4 paired samples to 0.0076 m with 256. Option A needs no extra parameters but ties the slow loop to the world model's latent space. Option C needs the most fast-side computation and, at realistic resolution, the largest message: 10,479 bytes for a 224 × 224 predicted frame compressed as JPEG. Quantising to int8 did not affect success, whereas Option C failed in every episode when pixel noise with a standard deviation of 50 grey levels was added.

Table 4. Subgoal interface options in the toy study: A sends a 32-value latent target, B an 8-value code and C a 64 × 64 goal image

Source: Authors' creation (2026); bytes and FLOPs are per subgoal; Option C's 220 bytes is the PNG-compressed toy image (4,096 bytes raw); error is the mean subgoal error; all options reached 100% toy success; C's FLOPs are for a toy centroid encoder, and a learned 224 × 224 image encoder is assumed to cost about 10^9 FLOPs.

Failure modes and compatibility follow from these results and from the design. Option A fails through coupling: any change to the world model's latent space invalidates the slow loop, so it suits a single team that trains and updates both models together, and it is compatible with latent-goal designs such as Director (Hafner et al., 2022). Option B is limited by the availability of paired data, but it lets the slow-loop backbone and the world model be developed and replaced separately. Option C is the most interpretable and is compatible with existing goal-image generators such as SuSIE (Black, Nakamoto, et al., 2024), but it has the largest message and was the least robust, failing in every episode under strong pixel noise.

3.4 Memory, Latency and Overhead Against a Unified VLA

Slow loops up to 0.5 billion parameters, together with a 50-million-parameter world model, fit a 4 GB device at any precision and run once per second even at 0.5 TFLOP/s, whereas a 7-billion-parameter model fits 8 GB only at 4-bit precision (int4), where it needs 4.23 GB (Figure 5a). The fast loop is the tighter constraint because it must finish within 100 ms: a 5-million-parameter world model meets this deadline at 0.5 TFLOP/s with small and medium CEM budgets, a 50-million-parameter model needs about 5 TFLOP/s for a medium budget, and a 200-million-parameter model with a large budget misses it on every tier (151 ms at 20 TFLOP/s). On the cloud processor, the toy CEM planner took a median of 1.53 ms with 64 samples and a 10-step horizon (Figure 5b). For a stand-in with a tanh MLP dynamics network of 67,584 parameters, the median step time was 41.1 ms at the medium budget and 251.6 ms at the large budget, which exceeds the 100 ms deadline on this processor.

Figure 5. Compute and memory: (a) slow-loop weight memory including runtime overhead against slow-loop size, with the usable memory of assumed 4 GB and 8 GB devices; (b) measured fast-loop latency per step on a cloud processor (not an edge device) against the number of CEM samples, with the 100 ms deadline. Source: Authors' creation (2026)

The two-loop design is not uniformly cheaper than a unified VLA (Table 5, for the 50-million-parameter world model and K = 10 where ranges are quoted). With a 0.03-billion-parameter VLA it costs 1.36 to 42.65 times as much, because the CEM rollouts outweigh a small model run every step; from 2 billion parameters upwards it costs 0.10 to 0.74 times as much. Across all 180 cases, the two-loop design was not cheaper in 68, all with slow loops of 2 billion parameters or fewer. Memory bandwidth points the same way: if the unified VLA reads its int8 weights once for the prompt and once for each of seven decoded action tokens per step (an assumption), a 2-billion-parameter model needs about 160 GB/s at 10 Hz, whereas the same model as a slow loop, which needs one pass per call to produce a subgoal, needs about 2 GB/s at K = 10.

Table 5. Per-step compute of a unified VLA (U) and the two-loop design (T) with a 50M-parameter world model and K = 10

Source: Authors' creation (2026); B = billion parameters; T/U below 1 means the two-loop design is cheaper; weight traffic assumes int8 weights read once per forward pass at 10 Hz, with eight passes per step for the unified VLA (one prompt pass and seven action tokens).

4. Discussion

4.1 What the Toy Study Does and Does Not Show

The toy study supports three limited statements. First, moving per-step control onto the device and calling a remote slow loop only every K steps cuts network traffic roughly in proportion to K and decouples the control rate from the RTT; this follows from the arithmetic as much as from the simulation. Second, in this toy the fallback policy changed outcomes whereas the interface choice did not, although the interfaces were compared only without outages. The cached-goal policy (P4) avoided both collisions and timeouts in the conditions tested (a property of the toy, as the Results explain), whereas keeping or expiring the subgoal alone (P2, P3) still timed out under long outages. Third, whether the two-loop design saves computation depends on the relative sizes of the slow loop, the world model and the planning budget; it is not a general property of the design.

The study does not show that a learned VLA-derived subgoal generator can produce useful subgoals, because the slow loop was an oracle without language or perception, nor that a linear world model in two dimensions says anything about visual world models with hundreds of millions of parameters. Latencies were measured on a cloud processor, and the edge tiers, link capacities and RTTs are assumptions. The remote baseline was given zero network latency, which favours it, and the static obstacles hide the risk of acting on a stale subgoal in a changing scene. The toy is therefore a check that the framework's claims can be stated in measurable terms, not evidence that they hold.

Which interface to recommend therefore remains open, because the toy study did not separate the options on task outcome. As a working position, the framework proposes Option A as the default where one team controls both models and bandwidth is tight, Option B where the slow-loop backbone or the world model must be replaced independently, and Option C only where interpretability or reuse of an off-the-shelf goal-image generator justifies a larger message. This ordering is a hypothesis for the benchmark studies proposed below, not a result.

4.2 Implications for Sub-Saharan Africa

The results correct a simplification that is easy to make: a narrow subgoal interface does not keep pixels off the network, because a remote slow loop still needs keyframes. What the design changes is how often. Where links offer a few hundred kbit/s, per-step remote control with independently coded frames exceeds the link (339% of 256 kbit/s), whereas a remote slow loop with K = 10 uses about a third of it. Where links are too unreliable for any remote dependency, the on-device configuration removes pixels from the network but moves the burden to memory and compute. The estimates suggest that a slow loop of up to about 0.5 billion parameters, in the range of SmolVLA and the smallest TinyVLA, together with a world model of a few tens of millions of parameters, could fit a 4 GB device and meet a 1 Hz slow-loop rate and a 10 Hz fast-loop rate on the assumed 5 TFLOP/s tier. On that tier a 0.5-billion-parameter slow loop is estimated at 57.6 ms per call and a 50-million-parameter world model with the medium CEM budget at 25.2 ms per step, so the combined load is about 58 ms of compute per second for the slow loop at 1 Hz plus about 252 ms per second for the fast loop at 10 Hz, roughly a third of that tier. These times rest on the assumed sustained throughput of the tier; if the real sustained throughput were only 30% of that value, the same loads would take about 192 ms per slow-loop call and 84 ms per fast-loop step, a combined load of about 1.03 s per second, so the estimates are sensitive to this assumption. Running a large backbone only every K steps would also be expected to lower energy use per control step, which matters where power is intermittent, but energy was not measured.

For the camera-based traffic systems in Nairobi and Lagos, the framework is offered as a design pattern rather than a ready solution. A junction controller could keep its fast loop locally, call a remote or on-site slow loop occasionally, and fall back to a fixed plan when the link or server fails, which is the behaviour engineering commentary on the Nairobi project asks for (Kenya Engineer, 2026). Safety is a recognised challenge for embodied AI systems built on learned models, which can fail in unsafe ways without safeguards (Zhang et al., 2024), and the watchdog is a fallback mechanism, not a safety guarantee.

4.3 Limitations and Future Work

The main limitation is that the framework has no empirical validation beyond the toy study: no learned subgoal generator, real perception, edge hardware or recorded network trace was used, so every claim above remains a hypothesis. The framework inherits the open problems of both model families: data efficiency and generalisation remain open challenges for VLA models, which often fail on out-of-distribution tasks (Sapkota et al., 2025), and collecting robot demonstrations is harder where sensors, storage and upload capacity are scarce. Four research steps follow: training the three interface options on a standard simulated benchmark with real perception and a learned VLA-derived subgoal generator; profiling a quantised small VLA backbone and a latent world model on actual edge hardware, including power draw; testing the fallback policies under recorded link traces from SSA networks and in changing scenes; and building benchmarks that score embodied agents under constrained bandwidth, compute and power.

5. Conclusion

This position paper has argued for a two-loop framework that couples a VLA-derived subgoal generator with an LWM planner through a single, narrow subgoal interface, for embodied AI in low-resource, infrastructure-constrained settings such as SSA. It does not claim the hierarchical pattern as new: Director, UniPi, SuSIE, 3D-VLA, GR00T N1, Helix and related systems already separate slow reasoning from fast control. Its contribution is a design rationale derived from bandwidth, compute and power constraints, an explicit bound on what crosses between the loops, an analysis of deployment configurations and fallback behaviour, a precise definition of three subgoal interfaces with a tentative, untested preference among them, and a proposed staged training scheme. An illustrative toy study quantified the traffic saved by sending keyframes every K steps, showed in a static world that an explicit expiry and cached-goal fallback kept the toy task on track under outages that degraded remote per-step control (to 28% when it held its last action and 84% when it output zero, at 50% outage with a 5 s mean), and found that the two-loop design saves compute only when the slow loop is large relative to the world model and the planning budget. None of this validates the framework on real robots, perception or networks; the next step is to test it with learned components on edge hardware under link conditions recorded in the region.

Declarations

Ethical statement. The study involved no human participants, so formal ethical approval was not required.

Funding. The authors received no specific funding for this work.

Conflicting interest. The authors have no conflict of interest to declare.

Use of generative AI. Claude (Anthropic) was used to edit, restructure and enhance the clarity of the manuscript in response to reviewer comments, and to help write the code for the toy simulation and the plots. All figures were drawn with plotting code and none was generated by an image model. The ideas, arguments, framework, interpretations and final content are the authors', who retain full responsibility for the accuracy, integrity and final version of the paper.

References

Ahn, M., Brohan, A., Brown, N., Chebotar, Y., Cortes, O., David, B., Finn, C., Fu, C., Gopalakrishnan, K., Hausman, K., Herzog, A., Ho, D., Hsu, J., Ibarz, J., Ichter, B., Irpan, A., Jang, E., Jauregui Ruano, R., Jeffrey, K., . . . Zeng, A. (2022). Do as I can, not as I say: Grounding language in robotic affordances (arXiv:2204.01691). arXiv. https://arxiv.org/abs/2204.01691

Ajay, A., Han, S., Du, Y., Li, S., Gupta, A., Jaakkola, T., Tenenbaum, J., Kaelbling, L., Srivastava, A., & Agrawal, P. (2023). Compositional foundation models for hierarchical planning. Advances in Neural Information Processing Systems, 36. https://arxiv.org/abs/2309.08587

Andrychowicz, M., Wolski, F., Ray, A., Schneider, J., Fong, R., Welinder, P., McGrew, B., Tobin, J., Abbeel, P., & Zaremba, W. (2017). Hindsight experience replay. Advances in Neural Information Processing Systems, 30. https://arxiv.org/abs/1707.01495

Bharadhwaj, H., Xie, K., & Shkurti, F. (2020). Model-predictive control via cross-entropy and gradient-based optimization. In A. M. Bayen, A. Jadbabaie, G. Pappas, P. A. Parrilo, B. Recht, C. Tomlin, & M. Zeilinger (Eds.), Proceedings of the 2nd Conference on Learning for Dynamics and Control (Vol. 120, pp. 277–286). PMLR. https://proceedings.mlr.press/v120/bharadhwaj20a.html

Black, K., Brown, N., Driess, D., Esmail, A., Equi, M., Finn, C., Fusai, N., Groom, L., Hausman, K., Ichter, B., Jakubczak, S., Jones, T., Ke, L., Levine, S., Li-Bell, A., Mothukuri, M., Nair, S., Pertsch, K., Shi, L. X., . . . Zhilinsky, U. (2024). π0: A vision-language-action flow model for general robot control (arXiv:2410.24164). arXiv. https://arxiv.org/abs/2410.24164

Black, K., Nakamoto, M., Atreya, P., Walke, H., Finn, C., Kumar, A., & Levine, S. (2024). Zero-shot robotic manipulation with pretrained image-editing diffusion models. In International Conference on Learning Representations (ICLR 2024). https://arxiv.org/abs/2310.10639

de Boer, P.-T., Kroese, D. P., Mannor, S., & Rubinstein, R. Y. (2005). A tutorial on the cross-entropy method. Annals of Operations Research, 134(1), 19–67. https://doi.org/10.1007/s10479-005-5724-z

Driess, D., Xia, F., Sajjadi, M. S. M., Lynch, C., Chowdhery, A., Ichter, B., Wahid, A., Tompson, J., Vuong, Q., Yu, T., Huang, W., Chebotar, Y., Sermanet, P., Duckworth, D., Levine, S., Vanhoucke, V., Hausman, K., Toussaint, M., Greff, K., . . . Florence, P. (2023). PaLM-E: An embodied multimodal language model. In A. Krause, E. Brunskill, K. Cho, B. Engelhardt, S. Sabato, & J. Scarlett (Eds.), Proceedings of the 40th International Conference on Machine Learning (Vol. 202, pp. 8469–8488). PMLR. https://proceedings.mlr.press/v202/driess23a.html

Du, Y., Yang, M., Dai, B., Dai, H., Nachum, O., Tenenbaum, J. B., Schuurmans, D., & Abbeel, P. (2023). Learning universal policies via text-guided video generation. Advances in Neural Information Processing Systems, 36. https://arxiv.org/abs/2302.00111

Elliott, E. O. (1963). Estimates of error rates for codes on burst-noise channels. Bell System Technical Journal, 42(5), 1977–1997. https://doi.org/10.1002/j.1538-7305.1963.tb00955.x

Figure AI. (2025, February 20). Helix: A vision-language-action model for generalist humanoid control [Blog post]. https://www.figure.ai/news/helix

Ghosh, D., Gupta, A., Reddy, A., Fu, J., Devin, C., Eysenbach, B., & Levine, S. (2021). Learning to reach goals via iterated supervised learning. In International Conference on Learning Representations (ICLR 2021). https://arxiv.org/abs/1912.06088

Gilbert, E. N. (1960). Capacity of a burst-noise channel. Bell System Technical Journal, 39(5), 1253–1265. https://doi.org/10.1002/j.1538-7305.1960.tb03959.x

GSMA. (2024). The state of mobile internet connectivity report 2024. https://www.gsmaintelligence.com/research/the-state-of-mobile-internet-connectivity-2024

GSMA Intelligence. (2024). The mobile economy Sub-Saharan Africa 2024. GSMA. https://www.gsma.com/solutions-and-impact/connectivity-for-good/mobile-economy/wp-content/uploads/2024/11/GSMA_ME_SSA_2024_Web.pdf

Hafner, D., Lee, K.-H., Fischer, I., & Abbeel, P. (2022). Deep hierarchical planning from pixels. Advances in Neural Information Processing Systems, 35. https://arxiv.org/abs/2206.04114

Hafner, D., Lillicrap, T., Fischer, I., Villegas, R., Ha, D., Lee, H., & Davidson, J. (2019). Learning latent dynamics for planning from pixels. In K. Chaudhuri & R. Salakhutdinov (Eds.), Proceedings of the 36th International Conference on Machine Learning (Vol. 97, pp. 2555–2565). PMLR. https://proceedings.mlr.press/v97/hafner19a.html

Hafner, D., Pasukonis, J., Ba, J., & Lillicrap, T. (2025). Mastering diverse control tasks through world models. Nature, 640(8059), 647–653. https://doi.org/10.1038/s41586-025-08744-2

Hansen, N., Su, H., & Wang, X. (2024). TD-MPC2: Scalable, robust world models for continuous control. In International Conference on Learning Representations (ICLR 2024). https://arxiv.org/abs/2310.16828

International Energy Agency, International Renewable Energy Agency, United Nations Statistics Division, World Bank, & World Health Organization. (2025). Tracking SDG 7: The energy progress report 2025. World Bank. https://unstats.un.org/unsd/energystats/pubs/documents/sdg_7_2025.pdf

ITEdgeNews. (2026, April 29). LAMATA deploys AI-powered smart traffic systems to cut congestion on Lagos roads. https://www.itedgenews.africa/lamata-deploys-ai-powered-smart-traffic-systems-to-cut-congestion-on-lagos-roads/

Kenya Engineer. (2026, August 10). Nairobi's KSh10.8 billion intelligent traffic project moves from signals to systems. https://www.kenyaengineer.co.ke/nairobis-ksh10-8-billion-intelligent-traffic-project-moves-from-signals-to-systems/

Kim, M. J., Pertsch, K., Karamcheti, S., Xiao, T., Balakrishna, A., Nair, S., Rafailov, R., Foster, E., Lam, G., Sanketi, P., Vuong, Q., Kollar, T., Burchfiel, B., Tedrake, R., Sadigh, D., Levine, S., Liang, P., & Finn, C. (2025). OpenVLA: An open-source vision-language-action model. In P. Agrawal, O. Kroemer, & W. Burgard (Eds.), Proceedings of The 8th Conference on Robot Learning (Vol. 270, pp. 2679–2713). PMLR. https://proceedings.mlr.press/v270/kim25c.html

Liu, S., Tang, J., Hassan, M. S., Sharkawy, M. H., Fouda, M. M. G., Shang, T., & Wang, Z. (2026). Infrastructure first: Enabling embodied AI for science in the Global South (arXiv:2604.06722). arXiv. https://arxiv.org/abs/2604.06722

Mburu, P. (2024, February 6). Nairobi gets traffic lights, surveillance cameras for 125 junctions in China deal. Business Daily. https://www.businessdailyafrica.com/bd/economy/new-traffic-lights-and-surveillance-cameras-for-125-junctions--4516290

Mendonca, R., Rybkin, O., Daniilidis, K., Hafner, D., & Pathak, D. (2021). Discovering and achieving goals via world models. Advances in Neural Information Processing Systems, 34. https://arxiv.org/abs/2110.09514

Mwita, M. (2025, March 20). Samsung to build Nairobi's Sh7.9bn intelligent traffic system. The Star. https://www.the-star.co.ke/business/2025-03-20-samsung-to-build-nairobis-sh79bn-intelligent-traffic-system

NVIDIA, Bjorck, J., Castañeda, F., Cherniadev, N., Da, X., Ding, R., Fan, L., Fang, Y., Fox, D., Hu, F., Huang, S., Jang, J., Jiang, Z., Kautz, J., Kundalia, K., Lao, L., Li, Z., Lin, Z., . . . Zhu, Y. (2025). GR00T N1: An open foundation model for generalist humanoid robots (arXiv:2503.14734). arXiv. https://arxiv.org/abs/2503.14734

Octo Model Team, Ghosh, D., Walke, H., Pertsch, K., Black, K., Mees, O., Dasari, S., Hejna, J., Kreiman, T., Xu, C., Luo, J., Tan, Y. L., Chen, L. Y., Sanketi, P., Vuong, Q., Xiao, T., Sadigh, D., Finn, C., & Levine, S. (2024). Octo: An open-source generalist robot policy. In Robotics: Science and Systems XX. https://doi.org/10.15607/RSS.2024.XX.090

Peng, X. B., Kumar, A., Zhang, G., & Levine, S. (2019). Advantage-weighted regression: Simple and scalable off-policy reinforcement learning (arXiv:1910.00177). arXiv. https://arxiv.org/abs/1910.00177

Peters, J., & Schaal, S. (2007). Reinforcement learning by reward-weighted regression for operational space control. In Proceedings of the 24th International Conference on Machine Learning (pp. 745–750). ACM. https://doi.org/10.1145/1273496.1273590

Sapkota, R., Cao, Y., Roumeliotis, K. I., & Karkee, M. (2025). Vision-language-action (VLA) models: Concepts, progress, applications and challenges (arXiv:2505.04769). arXiv. https://arxiv.org/abs/2505.04769

Shi, L. X., Ichter, B., Equi, M., Ke, L., Pertsch, K., Vuong, Q., Tanner, J., Walling, A., Wang, H., Fusai, N., Li-Bell, A., Driess, D., Groom, L., Levine, S., & Finn, C. (2025). Hi Robot: Open-ended instruction following with hierarchical vision-language-action models. In A. Singh, M. Fazel, D. Hsu, S. Lacoste-Julien, F. Berkenkamp, T. Maharaj, K. Wagstaff, & J. Zhu (Eds.), Proceedings of the 42nd International Conference on Machine Learning (Vol. 267, pp. 54919–54933). PMLR. https://proceedings.mlr.press/v267/shi25d.html

Shukor, M., Aubakirova, D., Capuano, F., Kooijmans, P., Palma, S., Zouitine, A., Aractingi, M., Pascal, C., Russi, M., Marafioti, A., Alibert, S., Cord, M., Wolf, T., & Cadene, R. (2025). SmolVLA: A vision-language-action model for affordable and efficient robotics (arXiv:2506.01844). arXiv. https://arxiv.org/abs/2506.01844

Srinivas, A., Jabri, A., Abbeel, P., Levine, S., & Finn, C. (2018). Universal planning networks: Learning generalizable representations for visuomotor control. In J. Dy & A. Krause (Eds.), Proceedings of the 35th International Conference on Machine Learning (Vol. 80, pp. 4732–4741). PMLR. https://proceedings.mlr.press/v80/srinivas18b.html

Wen, J., Zhu, Y., Li, J., Zhu, M., Tang, Z., Wu, K., Xu, Z., Liu, N., Cheng, R., Shen, C., Peng, Y., Feng, F., & Tang, J. (2025). TinyVLA: Toward fast, data-efficient vision-language-action models for robotic manipulation. IEEE Robotics and Automation Letters, 10(4), 3988–3995. https://doi.org/10.1109/LRA.2025.3544909

World Bank. (2026a). Access to electricity (% of population) (EG.ELC.ACCS.ZS) [Data set]. World Development Indicators. Retrieved October 15, 2026, from https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS

World Bank. (2026b). Individuals using the Internet (% of population) (IT.NET.USER.ZS) [Data set]. World Development Indicators. Retrieved October 15, 2026, from https://data.worldbank.org/indicator/IT.NET.USER.ZS

Zhang, W., Kong, X., Braunl, T., & Hong, J. B. (2024). SafeEmbodAI: A safety framework for mobile robots in embodied AI systems (arXiv:2409.01630). arXiv. https://arxiv.org/abs/2409.01630

Zhen, H., Qiu, X., Chen, P., Yang, J., Yan, X., Du, Y., Hong, Y., & Gan, C. (2024). 3D-VLA: A 3D vision-language-action generative world model. In R. Salakhutdinov, Z. Kolter, K. Heller, A. Weller, N. Oliver, J. Scarlett, & F. Berkenkamp (Eds.), Proceedings of the 41st International Conference on Machine Learning (Vol. 235, pp. 61229–61245). PMLR. https://proceedings.mlr.press/v235/zhen24a.html

Zitkovich, B., Yu, T., Xu, S., Xu, P., Xiao, T., Xia, F., Wu, J., Wohlhart, P., Welker, S., Wahid, A., Vuong, Q., Vanhoucke, V., Tran, H., Soricut, R., Singh, A., Singh, J., Sermanet, P., Sanketi, P. R., Salazar, G., . . . Han, K. (2023). RT-2: Vision-language-action models transfer web knowledge to robotic control. In J. Tan, M. Toussaint, & K. Darvish (Eds.), Proceedings of The 7th Conference on Robot Learning (Vol. 229, pp. 2165–2183). PMLR. https://proceedings.mlr.press/v229/zitkovich23a.html


[TABLE]

System | Slow (high-level) output | Fast (low-level) mechanism and planner | Relation to options A, B, C

PlaNet (Hafner et al., 2019) | None (single level) | Online latent planning; CEM | Source of the fast-loop planner

Director (Hafner et al., 2022) | Latent goal every 8 steps | Worker policy; actor-critic in imagination | Close to A; no language

DreamerV3 (Hafner et al., 2025) | None (single level) | Learned actor; no CEM | Possible world-model backbone

TD-MPC2 (Hansen et al., 2024) | None (single level) | Latent MPC with value; MPPI | Alternative fast loop

UniPi (Du et al., 2023) | Generated video plan | Inverse dynamics; no latent planner | Close to C (video)

SuSIE (Black, Nakamoto, et al., 2024) | Edited goal image | Goal-conditioned policy | Essentially C

HiP (Ajay et al., 2023) | Language, then video plan | Inverse dynamics; no latent planner | Language plus C-like plan

SayCan (Ahn et al., 2022) | Skill chosen in language | Pretrained skills | Language interface

3D-VLA (Zhen et al., 2024) | Goal image or point cloud, action tokens | Same model | C inside one model

Hi Robot (Shi et al., 2025) | Atomic language commands | π0 VLA policy | Language interface

GR00T N1 (NVIDIA et al., 2025) | VLM tokens at 10 Hz | Action module at 120 Hz | Wide latent, trained end to end

Helix (Figure AI, 2025) | One latent vector at 7–9 Hz | 80M policy at 200 Hz | Closest to A and B

This paper | Bounded subgoal message | LWM planner, every step; CEM or alternatives | Compares A, B and C under link loss


[TABLE]

Configuration | Bytes per step | kbit/s | Share of 256 kbit/s link (%)

M1, raw frame every step | 154,742 | 12,379 | 4,836

M1, JPEG frame every step | 10,853 | 868 | 339

M2, keyframe every 5 steps | 2,181 | 174 | 68.1

M2, keyframe every 10 steps | 1,090 | 87.2 | 34.1

M2, keyframe every 100 steps | 109 | 8.72 | 3.4

M3, both loops on device | 0.4 | 0.03 | 0.0


[TABLE]

Condition | P1 hold | P1 zero | P2 keep | P3 stop | P4 cached

No outage | 100 | 100 | 100 | 100 | 100

10%, mean 1 s | 80 | 100 | 100 | 100 | 100

10%, mean 5 s | 80 | 96 | 100 | 100 | 100

10%, mean 20 s | 93 | 96 | 96 | 96 | 100

30%, mean 1 s | 54 | 99 | 100 | 100 | 100

30%, mean 5 s | 58 | 96 | 100 | 100 | 100

30%, mean 20 s | 77 | 87 | 88 | 88 | 100

50%, mean 1 s | 33 | 99 | 100 | 100 | 100

50%, mean 5 s | 28 | 84 | 83 | 82 | 100

50%, mean 20 s | 60 | 81 | 81 | 80 | 100

Power drop, 10 s | 7 | 89 | 100 | 100 | 100

Power drop, 20 s | 1 | 79 | 100 | 100 | 100


[TABLE]

Option | Bytes | Fast-side FLOPs | Extra parameters | Training needs | Interpretability | Error (m)

A, shared latent | 64 | 0 | 0 | Latent-space training | Low | 0.0006

B, learned mapping | 16 | 5,312 | 2,080 | Paired data for the map | Low | 0.0076

C, goal image | 220 | 24,576 | 0 | Goal-image generator | High | 0.0057


[TABLE]

VLA size | U FLOPs per step | T/U, small CEM | T/U, medium CEM | T/U, large CEM | U weight traffic (GB/s)

0.03B | 1.77 × 1010 | 1.36 | 7.22 | 42.65 | 2.4

0.1B | 5.90 × 1010 | 0.48 | 2.23 | 12.86 | 8.0

0.5B | 2.95 × 1011 | 0.17 | 0.53 | 2.65 | 40

2B | 1.18 × 1012 | 0.12 | 0.20 | 0.74 | 160

7B | 4.13 × 1012 | 0.10 | 0.13 | 0.28 | 560