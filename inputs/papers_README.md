# VLA + Latent World Model papers (SSA)

Papers for "Towards a unified framework of vision-language-action models and latent world models for low-resource, infrastructure-constrained environments in Sub-Saharan Africa" by Temitope W. Ariyo and Ebun P. Fasina, Faculty of Computing and Informatics, Department of Computer Science, University of Lagos.

| Folder | Contents |
|---|---|
| `mirg-icair-2026/` | Revised camera-ready paper for MIRG ICAIR 2026 (Paper ID 100), in the ICAIR template, plus a response to reviewers |
| `unilag-conference-2026/` | UNILAG Annual Research Conference version of the paper, plus the A0 poster |
| `simulation/` | Toy feasibility study (communication cost, link outages, subgoal interfaces, compute) |
| `figures/` | Figures (matplotlib) and their data sources |
| `references/` | Reference verification notes and the final APA 7 list |
| `sources/` | Inputs: original draft, reviews, ICAIR template, UNILAG poster brief, poster sample |
| `build/` | Build scripts (`make_paper.py` turns a marked-up text source into the template .docx) |

Build a paper: `python build/make_paper.py <source.md> <out.docx> --pdf` (rendering the PDF requires Microsoft Word on Windows).
