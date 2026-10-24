TOWARD A UNIFIED FRAMEWORK OF VISION-LANGUAGE-ACTION MODELS AND LATENT WORLD MODELS FOR LOW-RESOURCE, INFRASTRUCTURE-CONSTRAINED ENVIRONMENTS IN SUB-SAHARAN AFRICA

TEMITOPE W. ARIYO; EBUN P. FASINA

temitopeariyo6@gmail.com, efasina@unilag.edu.ng

Faculty of Computing and Informatics, Department of Computer Science,

University of Lagos

Abstract

Artificial intelligence is moving away from systems that merely perceive their surroundings toward systems that predict what will happen next and act on that prediction. Vision-Language-Action models and world models are the two paradigms carrying this shift forward, yet they have largely developed on separate tracks: the former specializes in turning multimodal input into physical action, the latter in simulating plausible futures for planning. No architecture in the current literature brings the two together in a way that is both principled and truly unified. A second gap compounds the first. Almost everything published on these paradigms assumes conditions that simply do not hold across much of sub-Saharan Africa: dependable connectivity, generous compute budgets, and large curated datasets. Mobile internet penetration across the region sits at 27%, the continent hosts under one percent of global data-centre capacity, and more than 560 million people still lack reliable electricity. This paper reviews the literature on both paradigms published between 2023 and 2026 and proposes a hierarchical, two-timescale architecture that couples a Vision-Language-Action model with a latent world model. A slow, infrequently-running loop interprets language and visual context to produce a compact subgoal; a fast, continuously-running loop plans and executes action toward that subgoal through imagination-based rollouts in latent space. Only the subgoal itself crosses between the two loops. It is never raw language or raw pixels, a constraint intended to keep the system's cross-component communication small enough for constrained bandwidth. The paper is candid about what remains unresolved: the precise form of the subgoal interface is identified as the architecture's central open question, alongside five broader challenges facing the field: data inefficiency, weak generalization, unresolved safety guarantees, computational cost, and architectural fragmentation. No empirical validation is offered here; what is offered is a literature-grounded design and a research agenda for taking it further, aimed squarely at advancing embodied artificial intelligence in low-resource settings such as sub-Saharan Africa.

Keywords: embodied AI, vision-language-action models, latent world models, cross-modal alignment, hierarchical control, closed-loop decision-making, sub-Saharan Africa, low-resource AI

INTRODUCTION

Artificial intelligence has spent most of the last decade getting better at describing the world. It is only recently that it has begun getting better at acting in it. Before Vision-Language-Action models existed in anything like their current form, robotics and AI research tended to progress along separate, largely non-communicating tracks. One group worked on visual perception, another on language understanding, a third on control and actuation. Each of these lines produced systems that performed respectably within their own narrow remit, but the lack of integration between them showed up exactly where it mattered most: in cross-modal reasoning and in the ability to generalise to environments that had not been anticipated at design time (Sapkota et al., 2025).

The rise of foundation models changed the terms of the problem. Large-scale multimodal pretraining made it possible to learn representations that hold together across different kinds of data rather than treating vision and language as separate problems to be solved and then stitched together afterward (Bommasani et al., 2022). Transformer architectures, in particular, gave rise to vision-language models capable of real cross-modal reasoning: answering questions about an image, following an instruction, carrying on a multimodal dialogue (Radford et al., 2021; OpenAI, 2023). What these systems could still not do, however, was act. A model that can describe a scene with impressive fluency but cannot reach into that scene and change it is, for the purposes of embodied intelligence, still only half a system.

This is the gap that motivated the shift toward embodied AI: agents built to perceive, reason, and act within environments that respond to what they do, learning from the resulting feedback rather than from a fixed dataset alone. Vision-Language-Action (VLA) models emerged directly out of this shift, folding perception, language understanding, and decision-making into a single trainable architecture. Systems such as RT-2 (Brohan et al., 2023) and PaLM-E (Driess et al., 2023) showed, convincingly, that a natural-language instruction could be translated into an executable robotic action, not as a scripted response to a fixed command set but as something closer to genuine instruction-following. It is a real step toward general-purpose embodied intelligence, even if, as later sections of this paper will argue, it is only half of what such intelligence eventually requires.

That progress, however, has taken place almost entirely inside a fairly narrow envelope of assumptions. The datasets are large. The compute is abundant. The connectivity linking a robot to whatever backend infrastructure trains or runs its models is, by and large, taken for granted. These assumptions are reasonable inside the research institutions and well-resourced labs where this work is produced. They are not reasonable across most of sub-Saharan Africa, where mobile internet penetration remains at 27 percent despite far higher network coverage, where the entire continent hosts under one percent of the world's active data-centre capacity, and where more than 560 million people still lack access to reliable electricity (Africa Data Centres Association [ADCA], 2026; GSMA, 2024; Tracking SDG7, 2025). 

Figure 1 sets these figures against the high-resource conditions the current literature quietly assumes.

Figure 1: Infrastructure gap between the resource conditions assumed by current VLA and world-model research and the reported conditions across sub-Saharan Africa. Data drawn from GSMA (2024), Africa Data Centres Association (2026), and Tracking SDG7 (2025).

These are not minor footnotes to an otherwise complete research picture. They describe the operating conditions of a large and rapidly urbanising share of the world's population, including the residents of cities that are already, right now, piloting AI-assisted traffic and mobility infrastructure under exactly these constraints. Nairobi's Kenya Urban Roads Authority has deployed camera-based adaptive signal control across roughly 125 intersections while openly acknowledging unstable connectivity and power supply as live operational problems, not hypothetical ones. Lagos has piloted AI-driven traffic cameras at several major intersections for the same purpose. What the existing VLA and world-model literature offers these deployments, at present, is very little: no published architecture in this space has been designed from the ground up around intermittent connectivity, scarce compute, and unreliable power, as opposed to being designed under high-resource conditions and only afterward described as potentially useful elsewhere (Liu et al., 2026).

World models fill in half of the picture VLA models leave open. Where a VLA model maps input to action, a world model tries to anticipate what a given action would actually lead to, building an internal, learned simulation of the environment's dynamics and using it to plan several steps ahead rather than reacting one step at a time (Hafner et al., 2025; Schrittwieser et al., 2024). This predictive capacity is precisely what reactive VLA systems lack. But world models, too, have mostly been developed on a separate track from VLA models, optimised for prediction and simulation without much attention to the multimodal grounding problem VLA research has spent years working through (Feng et al., 2025; Xu, 2025). The result is a field with two mature but largely disconnected paradigms: strong perception-to-action mapping on one side, strong predictive planning on the other, and no widely accepted architecture that brings the two together as a single coherent system rather than two systems awkwardly bolted onto each other.

This paper takes on both gaps together, rather than treating the infrastructure question as a footnote to an otherwise conventional VLA-world-model integration paper. Five questions guide the work that follows: how VLA models evolved out of earlier vision-language systems and what architectural advances made action generation possible; what role world models play in prediction and long-horizon planning; what the central obstacles are to combining perception, prediction, and action into one system; what architectural principles could actually achieve that combination; and, specifically, what design properties would allow such an architecture to keep functioning under the bandwidth, compute, and power constraints typical of sub-Saharan African deployment settings.

The discussion that follows works through the literature on VLA models, world models, and the thin body of work addressing infrastructure-constrained AI, before laying out the proposed architecture in detail, then turning to applications, open challenges, and directions for future work, and closing with a final synthesis. Two things should be said plainly at the outset, so that nothing that follows is mistaken for more than it is: this paper does not report empirical validation of the architecture it proposes, and it does not address hardware design or low-level robotic control. What it offers instead is a design, argued for from the literature, together with an honest account of what that design has not yet earned the right to claim.

LITERATURE REVIEW

Multimodal AI has not arrived at its current form all at once. Early systems handled vision and language through separate pipelines, stitching the two together through comparatively shallow late-fusion techniques that never achieved much semantic depth (Lin, 2025).

The transformer changed that calculus by making unified representation learning across text and images practical at scale, and foundation models trained on correspondingly large datasets pushed the resulting systems toward genuine generalisation, handling a range of multimodal tasks with little or no task-specific retraining (Radford et al., 2021; OpenAI Team, 2024). 

Between 2023 and 2026, this trajectory extended further still, tying multimodal understanding directly to decision-making and physical execution (Feng et al., 2025). The underlying arc of perception, then reasoning, then action is now widely treated as the conceptual backbone of embodied AI research, and it is the arc this paper follows as well.

I. Vision-Language Models

Vision-language models learn joint representations of images and text, and the strongest of them, CLIP (Radford et al., 2021), Flamingo, and GPT-4V (OpenAI Team, 2024), perform well across captioning, visual question answering, and multimodal dialogue. Their strengths are real: robust multimodal representation learning, good generalisation across tasks, and the ability to scale with data. Their limitation is equally real and, for the purposes of embodied AI, more consequential: they do not act. A vision-language model can describe a scene in rich detail and still have no way to change it. This is not a minor gap to be closed with a small architectural patch; it is the reason Vision-Language-Action models exist at all (Li et al., 2025).

II. Vision-Language-Action Models

VLA models extend vision-language models with the missing piece: action generation. RT-2 (Brohan et al., 2024), PaLM-E (Driess et al., 2023), and VIMA (Jiang et al., 2023) each demonstrate, in different ways, that multimodal input can be mapped directly to an executable control policy. RT-X (Zitkovich et al., 2025) and SMART (Sun et al., 2024) push the same idea toward broader cross-task generalisation.

Brohan et al. (2024) show, in particular, that a VLA model can transfer knowledge learned from web-scale, non-robotic data into robotic tasks, meaningfully improving generalisation in the process, a result with real implications for any setting where large-scale robotic demonstration data is scarce, since it suggests the gap can be partly closed by better transfer rather than by more demonstrations alone. Driess et al. (2024) extend this by showing how embodied multimodal models bridge perception and control more broadly, while Reed et al. (2023) and Shridhar et al. (2023) contribute generalist agents and multi-task transformer policies of their own.

For all that progress, VLA models remain, overall, reactive. They are good at mapping a given input to an appropriate action; they are considerably less good at reasoning about what that action will actually lead to several steps down the line, and they tend to need a great deal of training data to reach even that level of reactive competence (Brohan et al., 2024; Li et al., 2025). It is also worth noting, because it will matter later in this paper, that every one of the systems named above was developed and evaluated inside high-bandwidth, high-compute research environments. None of the published literature on VLA models examines how their training or inference costs would translate to intermittent-connectivity, edge-only deployment. OpenVLA (Kim et al., 2024) is a partial exception: it supports quantisation, which at least opens a plausible path toward lighter-weight deployment, even though the paper itself was not written with that deployment context specifically in mind.

III. World Models

World models take on half of the problem VLA models leave open: prediction. Rather than mapping input directly to action, a world model learns an internal representation of how the environment behaves and uses that representation to simulate, or “imagine,” plausible futures before committing to a real action (Hafner et al., 2025; Schrittwieser et al., 2024). 

Hafner et al. (2025) introduced DreamerV3, a single configuration that outperforms specialised alternatives across more than 150 distinct tasks, a result achieved by learning an environment model and refining behaviour through imagined rollouts rather than costly real-world trial and error. MuZero-style approaches (Schrittwieser et al., 2024) go a step further, showing that competent planning is achievable without any explicit, hand-specified model of environment dynamics at all. More recent work has begun conditioning these predictive dynamics on language, extending world models' generalisation beyond what purely visual conditioning allows (Wang et al., 2025; Wu et al., 2025).

The practical significance of this predictive capacity is best illustrated by DayDreamer (Wu et al., 2023), in which a quadruped robot 

learned to walk from roughly one hour of real-world interaction, with no simulator involved at all. That is an extraordinary data-efficiency result by the standards of most reinforcement learning, and it is exactly the kind of result that matters most in settings where large-scale data collection is either prohibitively expensive or, as in much of sub-Saharan Africa, simply not available at the scale conventional training pipelines assume.

IV. The Integration Problem

Bringing VLA models and world models together is widely recognized as a genuine research frontier, not a resolved implementation detail.

Several recent papers report that hybrid systems combining multimodal perception with predictive dynamics do improve robustness and generalization over either paradigm alone (Gao et al., 2024; Zitkovich et al., 2025), and Xu (2025) goes further, arguing that a unified world model should be treated as the cornerstone around which perception, reasoning, and decision-making are organized, rather than one module among several bolted together after the fact.

Table 1 and Table 2 summarize how the three paradigms discussed so far compare on core capabilities and architectural properties.

Note: Adapted from Lin (2025), Li et al. (2025), Gupta et al. (2024), Xu (2025), and Feng et al. (2025).

Note: Adapted from Lin (2025), Li et al. (2025), Gupta et al. (2024), and Xu (2025).

Despite this recognition, building an integrated system remains hard, and the difficulty is not merely a matter of insufficient engineering effort.

Architectural complexity, computational overhead, and the challenge of keeping perception and prediction components meaningfully aligned with one another are all real obstacles, and none of the papers reviewed here treat them as anything less. 

What is largely missing, though, is any discussion of how these obstacles interact with deployment constraints: the additional bandwidth required to move data between perception and prediction components, or the on-device memory needed to run two learned models rather than one, in a setting where memory and bandwidth cannot simply be assumed to be available.

V. Synthesis and the Gap This Paper Addresses

Pulling the threads above together, five gaps recur across this literature. Fragmentation is the most cited: most systems treat perception, action, and prediction as separate components rather than parts of one coherent architecture (Feng et al., 2025; Zhu et al., 2025), and the inefficiencies that follow from that fragmentation are well documented. Generalization is weak: models trained in one setting routinely fail in a superficially similar but structurally different one, a pattern traced back to reliance on surface correlations rather than any deeper causal understanding (Li et al., 2025). Data remains expensive: training paradigm at scale requires more demonstration data than most real-world settings can supply, particularly where interaction with the physical world is costly (Brohan et al., 2024). Integration mechanisms remain ad hoc: no standardized architecture yet exists for combining multimodal perception with predictive modelling in a principled way (Xu, 2025). And deployment safety remains an open problem: reliability and robustness concerns persist wherever these systems are asked to operate outside tightly controlled conditions (Yang et al., 2024; Zhang et al., 2024; Zhao et al., 2026).

A sixth gap runs alongside these five, largely unaddressed by the literature surveyed above: nearly every architecture discussed in this section, VLA model or world model alike, was built, trained, and evaluated under stable connectivity, generous compute, and carefully curated data. The closest thing to an exception is Liu et al. (2026), who frame embodied AI research in the Global South as fundamentally a problem of infrastructure (manpower, power, connectivity) rather than one of architecture, which leaves entirely open the separate question this paper takes up: whether the architecture itself, not merely its deployment environment, should be designed differently for these conditions. No technical work identified in the course of this review proposes a VLA–world-model architecture whose design actually follows from sub-Saharan African constraints, as opposed to simply being motivated by reference to them after the fact.

This paper is positioned at the intersection of all six gaps. The field's progression is clear enough on its own terms. Vision-language models provide understanding, VLA models add action, world models add prediction, but no existing work combines all three into one architecture, and none does so with infrastructure constraints treated as a genuine input to the design process rather than an afterthought appended to the conclusion. 

The remainder of this paper proposes such architecture and evaluates its fit to bandwidth-, compute-, and power-constrained deployment throughout, not only in the paragraphs that introduce it.

PROPOSED ARCHITECTURE

Rather than a single pipeline that carries perception through to action in one continuous pass, the architecture proposed here is built from two coupled control loops running at different speeds:

1. A Slow Loop (VLAM — High Level, Infrequent)

2. A Fast Loop (World Model — Low Level, continuous) 

A slow loop, governed by a Vision-Language-Action model, is responsible for working out what the agent should be trying to achieve. A fast loop, governed by a latent world model, is responsible for working out how to get there, moment to moment, through imagination-based planning.

Figure 2 shows the two loops and the single narrow channel connecting them.

Figure 2

Figure 2: Proposed two-timescale architecture. The slow loop (left) grounds language and visual context into a compact subgoal; the fast loop (right) plans and executes action toward that subgoal through latent-space imagination. Only the subgoal crosses between the two loops.

This split is not simply a modelling convenience. It is a direct response to the integration ambiguity identified above: the absence, across the field, of any principled account of how language-based reasoning and latent-space reasoning should divide the labour between them. It is also, just as importantly, a direct response to the bandwidth constraint motivating this paper. Because the two loops exchange only a compact intermediate representation rather than raw language or raw pixels, the architecture's cross-component communication cost is minimized because of the design itself, rather than as a happy side effect discovered afterward.

I. The Slow Loop: VLA Subgoal Generation

The slow loop does not run at every timestep. It runs infrequently, triggered by a new language instruction, a periodic visual snapshot, or a sufficiently large change in scene context, and its job is to ground whatever instruction and visual context it receives into a subgoal: a compact latent target describing the intended outcome of the agent's next phase of behaviour, rather than a specific low-level action to be executed immediately.

Given a language instruction and a visual observation, the slow loop produces this subgoal using the same Vision Transformer and transformer-based language encoders already established in the VLA literature (Brohan et al., 2024; Driess et al., 2023). The subgoal it outputs is deliberately dimensioned to match the world model's own latent state space, so that it can serve directly as a planning target within that space rather than requiring a separate translation step downstream. Running infrequently and outputting only this compact target, rather than continuous raw output at every step, is the architecture's primary mechanism for bandwidth efficiency: whatever gets transmitted or computed by the slow loop is, by construction, several orders of magnitude smaller than the raw multimodal input from which it was derived, which is precisely the constraint this paper set out to address.

II. The Fast Loop: World Model Planning

The fast loop, in contrast, runs continuously, at every control timestep, and is responsible for turning the current subgoal into an actual executed action. It retains the latent state-space formulation already established in the world-model literature (Hafner et al., 2025): the latent state decomposes into a deterministic hidden component and a stochastic latent component, updated at each step from the previous state, the current observation, and the previous action.

What distinguishes planning inside this fast loop from a generic world-model planner is that it is explicitly conditioned on the subgoal handed down from the slow loop. Rather than optimising purely for a general reward signal, the planning procedure, implemented through the Cross-Entropy Method, or CEM, samples a batch of candidate action sequences, simulates each one forward through the learned dynamics model, and scores each candidate on both its predicted proximity to the subgoal in latent space and its predicted reward. The best-scoring sequences are kept, the sampling distribution is updated toward them, and the process repeats for several iterations before the loop commits to an action. Only the first action of the resulting sequence is actually executed; the loop then re-plans from scratch at the next timestep, in keeping with a receding-horizon control strategy.

Why the Cross-Entropy Method, and why latent space?

CEM is used here specifically because it does not require the scoring function to be differentiable, a real constraint in this setting, since scoring a candidate trajectory's proximity to a subgoal through a learned dynamics model does not straightforwardly produce gradients suitable for direct optimization. Planning takes place in the compact latent space rather than in raw pixel space for a related reason: CEM is an iterative, multi-sample method, and evaluating dozens of candidate trajectories per planning step would be computationally prohibitive in raw observation space on constrained hardware. It becomes tractable once each rollout operates over a latent state whose dimensionality is, by design, much smaller than the raw observation it was compressed from.

The Coupling Mechanism

The two loops communicate through exactly one channel: the subgoal itself. No raw language, no raw visual data, and no intermediate activation from the slow loop crosses into the fast loop, only the compact latent target. This is a considerably tighter constraint than the fusion strategies typical of the wider literature, which tend to combine vision, language, and latent representations at several points throughout a system rather than at one deliberately narrow interface. The constraint is imposed on purpose: it is what allows the slow loop to run infrequently, and potentially on different hardware or at a different point in a network topology, without the fast loop's real-time control requirements being affected by whatever latency the slow loop introduces.

This coupling gives the whole system a natural reading as an approximate two-level optimisation problem. The slow loop selects whichever subgoal seems most likely to serve the overall instruction across a longer horizon; the fast loop then solves a shorter-horizon problem, finding the action, at each step, that best serves that subgoal, through the CEM procedure described above, with the necessary expectations computed via the learned world model rather than through direct interaction with the real environment.

The unresolved core: the subgoal interface

This paper is candid that the subgoal representation itself, both its precise form and the mechanism by which the slow loop is trained to produce something the fast loop can actually use as a meaningful planning target, is the architecture's central open technical question, not a solved implementation detail dressed up as one. Three candidate approaches seem worth pursuing in future work, though none is adopted here as a final answer. The first would train the slow loop to output a target directly within the fast loop's existing latent space, which requires the two components to share a representational space from early in training. The second would introduce a separate, smaller mapping function that translates the slow loop's output into a fast-loop-compatible target, trained jointly with both components. The third would define the subgoal not as an abstract vector at all but as a predicted future observation, a predicted image, or a predicted state description, trading away some compactness in exchange for interpretability. This paper does not resolve which of the three is preferable and regards that question as the single most consequential one facing any future implementation of the architecture proposed here.

Training Considerations

Because the two loops operate at different timescales and produce structurally different kinds of output, this paper proposes that they be trained largely separately rather than end-to-end as a single system. The world model's encoder, dynamics model, and reward estimator are trained first, on observed transitions, using the standard three-term objective, reconstruction loss, a Kullback-Leibler regularization term, and reward prediction, so that a stable latent space exists before the slow loop is introduced into the picture at all. The slow loop is then trained to produce subgoals evaluated against this now-fixed world model, using task-completion signal as the training target for subgoal generation.

This staged approach is proposed specifically to avoid the training instability a single combined objective would likely introduce, given how much the two loops differ in input type, output type, and update frequency. That said, this paper does not empirically verify the staging's actual effect on convergence or stability. That verification, like the subgoal interface question above, remains a priority for future implementation work rather than something this paper claims to have already established.

Relation to Existing Systems

The fast loop's use of latent-space CEM planning aligns directly with DreamerV3 (Hafner et al., 2025) and MuZero-style approaches (Schrittwieser et al., 2024). The slow loop's language-grounding function draws on the same perception and language-encoding mechanisms already established by PaLM-E (Driess et al., 2023) and VIMA (Jiang et al., 2023). What actually distinguishes this architecture from its precedents is not either loop taken individually, both build on well-established components, but the explicit temporal and representational separation between them. Hierarchical control of this general kind is a well-established pattern in robotics and reinforcement learning more broadly; what appears not to have been proposed before, at least within the literature reviewed for this paper, is its specific application to the VLA–world-model integration gap identified earlier.

By design, this architecture is intended to support closed-loop, goal-conditioned decision-making while keeping cross-component communication substantially lower than systems that fuse language, vision, and latent representations continuously throughout their pipeline. This paper does not present empirical evidence for that claim, nor for the architecture's generalisation, safety, or overall performance more broadly. What is offered instead is the design itself, together with the reasoning behind it, as a proposal for future implementation and testing rather than a finished or validated system.

APPLICATIONS

An architecture of this kind is only interesting to the extent it connects to something a reader can picture happening. Several application domains illustrate what the coupling between a VLA model and a world model would concretely change, relative to systems that use one paradigm without the other.

In robotic manipulation, combining perception-and-action capability with predictive planning moves a system from purely reactive manipulation toward something closer to anticipatory manipulation. RT-2 (Brohan et al., 2024) and VIMA (Jiang et al., 2023) already demonstrate strong perception-to-action mapping; a world-model addition of the kind proposed here would let such a system simulate several candidate grasp trajectories before committing to one, selecting whichever is least likely to destabilize a fragile object, rather than discovering the mistake only after the fact. This matters most in domestic assistance settings, helping an elderly or disabled user, say, where the tolerance for trial-and-error learning is genuinely low.

In autonomous navigation, a vehicle or mobile robot must continuously predict how its surroundings will evolve over the next several seconds, not merely perceive them as they are right now. MuZero-style planning (Schrittwieser et al., 2024) shows that useful decision-making is achievable without any hand-coded model of environment dynamics at all; applied to navigation, the natural extension is a system that anticipates the likely paths of pedestrians and other vehicles well enough to plan around them, rather than reacting only once an obstacle is already directly ahead.

In human-robot interaction, a VLA model's language grounding already makes for more natural interaction than specialized control interfaces allow. Adding a world model extends this further: an agent can reason, before acting, about the likely downstream consequences of a request, recognizing, for instance, that a particular instruction might place a bystander at risk, and either flagging the concern or seeking clarification rather than proceeding blind. Current VLA-only systems, by contrast, typically execute whatever the most probable interpretation of an instruction happens to be, without simulating what following it would actually lead to.

In industrial automation, the same perception-prediction-action structure could support adaptive process control on a production line, adjusting behaviour in anticipation of predicted material variability, rather than only reacting once a defect has already occurred. This application is worth flagging as more constrained than the others, though: existing certified safety standards for collaborative robotics, such as ISO 10218 and ISO/TS 15066, were built around traditional, formally verifiable control systems, and there is not yet an established certification pathway for the kind of learned, non-deterministic decision-making this architecture proposes.

The application most directly motivating this paper's design choices, however, is urban traffic management in infrastructure-constrained cities. Several sub-Saharan African cities are already deploying AI-assisted traffic infrastructure under precisely the resource constraints this architecture was designed around. Nairobi's Kenya Urban Roads Authority runs a networked, camera-based adaptive signal control system across roughly 125 intersections and openly names unstable connectivity and power supply as ongoing operational challenges rather than solved problems. Lagos has piloted AI-powered traffic cameras at several major intersections for adaptive control and enforcement. Neither system currently incorporates predictive, imagination-based planning; both operate largely reactively, adjusting signal timing in response to congestion that has already been detected rather than congestion anticipated several steps ahead. A system built on the architecture proposed above, grounding traffic-camera input and operator instructions through its slow loop, while predicting near-future traffic flow through the fast loop's latent-space rollouts, would extend deployments like these from reactive control toward anticipatory management, while staying within their existing bandwidth and compute envelopes precisely because only the compact subgoal, not raw camera feed or raw operator instruction, needs to reach whatever component is performing real-time control. This example is worth dwelling on because it illustrates the paper's broader argument in miniature: any system proposed for this context must tolerate exactly the intermittent connectivity and modest compute budgets these real deployments already report, not as an afterthought but as a starting condition.

CHALLENGES AND LIMITATIONS

Even setting aside the specific proposal made above, the field this paper sits within faces a set of challenges that are well documented, largely unresolved, and worth stating plainly rather than gestured at.

I. Data inefficiency and scalability

Training a VLA model or a world model to a useful standard of competence still requires an enormous amount of data. RT-2 was trained on millions of robotic demonstrations and still struggles with tasks that fall meaningfully outside its training distribution (Brohan et al., 2024). This is a limitation everywhere, but it becomes especially acute wherever real-world interaction is slow, expensive, or physically risky, and teleoperated demonstration collection is a well-documented bottleneck across the field generally. In infrastructure-constrained regions the problem compounds further still: it is not simply that demonstration collection is expensive in the way it always is, but that the underlying data infrastructure needed to collect and curate such datasets at any scale, reliable sensors, consistent connectivity for uploading what they capture, adequate storage, is itself scarce, which makes the cost difference a difference in kind rather than only in degree.

II. Generalization gap

Existing models generalize poorly to environments that differ from their training distribution, even where the difference looks minor to a human observer. A manipulation policy trained in a curated kitchen setting will often fail in a warehouse, even on a task a person would consider a straightforward variation of what it already knows. The literature traces this to an over-reliance on surface-level statistical correlation rather than any deeper causal understanding of why a given action produces its observed effect (Gupta et al., 2024; Li et al., 2025): the model has learned that certain visual patterns tend to co-occur with certain successful actions, without learning the underlying mechanism connecting them, and so the pattern breaks the moment the surface appearance shifts even slightly.

III. Safety and robustness

Deploying embodied AI in unstructured, real-world environments raises safety questions that remain largely unresolved at any formal level. Current systems lack rigorous behavioural guarantees, which makes them unpredictable specifically in edge cases, situations rare or unusual enough that they were poorly represented, or entirely absent, in training data. This matters most in human-robot interaction, where a behavioural failure could mean physical injury (Yang et al., 2024; Zhang et al., 2024; Zhao et al., 2026). In the mixed formal and informal traffic environments common across many sub-Saharan African cities, where pedestrians, motorcycles, informal transit vehicles, and private cars routinely share space without the strict lane discipline many training environments assume, such edge cases are not statistically rare exceptions at all, they are a routine feature of the operating environment, which means safety guarantees developed and validated against more structured traffic environments elsewhere cannot simply be assumed to transfer.

IV. Computational complexity

Combining a VLA model with a world model introduces computational overhead beyond what either component costs on its own: real-time decision-making now requires efficient inference across both the perception-action pipeline and the predictive-planning pipeline at once, and current architectures generally struggle to balance predictive accuracy against the latency budgets real-time control demands (Feng et al., 2025). The layered separation proposed in this paper is intended to ease that tension, allowing the infrequent slow loop and the continuous fast loop to be optimized somewhat independently, but this paper has not measured the resulting latency or throughput in practice, and that measurement remains an open question rather than something already settled.

IV. Architectural fragmentation

This is the central gap motivating the present paper. Most existing systems still treat perception, prediction, and action as separate components joined by informally specified, ad hoc interfaces, rather than as parts of one architecture designed as a whole from the outset (Xu, 2025; Zhu et al., 2025). The costs of this fragmentation are concrete: redundant computation across components that could, in principle, share representations; genuine difficulty performing end-to-end optimisation across the full pipeline; and, as this paper has argued throughout, no principled basis on which to reason about how that pipeline's design should respond to deployment constraints such as bandwidth or power availability, since no unified architecture yet exists within which such constraints could even be evaluated as a whole.

Measured against these five challenges, the architecture proposed above offers a partial and deliberately modest response to each, a mechanism and a rationale, not a demonstrated solution. On fragmentation, the two-loop design provides a concrete structure with a defined, narrow interface between perception-prediction and action, though its actual effectiveness relative to more ad hoc alternatives remains untested. On generalization, the subgoal mechanism is proposed as a route toward zero-shot task generalization, a claim this paper has not itself verified across environments. On data inefficiency, the fast loop's imagination-based rollouts offer a plausible route to sample-efficient learning, consistent with results already demonstrated elsewhere in the field, DayDreamer's roughly one-hour real-world training time for a walking policy is the clearest example (Wu et al., 2023), but this paper's own architecture has not been trained or measured against any such benchmark. On weak integration, the coupling mechanism described above is more specified than the field's current ad hoc norm, though the subgoal interface itself and the proposed training staging both remain open, unverified questions rather than resolved ones. And on deployment safety, this paper claims nothing more than that the architecture's modular separation should, in principle, make targeted per-loop safety analysis easier than it would be for a monolithic system, a design affordance, not a safety guarantee the paper has demonstrated.

FUTURE RESEARCH DIRECTIONS

Several directions for future work follow directly from the limitations discussed above, some close at hand and others more foundational.

I. Unified foundation models for embodied AI

Work is already underway on foundation models that combine vision, language, and action within a single pretrained architecture rather than training each component separately. RT-2 and PaLM-E both show that web-scale pretraining on largely non-robotic data can transfer meaningfully into embodied, physical tasks, a result with real implications for the data-inefficiency problem discussed above, since it suggests that better transfer from abundant non-robotic data, not simply more robotic demonstration data, may be part of the answer. Future work will likely push this transfer-learning approach toward larger models, broader task distributions, and messier, less curated environments than current benchmarks represent.

II. Causality-aware world models

Current world models, including the one proposed in this paper, learn predominantly correlational relationships between states and outcomes, which produces brittle predictions whenever environmental dynamics shift even modestly from the training distribution. Gupta et al. (2024) argue that building genuine causal reasoning into world models, moving from noticing that one thing tends to follow another toward understanding why it does, may be necessary for robust generalization, since causal understanding should, in principle, transfer correctly even to situations never directly observed in training. This limitation carries particular weight for deployment in sub-Saharan African contexts specifically: informal and semi-structured transit patterns, variable road infrastructure, and inconsistent traffic-signal compliance diverge substantially from the relatively structured, well-instrumented environments in which most published world models have been trained and evaluated, which makes the correlational brittleness problem considerably more consequential here than in the settings where these models were originally developed.

III. Language as a universal interface

Natural language is increasingly serving not just as an input but as a general-purpose interface, for specifying tasks, giving step-by-step instructions, enabling human oversight, and potentially intervening in real time to correct or halt unsafe behaviour. Future systems are likely to lean on language more heavily across all of these functions: interactive learning through conversational feedback, explanation generation before an action is taken so a human can review it, and safety intervention specifically (Driess et al., 2023; Wang et al., 2025; Wu et al., 2025).

IV. Self-supervised and interactive learning

Self-supervised learning, extracting useful training signal from unlabeled interaction data rather than requiring costly human-annotated demonstrations for every step, offers a genuine route to reducing the data requirements discussed earlier. Paired with interactive learning approaches that use targeted human feedback at key decision points rather than full demonstrations throughout, these techniques could meaningfully cut the volume of expensive demonstration data current systems need (Reed et al., 2023; Shridhar et al., 2023), a direction with obvious relevance wherever large-scale demonstration collection is particularly costly.

V. Context-appropriate evaluation benchmarks

The field's lack of standardized, widely adopted benchmarks is well documented and makes it hard to compare approaches or track progress with any rigour. This paper argues the gap runs deeper still: even the benchmarks that do exist do not evaluate generalization, safety, or sample efficiency under the specific bandwidth, compute, and power constraints typical of infrastructure-limited deployment. A benchmark suite that tested embodied AI systems under simulated intermittent connectivity, constrained on-device compute, and realistic power limitations, rather than assuming the abundant resources most current benchmarks implicitly assume, would be a distinct contribution in its own right rather than an incremental extension of existing suites, and it is one this paper identifies as a priority without attempting it here.

VI. Safety and alignment

As embodied AI moves closer to practical deployment, safe and predictable behaviour becomes an urgent concern rather than a purely academic one. Future work needs formal verification methods capable of scaling to the high-dimensional, learned representations these systems use; safe exploration strategies that let an agent learn from real interaction without unacceptable risk during the learning process itself; and broader alignment with human values, including explicit safety-constraint specification, behavioural monitoring, and mechanisms for timely human intervention (Zhang et al., 2024; Zhao et al., 2026).

VII. Efficient architectures

The computational cost of current VLA models and world models substantially limit deployment on resource-constrained hardware, a limitation that matters well beyond infrastructure-constrained regions specifically, since edge deployment and on-device inference are shared goals across the field. Model compression, knowledge distillation, quantization, and specialized inference hardware are all likely to matter for deployment at any real scale (Feng et al., 2025). This is the specific direction the architecture proposed in this paper is designed to support, through its infrequent, subgoal-based slow loop and its compact latent-space fast loop, together with its explicit acknowledgment that the subgoal interface requires further design work before compression techniques could meaningfully be applied to it. None of these compression techniques have been implemented or benchmarked here, and doing so remains a clearly identified next step.

VIII. Multi-agent and collaborative systems

Most current work, including this paper, addresses a single agent in isolation. Real embodied AI systems will increasingly need to operate in real multi-agent settings, coordinating not only with other autonomous agents but with human operators, bystanders, and existing infrastructure at the same time. This introduces problems of communication, cooperative versus competing objectives, and social reasoning about human intent that current single-agent architectures are simply not built to address (Zhu et al., 2025). The relevance to the traffic-systems application discussed earlier is direct: an actual deployment would involve multiple control agents, human infrastructure operators, and a large, heterogeneous population of road users, all interacting at once, a coordination problem the architecture proposed here, built around one agent's perception-prediction-action loop, does not yet address.

IX. Subgoal representation learning

Finally, and specific to the architecture proposed in this paper, the representation and training of the subgoal passed between the slow and fast loops is identified here as the central unresolved technical question. Future work should investigate which of the candidate approaches outlined above, a shared latent space, a learned mapping function, or predicted-observation targets, best supports stable, meaningful coupling between language-grounded goal-setting and latent-space action planning, and under what conditions each approach breaks down.

CONCLUSION

This paper set out to examine how embodied artificial intelligence has moved from perception-driven systems toward predictive, action-oriented ones, with particular attention to Vision-Language-Action models and world models, and to a question the existing literature has largely left unasked: how such systems ought to be designed for deployment where connectivity, compute, and power cannot be taken for granted. A few things follow from the review and the design work presented above.

VLA models and world models are complementary, and neither is sufficient alone. VLA models are strong at multimodal perception and action generation, letting agents interpret instructions and act on them (Brohan et al., 2024; Driess et al., 2023; Jiang et al., 2023). 

World models are strong at predictive simulation and planning, letting agents anticipate consequences and reason across longer horizons (Hafner et al., 2025; Schrittwieser et al., 2024). 

The literature reviewed above shows both paradigms maturing largely in parallel, with limited technical overlap between them, which is precisely why fragmentation, rather than any shortage of capability in either paradigm individually, stands out as the field's central obstacle. 

Current systems still overwhelmingly treat perception, action, and prediction as separate modules stitched together through ad hoc interfaces (Feng et al., 2025; Zhu et al., 2025), and it is this fragmentation, more than any deficiency in the underlying components, that this paper takes as its primary diagnosis.

In response, this paper has proposed hierarchical, two-timescale architecture that couples a VLA model and a latent world model through a deliberately narrow subgoal interface, together with a staged approach to training the two components. The architecture suggests that such coupling is conceptually workable and, on the strength of its individual components' already-demonstrated properties, plausibly useful: by design, it is meant to support infrequent, language-grounded goal setting, continuous imagination-based planning toward that goal, and meaningfully reduced cross-component communication compared with systems that fuse modalities continuously throughout (Xu, 2025; Sun et al., 2024). This paper identifies the subgoal representation itself as the architecture's central open question and does not claim to have resolved it. Confirming these properties, individually and together, is left as a priority for future implementation and testing, not something asserted here on architecture’s behalf.

Real challenges remain, both for the field broadly and for this proposal specifically: data efficiency, generalization under distribution shift, safety guarantees, and computational cost all need continued work on multiple fronts (Yang et al., 2024; Zhang et al., 2024; Zhao et al., 2026), and this paper has argued that these challenges tend to be sharper, not merely equally present, under the connectivity, compute, and power constraints typical of sub-Saharan African deployment. 

At the same time, the pieces needed for real progress are converging large-scale foundation models, early work on causal reasoning within world models (Gupta et al., 2024), self-supervised learning, and steadily more efficient architectures together point toward a plausible, if not yet realized, path forward.

For researchers, the recommendation this paper would make is to treat principled integration as the priority, rather than continuing to specialize within either paradigm separately, building unified architectures through explicitly justified design choices, of the kind attempted above, rather than deferring integration until each component is separately mature. Developing benchmarks that evaluate generalisation, sample efficiency, safety, and real-world performance under realistic infrastructure constraints, rather than assuming abundant resources by default, stands out as a distinct and currently unmet priority. Moving beyond purely correlational learning toward genuine causal representation is likewise essential if the field is to close its generalization gap rather than merely work around it.

For practitioners, pretrained foundation models remain a strong starting point, and fine-tuning on domain-specific data can meaningfully cut data requirements relative to training from nothing (Radford et al., 2021; OpenAI Team, 2024). Designing for modularity, separating perception, prediction, and action into components joined by clearly defined interfaces, as this paper has attempted, makes testing, debugging, and targeted safety analysis considerably more tractable than a single monolithic system allows. Extensive simulation-based testing through a world model, well before any real-world deployment, lets practitioners surface likely failure modes at far lower cost and risk than learning through real trial and error (Hafner et al., 2025).

For institutions and funding bodies, embodied AI sits at the intersection of machine learning, robotics, cognitive science, and human-computer interaction, and funding structures should reflect that rather than treating it as belonging to any one of those fields alone. Investment in shared computational infrastructure, robotic platforms, and diverse testing environments remains necessary for the field to keep progressing, and, this paper would add, investment aimed specifically at infrastructure-constrained regions is necessary if the resulting technology is to end up broadly deployable rather than narrowly so. Safety research, verification methods, ethical frameworks, mechanisms for human oversight, deserves funding priority proportionate to how quickly the field is moving toward real-world deployment (Zhang et al., 2024; Zhao et al., 2026).

The shift from perception to prediction is a meaningful one for artificial intelligence, from systems built to see and understand toward agents built to anticipate and act. It is not simply an incremental refinement of what came before; it is a genuine move toward intelligence that is situated, embodied, and directed at goals rather than merely descriptive of its surroundings. Vision-Language-Action models and world models, integrated rather than developed on separate tracks, offer a plausible path toward that kind of intelligence: agents capable of perceiving their environment, understanding what they are asked to do, anticipating what will happen next, and planning accordingly.

This paper contributes one step along that path, a review of the complementary roles VLA models and world models play, an architectural proposal for integrating them in a principled way, and a research agenda for the work still ahead, with particular attention to a deployment context that existing research has largely overlooked: infrastructure-constrained, low-resource environments such as sub-Saharan Africa. The architecture proposed here is a reasoned starting point, grounded in established literature and honest about what it has and has not demonstrated, rather than a finished or validated solution. 

The path toward general-purpose, broadly deployable embodied intelligence remains open, and this paper's claim is narrower than that larger ambition, and, hopefully, more defensible for being so: that any credible path forward has to treat infrastructure-constrained deployment as a design consideration from the very beginning, not as an engineering concern to be handled once the real work is already done.

REFERENCES

[1]	Africa Data Centres Association. (2026). State of the African data centre industry 2026. ADCA.

[2]	Bommasani, R., Hudson, D. A., Adeli, E., et al. (2022). On the opportunities and risks of foundation models. Center for Research on Foundation Models, Stanford Institute for Human-Centered Artificial Intelligence, Stanford University.

[3]	Brohan, A., Brown, N., Carbajal, J., et al. (2024). RT-2: Vision-language-action models transfer web knowledge to robotic control. arXiv.

[4]	Driess, D., Xia, F., Sajjadi, M. S. M., et al. (2023). PaLM-E: An embodied multimodal language model. arXiv.

[5]	Feng, T., Wang, X., Jiang, Y.-G., & Zhu, W. (2025). Embodied AI: From LLMs to world models. IEEE Circuits and Systems Magazine.

[6]	Gao, J., et al. (2024). Hybrid multimodal-predictive architectures for embodied agents. arXiv.

[7]	GSMA. (2024). The mobile economy: Sub-Saharan Africa 2024. GSMA Intelligence.

[8]	Gupta, T., Gong, W., Ma, C., Pawlowski, N., Rigter, M., Bauer, S., & Zhang, C. (2024). The essential role of causality in foundation world models for embodied AI. arXiv.

[9]	Hafner, D., Pasukonis, J., Ba, J., & Lillicrap, T. (2025). Mastering diverse control tasks through world models. Nature.

[10]	Jiang, Y., Gupta, A., Zhang, Z., et al. (2023). VIMA: General robot manipulation with multimodal prompts. Proceedings of the International Conference on Machine Learning.

[11]	Kim, M. J., Pertsch, K., Karamcheti, S., et al. (2024). OpenVLA: An open-source vision-language-action model. Conference on Robot Learning.

[12]	Li, H., Chen, Y., Cui, W., et al. (2025). Survey of vision-language-action models for embodied manipulation (Version 2). arXiv.

[13]	Lin, F. (2025). Vision-language models: A survey of 26K papers. arXiv.

[14]	Liu, S., Tang, J., Hassan, M. S., Sharkawy, M. H., Fouda, M. M. G., Shang, T., & Wang, Z. (2026). Infrastructure first: Enabling embodied AI for science in the Global South. arXiv.

[15]	OpenAI. (2023). GPT-4 technical report. OpenAI.

[16]	OpenAI Team. (2024). GPT-4V system card addendum. OpenAI.

[17]	Radford, A., Kim, J. W., Hallacy, C., et al. (2021). Learning transferable visual models from natural language supervision. Proceedings of the 38th International Conference on Machine Learning.

[18]	Reed, S., Zolna, K., Parisotto, E., et al. (2023). A generalist agent. Transactions on Machine Learning Research.

[19]	Sapkota, R., Cao, Y., Roumeliotis, K. I., & Karkee, M. (2025). Vision-language-action (VLA) models: Concepts, progress, applications, and challenges. arXiv.

[20]	Schrittwieser, J., Antonoglou, I., Hubert, T., et al. (2024). Mastering Atari, Go, chess and shogi by planning with a learned model. Nature.

[21]	Shridhar, M., Manuelli, L., & Fox, D. (2023). Perceiver-Actor: A multi-task transformer for robotic manipulation. Conference on Robot Learning.

[22]	Sun, Y., Ma, S., Madaan, R., et al. (2024). SMART: A unified foundation model for embodied AI. arXiv.

[23]	Tracking SDG7. (2025). Tracking SDG7: The energy progress report 2025. International Energy Agency, International Renewable Energy Agency, United Nations Statistics Division, World Bank, & World Health Organization.

[24]	Wang, Y., Li, X., & Liu, Z. (2025). Language-conditioned world models for robust robotic control. International Conference on Learning Representations.

[25]	Wu, P., Escontrela, A., Hafner, D., Abbeel, P., & Goldberg, K. (2023). DayDreamer: World models for physical robot learning. Conference on Robot Learning.

[26]	Wu, J., Antonova, R., & Pinto, L. (2025). Learning to plan with world models and language. arXiv.

[27]	Xu, Y. (2025). A unified world model is the cornerstone for integrating perception, reasoning, and decision-making in embodied AI. NeurIPS Workshop.

[28]	Yang, Z., Zhang, W., & Liu, X. (2024). Evaluating safety of embodied AI systems: A benchmark. arXiv.

[29]	Zhang, W., Kong, X., Braunl, T., & Hong, J. B. (2024). SafeEmbodAI: A safety framework for mobile robots in embodied AI systems. IEEE International Conference on Robotics and Automation.

[30]	Zhao, Y., Liu, H., & Wang, C. (2026). Scaling world models to real-world robotics: Challenges and opportunities. Annual Review of Control, Robotics, and Autonomous Systems.

[31]	Zhu, Y., Zhao, D., & Fei-Fei, L. (2025). Embodied AI: Where are we and where are we going? Communications of the ACM.

[32]	Zitkovich, B., Yu, T., Xu, S., et al. (2025). RT-X: A unified vision-language-action model for robot manipulation. arXiv.


[TABLE]

Model Type | Core Function | Strengths | Limitations | Typical Uses

Vision-language models | Perception and reasoning | Strong multimodal understanding | No action capability | Image captioning, visual QA

VLA models | Perception and action | Task execution, generalisation | Reactive; data-heavy | Robotics, navigation

World models | Prediction and planning | Long-horizon reasoning | Complex to train | Simulation, planning


[TABLE]

Feature | Vision-language models | VLA models | World models

Multimodal input | Yes | Yes | Limited

Action output | No | Yes | Indirect

Prediction capability | No | Limited | Yes

Planning | No | Limited | Yes

Real-world interaction | No | Yes | Yes (via integration)