# AfriCoT-VLA: Project Context

Context for building the AfriCoT-VLA traffic-control system. Exported from the "Unilag Traffic Dissertation" project memory on 6 October 2026.

## Author

- Temitope W. Ariyo, Machine Learning Research Group, Department of Artificial Intelligence and Robotics, Faculty of Computing and Informatics, University of Lagos.
- Supervisor: Dr. Fasina.
- There are two related works:
  - the dissertation (AfriCoT-VLA)
  - a journal paper co-authored with Ebun P. Fasina

## Dissertation: AfriCoT-VLA

- Title: "A Traffic Control System for Sub-Saharan African Cities Combining CoT, VLAMs and Latent World Models".
- Goal: AI traffic signal control designed around Sub-Saharan African (SSA) constraints:
  - mixed informal transit (okadas, kekes, danfo, matatus, boda-boda)
  - intermittent connectivity and power
  - limited sensors
  - regulatory explainability
- Components:
  - Latent World Model (LWM)
  - Chain-of-Thought (CoT) reasoning
  - Vision-Language-Action Model (VLAM)
- CoT will also be added to the journal paper later.

## Journal paper

- Title: "Toward a Unified Framework of Vision-Language-Action Models and Latent World Models for Low-Resource, Infrastructure-Constrained Environments in Sub-Saharan Africa".
- Hierarchical two-timescale architecture, approved by the supervisor as Option 4:
  - a slow, infrequent loop generates compact subgoals
  - a fast, continuous loop does Cross-Entropy Method (CEM) imagination-based planning with a latent world model
- Treats SSA infrastructure gaps as design inputs.
- Fully drafted. Ebun P. Fasina's email is still a placeholder.

## Physical setting

- As Temitope described it: four cameras at a T-junction scan approaching cars and coordinate with each other, and a timer tells each wing to stop, get ready or go.
- The junctions in the target area are never far from one another.
- Proposed camera layout: three cameras on the approaches, plus one overseeing the junction box to catch stalled vehicles.
- Each junction has an edge computer connected to the existing signal controller.

## Proposed architecture

These are proposals, not yet confirmed by the supervisor.

- **Edge perception (on site).** A lightweight detector classifies the vehicle classes and pedestrians. It outputs per-approach queue length, counts and occupancy. Raw video never leaves the site.
- **Fast loop (on site, every few seconds).**
  - The LWM predicts how queues will evolve.
  - The CEM planner picks a phase timing.
  - It always runs locally and is never routed elsewhere.
- **Slow loop (every few minutes, or on unusual events).**
  - The VLAM with CoT reads keyframes plus context: time, market days, events, incidents, weather.
  - It outputs a subgoal with a written justification.
- **Subgoal interface.**
  - A compact vector of cost weights and constraint bounds for the CEM objective, e.g. per-approach queue priority, pedestrian weight, max wait, transit priority.
  - The VLAM's "action" is the subgoal, not a phase command.
  - The exception is emergency-vehicle priority, which can override directly.
- **Safety shield.**
  - A rule-based layer between the planner and the controller.
  - Enforces minimum green, amber, all-red clearance and pedestrian crossing time, plus a spillback rule: don't release traffic towards a full downstream approach.
  - Nothing learned can bypass it.
- **Explainability log.** Every decision is timestamped with its CoT trace and the conditions that triggered it, for LASTMA and Ministry of Transportation audit.
- **Coupling, not fusion.**
  - The VLAM and the LWM stay separate models linked only by the subgoal.
  - Full VLA/world-model unification is an open research problem. Coupling is a deliberate choice under SSA compute and connectivity limits.

### Degradation tiers

| Condition | Behaviour |
|---|---|
| Full connectivity | Slow loop runs a large VLAM in the cloud |
| Weak connectivity | Small VLM on the edge, or a cached time-of-day subgoal schedule |
| No connectivity | Fast loop continues on the last subgoal |
| System fault | Fixed-time signal plan |

### Capability-aware coordinator

- Rule-based, not learned.
- Routes only slow-loop tasks, based on connectivity, available compute and scene novelty. A rise in world-model prediction error signals heavier reasoning is needed.
- A routine scene goes to the edge VLM. An unusual scene goes to the cloud VLAM when connected. Emergencies trigger a direct override.

### Tiered communication

1. 4G or fibre: everything except raw video.
2. SMS over GSM: alerts and subgoals only, when data is down.
3. Store-and-forward: logs and training data, sent later.
4. Junction-to-junction mesh relay over Wi-Fi or LoRa: the main offline path, since junctions are close.
5. Satellite: optional, for critical alerts only.

All incoming messages must be cryptographically signed. Messages can only change priorities; they can never bypass the safety shield.

### Multi-junction (junctions are close)

- World models take neighbours' outflows as inputs.
- Neighbours share queue and plan data over the mesh, so green waves keep working offline.
- An optional shared cluster edge server runs the small VLM, while each junction keeps its own fast loop.

## 8-layer deployment framework (from Dr. Fasina)

The layer structure comes from the supervisor. During the class session on 27 July 2026, Dr. Fasina typed it into DeepSeek on their shared screen (see preview9.webp and preview16.webp). Credit it to them.

Their wording: "Design a cloud-based 8-layer framework for AfriCoT-VLA."
1. Sensor Layer from Cameras and actuators for traffic lights
2. Network Connection for compressed video from cameras over the internet to the cloud
3. Data store
4. Model layer for CoT, LWMs, VLAM
5. Explainability Layer
6. Service Layer
7. AI Agent Layer
8. Autonomous Agentic

**Proposed refinements** (Temitope's, not yet confirmed):
- Layer 3: a hot window plus cold history.
- Layer 4: the two-timescale design.
- Layer 6: decision, query, override and health APIs.
- Layer 7: corridor coordination.
- Layer 8: plan proposals, what-if simulations and human sign-off.
- Any layer above 4 can fail, and the system falls back to fixed-time control.
- Layer 2 is the real bottleneck.
- Layer 5 is a deployment gate.

**Tension to resolve.** The supervisor framed the framework as cloud-based, with compressed video going to the cloud. The proposed architecture keeps raw video on site and runs the fast loop locally. A possible reconciliation:
- keep the 8 layers
- treat the cloud as the full-connectivity tier
- have Layer 2 carry compressed keyframes for the slow loop rather than continuous video

## Development plan

- **Scope:** SUMO simulation. Proposed main setting: a 2–3 junction Lagos corridor rather than a single isolated junction. No physical field trial in the dissertation.
- **Scenarios:** normal peak, market day, incident, network outage. Include motorcycle lane-splitting.
- **Baselines:**
  - fixed-time
  - camera-count-plus-timer
  - max-pressure
  - a deep RL controller
  - LLMLight
- **Metrics:** average travel time (ATT), average queue length (AQL), average waiting time (AWT), throughput.
- **Ablations:**
  - without the slow loop
  - without the world model
  - under connection loss
  - with vs without neighbour information
  - fixed vs capability-aware routing
- **Perception in simulation:** SUMO ground truth plus noise. The detector can be tested separately on real Lagos footage.
- **Integration:** control SUMO through TraCI.
- **Deployment roadmap** (described, not built): Jetson-class edge hardware with hardware-in-the-loop testing, then shadow mode, then a supervised pilot with override, then live operation.

## Model constraints

- Only open-source, open-weight models.
- Do not train foundation models from scratch.
- Candidates:
  - world model: DreamerV3, V-JEPA 2
  - VLA: OpenVLA, Octo, π0
  - reasoning: DeepSeek-R1
  - traffic LLM baselines: LLMLight, LightGPT
  - offline RL: CQL, OffLight
- Not adoptable, because they are not open-weight: Genie/Genie 2, RT-2.
- Citations: ECoT (arXiv:2407.08693) and InstructVLA (arXiv:2507.17520) for CoT plus control.

## Class-session material (Dr. Fasina's session, 27 July 2026)

The project began as a class exercise. Students prompted Gemini, Claude and DeepSeek to describe a project combining CoT, VLAMs and LWMs for a resource-constrained problem in Sub-Saharan Africa, each choosing a sector. Temitope chose traffic control. The responses added the following.

**Extra candidate models**
- Reasoning:
  - Qwen3 in thinking mode, which is multilingual
  - DeepSeek-R1 distills (R1-Distill-Qwen-14B/32B)
- VLA:
  - OpenVLA-OFT, which has a continuous action head and LoRA adapters and is faster at inference
  - π0.5
- World model:
  - TD-MPC2, which is lighter than V-JEPA 2
  - NVIDIA Cosmos, for training-time simulation only, not edge deployment

**Three-tier placement (from the Claude response)**
- The LWM runs on the junction's edge device.
- The VLAM runs on a regional edge server and selects control actions.
- CoT runs in a cloud control centre and coordinates the corridor. It uses retrieval over incident logs and event calendars.
- An operator dashboard has an SMS/USSD fallback.

**"Frugal-first" pairing**
- DreamerV3 or TD-MPC2 as the edge LWM, with OpenVLA-OFT on the regional server.
- V-JEPA 2 and π0 are reserved for offline training and simulation.

**DeepSeek's Layer 5 (explainability) ideas**
- A counterfactual "what-if" generator, using the LWM.
- Grad-CAM or attention heatmaps overlaid on camera feeds.
- A translator into local languages: English, Swahili, French, Pidgin.
- An immutable audit log recording the timestamp, frame hash, CoT trace, action taken, and predicted versus actual outcome.
- A confidence scorer that flags decisions below 0.7 for manual review.
- CoT hosted through TGI (Text Generation Inference).

**Cautions**
- These names from the responses are unverified, so check them before citing:
  - "LeWM" (the claim of about 15M parameters is also unverified)
  - "VLA-JEPA"
  - "Lota-Carinae"
  - "AfriSCOP-CC"
- DeepSeek presents "interpretable reasoning with precise control" as a quote, but it is a paraphrase.
- In those responses the VLAM commands the signals directly. The current design instead has the VLAM set priorities for the on-site planner.

## Writing conventions (dissertation and paper)

- Use proposal verbs ("is designed to", "is intended to support"), not "demonstrates", "achieves" or "enables".
- Journal-style flowing prose. No em-dashes.
- Cross-references in natural phrasing, not "Section N".
- Abstracts are 150–300 words.
- APA formatting, Times New Roman, one column, justified.
- Figures are made with Python/matplotlib, with no figure numbers baked into the images.

## Open questions for the supervisor

- Reusing the journal paper's architecture core in the dissertation.
- Junction configuration.
- Simulation-only evaluation.
- Naming a reference Lagos junction.
- Corridor scope.
- Adding the coordinator and tiered communication.
- The 8-layer framework is cloud-based, with video going to the cloud. How does that fit with keeping raw video on site and the fast loop local?

## Pending

- Update the architecture PDF with the corridor scope, coordinator and tiered communication.
- Add a timeline once the submission/defence date is known.
- Write dissertation Chapters 2–5.
- Replace Fasina's email placeholder in the paper.
