# Workforce reconciliation work sample

All ten rows are synthetic. This task assesses data reasoning and communication; it is not an employee dataset or evidence of a completed learner project.

Create a SQLite table from `workforce.csv`. Produce: (1) raw counts by snapshot; (2) duplicate, missing-ID and out-of-range FTE exceptions; (3) an accepted-record headcount and FTE summary by department; (4) a short management memo explaining how the exceptions affect the comparison. Define FTE range as 0–1 for this exercise. Exclude invalid rows and all copies of duplicate employee/snapshot keys until resolved; explain that quarantine rule rather than silently deduplicating.

Expected checks under that rule: September raw/accepted headcount 4/4, FTE 3.3; October raw/accepted row count 6/2, accepted headcount 2 and FTE 1.6. Four October rows are quarantined: both E03 rows, the missing-ID row and E05. You cannot infer genuine workforce contraction from the accepted-record change because unresolved exceptions affect coverage.

Submit SQL, a machine-readable exception list and a memo with units, denominators and assumptions. Record actual hours and artifact location in the learning workspace. Ask a reviewer to rerun the queries and add one new malformed row without giving you the fix. Rate correctness, reproducibility, interpretation and independence 0–3; a self-assessment must be labeled as such. All four dimensions need at least 2 for a declared pass.

Suggested 12-hour allocation: 2 hours setup, 4 queries, 2 validation, 2 memo and 2 review/adaptation. This is an analyst planning assumption, not observed completion time.
