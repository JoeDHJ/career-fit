# Human capital investment under time and budget constraints

Prepared by Haojian Dui · November 16, 2026 · Public-data demonstration

## Decision and evidence

An applicant needs a useful development plan, not a list of every missing keyword. An organization needs to compare development, mobility and hiring under the same resources. Career Fit addresses both questions with a reviewed evidence map and a small, transparent optimization model.

This case combines actual public occupational observations with deliberately fictional people. The personal case uses a decision-relevant paraphrase of an [official Amazon Talent Intelligence Analyst posting, 10569918](https://www.amazon.jobs/en/jobs/10569918/talent-intelligence-analyst-global-specialty-recruiting), checked November 16, 2026. The candidate is not Haojian Dui and the training options are illustrative work projects, not actual provider offers. The organization case uses six synthetic employees and four assumed vacancies. No customer, employer engagement or observed company workforce is claimed.

The source snapshot contains [BLS table 1.2, 2025–2035](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm) and the [O*NET 31.0 Database](https://www.onetcenter.org/database.html). BLS publishes national occupational employment estimates, wage estimates and projections. O*NET publishes occupation-level skill importance ratings. Neither source observes these fictional people's proficiency or their response to training.

| US occupation (SOC 2018) | Employment, 2025 | Average annual openings, 2025–2035 | Projected change | Median annual wage, 2025 USD |
| --- | ---: | ---: | ---: | ---: |
| Human resources specialists, 13-1071 | 939,700 | 73,700 | 6.4% | $75,940 |
| Operations research analysts, 15-2031 | 113,100 | 7,500 | 11.9% | $88,940 |
| Data scientists, 15-2051 | 275,600 | 24,800 | 34.6% | $120,230 |

Employment and openings are converted from thousands to persons. Wages are nominal 2025 values. Openings include replacement needs and are projections, not counts of current job postings. These occupations provide broad context; they do not establish that a particular employer will hire the candidate. Seattle receives an explicitly labeled national fallback. Non-US locations remain uncovered by this snapshot.

## Personal investment decision

The fictional candidate brings academic research, Python work samples and writing, with no corporate recruiting or executive-advising experience. The reviewed map separates direct research evidence, transferable communication and visualization evidence, missing proof, and hard experience gates. Manual review adds spreadsheet and CRM requirements that the English-first dictionary does not safely infer. Custom skill labels are bound to catalog outcomes so an edited requirement cannot inherit an unrelated course match.

The candidate supplies $600 cash, 90 total hours, seven hours per week, a six-hour preparation reserve and a $20 hourly time value. The planner evaluates eligible course subsets and prerequisite orderings. It maximizes the importance of distinct reviewed gaps addressed, then minimizes cost. It does not assign a monetary return to the occupation's wage.

The selected portfolio is:

| Work project | Assumed hours | Fee | Reviewable output |
| --- | ---: | ---: | --- |
| Spreadsheet scenario model | 20 | $80 | Reconciled training-versus-hiring cost workbook |
| Executive research translation | 18 | $60 | Decision memo and short briefing |
| AI-assisted research verification | 24 | $180 | Source-linked workflow with a manually checked error log |
| Evidence preparation and review | 6 | $0 | Eligibility checklist, evidence card and application review |
| **Total** | **68** | **$320** | **Economic cost: $320 + 68 × $20 = $1,680** |

The $500 leadership seminar has unknown entry eligibility and is excluded. A dashboard project has value but does not fit alongside the selected targets within the available hours. Selection is a scenario about feasible work, not a claim that proficiency has improved.

By day 30, the candidate should have a sourced eligibility checklist and one translated evidence card, alongside the scheduled work project. By day 60, a reviewer should be able to run the work sample and reconcile its calculations. By day 90, the evidence map and application pack should link every new claim to completed work. The [generated plan](../examples/human_capital/investment_brief.md) gives phase-specific hours, artifacts and assessment criteria.

The central application conclusion is unchanged by the course portfolio: the senior role's two experience gates remain unmet. Develop adjacent-role evidence and verify any alternative qualifying route with the employer. The product does not treat skill overlap as eligibility.

Sensitivity identifies the binding resource. With 40 hours and $150, the spreadsheet project plus preparation is feasible for $80 and 26 hours. With 68 hours and a $150 budget, spreadsheet and communication work total $140 and 44 hours; expanding the cash budget to $320 adds the AI work. Raising total hours from 90 to 110 without increasing seven weekly hours does not expand the 90-day capacity. All case sensitivity outputs are saved in [sensitivity.json](../examples/human_capital/sensitivity.json).

The base case has no benefit input, so ROI and NPV are absent. A user can enter an explicitly justified paid-project income or other incremental benefit to calculate a scenario return, with 0.5×/1×/1.5× sensitivity. This does not turn a supplied assumption into an estimated treatment effect.

## Organization decision

The organization assumes two operations-analysis vacancies and two people-reporting vacancies. Mathematics, critical thinking, speaking and systems evaluation use exact O*NET skill IDs and published importance weights for operations research analysts and human resources specialists. Competency thresholds and employee levels are on a separate 0–1 scenario scale. The public importance ratings do not validate these thresholds.

The model permits one position and at most one training package per employee, observes individual and cohort release-hour limits, and respects package seats and prerequisites. Unknown or unmet role eligibility prevents an assignment even if its skill coverage is high. Two packages have one seat each: a 24-hour systems-evaluation practicum costing $600, and a 32-hour operations-mathematics bridge costing $800. Proposed training outcomes must be assessed before mobility.

At $10,000 cash and 56 released hours:

| Strategy | Vacancies filled | Fees / hiring costs | Economic cost | Released hours |
| --- | ---: | ---: | ---: | ---: |
| External hiring only | 1 of 4 | $7,000 | $7,000 | 0 |
| Existing skills plus hiring | 3 of 4 | $7,000 | $7,000 | 0 |
| Internal mobility plus training | 4 of 4 | $1,400 | $3,016 | 56 |
| Hybrid optimum | 4 of 4 | $1,400 | $3,016 | 56 |

The proposed hybrid uses E03 directly in operations, E01 after the systems package in operations, E04 directly in people reporting, and E02 after the mathematics bridge in people reporting. The last assignment illustrates a useful tradeoff: the bridge's combined outcome also closes E02's systems-evaluation gap, freeing the scarce systems seat for E01. A greedy choice for one employee can therefore obstruct the cohort solution.

Released time costs 24 hours × $30/hour = $720 for E01 and 32 hours × $28/hour = $896 for E02. Adding $1,400 fees yields $3,016. At only 24 release hours and $1,400 cash, three positions can be filled; at zero release hours, only the two directly eligible internal moves fit that cash budget. At $30,000 and 56 release hours, both the no-training and hybrid strategies fill the same two operations and two people-reporting positions. Their $15,000 versus $3,016 incremental costs imply an $11,984 scenario saving at equal role coverage.

These are incremental recruitment, onboarding and training costs. Recurring compensation, employee preferences, displaced duties and backfill are outside this short-run example. A real employer should supply those material costs and assess employee consent before treating this as a business case. No personal attributes or demographic variables enter the allocation; custom skill fields are reviewed for semantic proxy risks. Nothing in the model authorizes a personnel action.

## Delivery and reproducibility

The [personal brief](../examples/human_capital/investment_brief.md) and [workforce brief](../examples/human_capital/workforce_brief.md) are generated from the same result objects used by the interface. JSON inputs, results and sensitivity records are included. Run `python tools/run_human_capital_cases.py` from the repository to regenerate the complete case without network access. `career-fit invest` and `career-fit workforce` work from an installed package outside the source tree.

The [methods](human-capital-methods.md) state the objective, constraints, costs, units and source contract. The [employer requirements matrix](employer-requirements.md) connects the artifacts to actual people-analytics and talent-intelligence work. The browser demonstration and validation record are in [implementation status](implementation-status.md).
