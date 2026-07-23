"""Run 500 deterministic Career Fit jobseeker journeys.

The audit expands each of the 50 maintained golden profiles through ten
controlled input and journey variants.  It is intentionally separate from the
50-case regression runner: the golden set protects named user stories while
this runner stress-tests the same contract across systematic variations.

The release result also includes a focused 32-case hard-gate edge matrix so
experience negation and historical/expired eligibility states are checked
alongside, without changing, the 500-journey count.
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path
from typing import Any, Callable

from skillbundle.career import analyze_fit, compare_roles

from audit_jobseeker_scenarios import _manual_evidence_harness


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "jobseeker_scenarios.json"


VariantTransform = Callable[[str, str], tuple[str, str]]


def _identity(job_text: str, candidate_text: str) -> tuple[str, str]:
    return job_text, candidate_text


def _casefold(job_text: str, candidate_text: str) -> tuple[str, str]:
    return job_text.upper(), candidate_text.upper()


def _spacing(job_text: str, candidate_text: str) -> tuple[str, str]:
    return (
        re.sub(r"\s+", "  ", job_text.strip()),
        re.sub(r"\s+", "  ", candidate_text.strip()),
    )


def _context(job_text: str, candidate_text: str) -> tuple[str, str]:
    return (
        job_text + " The team documents decisions and collaborates across functions.",
        candidate_text + " I explained the context, coordinated with stakeholders, and documented the work.",
    )


def _result(job_text: str, candidate_text: str) -> tuple[str, str]:
    return (
        job_text,
        candidate_text + " The result was a measurable improvement that I can explain with a concrete example.",
    )


def _duration(job_text: str, candidate_text: str) -> tuple[str, str]:
    return job_text, candidate_text + " I performed this work for 18 months."


def _claim(job_text: str, candidate_text: str) -> tuple[str, str]:
    return job_text, candidate_text + " I am familiar with adjacent tools and can discuss how I would learn the rest."


def _low_information(job_text: str, candidate_text: str) -> tuple[str, str]:
    del candidate_text
    return job_text, "Seeking a new opportunity and open to learning."


def _resume_style(job_text: str, candidate_text: str) -> tuple[str, str]:
    return job_text, "- " + candidate_text.replace(". ", ".\n- ")


def _negation(job_text: str, candidate_text: str) -> tuple[str, str]:
    return job_text, candidate_text + " I have no direct experience with an unrelated legacy platform."


VARIANTS: tuple[tuple[str, VariantTransform, bool], ...] = (
    ("plain", _identity, False),
    ("casefold", _casefold, False),
    ("spacing", _spacing, False),
    ("context", _context, False),
    ("result", _result, False),
    ("duration", _duration, False),
    ("claim", _claim, False),
    ("low_information", _low_information, False),
    ("resume_style", _resume_style, False),
    ("manual_evidence", _identity, True),
)


HARD_GATE_EDGE_CASES: tuple[dict[str, str], ...] = (
    {
        "id": "experience_current_negative",
        "job": "Five years of operations experience required.",
        "candidate": "I do not have five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_domain_conflict",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of experience, but not in operations.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_threshold_phrase",
        "job": "Five years of operations experience required.",
        "candidate": "I have no less than five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "met",
    },
    {
        "id": "experience_threshold_no_fewer",
        "job": "Five years of operations experience required.",
        "candidate": "I have no fewer than five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "met",
    },
    {
        "id": "experience_threshold_not_only",
        "job": "Five years of operations experience required.",
        "candidate": "I have not only five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "met",
    },
    {
        "id": "experience_threshold_more_than",
        "job": "Five years of operations experience required.",
        "candidate": "I have more than five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "met",
    },
    {
        "id": "experience_insufficient_less_than",
        "job": "Five years of operations experience required.",
        "candidate": "I have less than five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_insufficient_under",
        "job": "Five years of operations experience required.",
        "candidate": "I have under five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_insufficient_fewer_than",
        "job": "Five years of operations experience required.",
        "candidate": "I have fewer than five years of operations experience.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_post_none_relevant",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience, but none is relevant.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_post_not_relevant",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience, but it is not relevant.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_post_not_qualifying",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience, but none is qualifying.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_post_requirement_conflict",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience; however, I do not meet the requirement.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_following_not_relevant",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience. It is not relevant.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_following_none_relevant",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience. None is relevant.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_following_requirement_conflict",
        "job": "Five years of operations experience required.",
        "candidate": "I have five years of operations experience. I do not meet the requirement.",
        "requirement_type": "experience_floor",
        "expected": "not_met",
    },
    {
        "id": "experience_future",
        "job": "Five years of operations experience required.",
        "candidate": "I will have five years of operations experience by 2027.",
        "requirement_type": "experience_floor",
        "expected": "unknown",
    },
    {
        "id": "authorization_historical",
        "job": "Authorization to work in the United States is required.",
        "candidate": "I was authorized to work in the United States.",
        "requirement_type": "work_authorization",
        "expected": "unknown",
    },
    {
        "id": "authorization_expired",
        "job": "Authorization to work in the United States is required.",
        "candidate": "I was authorized to work, but my authorization expired.",
        "requirement_type": "work_authorization",
        "expected": "not_met",
    },
    {
        "id": "authorization_current",
        "job": "Authorization to work in the United States is required.",
        "candidate": "I have current work authorization.",
        "requirement_type": "work_authorization",
        "expected": "met",
    },
    {
        "id": "authorization_future",
        "job": "Authorization to work in the United States is required.",
        "candidate": "I will be authorized to work next month.",
        "requirement_type": "work_authorization",
        "expected": "unknown",
    },
    {
        "id": "authorization_current_with_start_date",
        "job": "Authorization to work in the United States is required.",
        "candidate": "I am authorized to work and can start next month.",
        "requirement_type": "work_authorization",
        "expected": "met",
    },
    {
        "id": "license_historical",
        "job": "An active nursing license is required.",
        "candidate": "I previously held an active nursing license.",
        "requirement_type": "professional_license",
        "expected": "unknown",
    },
    {
        "id": "license_expired",
        "job": "An active nursing license is required.",
        "candidate": "My nursing license is expired.",
        "requirement_type": "professional_license",
        "expected": "not_met",
    },
    {
        "id": "license_current",
        "job": "An active nursing license is required.",
        "candidate": "I hold a current nursing license.",
        "requirement_type": "professional_license",
        "expected": "met",
    },
    {
        "id": "license_current_synonym",
        "job": "An active nursing license is required.",
        "candidate": "I am currently licensed as a nurse.",
        "requirement_type": "professional_license",
        "expected": "met",
    },
    {
        "id": "license_negative_synonym",
        "job": "An active nursing license is required.",
        "candidate": "I am not currently licensed as a nurse.",
        "requirement_type": "professional_license",
        "expected": "not_met",
    },
    {
        "id": "license_current_with_start_date",
        "job": "An active nursing license is required.",
        "candidate": "I hold an active nursing license and can start next month.",
        "requirement_type": "professional_license",
        "expected": "met",
    },
    {
        "id": "license_future",
        "job": "An active nursing license is required.",
        "candidate": "I will obtain a nursing license next year.",
        "requirement_type": "professional_license",
        "expected": "unknown",
    },
    {
        "id": "background_current_with_start_date",
        "job": "A background check is required.",
        "candidate": "I passed a background check and can start next month.",
        "requirement_type": "background_check",
        "expected": "met",
    },
    {
        "id": "background_future",
        "job": "A background check is required.",
        "candidate": "I will have completed a background check.",
        "requirement_type": "background_check",
        "expected": "unknown",
    },
    {
        "id": "authorization_negative_synonym",
        "job": "Authorization to work in the United States is required.",
        "candidate": "I am not eligible to work in the United States.",
        "requirement_type": "work_authorization",
        "expected": "not_met",
    },
)


def generate_cases() -> list[tuple[dict[str, Any], str, VariantTransform, bool]]:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [
        (case, variant_id, transform, adds_manual_evidence)
        for case in cases
        for variant_id, transform, adds_manual_evidence in VARIANTS
    ]


def _candidate_language(case: dict[str, Any]) -> str:
    if case["id"] == "spanish_profile":
        return "es"
    if case["id"] == "chinese_profile":
        return "zh"
    return "auto"


def _audit_hard_gate_edges() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in HARD_GATE_EDGE_CASES:
        result = analyze_fit(case["job"], case["candidate"])
        gate = next(
            (
                item
                for item in result["hard_constraints"]
                if item["requirement_type"] == case["requirement_type"]
            ),
            None,
        )
        actual = gate["status"] if gate else None
        results.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "actual": actual,
                "passed": actual == case["expected"],
            }
        )
    return results


def _score_visibility_is_safe(result: dict[str, Any]) -> bool:
    summary = result["summary"]
    if summary["analysis_status"] == "scored":
        return summary["score_visibility"] == "visible"
    return summary["score_visibility"] == "hidden" and all(
        summary.get(field) is None
        for field in (
            "evidence_fit_score",
            "capability_signal",
            "proof_signal",
            "application_readiness",
        )
    )


def _guided_intake_harness(case: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    """Model the short task/context form used when no mapped evidence exists."""

    del case
    requirement = next(
        (
            item
            for item in baseline.get("review_queue", [])
            if not item.get("hard_constraint") and item.get("skill_id")
        ),
        None,
    )
    if requirement is None:
        return []
    skill = str(requirement["canonical_skill"])
    return [
        {
            "skill_id": requirement["skill_id"],
            "canonical_skill": skill,
            "analysis_category_code": requirement.get("analysis_category_code", ""),
            "evidence_type": "work",
            "source_text": f"Completed a real task using {skill} while helping organize work for a community activity.",
            "result": "Kept the work organized and followed through on the requested result.",
            "duration_months": 6,
            "recency_years": 1,
        }
    ]


def _audit_case(
    case: dict[str, Any],
    variant_id: str,
    transform: VariantTransform,
    adds_manual_evidence: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    job_text, candidate_text = transform(
        str(case["job_text"]), str(case["candidate_text"])
    )
    language = _candidate_language(case)
    issues: list[dict[str, Any]] = []
    try:
        baseline = analyze_fit(job_text, candidate_text, candidate_language=language)
        reviewed = analyze_fit(
            job_text,
            candidate_text,
            review={"scope": "role_requirements", "applied": True},
            candidate_language=language,
        )
        manual_evidence = _manual_evidence_harness(case, baseline)
        evidence_route = "review_panel_evidence" if manual_evidence else None
        if variant_id == "low_information" or (adds_manual_evidence and not manual_evidence):
            manual_evidence = _guided_intake_harness(case, baseline)
            evidence_route = "guided_intake" if manual_evidence else None
        structured = analyze_fit(
            job_text,
            candidate_text,
            evidence=manual_evidence or None,
            review={"scope": "role_requirements", "applied": True},
            candidate_language=language,
        )
        if adds_manual_evidence and not manual_evidence:
            issues.append({"issue": "manual_evidence_fixture_empty"})
        if not _score_visibility_is_safe(baseline):
            issues.append({"issue": "baseline_score_visibility_leak"})
        if not _score_visibility_is_safe(reviewed):
            issues.append({"issue": "reviewed_score_visibility_inconsistent"})
        if not _score_visibility_is_safe(structured):
            issues.append({"issue": "structured_score_visibility_inconsistent"})
        if not reviewed["next_actions"] and not structured["next_actions"]:
            issues.append({"issue": "no_next_actions"})
        if reviewed["summary"]["analysis_status"] == "review_required":
            issues.append({"issue": "applied_review_did_not_leave_provisional_state"})
        if case.get("compare_roles") and variant_id != "low_information":
            comparison = compare_roles(
                case["compare_roles"],
                candidate_text,
                evidence=manual_evidence or None,
                review={"scope": "candidate_evidence", "applied": True},
                candidate_language=language,
            )
            if comparison["role_count"] != len(case["compare_roles"]):
                issues.append({"issue": "comparison_role_count_mismatch"})
        row = {
            "id": f"{case['id']}__{variant_id}",
            "base_id": case["id"],
            "variant": variant_id,
            "baseline_status": baseline["summary"]["analysis_status"],
            "reviewed_status": reviewed["summary"]["analysis_status"],
            "structured_status": structured["summary"]["analysis_status"],
            "score_visibility": reviewed["summary"]["score_visibility"],
            "requirements": reviewed["summary"]["requirement_count"],
            "next_actions": len(reviewed["next_actions"]),
            "evidence_route": evidence_route,
            "language_review": bool(
                reviewed["summary"]["candidate_language"].get(
                    "requires_language_review"
                )
            ),
        }
    except Exception as exc:  # pragma: no cover - the audit reports unexpected cases
        row = {"id": f"{case['id']}__{variant_id}", "base_id": case["id"], "variant": variant_id}
        issues.append({"issue": "unexpected_exception", "detail": f"{type(exc).__name__}: {exc}"})
    return row, [{"id": row["id"], **issue} for issue in issues]


def run() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for case, variant_id, transform, adds_manual_evidence in generate_cases():
        row, case_issues = _audit_case(case, variant_id, transform, adds_manual_evidence)
        rows.append(row)
        issues.extend(case_issues)

    hard_gate_edges = _audit_hard_gate_edges()
    issues.extend(
        {
            "id": f"hard_gate_edge__{item['id']}",
            "issue": "hard_gate_edge_mismatch",
            "detail": item,
        }
        for item in hard_gate_edges
        if not item["passed"]
    )

    counts: collections.Counter[str] = collections.Counter()
    routes: collections.Counter[str] = collections.Counter()
    for row in rows:
        counts[f"baseline:{row.get('baseline_status', 'error')}"] += 1
        counts[f"reviewed:{row.get('reviewed_status', 'error')}"] += 1
        counts[f"structured:{row.get('structured_status', 'error')}"] += 1
        if row.get("language_review"):
            counts["language_review:true"] += 1
        route = "role_plan_ready"
        if row.get("reviewed_status") != "scored":
            route = "guided_intake_or_manual_evidence"
        if row.get("language_review"):
            route = "language_assisted_manual_evidence"
        if row.get("variant") == "low_information":
            route = "guided_intake_required"
        routes[route] += 1

    issue_counts = collections.Counter(str(item["issue"]) for item in issues)
    return {
        "case_count": len(rows),
        "base_case_count": len(json.loads(FIXTURE.read_text(encoding="utf-8"))),
        "variants_per_case": len(VARIANTS),
        "hard_gate_edge_case_count": len(hard_gate_edges),
        "hard_gate_edge_cases_passed": sum(
            1 for item in hard_gate_edges if item["passed"]
        ),
        "counts": dict(counts),
        "route_counts": dict(routes),
        "issue_count": len(issues),
        "issue_counts": dict(issue_counts),
        "issue_samples": issues[:30],
        "all_cases_have_next_actions": all(row.get("next_actions", 0) > 0 for row in rows),
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
