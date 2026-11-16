# Career Fit 0.8.0 implementation and review record

Authorized full implementation: November 16, 2026. Base: published 0.7.0. Branch: `codex/evidence-decisions-0.8.0`. The implementation preserves the original consumer workflow and user-owned output files.

## Delivered work

| Review dimension | Concrete evidence | Remaining validity boundary |
| --- | --- | --- |
| Capability demonstration | Employer-to-task research, generated personal/business briefs, 2/10/30-minute showcase routes | Fictional learner and employees do not establish the author's employment history |
| Knowledge depth | External extraction metrics, one-to-one evaluation, construct distinctions, complementary skills, explicit objectives and sensitivity | Fit weights and individual training effects are not calibrated against human outcomes |
| Professional skills | Normalized SQLite and actual SQL, train-only baselines, exact and mixed-integer optimization, source metadata, portable package | No claim of production HR warehouse deployment or real employer savings |
| User experience | Ordinary forms, editable mappings, task rubric, preserved evidence/progress round trip, local save/restore | No completed human usability study |
| Presentation | Showcase, actual-result charts, responsive screens, executive/methods/reproduction/interview materials | Public observations and designed scenarios remain visibly distinct |

## Independent round 1 and repairs

Two read-only reviewers inspected methods/calculations and the actual browser workflows. Repairs addressed:

- Existing negative evidence could become positive when moved to a different evidence schema. Original structured evidence now remains intact, including negation and verification metadata.
- Repeated transfer of the same artifact could increase evidence strength without new work. Stable skill/artifact matching now updates review notes rather than duplicating proof.
- The ordinary role-review route omitted structured evidence and language. Analysis, report and investment transfers now preserve them.
- A review round trip discarded learning records and rebuilt generic tasks. The session now restores the catalog, costs and progress, and safely remaps custom targets by reviewed label.
- The business deep link opened the personal workspace, reset invoked an earlier loader, and an encoding conversion damaged characters. These routes and display were repaired.
- Cost annotations omitted backfill/vacancy loss. Priority units, horizon and complete economic components are now explicit.
- Missing consent defaulted to met. It now defaults to unknown; legacy fictional cases explicitly declare assumed consent.
- The Systems Evaluation label and supervised model variant could be mislabeled. Both now match the source/method.
- Offline evaluation could rewrite source retrieval dates. Acquisition manifests and local file times are separated from evaluation time.
- New pytest functions were initially outside the old unittest CI runner. CI now uses pytest and includes a dedicated optimization job.

## Independent round 2

The methods reviewer confirmed the negative-evidence, duplicate-transfer, consent, model-label, skill-label and date fixes with focused checks and the nine new tests. The product reviewer actually repeated the ordinary review and assessed-artifact workflows, including preservation of language, evidence, fees, budget, progress and negative statements. Both found no remaining P1 in the reviewed scope. CI coverage and generated provenance were completed as release preparation. Automated review does not count as a human participant study.

## Validation

- Local Python suite: **103 tests passed**, including nine new focused tests. The optional optimization path executed locally.
- Static checks: Ruff and source compilation; changed Python and web files formatted for inspection.
- New browser tasks: showcase metrics and sensitivity, business deep link and forms, invalidation, source facts, preserved structured evidence, task rubric, fresh-review requirement, saved-plan restoration and desktop/mobile layout.
- Legacy browser tasks: original review/edit gates, budgets/hours, named gaps, benefit scenarios, JSON/Markdown and existing PDF export, and current-ID consumer transfer. Both runners pass with no page errors or document-level overflow at 1440px/390px.
- External experiment: official train/dev/test sizes 4,800/3,174/3,569; all three methods and both named dictionary tasks retained. Low exact results are reported without a reliability claim.
- Clean distribution checks install wheel and source distributions outside the checkout, run both CLI namespaces, source research, measurement summaries, personal/small/medium decisions and existing PDF generation, and inspect packaged assets/licenses. Local logs stay under ignored `build/`.
- Cloud CI runs Python 3.10–3.14, optional optimization, the existing Atlas/browser integration, both capital browser suites, the existing 500-case journey audit and clean release smoke. Live results: [CI workflow](https://github.com/JoeDHJ/career-fit/actions/workflows/ci.yml).

## Release destinations

The reviewed 0.8.0 change is published through the repository's existing release workflow: [GitHub release](https://github.com/JoeDHJ/career-fit/releases/tag/v0.8.0) · [PyPI version](https://pypi.org/project/career-fit/0.8.0/) · [publishing workflow](https://github.com/JoeDHJ/career-fit/actions/workflows/publish.yml). These links expose the final remote status. No new Word/PDF deliverable or user output file is included in the change.
