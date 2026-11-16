# Human capital methods and interfaces

Career Fit 0.7 preserves the reviewed single-role `career_fit.v0.5` and comparison `career_fit.compare.v0.4` contracts. New contracts are `career_fit.investment.v1`, `career_fit.workforce.v1`, and the shared public context contract `portfolio.v1`. Product and schema versions are separate.

## Personal investment

The planner recomputes the role analysis from `analysis_input` (job text, candidate text, language, structured evidence and review). It requires visible reviewed results. Requirement removals, additions, importance edits, gate overrides and labeled evidence carry into the plan. A training choice never writes back a skill claim or changes an eligibility gate.

Each course has a stable ID, hours, fee, skill IDs, prerequisite skill IDs, eligibility (`met`, `unknown`, `not_met`), work-sample artifact and completion criterion. These are supplied assumptions, not measured learning effects or provider recommendations. The demo prices are illustrative project costs, not advertised course prices. A user should replace them with actual quotes and accessible learning resources. Non-English applicants can use the existing trusted-translation and user-labeled evidence routes before entering this workspace. Neither a degree nor a resume is required by the planner itself.

Enumerate subsets of up to 12 options. Exclude unknown/unmet course eligibility. Topologically order selected courses: prerequisites must come from reviewed direct work/project evidence, explicitly confirmed prerequisite IDs, or earlier selected training. Transferable evidence does not automatically meet a prerequisite. Cycles and unsatisfied prerequisites make that subset infeasible. Duplicate skill coverage is counted once.

The objective is lexicographic: maximize the sum of importance weights of distinct reviewed gaps addressed by course outcomes, minimize economic cost, then minimize hours. A direct-evidence requirement is not a training target. Coverage is a planning quantity; it does not estimate post-training proficiency, hiring probability or returns. The output retains uncovered requirements. Alternatives show the eight highest-ranked feasible subsets, not every feasible subset.

Cash constraint: sum of course fees ≤ cash budget. Hours constraint: course hours + preparation reserve ≤ min(total available hours, weekly hours × 90/7). The default six-hour reserve covers gate verification, translation of existing evidence, critique and final application review. Course hours include their deliverable. Training is scheduled sequentially into 30-day phases, with hours and due days shown; no course is assumed completed because it was selected.

Economic cost = fees + supplied foregone income + hours × hourly time value. If the hourly value is missing, total economic cost is missing; the tie-breaker uses fees plus any explicit foregone income. An intentional zero hourly value is accepted. Positive hourly valuation and positive course foregone income cannot be combined, preventing duplicate valuation of the same time. Currency is declared once per input; convert quoted costs before entering them.

No benefit input means no ROI or NPV. An explicit benefit requires annual incremental amount, integer years, discount rate and a written basis. All costs occur at time zero, benefits at each year-end. NPV discounts benefits; ROI is cumulative undiscounted net benefits divided by economic cost. ROI is undefined for zero cost. Sensitivity uses 0.5×, 1× and 1.5× the entered benefit. Wage differences between occupations are never substituted for training benefits.

## Workforce allocation

The small exact solver accepts 1–8 pseudonymous employees, up to four roles, six total positions, and six training packages. One employee fills at most one position and takes at most one package. Package prerequisites use initial skill evidence. Multiple modules can be defined as a single reviewed package with their full combined hours, cost and outcomes.

Employee levels and role thresholds lie on an explicitly synthetic/user-reviewed 0–1 competency scale. A role is feasible only if every named skill meets its threshold and role eligibility is `met`. Missing skill evidence is treated as zero **within this supplied planning rubric**; this is not a claim of zero real ability. O*NET importance ratings (IM, 1–5) weight descriptive gap coverage. They do not set employee thresholds or validate training effects.

Constraints cover employee release hours, cohort release hours, cash budget and package seats. Unknown/unmet employee or training eligibility is excluded. External hiring requires an explicit incremental cost and `external_eligible: met` scenario assumption. No-training plus hiring, external-only, internal plus training, and hybrid scenarios all use the same cash/hour budgets.

Exact enumeration maximizes filled positions, then minimizes incremental economic cost, then prefers internal moves. Direct internal moves cost zero in this incremental short-run model. Released time is valued at each employee's supplied hourly cost. External costs include recruitment/onboarding, not recurring salary; displaced duties and backfill are outside this example and should be added to a decision model where material. The model stops with an actionable error after 300,000 search nodes rather than presenting a partial answer as an optimum. This is a small-cohort decision example, not a production optimizer for thousands of employees.

A cost saving is reported only when the same number of each role's positions is filled. If role coverage differs, report the coverage and cost differences separately. The outcome is a proposal for human assessment and voluntary mobility. No automatic hiring, termination or employee exclusion workflow is implemented. Employee, role and training inputs use strict field allowlists; demographic attributes, names, addresses and institution prestige are not accepted matching fields. Recognizable protected/proxy labels are also rejected inside skill maps; a human must review custom skill definitions for less obvious semantic proxies.

## Offline market adapter

`career-fit market --occupation-id 15-2031 --geography US` reads the bundled snapshot. `--snapshot-file` accepts a replacement `portfolio.v1` JSON file; the investment input can also carry `market_snapshot`. No Atlas service is required. The original optional live Atlas occupation/review integration is retained separately in the job seeker workspace.

Every source carries its ID, URL, retrieval time, vintage, geography, unit, period, currency/price year where relevant, schema and observed/estimated/scenario status. Occupations retain native ID, taxonomy and vintage. The bundled source is BLS table 1.2 (2025–2035), with employment/openings converted from thousands to persons and wages left in nominal 2025 USD. These are survey estimates and official projections, not local vacancy counts. O*NET 31.0 supplies 105 importance ratings: 35 skills for each of three exact `.00` occupations. O*NET-SOC 2019 `.00` to SOC 2018 parent matching has weight 1 for these selected occupations only; there is no general many-to-many crosswalk or aggregation.

The interface reports exact geography, US national-only fallback, missing coverage, stale retrieval (>180 days), future-dated retrieval and missing metrics. `null` remains missing; zero stays zero. Seattle requests may show national context but are labeled `national_only`. Non-US locations do not silently receive US values. Retrieval freshness is distinct from data vintage. Use `--as-of 2026-11-16` for the recorded case. The source-refresh script requires the expected BLS vintage and fails if the upstream table changes.

## Execution and privacy

```powershell
career-fit invest --format markdown
career-fit workforce --format json
career-fit market --occupation-id 15-2031 --geography US
python tools/run_human_capital_cases.py
career-fit serve
# http://127.0.0.1:8766/capital
```

`invest` and `workforce` accept `--input path.json`. Omitting the input runs the attributed fictional demonstration. HTTP POST `/api/invest` and `/api/workforce` return the result and Markdown generated from that same result; bodies are limited to 320,000 bytes. Input edits hide stale results and disable exports. The job seeker workspace transfers a reviewed input to the planner only on the user's button click; temporary session storage is removed after transfer. The human capital workspace makes no external AI calls, saves no personal inputs and requires explicit review. Original Markdown/PDF exports and optional review-sharing confirmation remain available in the job seeker workspace.
