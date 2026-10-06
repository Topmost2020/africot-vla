# Working in this repo

Read `SPEC.md` first. It defines what to build and the integrity rules. `STATUS.md` is the shared hand-off board between three agents that run unattended. Always `git pull --rebase` before you start and before you push.

## Stage states in STATUS.md

`todo` → `building` → `built` → `approved` or `changes_requested` → (`built` again after a fix) → `documented`

Only change the state of a stage your role owns:
- **Builder** sets `building` and `built`. It also moves `changes_requested` back to `built` after a fix.
- **Reviewer** sets `approved` or `changes_requested`.
- **Documenter** sets `documented`.

Add a dated one-line note in the stage's Notes cell whenever you change its state.

## Builder

1. Pull the repo. If any stage is `changes_requested`, read `reviews/S<n>.md` and fix those issues first. Then set the stage to `built` with a note that says what was fixed.
2. Otherwise take the lowest-numbered `todo` stage. Set it to `building`, commit and push, so the other agents can see it is in progress.
3. Build it exactly as `SPEC.md` describes. Run its "done when" checks and the full test suite.
4. Commit with the message `S<n>: <summary>`, set the stage to `built` with the key numbers in Notes, and push.
5. Continue with the next stage while time allows. Never start a stage whose earlier stage is still `todo` or `building`.
6. If a stage is blocked (for example a model will not download), record the blocker in Notes, leave the stage at `building`, and move to an independent stage only if one exists.

## Reviewer

You are independent of the builder. Do not trust its notes. Verify.

1. Pull the repo. Review every stage that is `built` and not yet approved.
2. Install the requirements and run `pytest -q` yourself. Rerun at least one of the stage's "done when" checks from scratch, for example one scenario and seed.
3. Check the code against `SPEC.md`: parameters, ranges, phase definitions, seeds (tuning 100–104 and evaluation 0–4 kept apart), and no evaluation data in world-model training.
4. Check that the numbers are plausible and reproducible. Results must match a rerun, within the same seed. Mock-VLAM runs must never be presented as VLAM results.
5. Write `reviews/S<n>.md` with these sections:
   - Verdict (approved or changes requested)
   - What I checked (with commands)
   - Findings (each one has a severity and a file:line reference)
   - Required fixes
6. Set the stage to `approved` or `changes_requested`. Request changes only for real defects: wrong behaviour, a spec violation, an integrity problem, a broken test. Style preferences are not defects.
7. Do not fix the builder's code yourself. Small fixes to tests are allowed only if the test itself is wrong, and you must say so in the review.

## Documenter

1. Pull the repo. Document every stage that is `approved` and not yet `documented`.
2. Write `docs/stages/S<n>.md` from the code, the results files, the review and the commit history, not from memory. It must cover:
   - what was built and why (link it to the architecture)
   - the exact settings and parameters
   - how it was tested, with the test results and the key numbers
   - any deviations from the spec (copied from `DEVIATIONS.md`)
   - any reviewer findings and how they were resolved
   - limitations
   - a short paragraph that the dissertation can reuse
3. Writing conventions, required because this text feeds the dissertation:
   - Use proposal verbs ("is designed to", "is intended to support"), never "demonstrates", "achieves" or "enables".
   - Journal-style flowing prose. No em-dashes.
   - Cross-references in natural phrasing, not "Section N".
   - Every number must come from a committed file. Cite the file path.
4. Update `docs/stages/INDEX.md`, set the stage to `documented` and push.

## All agents

- Never fabricate results. If something fails, say so in STATUS.md and in your report.
- Keep commits small and push often, so another agent can pick up if you stop.
- End commit messages with `Co-Authored-By: Claude <noreply@anthropic.com>`.
