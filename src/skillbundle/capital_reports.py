"""Reports built from the exact reviewed decision output."""

from __future__ import annotations


def clean(value) -> str:
    return (
        str(value if value is not None else "Not supplied")
        .replace("|", "/")
        .replace("\n", " ")
    )


def capital_markdown(result: dict) -> str:
    lines = [
        "# Career Fit human capital decision brief",
        "",
        f"Input status: {clean(result.get('input_status'))}",
        f"Currency: {clean(result['currency'])}; cost price year: {clean(result.get('price_year'))}. All training outcomes and personal/cohort inputs are scenarios.",
        "",
    ]
    if result["schema_version"] == "career_fit.investment.v1":
        best = result["best_plan"]
        lines += ["## Personal investment", "", result["objective"], ""]
        if best:
            lines += [
                f"Selected: {', '.join(best['course_ids']) or 'Evidence preparation only'}",
                f"Cash cost: {best['cash_cost']}; economic cost: {clean(best['economic_cost'])}; total hours: {best['hours']} (including {result['preparation_hours']} preparation hours).",
                "",
            ]
        else:
            lines += [result["infeasibility_reason"], ""]
        lines += [
            "## Evidence map",
            "",
            "| Requirement | Current evidence | Training target |",
            "| --- | --- | --- |",
        ]
        for row in result["evidence_map"]:
            lines.append(
                f"| {clean(row['skill'])} | {clean(row['status'])} | {'Yes, subject to assessment' if row['training_target'] else 'No'} |"
            )
        lines += ["", "## Eligibility gates", ""]
        for gate in result["eligibility_gates"]:
            lines.append(f"- {clean(gate['canonical_skill'])}: {clean(gate['status'])}")
        if not result["eligibility_gates"]:
            lines.append("No gate was extracted; verify the full posting.")
        lines += ["", "## 30/60/90-day plan", ""]
        for phase in result["timeline"]:
            lines += [f"### By day {phase['day']}", ""]
            lines += [f"- {a}" for a in phase["actions"]]
            for training in phase["training"]:
                lines += [
                    f"- {training['title']}: {training['hours']} hours in this phase; due day {training['due_day']}.",
                    f"  Artifact: {training['artifact']}. Completion: {training['completion_criterion']}.",
                ]
            lines += [
                f"- Deliverable: {phase['artifact']}.",
                f"- Completion: {phase['completion_criterion']}",
                "",
            ]
        lines += [
            "## Returns",
            "",
            clean(result["returns"].get("reason", result["returns"].get("timing"))),
            "",
        ]
        if result["returns"]["status"] == "scenario":
            lines += [
                f"Annual incremental benefit: {result['returns']['annual_benefit']} {result['currency']}; years: {result['returns']['years']}; discount rate: {result['returns']['discount_rate']}.",
                "",
            ]
            lines += [
                f"Benefit basis: {clean(result['returns']['benefit_basis'])}",
                "",
                "| Benefit multiplier | NPV | Cumulative ROI (%) |",
                "| --- | ---: | ---: |",
            ]
            for s in result["returns"]["sensitivity"]:
                lines.append(
                    f"| {s['benefit_multiplier']} | {s['npv']} | {clean(s['roi_pct'])} |"
                )
        lines += ["", "## Resource facts and practice assumptions", ""]
        for course in best["selected_courses"] if best else []:
            lines += [
                f"- {clean(course['title'])}: planned {course['hours']} hours; fee {course['fee']}. Provider hours: {clean(course.get('provider_hours'))}. {clean(course.get('provider_fee_scope', 'Practice fee is a scenario assumption'))}.",
                f"  Artifact: {clean(course['artifact'])}. Check: {clean(course['completion_criterion'])}.",
            ]
            source = course.get("source", {})
            if source:
                lines.append(
                    f"  Source: [{clean(source['source_id'])}]({source['source_url']}), checked {clean(source['retrieved_at'])}."
                )
        progress = result.get("progress", {})
        lines += [
            "",
            "## Work-sample progress",
            "",
            progress.get("interpretation", "No progress supplied."),
            "",
        ]
        for record in progress.get("records", []):
            lines += [
                f"- {clean(record['title'])}: {record['status']}; assessment {record['assessment']}; reported actual hours {clean(record['actual_hours'])}.",
                f"  Artifact: {clean(record['artifact'])}. Review: {clean(record['review_note'])}. Rubric: {clean(record['rubric'])}. {record['evidence_status']}.",
            ]
        contexts = [result["market_context"]]
    else:
        lines += [
            "## Workforce allocation",
            "",
            result["objective"],
            "",
            f"Horizon: {result.get('horizon_days', 90)} days; solver: {result.get('solver', 'exact')}; training effect multiplier: {result.get('training_effect_multiplier', 1)}.",
            "| Scenario | Filled | Priority units | Unfilled | Cash cost | Economic cost | Released hours |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for name, scenario in result["scenarios"].items():
            lines.append(
                f"| {name} | {scenario['filled']} | {scenario.get('filled_priority', scenario['filled'])} | {scenario['unfilled']} | {scenario['cash_cost']} | {scenario['economic_cost']} | {scenario['hours']} |"
            )
        comparison = result["comparison"]
        lines += [
            "",
            f"Additional positions filled versus no training: {comparison['additional_positions_filled']}; economic cost difference: {comparison['economic_cost_difference']}.",
            "Cost savings at equal coverage: "
            + clean(comparison["cost_saving_at_equal_coverage"])
            + ". A comparison with different filled positions is not a like-for-like saving.",
            "",
            "## Proposed hybrid assignments",
            "",
            "| Role / position | Employee | Route | Training | Economic cost |",
            "| --- | --- | --- | --- | ---: |",
        ]
        for row in result["scenarios"]["hybrid"]["assignments"]:
            lines.append(
                f"| {clean(row['role_id'])} / {row['position']} | {clean(row['employee_id'])} | {row['mode']} | {clean(row['training_id'])} | {row['economic_cost']} |"
            )
        components = {}
        for assignment in result["scenarios"]["hybrid"]["assignments"]:
            for name, value in assignment.get("cost_components", {}).items():
                components[name] = components.get(name, 0) + value
        lines += ["", "## Incremental hybrid cost components", ""]
        lines += [
            f"- {name.replace('_', ' ')}: {value:.2f} {result['currency']}"
            for name, value in components.items()
        ]
        lines += [
            "",
            "Recurring compensation is outside this incremental scenario. Cost differences with different role coverage are not like-for-like savings.",
            "",
            "## Assessment before mobility",
            "",
        ]
        for course in result["training_packages"]:
            lines.append(
                f"- {course['title']}: {course['artifact']}. Completion: {course['completion_criterion']}."
            )
        lines += [
            "",
            "## Employee–role evidence gaps",
            "",
            "| Employee | Role | Eligibility | Weighted coverage | Gaps on scenario 0–1 scale |",
            "| --- | --- | --- | ---: | --- |",
        ]
        for row in result["matrix"]:
            detail = (
                "; ".join(
                    f"{g['label']} ({g['skill_id']}): {g['gap']}"
                    for g in row["gap_details"]
                    if g["gap"] > 0
                )
                or "None"
            )
            lines.append(
                f"| {row['employee_id']} | {row['role_id']} | {row['eligibility']} | {row['weighted_coverage']} | {clean(detail)} |"
            )
        contexts = result.get("market_contexts", [])
    lines += ["", "## Public market context", ""]
    seen = set()
    for ctx in contexts:
        row = ctx.get("occupation")
        lines += [f"Coverage: {ctx['status']}; geography: {ctx['geography_status']}."]
        if row:
            lines += [
                f"{row['title']} ({row['taxonomy']} {row['taxonomy_vintage']} {row['occupation_id']}), {row['geography']}, {row['period']}: employment {clean(row.get('employment'))}; projected annual openings {clean(row.get('annual_openings'))}; projected change {clean(row.get('projected_change_pct'))}%; median annual wage {clean(row.get('median_annual_wage'))} {row.get('currency')} ({row.get('price_year')} prices)."
            ]
        for src in ctx["sources"]:
            if src["source_id"] not in seen:
                seen.add(src["source_id"])
                lines.append(
                    f"- [{src['source_id']}]({src['source_url']}), {src['source_vintage']}, retrieved {src['retrieved_at']}; {src['status']}."
                )
        lines.append("")
    lines += ["## Assumptions and decision boundary", ""]
    lines += [f"- {a}" for a in result["assumptions"]]
    return "\n".join(lines) + "\n"
