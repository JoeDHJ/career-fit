# Demonstration and interview guide

Use these statements only after you can reproduce and explain the corresponding work. The fictional learner and employees are not personal employment experience. Acknowledge AI-assisted development when describing the workflow; demonstrate your own judgment through adaptation and error diagnosis.

## Two-minute product demonstration

0:00–0:25 — Open `/showcase`. Explain the problem: role descriptions, candidate claims and learning plans carry different evidence, so a single opaque matching score hides actionable distinctions.

0:25–1:00 — Open Learning plan. Show the archived NHS role and provider facts. Compare the 46-hour portfolio, then reduce available hours and recompute. Explain the changed task choice and one experience gate that training cannot erase.

1:00–1:30 — Expand a practice option and the task assessment. Show the artifact, acceptance criterion and four rubric dimensions. Explain that a declared pass must return to a fresh evidence review; it does not silently become proficiency.

1:30–2:00 — Return to the showcase, compare no-training and hybrid coverage, then show the learning-effect sensitivity. Close with the boundary: the system demonstrates conditional planning, while actual learning gains and human usability still need observation.

## Ten-minute technical route

Spend two minutes on source selection, archived/indexed states, SQL normalization and qualification gates. Spend two on the exact versus overlap metric and why one-to-one matching matters. Spend three on variables, eligibility/consent, seat/cash/hour constraints, role priority and incremental costs. Spend two on the progress/evidence round trip and one on remaining validation.

Be ready to explain:

- Why an overlap F1 can look much better than exact F1, and why the averaged baseline does not outperform the legacy test exact F1 here.
- Why a mentioned skill is different from an explicitly required skill and why a small mixed sample cannot estimate labor-market prevalence.
- Why future task hours cannot be inferred by subtracting actual hours from planned hours.
- Why equal numbers of filled positions can still be incomparable when the role mix differs.
- How missing consent, a longer lead time, a lower learning multiplier or expensive backfill changes feasibility.
- Why a lexicographic priority objective can choose fewer high-priority positions, and what would change under a monetary value objective.
- What the model omits: uncertainty distributions, recurring wage differences, multi-course training, actual performance and employee preferences beyond recorded consent.

## Suggested project description

“Built an inspectable career and human-capital workbench connecting attributed employer research, SQLite analysis, reviewed work evidence and constrained investment decisions. Evaluated three extraction baselines on official SkillSpan splits, implemented exact and mixed-integer workforce allocation, and developed a task-assessment workflow with browser and package verification.”

Qualify this description with your actual contribution and the assistance used. Add specific outcome numbers only with “synthetic scenario” or “external extraction benchmark” labels. Do not claim employer savings, job-placement gains, production HR integration or independently validated proficiency.

## Preparation over 30/60/90 days

By day 30, rerun SQL and the documented cases, complete the reconciliation task and explain a changed malformed-input example without the solution. By day 60, replace the fictional learner with your actual redacted evidence, obtain an artifact review and conduct the first local task walkthroughs using the feedback instrument. By day 90, select concrete role descriptions, prepare role-specific evidence and practice the technical questions above. Keep actual task records, feedback and interview adjustments; do not present planned milestones as completed achievements.
