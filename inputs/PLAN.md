# Plan: AfriCoT-VLA dissertation, new journal paper, and live demo

Draft v1, 23 October 2026. Author: Temitope W. Ariyo, matric 249074175. Supervisor: Dr. E. P. Fasina.

## 0. Facts established from the workspace

- Code: https://github.com/Topmost2020/africot-vla. `main` holds only the spec. The built system is on branch `claude/africot-build` (stages S0-S8 all `documented`, reviewed, 68 tests passing, results for 100 runs, figures, trained world model).
- Results: read ONLY from `results/summary.csv` at commit cf3e7ed (n=5 seeds, mean and SD). No numbers are quoted in this plan (an earlier draft quoted superseded pre-fix numbers; corrected after critic review). Qualitatively: max_pressure is best on normal and incident; africot_noslow is nominally ahead of max_pressure on market but the gap is well inside one SD, so it is reported as "comparable"; africot_nowm is worse than fixed_time. The outage rows are identical to market for every controller except africot_full, so outage is not an independent scenario for them.
- Built baselines: 3 (fixed_time, count_timer, max_pressure). CLAUDE.md lists 5; deep RL and LLMLight are absent.
- NO africot_full result exists. The VLAM (Qwen2.5-VL-7B) grid needs a GPU (Colab notebook written, never executed). A 3B CPU smoke test gave a parseable subgoal but unreliable reasoning (150 s per call).
- Scope in the repo is a SINGLE junction, not the 2-3 junction corridor in CLAUDE.md. This must be stated as a limitation and future work.
- The template (MIT 899 Dissertation Template.pdf) is a structural skeleton only: cover, certification, dedication, acknowledgement, TOC, list of figures, list of tables, abstract. Its sample cover carries another student's title, department (Computer Sciences) and degree (MIT in Computer Science).

## 1. Deliverables

D1. Dissertation (.docx and .pdf): cover, certification, dedication, acknowledgement, TOC, list of figures, list of tables, abstract, then Chapters 1-5, references, appendices.
D2. New journal paper (.docx and .pdf), derived from the dissertation but distinct from the existing journal paper (Toward a Unified Framework ...). It adds CoT and reports the SUMO results.
D3. Public demo (Gradio on a Hugging Face Space) with a shareable link for the supervisor.
D4. Everything saved to the laptop folder when the laptop is next on.

## 2. Honesty rules for every writer

1. Every number in text, tables and figures is read from `results/summary.csv`, `models/wm_metrics.json` or the stage docs by script, never typed from memory.
2. No claim that africot_full works, wins, or "achieves" anything until real africot_full results exist. If they do not, report the architecture as designed and tested for wiring only, and say so in Chapter 4 and the abstract.
3. Negative results stay in: noslow loses to max_pressure on normal and incident; max_pressure and count_timer behave oddly on market; the incident scenario barely raises AWT under fixed_time; novelty trigger is not incident-specific; 3B CoT is unreliable.
4. Proposal verbs ("is designed to", "is intended to support"). No em-dashes. Journal-style flowing prose. Natural cross-references. APA 7, Times New Roman, justified, one column. Abstracts 150-300 words.
5. Credit Dr. Fasina for the 8-layer framework (27 July 2026 session) and state the cloud-vs-on-site-video tension and the reconciliation.
6. No invented citations. Only references that can be verified (ECoT arXiv:2407.08693, InstructVLA arXiv:2507.17520, DreamerV3, max-pressure, LLMLight, etc.). Names flagged unverified in CLAUDE.md (LeWM, VLA-JEPA, Lota-Carinae, AfriSCOP-CC) are not cited. Each reference gets a verification pass (web search) and unverifiable ones are dropped or marked TODO.
7. Figures are matplotlib, no figure numbers baked in.

## 3. Workstreams

### W0. Foundation (me, first)
- Check out `claude/africot-build`; run pytest; confirm it reproduces `results/summary.csv`.
- Extract a machine-readable "facts pack" (results, metrics, deviations, design) into `facts/` so writers cite one source.
- Decide the front-matter wording (see open decisions).

### W1. Demo (Gradio, Hugging Face Space)
- Do not run SUMO live on a free CPU Space. Instead:
  - Tab 1 "Results": interactive tables and bar charts per scenario and controller, from committed results (read-only, always works).
  - Tab 2 "Replay": step through recorded episodes (queues, phase, shield interventions) for each scenario and controller, with the explainability log and CoT text beside the signal state.
  - Tab 3 "Safety shield": feed deliberately unsafe proposals and show the shield correcting them (this is cheap and runs live in pure Python).
  - Tab 4 "Slow loop": the example snapshot image, the rendered context, the VLAM output and parsed subgoal; mock backend live, real output labelled as recorded.
  - Tab 5 "Outage": the degradation-tier timeline (online, hold-last, cached schedule, online) from the committed logs.
  - Tab 6 "About and limits": scope, single junction, what is not yet shown.
- The page states plainly which parts are live code and which are recorded runs. It does not claim "works and achieves expectations" beyond what the data shows.
- Needs: a Hugging Face account and write token (user action; I will not handle credentials from this session beyond what the user supplies), or the user creates the Space and adds a deploy key.
- Fallback if HF is not possible: the same app as a Colab notebook with a `share=True` Gradio link (72-hour link) and a static HTML export.

### W2. Experiments gap (Colab, user action needed)
- The only way to obtain africot_full results is a GPU run of `colab_experiments.ipynb`. Options: (a) user runs it (about one GPU session); (b) skip, and report africot_full as implemented, wiring-tested, not yet evaluated. The writers are told to draft for case (b) and to expose a single results table that can be regenerated if (a) completes.

### W3. Dissertation (writer agents, one per chapter, then an assembler)
- Ch1 Introduction: background, SSA traffic context, problem statement, aim and objectives, research questions, scope and delimitations, significance, structure.
- Ch2 Literature Review: traffic signal control (fixed-time, actuated, max-pressure, RL, LLM-based such as LLMLight), world models (Dreamer, TD-MPC2, V-JEPA 2), VLA models and CoT for control (ECoT, InstructVLA, OpenVLA), explainability and regulation, SSA constraints, research gap.
- Ch3 Methodology and System Design: the architecture (perception, fast loop, slow loop, subgoal interface, shield, explainability log, coordinator, degradation tiers, tiered communication), the 8-layer deployment framework and the cloud-versus-edge reconciliation, SUMO setup, scenarios, baselines, metrics, ablations, seeds, reproducibility.
- Ch4 Implementation, Results and Discussion: stage-by-stage implementation, world-model accuracy, controller comparison with tables and figures, shield audit, slow-loop wiring evidence, ablations that exist (nowm, noslow), honest discussion, threats to validity.
- Ch5 Summary, Conclusion, Recommendations and Future Work: includes corridor extension, neighbour exchange, africot_full GPU evaluation, hardware-in-the-loop, shadow mode, pilot, deployment roadmap, timeline.
- Preliminary pages follow the template order. Dedication and acknowledgement text is drafted by me for the user to edit (placeholders for personal names).
- Build pipeline: python-docx (installed) generates .docx with real Word heading styles and an auto TOC field, Times New Roman, justified; LibreOffice or Word converts to PDF if available (to be checked), otherwise docx only plus a reportlab PDF.

### W4. New journal paper (one writer agent)
- Working title (to be agreed): "AfriCoT-VLA: Coupling Chain-of-Thought Vision-Language Reasoning with a Latent World Model for Infrastructure-Constrained Traffic Signal Control in Sub-Saharan Africa".
- Novelty versus the existing journal paper: adds CoT-based slow loop with justification logs, the safety shield and audit, the coordinator and degradation tiers, and SUMO evidence including negative results.
- Structure: abstract (150-300 words), introduction, related work, method, experimental setup, results, discussion, limitations, conclusion, references. About 6,000-8,000 words. Reuse of text from the existing journal paper is flagged and minimised (self-plagiarism check against it).
- Co-author Ebun P. Fasina (email placeholder kept, not invented).

### W5. Critic loop
- Critic pass 1: this plan (now).
- Critic pass 2: each chapter and the paper against the honesty rules, the facts pack, the template and the writing conventions.
- Critic pass 3: the demo against the claims made in the dissertation.
- Fix cycle until the critic reports no blocking issues, then final assembly.

### W6. Delivery
- Save to `Project doc/Dissertation/` and `Project doc/New Journal Paper/` on the laptop, plus the demo URL in a README.

## 4. Where the work runs (the laptop-off constraint)

A local background agent stops when the laptop sleeps or shuts down. For work that must continue with the laptop off:
- Run the writers and the demo build in a cloud session (remote isolation) that works on the GitHub repo (a new branch `claude/dissertation`) and commits chapters and the paper there as .md/.docx.
- When the laptop is next on, I (or a one-line git pull) copy the finished files into the laptop folders. A cloud agent cannot write to the laptop directly, so "saved on my laptop upon completion" can only be completed at that sync step.
- If remote isolation is unavailable on this account, fall back to running locally and keeping the laptop awake (power settings), or to a scheduled routine.

## 5. Open decisions for the user

1. Front matter: the template cover shows Department of Computer Sciences and "Master of Information Technology in Computer Science", but an earlier project file named a different department (now corrected to Faculty of Computing and Informatics, Department of Computer Science). Which department and degree title go on the cover and certification? Same question for "Dr. E. P. Fasina" and the department on the certification page.
2. Hugging Face: do you have an account, and will you create the Space or give a token?
3. GPU run for africot_full: will you run the Colab notebook, or report africot_full as implemented but not yet evaluated?
4. Scope: the repo is a single junction; CLAUDE.md prefers a 2-3 junction corridor. Report single junction honestly and put the corridor in future work (recommended), or extend the code first?
5. Is the cloud agent route acceptable (repo gets a new branch with the drafts, pushed to your GitHub)?

## 6. Risks

- Results are mixed; a dissertation that says "achieves expected results" would be false. Mitigated by the honesty rules.
- africot_full unevaluated: the central claim (slow loop helps) is untested. Mitigated by (W2) or by framing as design plus partial evidence.
- Template mismatch and personal details guessed wrong. Mitigated by decision 1.
- Reference hallucination. Mitigated by verification pass.
- Examiner or supervisor expectations on length and format are unknown (page count, referencing style, plagiarism limit). Ask for the MIT 899 guidelines if they exist.
- Demo credibility: a recorded-replay demo is honest but is not proof of live operation; label accordingly.
