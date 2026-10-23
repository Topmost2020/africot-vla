# Decisions and flags (record of choices taken without asking, 23 October 2026)

## Gate G3 (environment and reproduction)
- Commit under test: 1cc74a9f7eabf43fa4ad9ccc5b4747476b9663f6 (branch claude/dissertation, code identical to cf3e7ed plus the task brief).
- SUMO 1.27.1 installed from the eclipse-sumo wheel (Windows, Python 3.13.2). torch 2.12.1+cpu was used because the pinned 2.14.1 was not installable on this machine. Other pins not enforced.
- `python -m pytest -q`: 68 passed in 147 s (matches STATUS.md).
- Reproduction: normal, seed 0, for fixed_time, count_timer, max_pressure, africot_noslow, africot_nowm re-run with `--force`; AWT, ATT, AQL, throughput, pedestrian wait and shield counts are identical to the committed result files (only wall time, git hash and a 1e-8 float difference in the world-model error differ). The re-run files were then restored with `git checkout results`. `python plots.py` regenerated results/summary.csv and summary.md byte-identically (no diff).
- Outcome: PASSED. Scope of the reproduction: one scenario and one seed per controller, not all 100 runs.

## Front matter
- Author on cover: ARIYO, TEMITOPE WILLIAMS (cover, capitals as in the template); certification: "Ariyo, Temitope Williams". Matric 249074175. Full name supplied by the user during the run; no further confirmation needed.
- Supervisor: Dr. Ebun P. Fasina; certification page uses "Dr. E. P. Fasina" as in the template.
- Head of Department: "Prof. F. A. Oladeji" copied from the template. FLAG: confirm this is the current Head of Department.
- Department on cover/certification: Department of Computer Sciences (template), not "Artificial Intelligence and Robotics" as in CLAUDE.md. FLAG: the author's group affiliation (Machine Learning Research Group, Department of Artificial Intelligence and Robotics) is kept on the journal paper only. Confirm which is correct for the dissertation.
- Degree: Master of Information Technology in Computer Science; October 2026.
- Title used: "A Traffic Control System for Sub-Saharan African Cities Combining Chain-of-Thought, Vision-Language-Action Models and Latent World Models" (TASK.md wording; CLAUDE.md abbreviates CoT and VLAMs).
- Dedication and acknowledgement are short drafts with square-bracket placeholders for personal names.

## Journal paper
- Co-author email: the existing paper's front matter gives efasina@unilag.edu.ng for Ebun P. Fasina (not a placeholder there) and temitopeariyo6@gmail.com for the first author. The new paper copies exactly those. FLAG: CLAUDE.md says the email was a placeholder; confirm that the address in the submitted paper is real.
- Affiliation on the paper follows the existing paper (Machine Learning Research Group, Department of Artificial Intelligence and Robotics).

## Scope and evidence
- africot_full: no reportable africot_full runs exist in results/ (checked by script, facts.africot_full_reportable_runs = 0). Every document is written for the "implemented, wiring-tested, not yet evaluated" case; every africot_full statement is isolated in one marked place per document and listed in output/UPDATE_WHEN_COLAB_FINISHES.md.
- Built baselines: fixed_time, count_timer, max_pressure. Deep RL and LLMLight are not built; disclosed and moved to future work. LLMLight is cited only as related work.
- Single junction only (not the 2 to 3 junction corridor in CLAUDE.md). Stated as a limitation and future work.
- Paired by-seed tests (n=5, scripts/build_facts.py) are reported as exploratory. Where the paired test finds a consistent difference (for example max_pressure ahead of africot_noslow on normal in 5 of 5 seeds) the text says so; where it does not (market, incident) the text says "comparable".
- 8-layer framework credited to Dr. Fasina (27 July 2026 class session), with the cloud versus on-site video tension stated and the reconciliation from CLAUDE.md offered as a proposal, not as supervisor-approved.
- Not cited: LeWM, VLA-JEPA, Lota-Carinae, AfriSCOP-CC. Webster 1958 dropped (unverifiable). LLMLight cited as arXiv preprint (venue unconfirmed).
- Numbers in PLAN.md were ignored; all numbers come from facts/facts.json built by scripts/build_facts.py from committed repo files.
- Environment: the run happens on the user's Windows machine (not a cloud sandbox). LibreOffice is absent; PDF conversion and field refresh use Microsoft Word through COM if it works (see output/README.md).

## Cloud framing change (user instruction during the run)
- New dissertation title: "A Cloud-Based Traffic Control System for Sub-Saharan African Cities Combining Chain-of-Thought, Vision-Language-Action Models and Latent World Models", subtitle "Cloud-Hosted Reasoning with Edge Fallback for Intermittent Connectivity". Cover shows title and subtitle; the certification page shows the title only, as the template does.
- Framing: cloud is the intended primary tier for layers 3 to 8 of Dr. Fasina's framework; layer 2 carries compressed keyframes; the on-site fast loop and safety shield are the resilience tier. A new "Cloud deployment architecture" section was added to the methodology chapter and cloud deployment and measurement to future work. No cloud deployment has been built or tested; every document says so.
- Chapter length budgets were enforced with scripts/wordcount.py (chapters total about 17,700 prose words, excluding table rows and figure lines).

## Toolchain decisions
- Microsoft Word was NOT used for the dissertation outputs: on this machine Word applies a corporate sensitivity label that encrypts saved .docx and exported PDF files, which would make them unreadable outside the organisation. The documents are built with python-docx and refreshed and converted by LibreOffice 26.2.6 (extracted from the official MSI to C:\lo with lessmsi, since installation needs admin rights). The master .docx is the LibreOffice-refreshed file (table of contents, list of figures and list of tables populated).
- Reference entries are plain text from the verified lists; APA italics for titles and venues are not applied (the lists do not encode italics). FLAG: italicise titles and volumes in Word before submission.
- COLAB-block text is highlighted yellow in the docx (and visible in the PDF) so that the places to update when africot_full results exist are obvious; remove the highlight after updating.
- Journal paper and demo: taken over by other agents (branches claude/paper and claude/demo) per the user; the paper source and build in this branch are a snapshot and are not maintained here.
