# Career Fit human capital decision brief

Input status: Synthetic 30-employee business case; actual O*NET importance weights; scenario vacancies, consent, costs, learning effects and lead times
Currency: USD; cost price year: 2026. All training outcomes and personal/cohort inputs are scenarios.

## Workforce allocation

Maximize filled role-priority units, then minimize total scenario cost (fees, released time, backfill and vacancy delay/unfilled costs), then prefer internal moves. All economic inputs require review.

Horizon: 60.0 days; solver: milp; training effect multiplier: 1.0.
| Scenario | Filled | Priority units | Unfilled | Cash cost | Economic cost | Released hours |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_training | 10 | 18.0 | 2 | 32200.0 | 122000.0 | 0 |
| external_only | 4 | 8.0 | 8 | 32000.0 | 188000.0 | 0 |
| internal_only | 11 | 21.0 | 1 | 7800.0 | 75040.0 | 88.0 |
| hybrid | 12 | 24.0 | 0 | 21800.0 | 81040.0 | 88.0 |

Additional positions filled versus no training: 2; economic cost difference: -40960.0.
Cost savings at equal coverage: Not supplied. A comparison with different filled positions is not a like-for-like saving.

## Proposed hybrid assignments

| Role / position | Employee | Route | Training | Economic cost |
| --- | --- | --- | --- | ---: |
| ops / 1 | E09 | direct_internal | Not supplied | 1900.0 |
| ops / 2 | E15 | direct_internal | Not supplied | 1900.0 |
| ops / 3 | E21 | direct_internal | Not supplied | 1900.0 |
| ops / 4 | E27 | direct_internal | Not supplied | 1900.0 |
| people / 1 | E04 | direct_internal | Not supplied | 1600.0 |
| people / 2 | E10 | direct_internal | Not supplied | 1600.0 |
| people / 3 | E22 | direct_internal | Not supplied | 1600.0 |
| people / 4 | E28 | direct_internal | Not supplied | 1600.0 |
| data / 1 | E13 | train_and_move | systems | 10120.0 |
| data / 2 | E25 | train_and_move | systems | 10120.0 |
| data / 3 | E07 | train_and_move | science | 16800.0 |
| data / 4 | Not supplied | external_hire | Not supplied | 30000.0 |

## Incremental hybrid cost components

- training fee: 2400.00 USD
- backfill: 5400.00 USD
- released time: 2640.00 USD
- vacancy delay: 56600.00 USD
- external hiring: 14000.00 USD
- unfilled vacancy: 0.00 USD

Recurring compensation is outside this incremental scenario. Cost differences with different role coverage are not like-for-like savings.

## Assessment before mobility

- Systems evaluation practicum: Tested workforce dashboard and decision-log walkthrough. Completion: Human assessor confirms systems-evaluation threshold using a common rubric.
- Operations mathematics bridge: Hand-checked allocation model and sensitivity memo. Completion: Independent reviewer reproduces the optimum and verifies feasibility.
- Applied workforce analysis practicum: Reproducible workforce analysis and reviewed management memo. Completion: Assessor confirms the scenario competency thresholds on a common task rubric.

## Employee–role evidence gaps

| Employee | Role | Eligibility | Weighted coverage | Gaps on scenario 0–1 scale |
| --- | --- | --- | ---: | --- |
| E01 | ops | met | 0.921 | Systems Evaluation (2.B.4.h): 0.2 |
| E02 | ops | met | 0.882 | Mathematics (2.A.1.e): 0.2; Systems Evaluation (2.B.4.h): 0.1 |
| E03 | ops | met | 1.0 | None |
| E04 | ops | met | 0.9215 | Mathematics (2.A.1.e): 0.2 |
| E05 | ops | unknown | 0.7684 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E06 | ops | not_met | 0.9605 | Systems Evaluation (2.B.4.h): 0.1 |
| E07 | ops | met | 0.921 | Systems Evaluation (2.B.4.h): 0.2 |
| E08 | ops | met | 0.882 | Mathematics (2.A.1.e): 0.2; Systems Evaluation (2.B.4.h): 0.1 |
| E09 | ops | met | 1.0 | None |
| E10 | ops | met | 0.9215 | Mathematics (2.A.1.e): 0.2 |
| E11 | ops | unknown | 0.7684 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E12 | ops | not_met | 0.9605 | Systems Evaluation (2.B.4.h): 0.1 |
| E13 | ops | met | 0.921 | Systems Evaluation (2.B.4.h): 0.2 |
| E14 | ops | met | 0.882 | Mathematics (2.A.1.e): 0.2; Systems Evaluation (2.B.4.h): 0.1 |
| E15 | ops | met | 1.0 | None |
| E16 | ops | met | 0.9215 | Mathematics (2.A.1.e): 0.2 |
| E17 | ops | unknown | 0.7684 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E18 | ops | not_met | 0.9605 | Systems Evaluation (2.B.4.h): 0.1 |
| E19 | ops | met | 0.921 | Systems Evaluation (2.B.4.h): 0.2 |
| E20 | ops | met | 0.882 | Mathematics (2.A.1.e): 0.2; Systems Evaluation (2.B.4.h): 0.1 |
| E21 | ops | met | 1.0 | None |
| E22 | ops | met | 0.9215 | Mathematics (2.A.1.e): 0.2 |
| E23 | ops | unknown | 0.7684 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E24 | ops | not_met | 0.9605 | Systems Evaluation (2.B.4.h): 0.1 |
| E25 | ops | met | 0.921 | Systems Evaluation (2.B.4.h): 0.2 |
| E26 | ops | met | 0.882 | Mathematics (2.A.1.e): 0.2; Systems Evaluation (2.B.4.h): 0.1 |
| E27 | ops | met | 1.0 | None |
| E28 | ops | met | 0.9215 | Mathematics (2.A.1.e): 0.2 |
| E29 | ops | unknown | 0.7684 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E30 | ops | not_met | 0.9605 | Systems Evaluation (2.B.4.h): 0.1 |
| E01 | people | met | 0.9261 | Systems Evaluation (2.B.4.h): 0.25 |
| E02 | people | met | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E03 | people | unknown | 0.9762 | Speaking (2.A.1.d): 0.05 |
| E04 | people | met | 1.0 | None |
| E05 | people | met | 0.8365 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05; Speaking (2.A.1.d): 0.1; Systems Evaluation (2.B.4.h): 0.25 |
| E06 | people | unknown | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E07 | people | met | 0.9261 | Systems Evaluation (2.B.4.h): 0.25 |
| E08 | people | met | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E09 | people | unknown | 0.9762 | Speaking (2.A.1.d): 0.05 |
| E10 | people | met | 1.0 | None |
| E11 | people | met | 0.8365 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05; Speaking (2.A.1.d): 0.1; Systems Evaluation (2.B.4.h): 0.25 |
| E12 | people | unknown | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E13 | people | met | 0.9261 | Systems Evaluation (2.B.4.h): 0.25 |
| E14 | people | met | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E15 | people | unknown | 0.9762 | Speaking (2.A.1.d): 0.05 |
| E16 | people | met | 1.0 | None |
| E17 | people | met | 0.8365 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05; Speaking (2.A.1.d): 0.1; Systems Evaluation (2.B.4.h): 0.25 |
| E18 | people | unknown | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E19 | people | met | 0.9261 | Systems Evaluation (2.B.4.h): 0.25 |
| E20 | people | met | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E21 | people | unknown | 0.9762 | Speaking (2.A.1.d): 0.05 |
| E22 | people | met | 1.0 | None |
| E23 | people | met | 0.8365 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05; Speaking (2.A.1.d): 0.1; Systems Evaluation (2.B.4.h): 0.25 |
| E24 | people | unknown | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E25 | people | met | 0.9261 | Systems Evaluation (2.B.4.h): 0.25 |
| E26 | people | met | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E27 | people | unknown | 0.9762 | Speaking (2.A.1.d): 0.05 |
| E28 | people | met | 1.0 | None |
| E29 | people | met | 0.8365 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05; Speaking (2.A.1.d): 0.1; Systems Evaluation (2.B.4.h): 0.25 |
| E30 | people | unknown | 0.9556 | Systems Evaluation (2.B.4.h): 0.15 |
| E01 | data | met | 0.9214 | Systems Evaluation (2.B.4.h): 0.3 |
| E02 | data | unknown | 0.8027 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E03 | data | met | 0.964 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05 |
| E04 | data | unknown | 0.8551 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1 |
| E05 | data | unknown | 0.686 | Mathematics (2.A.1.e): 0.4; Critical Thinking (2.A.2.a): 0.2; Speaking (2.A.1.d): 0.05; Systems Evaluation (2.B.4.h): 0.3 |
| E06 | data | unknown | 0.8757 | Mathematics (2.A.1.e): 0.1; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E07 | data | met | 0.9214 | Systems Evaluation (2.B.4.h): 0.3 |
| E08 | data | unknown | 0.8027 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E09 | data | met | 0.964 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05 |
| E10 | data | unknown | 0.8551 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1 |
| E11 | data | unknown | 0.686 | Mathematics (2.A.1.e): 0.4; Critical Thinking (2.A.2.a): 0.2; Speaking (2.A.1.d): 0.05; Systems Evaluation (2.B.4.h): 0.3 |
| E12 | data | unknown | 0.8757 | Mathematics (2.A.1.e): 0.1; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E13 | data | met | 0.9214 | Systems Evaluation (2.B.4.h): 0.3 |
| E14 | data | unknown | 0.8027 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E15 | data | met | 0.964 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05 |
| E16 | data | unknown | 0.8551 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1 |
| E17 | data | unknown | 0.686 | Mathematics (2.A.1.e): 0.4; Critical Thinking (2.A.2.a): 0.2; Speaking (2.A.1.d): 0.05; Systems Evaluation (2.B.4.h): 0.3 |
| E18 | data | unknown | 0.8757 | Mathematics (2.A.1.e): 0.1; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E19 | data | met | 0.9214 | Systems Evaluation (2.B.4.h): 0.3 |
| E20 | data | unknown | 0.8027 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E21 | data | met | 0.964 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05 |
| E22 | data | unknown | 0.8551 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1 |
| E23 | data | unknown | 0.686 | Mathematics (2.A.1.e): 0.4; Critical Thinking (2.A.2.a): 0.2; Speaking (2.A.1.d): 0.05; Systems Evaluation (2.B.4.h): 0.3 |
| E24 | data | unknown | 0.8757 | Mathematics (2.A.1.e): 0.1; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E25 | data | met | 0.9214 | Systems Evaluation (2.B.4.h): 0.3 |
| E26 | data | unknown | 0.8027 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |
| E27 | data | met | 0.964 | Mathematics (2.A.1.e): 0.05; Critical Thinking (2.A.2.a): 0.05 |
| E28 | data | unknown | 0.8551 | Mathematics (2.A.1.e): 0.3; Critical Thinking (2.A.2.a): 0.1 |
| E29 | data | unknown | 0.686 | Mathematics (2.A.1.e): 0.4; Critical Thinking (2.A.2.a): 0.2; Speaking (2.A.1.d): 0.05; Systems Evaluation (2.B.4.h): 0.3 |
| E30 | data | unknown | 0.8757 | Mathematics (2.A.1.e): 0.1; Critical Thinking (2.A.2.a): 0.1; Systems Evaluation (2.B.4.h): 0.2 |

## Public market context

Coverage: available; geography: exact.
Operations research analysts (SOC 2018 15-2031), US, 2025–2035: employment 113100; projected annual openings 7500; projected change 11.9%; median annual wage 88940.0 USD (2025 prices).
- [onet31-essential_skills](https://www.onetcenter.org/dl_files/database/db_31_0_csv/essential_skills.csv), O*NET 31.0 (August 2026), retrieved 2026-11-16T06:47:43+00:00; estimated.
- [onet31-transferable_skills](https://www.onetcenter.org/dl_files/database/db_31_0_csv/transferable_skills.csv), O*NET 31.0 (August 2026), retrieved 2026-11-16T06:47:43+00:00; estimated.
- [bls-ep-2025-2035](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm), Table 1.2, 2025–2035 (August 2026), retrieved 2026-11-16T06:47:43+00:00; estimated.

Coverage: available; geography: exact.
Human resources specialists (SOC 2018 13-1071), US, 2025–2035: employment 939700; projected annual openings 73700; projected change 6.4%; median annual wage 75940.0 USD (2025 prices).

Coverage: available; geography: exact.
Data scientists (SOC 2018 15-2051), US, 2025–2035: employment 275600; projected annual openings 24800; projected change 34.6%; median annual wage 120230.0 USD (2025 prices).

## Assumptions and decision boundary

- Employee levels and thresholds are synthetic or reviewed user inputs on a 0–1 scenario scale; O*NET importance weights are not employee proficiency thresholds.
- Each employee may fill one position and take at most one training package. Package prerequisites use pre-training evidence. Training outcomes require assessment before any move.
- Unknown or unmet eligibility excludes an assignment. External candidates are assumed qualified only where explicitly marked met.
- Economic cost includes fees, released time, supplied backfill and vacancy delay/unfilled costs over the stated horizon. Recurring compensation is outside this incremental comparison; zero/default costs mean omitted by the scenario, not empirically free.
- Role priorities, lead times, competency thresholds and economic losses are scenario assumptions. Only reviewed eligibility and consent permit an internal assignment; completed training must still pass assessment.
- No protected attributes, demographic fields, names, addresses, or employer prestige are accepted as matching variables. IDs are for bookkeeping only.
- This is a planning aid for voluntary development and reviewed mobility, not authorization for hiring, dismissal or automatic personnel decisions.
