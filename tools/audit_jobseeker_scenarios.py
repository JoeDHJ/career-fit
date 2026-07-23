"""Run a deterministic end-to-end audit across diverse job-seeker profiles."""

from __future__ import annotations

import collections
import json
from pathlib import Path

from skillbundle.career import analyze_fit, compare_roles


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "jobseeker_scenarios.json"


def _manual_evidence_harness(case: dict[str, object], baseline: dict[str, object]) -> list[dict[str, object]]:
    """Model evidence a user deliberately adds in the review panel.

    This is not an automatic result. It only checks that the product can carry
    a user-labeled claim through the real review route. Language-limited cases
    are included explicitly because their mapped evidence cannot be inferred
    safely from the English dictionary.
    """

    candidate_text = str(case["candidate_text"])
    existing = {
        str(item.get("skill_id"))
        for item in baseline.get("evidence", [])
        if not item.get("negated") and item.get("skill_id")
    }
    rows: list[dict[str, object]] = []
    for item in baseline.get("evidence", []):
        if item.get("negated") or not item.get("skill_id"):
            continue
        rows.append(
            {
                "skill_id": item["skill_id"],
                "canonical_skill": item["canonical_skill"],
                "analysis_category_code": item.get("analysis_category_code", ""),
                "evidence_type": "self_reported",
                "source_text": candidate_text,
                "evidence_status": "user_confirmed_self_report",
                "verification_status": "user_declared",
            }
        )

    # A real Spanish/CJK user can add a claim against each extracted English
    # requirement after translating the task wording or receiving assistance.
    # Keep that path explicit rather than pretending the dictionary understood
    # the original profile.
    if "multilingual" in case.get("tags", []):
        for requirement in baseline.get("requirements", []):
            if requirement.get("hard_constraint") or not requirement.get("skill_id"):
                continue
            skill_id = str(requirement["skill_id"])
            if skill_id in existing:
                continue
            rows.append(
                {
                    "skill_id": skill_id,
                    "canonical_skill": requirement["canonical_skill"],
                    "analysis_category_code": requirement.get("analysis_category_code", ""),
                    "evidence_type": "self_reported",
                    "source_text": candidate_text,
                    "evidence_status": "user_confirmed_self_report",
                    "verification_status": "user_declared",
                }
            )
            existing.add(skill_id)
    return rows


def run() -> dict[str, object]:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    counts: collections.Counter[str] = collections.Counter()
    issues: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for case in cases:
        candidate_language = (
            "es"
            if case["id"] == "spanish_profile"
            else "zh"
            if case["id"] == "chinese_profile"
            else "auto"
        )
        baseline = analyze_fit(
            case["job_text"], case["candidate_text"], candidate_language=candidate_language
        )
        reviewed = analyze_fit(
            case["job_text"],
            case["candidate_text"],
            review={"scope": "role_requirements", "applied": True},
            candidate_language=candidate_language,
        )
        manual_evidence = _manual_evidence_harness(case, baseline)
        structured = analyze_fit(
            case["job_text"],
            case["candidate_text"],
            evidence=manual_evidence or None,
            review={"scope": "role_requirements", "applied": True},
            candidate_language=candidate_language,
        )
        baseline_summary = baseline["summary"]
        reviewed_summary = reviewed["summary"]
        structured_summary = structured["summary"]
        counts[f"baseline:{baseline_summary['analysis_status']}"] += 1
        counts[f"review_only:{reviewed_summary['analysis_status']}"] += 1
        counts[f"review_only_visibility:{reviewed_summary['score_visibility']}"] += 1
        counts[f"structured:{structured_summary['analysis_status']}"] += 1
        route = "role_plan_ready"
        if reviewed_summary["analysis_status"] != "scored":
            route = "guided_intake_or_manual_evidence"
        if "multilingual" in case.get("tags", []):
            route = "language_assisted_manual_evidence"
        if "low_information" in case.get("tags", []):
            route = "guided_intake_required"
        if not reviewed["next_actions"] and not structured["next_actions"]:
            issues.append({"id": case["id"], "issue": "no_next_actions"})
        if reviewed_summary["analysis_status"] != "scored":
            issues.append(
                {
                    "id": case["id"],
                    "issue": "review_only_score_unavailable",
                    "status": reviewed_summary["analysis_status"],
                    "reasons": reviewed_summary["analysis_reasons"],
                    "route": route,
                }
            )
        if "multilingual" in case.get("tags", []) and not baseline["evidence"]:
            issues.append(
                {
                    "id": case["id"],
                    "issue": "language_input_not_mapped",
                    "recommendation": "Use the language status, then add user-labeled evidence or a trusted translation before relying on a score.",
                }
            )
        comparison_roles = case.get("compare_roles")
        comparison_count = None
        if comparison_roles:
            comparison = compare_roles(
                comparison_roles,
                case["candidate_text"],
                evidence=manual_evidence or None,
                review={"scope": "candidate_evidence", "applied": True},
                candidate_language=candidate_language,
            )
            comparison_count = comparison["role_count"]
            counts["compare:ok"] += 1
        rows.append(
            {
                "id": case["id"],
                "tags": case.get("tags", []),
                "baseline_status": baseline_summary["analysis_status"],
                "review_only_status": reviewed_summary["analysis_status"],
                "structured_status": structured_summary["analysis_status"],
                "score_visibility": reviewed_summary["score_visibility"],
                "requirements": reviewed_summary["requirement_count"],
                "auto_evidence": baseline_summary["evidence_count"],
                "structured_evidence": structured_summary["evidence_count"],
                "next_actions": len(reviewed["next_actions"]),
                "route": route,
                "comparison_roles": comparison_count,
            }
        )
    return {
        "case_count": len(cases),
        "counts": dict(counts),
        "issues": issues,
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
