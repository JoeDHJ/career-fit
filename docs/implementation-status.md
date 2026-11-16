# Career Fit 0.7.0 implementation status

Scope: Skills Intelligence and Human Capital Decision System (2026-11-16).

## Inspection and plan

- Base: `origin/main`, containing the 0.6.0 release; work branch `codex/human-capital-0.7.0`.
- Preserve: evidence extraction, review-before-score, hard gates, multilingual and resume-free routes, role comparison, optional semantic review, Markdown/PDF export, legacy `skillbundle` API.
- Preserve user files: `output/`, `output-unicode-test.pdf`, `output-unicode-test.png` (untracked, excluded from this change).
- Fix: missing packaged font license, stale product versions/import descriptions, invalid review-file example, context cut inside words.
- Add: offline `portfolio.v1` public context, constrained personal training and 30/60/90-day plans, workforce mobility/training/hiring scenarios, CLI/UI/export, official-JD and public-occupation cases.
- Verify: baseline 71 tests pass. Then calculation/constraint tests, clean wheel/sdist installation, browser workflows and responsive screens, independent read-only review, scoped fixes and release CI.

## Progress

- Initial repository/remote inspection complete. No tracked user modifications present.
- Official sources checked: O*NET 31.0; BLS table 1.2, 2025–2035; Amazon Talent Intelligence Analyst (10569918); Apple People Analytics Full Stack Developer (200682909-1418, dated official search snapshot).
- Implemented offline market context, constrained training portfolios and 30/60/90-day schedules, explicit-benefit DCF sensitivity, and exact small-cohort workforce comparison. Original consumer routes and exports retained.
- Completed attributed real-JD/fictional-candidate and public-occupation/synthetic-cohort cases. Inputs, outputs, generated briefs and resource sensitivity are in `examples/human_capital/`.
- Added an executive brief, substantive case report, two official employer requirement mappings, methods/contracts, two-minute demonstration and full-module desktop/mobile screenshots.

## Validation evidence

- Full unit suite: **94 tests passed** (71 existing, 23 human-capital regressions).
- Existing journey regression: **500 cases + 32 hard-gate edges passed, zero issues**. Detailed local record: `build/career-fit-0.7.0-scenario-audit.json`.
- Ruff and compilation checks passed; `git diff --check` passed.
- Real browser: 1440px desktop and 390px mobile; review confirmation, edited-input invalidation, budget/hour changes, ROI assumptions, named skill gaps, Markdown/JSON and original PDF exports, and safe transfer from consumer evidence to proposed work samples. No page errors or document-level horizontal overflow. The new browser runner is included in CI.
- Wheel and sdist both contain font copyright/license, attribution notice, market snapshot, demo inputs and UI assets. Clean temporary environments outside the source checkout executed offline `invest`, `workforce`, `market`, both console-script namespaces and PDF generation. User output artifacts are absent from both distributions.
- Source retrieval: BLS/O*NET downloaded on November 16, 2026; 3 occupations and 105 exact `.00` importance ratings. Row counts, sizes, vintages and source paths recorded; no explicit hashes or statistical multiple-testing procedures used.

## Independent review and repairs

Two independent read-only reviewers covered requirements, calculations, edge cases, code quality, tests and runtime. Repairs included filled-role composition in cost comparisons, protected/proxy keys in nested skill maps, custom-ID/label binding, all-source freshness, malformed snapshot validation, taxonomy ambiguity and exact mapping, safe user transfer, explicit DCF assumptions, named gaps, and pending/in-flight consumer review/comparison invalidation. Both focused re-reviews found **no unresolved P0/P1 or material requirement gap**.

## Publication

Version: **0.7.0**. Branch: `codex/human-capital-0.7.0`.

- Reviewed change: https://github.com/JoeDHJ/career-fit/pull/25
- Full cloud CI passed: https://github.com/JoeDHJ/career-fit/actions/runs/43824587271 (Python 3.10–3.14, original Atlas integration, independent capital browser, release smoke and journey regression).
- Release destination: https://github.com/JoeDHJ/career-fit/releases/tag/v0.7.0
- Package destination: https://pypi.org/project/career-fit/0.7.0/
- Distribution status: https://github.com/JoeDHJ/career-fit/actions/workflows/publish.yml

The existing GitHub release workflow publishes the immutable version to PyPI. The release page and publishing workflow provide the final distribution status. No user output files were committed or modified.
