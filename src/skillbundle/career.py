from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .dictionary import extract
from .requirements import IMPORTANCE_WEIGHTS, extract_requirements


EVIDENCE_WEIGHTS = {
    "work": 0.95,
    "research_project": 0.90,
    "portfolio": 0.80,
    "github_project": 0.80,
    "course": 0.60,
    "certificate": 0.55,
    "self_reported": 0.35,
    "unknown": 0.25,
}

STATUS_LABELS = {
    "direct": "Direct evidence / 直接证据",
    "direct_weak": "Direct but weak evidence / 直接但证据较弱",
    "transferable": "Transferable evidence / 可迁移证据",
    "missing": "No evidence found / 未找到证据",
    "met": "Requirement appears met / 看起来已满足",
    "not_met": "Explicitly not met / 明确不满足",
    "unknown": "Needs verification / 需要核实",
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _recency_score(item: dict[str, Any]) -> float:
    years = item.get("recency_years")
    if years in (None, ""):
        return 0.70
    value = max(0.0, _number(years))
    if value <= 2:
        return 1.0
    if value <= 5:
        return 0.80
    return 0.60


def _depth_score(item: dict[str, Any]) -> float:
    months = item.get("duration_months")
    if months in (None, ""):
        return 0.45 if item.get("evidence_type") == "self_reported" else 0.65
    value = max(0.0, _number(months))
    if value >= 24:
        return 1.0
    if value >= 6:
        return 0.80
    if value >= 1:
        return 0.60
    return 0.40


def _evidence_score(item: dict[str, Any]) -> float:
    evidence_type = str(item.get("evidence_type", "unknown"))
    base = EVIDENCE_WEIGHTS.get(evidence_type, EVIDENCE_WEIGHTS["unknown"])
    if item.get("measurable_result") or item.get("result"):
        base = min(1.0, base + 0.08)
    return base


def evidence_from_text(text: str) -> list[dict[str, Any]]:
    """Create conservative evidence objects from a free-text candidate profile."""
    items = []
    for index, item in enumerate(extract(text), start=1):
        items.append(
            {
                "evidence_id": f"evidence-{index:03d}",
                "skill_id": item["skill_id"],
                "canonical_skill": item["canonical"],
                "analysis_category_code": item["analysis_category_code"],
                "evidence_type": "self_reported",
                "source_text": item["text"],
                "mapping_method": item["mapping_method"],
                "extraction_confidence": item["confidence"],
                "evidence_status": "self_reported_baseline",
            }
        )
    return items


def _normalize_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, item in enumerate(evidence, start=1):
        copied = dict(item)
        copied.setdefault("evidence_id", f"evidence-{index:03d}")
        copied.setdefault("evidence_type", "unknown")
        copied.setdefault("evidence_status", "user_provided")
        if copied.get("skill_id") is None and copied.get("canonical_skill"):
            matched = extract(str(copied["canonical_skill"]))
            if matched:
                copied["skill_id"] = matched[0]["skill_id"]
                copied["analysis_category_code"] = matched[0]["analysis_category_code"]
        normalized.append(copied)
    return normalized


def _constraint_status(requirement: dict[str, Any], candidate_text: str) -> str:
    lowered = candidate_text.casefold()
    requirement_type = requirement["requirement_type"]
    if requirement_type == "professional_license":
        positive = re.search(r"\b(licensed|licence|license|certified|certification)\b", lowered)
        negative = re.search(r"\b(no|without|lack(?:s|ing)?|not)\b[^.!?;\n]{0,25}\b(license|licence|certification|certified)\b", lowered)
    elif requirement_type == "work_authorization":
        positive = re.search(r"\b(authorized|eligible|work permit|visa)\b", lowered)
        negative = re.search(r"\b(no|without|not)\b[^.!?;\n]{0,25}\b(authorization|permit|visa)\b", lowered)
    elif requirement_type == "education":
        positive = re.search(r"\b(bachelor|master|ph\.?d|doctorate|doctoral)\b", lowered)
        negative = None
    elif requirement_type == "experience_floor":
        years = re.search(r"\b(\d+)\+?\s+years?\b", lowered)
        required = int(re.search(r"\d+", requirement["canonical_skill"]).group(0))
        positive = years and int(years.group(1)) >= required
        negative = None
    else:
        positive = None
        negative = None
    if negative:
        return "not_met"
    if positive:
        return "met"
    return "unknown"


def _match_evidence(
    requirement: dict[str, Any],
    evidence_by_skill: dict[str, list[dict[str, Any]]],
    evidence_by_category: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    skill_id = requirement.get("skill_id")
    category = requirement.get("analysis_category_code")
    direct = evidence_by_skill.get(str(skill_id), [])
    transferable = [] if direct else evidence_by_category.get(str(category), [])
    selected = direct or transferable
    if direct:
        coverage, status = 1.0, "direct"
        proficiency = 0.85
    elif transferable:
        coverage, status = 0.55, "transferable"
        proficiency = 0.65
    else:
        coverage, status = 0.0, "missing"
        proficiency = 0.0
    if selected:
        evidence = sum(_evidence_score(item) for item in selected) / len(selected)
        recency = sum(_recency_score(item) for item in selected) / len(selected)
        depth = sum(_depth_score(item) for item in selected) / len(selected)
    else:
        evidence, recency, depth = 0.0, 0.0, 0.0
    score = 0.35 * coverage + 0.25 * evidence + 0.20 * proficiency + 0.10 * recency + 0.10 * depth
    if status == "direct" and evidence < 0.55:
        status = "direct_weak"
    return {
        "status": status,
        "status_label": STATUS_LABELS[status],
        "match_score": round(score, 3),
        "coverage": round(coverage, 3),
        "evidence_strength": round(evidence, 3),
        "evidence_ids": [item["evidence_id"] for item in selected],
        "evidence": selected,
    }


def _gap_for(
    requirement: dict[str, Any], assessment: dict[str, Any]
) -> dict[str, Any] | None:
    status = assessment.get("status")
    if status == "direct":
        return None
    canonical = str(requirement.get("canonical_skill", requirement.get("original_text")))
    importance = str(requirement.get("importance_level", "inferred"))
    impact = IMPORTANCE_WEIGHTS.get(importance, 0.2) * (1 - _number(assessment.get("match_score")))
    if status == "direct_weak":
        gap_type = "evidence_gap"
        action = f"Add a concrete task and measurable result showing how you used {canonical}."
        horizon = "before applying"
    elif status == "transferable":
        gap_type = "adjacent_skill_gap"
        action = f"Build a small portfolio example applying {canonical}, then explain the transfer from the existing skill evidence."
        horizon = "short term"
    else:
        gap_type = "structural_gap"
        action = f"Plan structured training or an adjacent role before relying on {canonical} as a core qualification."
        horizon = "medium term"
    return {
        "requirement_id": requirement["requirement_id"],
        "canonical_skill": canonical,
        "gap_type": gap_type,
        "importance_level": importance,
        "impact_score": round(impact, 3),
        "priority": "high" if impact >= 0.45 else "medium" if impact >= 0.20 else "low",
        "time_horizon": horizon,
        "action": action,
        "basis": "This is a transparent preparation recommendation, not a predicted hiring effect.",
    }


def analyze_fit(
    job_text: str,
    candidate_text: str,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    requirements = extract_requirements(job_text)
    candidate_evidence = _normalize_evidence(
        evidence if evidence is not None else evidence_from_text(candidate_text)
    )
    evidence_by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidate_evidence:
        if item.get("skill_id"):
            evidence_by_skill[str(item["skill_id"])].append(item)
        if item.get("analysis_category_code"):
            evidence_by_category[str(item["analysis_category_code"])].append(item)

    assessments = []
    gaps = []
    hard_constraints = []
    weighted_total = 0.0
    weight_total = 0.0
    skill_requirement_count = 0
    direct_count = 0
    for requirement in requirements:
        if requirement["hard_constraint"]:
            status = _constraint_status(requirement, candidate_text)
            item = {
                **requirement,
                "status": status,
                "status_label": STATUS_LABELS[status],
                "match_score": 1.0 if status == "met" else 0.0,
                "evidence_ids": [],
            }
            hard_constraints.append(item)
            assessments.append(item)
            continue
        skill_requirement_count += 1
        assessment = _match_evidence(requirement, evidence_by_skill, evidence_by_category)
        if assessment["status"] == "direct":
            direct_count += 1
        weight = _number(requirement["importance_weight"], 0.2)
        weighted_total += weight * _number(assessment["match_score"])
        weight_total += weight
        item = {**requirement, **{key: value for key, value in assessment.items() if key != "evidence"}}
        assessments.append(item)
        gap = _gap_for(requirement, assessment)
        if gap:
            gaps.append(gap)

    soft_fit = round(100 * weighted_total / weight_total) if weight_total else 0
    job_clarity = min(1.0, skill_requirement_count / 5) if skill_requirement_count else 0.35
    candidate_quality = (
        sum(_evidence_score(item) for item in candidate_evidence) / len(candidate_evidence)
        if candidate_evidence
        else 0.0
    )
    direct_share = direct_count / skill_requirement_count if skill_requirement_count else 0.0
    assessment_confidence = round(100 * (0.35 * job_clarity + 0.35 * candidate_quality + 0.30 * direct_share))
    blocking = [item for item in hard_constraints if item["status"] != "met"]
    if blocking:
        decision = "blocked_pending_verification"
        decision_label = "Verify admission requirements before relying on the soft score."
    elif soft_fit >= 80:
        decision = "ready_with_targeted_improvements"
        decision_label = "Strong baseline fit; focus on targeted evidence and framing."
    elif soft_fit >= 60:
        decision = "needs_targeted_evidence"
        decision_label = "Promising overlap, but targeted evidence or skills are still needed."
    else:
        decision = "substantial_gaps"
        decision_label = "Several important requirements need evidence or structured preparation."
    for item in blocking:
        gaps.append(
            {
                "requirement_id": item["requirement_id"],
                "canonical_skill": item["canonical_skill"],
                "gap_type": "hard_constraint",
                "importance_level": "must",
                "impact_score": 1.0,
                "priority": "high",
                "time_horizon": "before applying",
                "action": f"Verify or address the requirement: {item['canonical_skill']}.",
                "basis": "A hard constraint is reported separately and can block readiness even when soft fit is high.",
            }
        )
    gaps.sort(key=lambda item: (-_number(item.get("impact_score")), item.get("canonical_skill", "")))
    return {
        "schema_version": "career_fit.v0.1",
        "product": "Career Fit",
        "mode": "single_job",
        "requirements": assessments,
        "evidence": candidate_evidence,
        "hard_constraints": hard_constraints,
        "gaps": gaps,
        "summary": {
            "role_fit_score": soft_fit,
            "assessment_confidence": assessment_confidence,
            "decision": decision,
            "decision_label": decision_label,
            "requirement_count": len(requirements),
            "skill_requirement_count": skill_requirement_count,
            "hard_constraint_count": len(hard_constraints),
            "blocking_constraint_count": len(blocking),
            "direct_evidence_count": direct_count,
            "evidence_count": len(candidate_evidence),
        },
        "interpretation": {
            "fit": "Role Fit Score summarizes transparent requirement coverage and evidence quality; it is not a hiring probability.",
            "confidence": "Assessment Confidence reflects text completeness and evidence strength; it is not a calibrated statistical probability.",
            "actions": "Actions prioritize preparation value under the available evidence; they do not estimate a causal hiring effect.",
        },
    }
