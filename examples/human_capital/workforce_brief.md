# Career Fit human capital decision brief

Input status: synthetic_employee_cohort_and_costs; actual_ONET_importance_weights
Currency: USD. All training outcomes and personal/cohort inputs are scenarios.

## Workforce allocation

Maximize filled positions, then minimize incremental economic cost, then prefer internal moves. Exact enumeration within the stated model and search limit.

| Scenario | Filled | Unfilled | Cash cost | Economic cost | Released hours |
| --- | ---: | ---: | ---: | ---: | ---: |
| no_training | 3 | 1 | 7000.0 | 7000.0 | 0 |
| external_only | 1 | 3 | 7000.0 | 7000.0 | 0 |
| internal_only | 4 | 0 | 1400.0 | 3016.0 | 56.0 |
| hybrid | 4 | 0 | 1400.0 | 3016.0 | 56.0 |

Additional positions filled versus no training: 1; economic cost difference: -3984.0.
Cost savings at equal coverage: Not supplied. A comparison with different filled positions is not a like-for-like saving.

## Proposed hybrid assignments

| Role / position | Employee | Route | Training | Economic cost |
| --- | --- | --- | --- | ---: |
| ops / 1 | E03 | direct_internal | Not supplied | 0.0 |
| ops / 2 | E01 | train_and_move | systems | 1320.0 |
| people / 1 | E04 | direct_internal | Not supplied | 0.0 |
| people / 2 | E02 | train_and_move | math | 1696.0 |

## Assessment before mobility

- Systems evaluation practicum: Tested workforce dashboard and decision-log walkthrough. Completion: Human assessor confirms systems-evaluation threshold using a common rubric.
- Operations mathematics bridge: Hand-checked allocation model and sensitivity memo. Completion: Independent reviewer reproduces the optimum and verifies feasibility.

## Employee–role evidence gaps

| Employee | Role | Eligibility | Weighted coverage | Gaps on scenario 0–1 scale |
| --- | --- | --- | ---: | --- |
| E01 | ops | met | 0.921 | Systems Evaluation (2.B.4.h): 0.2 |
| E02 | ops | met | 0.882 | Mathematics (2.A.1.e): 0.2; Systems Evaluation (2.B.4.h): 0.1 |
| E03 | ops | met | 1.0 | None |
| E04 | ops | met | 0.9215 | Mathematics (2.A.1.e): 0.2 |
| E05 | ops | unknown | 0.7684 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E06 | ops | not_met | 0.9605 | Systems Evaluation (2.B.4.h): 0.1 |
| E01 | people | met | 0.9261 | Systems Evaluation (2.B.4.h): 0.25 |
| E02 | people | met | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E03 | people | unknown | 0.9762 | Speaking (2.A.1.d): 0.05 |
| E04 | people | met | 1.0 | None |
| E05 | people | met | 0.8365 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05; Speaking (2.A.1.d): 0.1; Systems Evaluation (2.B.4.h): 0.25 |
| E06 | people | unknown | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |

## Public market context

Coverage: available; geography: exact.
Operations research analysts (SOC 2018 15-2031), US, 2025–2035: employment 113100; projected annual openings 7500; projected change 11.9%; median annual wage 88940.0 USD (2025 prices).
- [onet31-essential_skills](https://www.onetcenter.org/dl_files/database/db_31_0_csv/essential_skills.csv), O*NET 31.0 (August 2026), retrieved 2026-11-16T06:47:43+00:00; estimated.
- [onet31-transferable_skills](https://www.onetcenter.org/dl_files/database/db_31_0_csv/transferable_skills.csv), O*NET 31.0 (August 2026), retrieved 2026-11-16T06:47:43+00:00; estimated.
- [bls-ep-2025-2035](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm), Table 1.2, 2025–2035 (August 2026), retrieved 2026-11-16T06:47:43+00:00; estimated.

Coverage: available; geography: exact.
Human resources specialists (SOC 2018 13-1071), US, 2025–2035: employment 939700; projected annual openings 73700; projected change 6.4%; median annual wage 75940.0 USD (2025 prices).

## Assumptions and decision boundary

- Employee levels and thresholds are synthetic or reviewed user inputs on a 0–1 scenario scale; O*NET importance weights are not employee proficiency thresholds.
- Each employee may fill one position and take at most one training package. Package prerequisites use pre-training evidence. Training outcomes require assessment before any move.
- Unknown or unmet eligibility excludes an assignment. External candidates are assumed qualified only where explicitly marked met.
- Economic cost includes fees plus released employee time. External hiring costs are incremental recruitment/onboarding costs; recurring compensation and displaced duties are outside this short-run comparison.
- No protected attributes, demographic fields, names, addresses, or employer prestige are accepted as matching variables. IDs are for bookkeeping only.
- This is a planning aid for voluntary development and reviewed mobility, not authorization for hiring, dismissal or automatic personnel decisions.
