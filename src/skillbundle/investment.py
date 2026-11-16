"""Transparent, bounded training choice. Outputs describe scenarios, not outcomes."""

from __future__ import annotations

from itertools import combinations
import math

from .career import analyze_fit
from .market import market_context


def number(value, label: str, minimum: float = 0, maximum: float = 1e9) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{label} must be a finite number from {minimum} to {maximum}")
    return float(value)


def strings(value, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(x, str) or not x.strip() for x in value
    ):
        raise ValueError(f"{label} must be a list of nonempty strings")
    return list(dict.fromkeys(value))


def text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def courses_checked(courses) -> list[dict]:
    if not isinstance(courses, list) or len(courses) > 12:
        raise ValueError("courses must be a list of at most 12 training options")
    result = []
    for raw in courses:
        if not isinstance(raw, dict):
            raise ValueError("training options must be objects")
        item = dict(raw)
        for key in ("id", "title", "artifact", "completion_criterion"):
            item[key] = text(item.get(key), f"course {key}")
        for key in ("hours", "fee"):
            item[key] = number(item.get(key), f"course {key}")
        item["skills"] = strings(item.get("skills"), "course skills")
        item["prerequisites"] = strings(
            item.get("prerequisites", []), "course prerequisites"
        )
        item["eligibility"] = item.get("eligibility", "unknown")
        if item["eligibility"] not in {"met", "unknown", "not_met"}:
            raise ValueError("course eligibility must be met, unknown, or not_met")
        item["foregone_income"] = number(
            item.get("foregone_income", 0), "foregone_income"
        )
        result.append(item)
    ids = [c["id"] for c in result]
    if len(ids) != len(set(ids)):
        raise ValueError("course IDs must be unique")
    return result


def order_courses(selected: list[dict], known: set[str]) -> list[dict] | None:
    pending = selected.copy()
    ordered = []
    available = set(known)
    while pending:
        ready = next((c for c in pending if set(c["prerequisites"]) <= available), None)
        if ready is None:
            return None
        pending.remove(ready)
        ordered.append(ready)
        available.update(ready["skills"])
    return ordered


def benefit_analysis(cost: float | None, benefits) -> dict:
    if benefits is None:
        return {
            "status": "not_computed",
            "reason": "No explicit benefit input. Market wages are not substituted for benefits.",
        }
    if not isinstance(benefits, dict):
        raise ValueError("benefits must be an object")
    annual = number(benefits.get("annual_benefit"), "annual_benefit")
    years = number(benefits.get("years"), "benefit years", 1, 30)
    if years != int(years):
        raise ValueError("benefit years must be an integer")
    rate = number(benefits.get("discount_rate"), "discount_rate", 0, 1)
    basis = text(benefits.get("basis"), "benefit basis")
    if cost is None:
        return {
            "status": "not_computed",
            "reason": "Supply an hourly time value (zero is allowed if intentional) to complete economic costs.",
            "benefit_basis": basis,
        }
    scenarios = []
    for factor in (0.5, 1.0, 1.5):
        total = annual * factor * years
        pv = sum(annual * factor / (1 + rate) ** t for t in range(1, int(years) + 1))
        scenarios.append(
            {
                "benefit_multiplier": factor,
                "npv": round(pv - cost, 2),
                "roi_pct": round(100 * (total - cost) / cost, 2) if cost > 0 else None,
            }
        )
    return {
        "status": "scenario",
        "annual_benefit": annual,
        "years": int(years),
        "discount_rate": rate,
        "benefit_basis": basis,
        "timing": "All costs at time zero; equal benefits at each year-end; ROI is undiscounted cumulative net benefit / economic cost",
        "sensitivity": scenarios,
    }


def plan_investment(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("investment input must be an object")
    reviewed = payload.get("analysis_input")
    if not isinstance(reviewed, dict):
        raise ValueError("analysis_input must contain the reviewed role and evidence")
    analysis = analyze_fit(
        reviewed.get("job_text", ""),
        reviewed.get("candidate_text", ""),
        reviewed.get("evidence"),
        reviewed.get("review"),
        reviewed.get("candidate_language", "auto"),
    )
    if analysis["summary"]["score_visibility"] != "visible":
        raise ValueError(
            "Review the role requirements and evidence before planning training"
        )
    budget = number(payload.get("budget"), "cash budget")
    hours = number(payload.get("hours"), "total available hours", 0, 2000)
    weekly = number(payload.get("weekly_hours"), "weekly hours", 0.1, 80)
    reserve = number(payload.get("preparation_hours", 6), "preparation_hours", 0, 200)
    hourly = payload.get("hourly_value")
    if hourly is not None:
        hourly = number(hourly, "hourly_value")
    currency = text(payload.get("currency"), "currency")
    courses = courses_checked(payload.get("courses", []))
    from .learning import review_progress

    progress = review_progress(payload, courses)
    if hourly and any(c["foregone_income"] for c in courses):
        raise ValueError(
            "Use hourly time value or course foregone_income, not both, to avoid double counting"
        )
    requirements = [r for r in analysis["requirements"] if not r.get("hard_constraint")]
    known = set(
        strings(payload.get("confirmed_prerequisites", []), "confirmed_prerequisites")
    )
    # Direct evidence may satisfy a training prerequisite; transfer is not equivalence.
    known.update(
        r["skill_id"]
        for r in requirements
        if r.get("status") == "direct" and r.get("skill_id")
    )
    gaps = [r for r in requirements if r.get("status") != "direct"]
    weights = {
        r.get("skill_id", r["requirement_id"]): float(r["importance_weight"])
        for r in gaps
    }
    reviewed_labels = {r.get("skill_id"): r["canonical_skill"] for r in requirements}
    capacity = min(hours, weekly * 90 / 7)
    blocked = [
        {"id": c["id"], "reason": "Training eligibility " + c["eligibility"]}
        for c in courses
        if c["eligibility"] != "met"
    ]
    candidates = []
    for course in courses:
        invalid_custom = False
        for skill in course["skills"] + course["prerequisites"]:
            if skill.startswith("user.custom."):
                if skill not in reviewed_labels:
                    invalid_custom = True
                    continue
                labels = course.get("skill_labels", {})
                if (
                    not isinstance(labels, dict)
                    or labels.get(skill) != reviewed_labels[skill]
                ):
                    raise ValueError(
                        f"Course {course['id']} custom skill label changed or is missing; remap the catalog to the reviewed requirement"
                    )
        if invalid_custom:
            blocked.append(
                {
                    "id": course["id"],
                    "reason": "Custom skill is no longer in the reviewed requirement map",
                }
            )
        elif course["eligibility"] == "met":
            candidates.append(course)
    feasible = []
    for size in range(len(candidates) + 1):
        for chosen in combinations(candidates, size):
            time = sum(c["hours"] for c in chosen) + reserve
            fee = sum(c["fee"] for c in chosen)
            foregone = sum(c["foregone_income"] for c in chosen)
            if time > capacity + 1e-8 or fee > budget + 1e-8:
                continue
            ordered = order_courses(list(chosen), known)
            if ordered is None:
                continue
            gained = (
                set().union(*(set(c["skills"]) for c in chosen)) if chosen else set()
            )
            value = sum(w for s, w in weights.items() if s in gained)
            economic = fee + foregone + time * hourly if hourly is not None else None
            feasible.append(
                {
                    "course_ids": [c["id"] for c in ordered],
                    "target_weight_covered": round(value, 6),
                    "cash_cost": round(fee, 2),
                    "foregone_income": round(foregone, 2),
                    "hours": round(time, 2),
                    "economic_cost": round(economic, 2)
                    if economic is not None
                    else None,
                    "_courses": ordered,
                }
            )
    feasible.sort(
        key=lambda p: (
            -p["target_weight_covered"],
            p["economic_cost"]
            if p["economic_cost"] is not None
            else p["cash_cost"] + p["foregone_income"],
            p["hours"],
            p["course_ids"],
        )
    )
    best = feasible[0] if feasible else None
    for course in candidates:
        if order_courses(candidates, known) is None and not set(
            course["prerequisites"]
        ) <= known | set().union(*(set(c["skills"]) for c in candidates)):
            blocked.append(
                {
                    "id": course["id"],
                    "reason": "Prerequisites cannot be supplied by this catalog or confirmed evidence",
                }
            )
    timeline = []
    for day in (30, 60, 90):
        timeline.append(
            {
                "day": day,
                "training": [],
                "actions": [],
                "artifact": "",
                "completion_criterion": "",
            }
        )
    gates = analysis["hard_constraints"]
    timeline[0].update(
        actions=[
            "Verify each unresolved eligibility gate with the employer or records: "
            + "; ".join(
                g["canonical_skill"] + " (" + g["status"] + ")"
                for g in gates
                if g["status"] != "met"
            )
            if any(g["status"] != "met" for g in gates)
            else "Recheck eligibility against the complete current posting.",
            "Translate one existing direct or transferable example into task, context, result, and a reviewable artifact.",
        ],
        artifact="Reviewed eligibility checklist and one role-specific evidence card",
        completion_criterion="Each gate has a source or an explicit unresolved status; the evidence card links to an actual work sample.",
    )
    timeline[1].update(
        actions=[
            "Test the selected work sample against the role's named requirements; request a human critique."
        ],
        artifact="Runnable work sample, validation checks, and short decision memo",
        completion_criterion="Another person can reproduce the result and locate the requirement it supports.",
    )
    timeline[2].update(
        actions=[
            "Reassess the evidence map, document remaining gaps, and prepare an application or an adjacent-role search."
        ],
        artifact="Updated evidence map and tailored application pack",
        completion_criterion="Every new claim points to completed work; unresolved gates remain visible.",
    )
    if best:
        elapsed = reserve / 2
        for course in best["_courses"]:
            start = elapsed
            elapsed += course["hours"]
            for phase in timeline:
                lo = (phase["day"] - 30) / 7 * weekly
                hi = phase["day"] / 7 * weekly
                allocated = max(0, min(elapsed, hi) - max(start, lo))
                if allocated > 1e-8:
                    phase["training"].append(
                        {
                            "course_id": course["id"],
                            "title": course["title"],
                            "hours": round(allocated, 2),
                            "artifact": course["artifact"],
                            "completion_criterion": course["completion_criterion"],
                            "due_day": min(90, math.ceil(elapsed / weekly * 7)),
                        }
                    )
        best["selected_courses"] = best.pop("_courses")
    alternatives = [
        {k: v for k, v in p.items() if k != "_courses"} for p in feasible[:8]
    ]
    selected_skills = (
        set().union(*(set(c["skills"]) for c in best["selected_courses"]))
        if best
        else set()
    )
    market = market_context(
        str(payload.get("occupation_id", "")),
        str(payload.get("geography", "US")),
        payload.get("market_snapshot"),
        payload.get("as_of"),
    )
    return {
        "schema_version": "career_fit.investment.v1",
        "status": "scenario_plan" if best else "infeasible",
        "input_status": payload.get("input_status", "user_supplied"),
        "currency": currency,
        "price_year": payload.get("price_year"),
        "progress": progress,
        "budget": budget,
        "hours_capacity_90_days": round(capacity, 2),
        "preparation_hours": reserve,
        "hourly_value": hourly,
        "reviewed_summary": analysis["summary"],
        "eligibility_gates": gates,
        "evidence_map": [
            {
                "skill": r["canonical_skill"],
                "skill_id": r.get("skill_id"),
                "status": r["status"],
                "training_target": r.get("skill_id") in selected_skills,
                "importance": r["importance_level"],
            }
            for r in requirements
        ],
        "objective": "Maximize distinct reviewed gap importance covered by assumed training outcomes; then minimize economic cost (cash plus supplied foregone income if time value missing), then hours. Coverage is not proficiency or a predicted job outcome.",
        "best_plan": best,
        "alternatives": alternatives,
        "feasible_portfolios": len(feasible),
        "blocked_options": blocked,
        "remaining_targets": [
            r["canonical_skill"]
            for r in gaps
            if r.get("skill_id") not in selected_skills
        ],
        "timeline": timeline if best else [],
        "market_context": market,
        "returns": benefit_analysis(
            best["economic_cost"] if best else None, payload.get("benefits")
        ),
        "assumptions": [
            "Training skill outcomes, effort, costs and benefits are user-supplied scenarios; completion requires the stated artifact and human review.",
            "Course prerequisites can be met only by confirmed prerequisites, direct evidence, or earlier selected training.",
            "Preparation hours reserve time for verification, evidence translation and final review; course hours include their work samples.",
            "Training cannot resolve an experience, license, authorization or degree gate automatically.",
        ],
        "infeasibility_reason": None
        if best
        else "Even the preparation reserve exceeds available time. Reduce scope or increase available hours.",
    }
