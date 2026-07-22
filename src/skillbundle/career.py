from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .dictionary import extract
from .requirements import IMPORTANCE_WEIGHTS, extract_requirements, parse_number


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
    "direct": "Direct evidence",
    "direct_weak": "Mentioned, proof is thin",
    "transferable": "Transferable evidence",
    "missing": "No evidence found",
    "met": "Requirement appears met",
    "not_met": "Explicitly not met",
    "unknown": "Needs verification",
}

# This map makes transfer assumptions auditable instead of silently treating
# every skill in one broad category as equivalent.
TRANSFER_SKILL_IDS = {
    "software.sql": {"software.python", "software.r", "software.pandas"},
    "software.python": {"software.r", "software.pandas", "software.numpy"},
    "software.tableau": {"software.power_bi", "skill.data_visualization"},
    "software.power_bi": {"software.tableau", "skill.data_visualization"},
    "skill.people_analytics": {
        "skill.hr_data",
        "skill.labor_economics",
        "skill.data_analysis",
        "skill.statistics",
    },
    "skill.hr_data": {
        "skill.people_analytics",
        "skill.labor_economics",
        "skill.data_analysis",
    },
    "skill.data_visualization": {
        "software.tableau",
        "software.power_bi",
        "software.python",
        "software.r",
    },
    "skill.stakeholder_communication": {
        "skill.communication",
        "skill.writing",
        "skill.project_management",
    },
    "skill.process_improvement": {
        "skill.problem_solving",
        "skill.project_management",
    },
    "skill.leadership": {"skill.supervision", "skill.project_management"},
}
CATEGORY_BASELINE_TRANSFER = {
    "cognitive_skill",
    "social_skill",
    "character_skill",
    "writing_skill",
    "customer_project_management_skill",
    "people_management_skill",
    "financial_skill",
    "general_computer_skill",
    "ai_skill",
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


def _local_clause(text: str, start: int, end: int) -> str:
    boundaries = ".!?;\n"
    left = max((text.rfind(mark, 0, start) for mark in boundaries), default=-1) + 1
    right_candidates = [text.find(mark, end) for mark in boundaries]
    right_candidates = [value for value in right_candidates if value >= 0]
    right = min(right_candidates, default=len(text))
    return text[left:right].strip()


def _is_negated(text: str, start: int, end: int) -> bool:
    """Detect conservative local negation before a skill mention."""
    clause = _local_clause(text, start, end)
    mention_offset = clause.casefold().find(text[start:end].casefold())
    if mention_offset < 0:
        return False
    prefix = clause[:mention_offset]
    if prefix.rstrip().casefold().endswith("not only"):
        return False
    return bool(
        re.search(
            r"\b(?:no|without|lack(?:s|ing)?|not|never|haven't|hasn't|have not|"
            r"has not|doesn't|don't|didn't)\b[^.!?;\n]{0,80}$",
            prefix,
            re.IGNORECASE,
        )
    )


def _infer_evidence_type(text: str, start: int, end: int) -> str:
    clause = _local_clause(text, start, end)
    if re.search(
        r"\b(research|thesis|dissertation|academic study|research project)\b",
        clause,
        re.I,
    ):
        return "research_project"
    if re.search(r"\b(portfolio|github|repository|open-source)\b", clause, re.I):
        return "portfolio"
    if re.search(r"\b(course|class|training|bootcamp)\b", clause, re.I):
        return "course"
    if re.search(r"\b(certificate|certification)\b", clause, re.I):
        return "certificate"
    if re.search(
        r"\b(worked|managed|led|delivered|employment|role|job|professional|experience)\b",
        clause,
        re.I,
    ):
        return "work"
    return "self_reported"


def evidence_from_text(text: str) -> list[dict[str, Any]]:
    """Create conservative, inspectable evidence objects from profile text.

    Mentions inside a detected negative statement are retained for auditability
    but are explicitly excluded from matching.
    """
    items = []
    for index, item in enumerate(extract(text), start=1):
        negated = _is_negated(text, int(item["start"]), int(item["end"]))
        evidence_type = (
            "unknown"
            if negated
            else _infer_evidence_type(text, int(item["start"]), int(item["end"]))
        )
        items.append(
            {
                "evidence_id": f"evidence-{index:03d}",
                "skill_id": item["skill_id"],
                "canonical_skill": item["canonical"],
                "analysis_category_code": item["analysis_category_code"],
                "evidence_type": evidence_type,
                "source_text": item["text"],
                "mapping_method": item["mapping_method"]
                + ("+negation_rule" if negated else ""),
                "extraction_confidence": item["confidence"],
                "source_taxonomy": item["source_taxonomy"],
                "source_skill_id": item["source_skill_id"],
                "review_status": item["review_status"],
                "match_mode": item["match_mode"],
                "dictionary_version": item["dictionary_version"],
                "evidence_status": "negated_statement"
                if negated
                else "candidate_profile_inferred",
                "negated": negated,
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
        copied.setdefault("negated", False)
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
        positive = re.search(
            r"\b(licensed|licence|license|certified|certification)\b", lowered
        )
        negative = re.search(
            r"\b(no|without|lack(?:s|ing)?|not)\b[^.!?;\n]{0,35}\b(license|licence|certification|certified)\b",
            lowered,
        )
    elif requirement_type == "work_authorization":
        positive = re.search(
            r"\b(authorized to work|authorization to work|work authorization|eligible to work|"
            r"right to work|work permit|valid visa|does not require sponsorship|no sponsorship required)\b",
            lowered,
        )
        negative = re.search(
            r"\b(?:not authorized|no work authorization|without authorization|requires sponsorship|"
            r"need(?:s)? sponsorship|no valid visa)\b",
            lowered,
        )
        missing_statement = re.search(
            r"\b(?:does not state|not stated|not mentioned|no mention)\b"
            r"[^.!?;\n]{0,45}\b(?:authorization|authorized|permit|visa|right to work)\b",
            lowered,
        )
    elif requirement_type == "education":
        positive = re.search(
            r"\b(bachelor|master|ph\.?d|doctorate|doctoral)\b", lowered
        )
        negative = re.search(
            r"\b(no|without|not|lack(?:s|ing)?)\b[^.!?;\n]{0,25}\b(bachelor|master|ph\.?d|doctorate|doctoral)\b",
            lowered,
        )
    elif requirement_type == "experience_floor":
        required = int(requirement.get("required_years", 0))
        years = re.findall(
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\+?\s+years?\b",
            lowered,
        )
        positive = any((parse_number(value) or 0) >= required for value in years)
        negative = None
    else:
        positive = None
        negative = None
    if negative:
        return "not_met"
    if requirement_type == "work_authorization" and missing_statement:
        return "unknown"
    if positive:
        return "met"
    return "unknown"


def _match_evidence(
    requirement: dict[str, Any],
    evidence_by_skill: dict[str, list[dict[str, Any]]],
    evidence_by_category: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    skill_id = str(requirement.get("skill_id"))
    category = str(requirement.get("analysis_category_code"))
    direct = [
        item for item in evidence_by_skill.get(skill_id, []) if not item.get("negated")
    ]
    matching_method = "direct_skill_id"
    if direct:
        selected, coverage, status, proficiency = direct, 1.0, "direct", 0.85
    else:
        transferable = []
        for candidate_id in TRANSFER_SKILL_IDS.get(skill_id, set()):
            transferable.extend(
                item
                for item in evidence_by_skill.get(candidate_id, [])
                if not item.get("negated")
            )
        if transferable:
            selected, coverage, status, proficiency = (
                transferable,
                0.55,
                "transferable",
                0.65,
            )
            matching_method = "reviewable_transfer_crosswalk"
        elif category in CATEGORY_BASELINE_TRANSFER:
            category_items = [
                item
                for item in evidence_by_category.get(category, [])
                if not item.get("negated") and str(item.get("skill_id")) != skill_id
            ]
            if category_items:
                selected, coverage, status, proficiency = (
                    category_items,
                    0.45,
                    "transferable",
                    0.55,
                )
                matching_method = "same_category_baseline"
            else:
                selected, coverage, status, proficiency = [], 0.0, "missing", 0.0
        else:
            selected, coverage, status, proficiency = [], 0.0, "missing", 0.0
    if selected:
        evidence = sum(_evidence_score(item) for item in selected) / len(selected)
        recency = sum(_recency_score(item) for item in selected) / len(selected)
        depth = sum(_depth_score(item) for item in selected) / len(selected)
    else:
        evidence, recency, depth = 0.0, 0.0, 0.0
    score = (
        0.35 * coverage
        + 0.25 * evidence
        + 0.20 * proficiency
        + 0.10 * recency
        + 0.10 * depth
    )
    if status == "direct" and evidence < 0.55:
        status = "direct_weak"
    return {
        "status": status,
        "status_label": STATUS_LABELS[status],
        "match_score": round(score, 3),
        "coverage": round(coverage, 3),
        "evidence_strength": round(evidence, 3),
        "evidence_ids": [item["evidence_id"] for item in selected],
        "matching_method": matching_method,
        "evidence": selected,
    }


def _gap_for(
    requirement: dict[str, Any], assessment: dict[str, Any]
) -> dict[str, Any] | None:
    status = assessment.get("status")
    if status in ("direct", "met"):
        return None
    canonical = str(
        requirement.get("canonical_skill", requirement.get("original_text"))
    )
    importance = str(requirement.get("importance_level", "inferred"))
    impact = IMPORTANCE_WEIGHTS.get(importance, 0.2) * (
        1 - _number(assessment.get("match_score"))
    )
    if status == "direct_weak":
        gap_type = "proof_gap"
        action_type = "package_proof"
        action = f"Turn your existing {canonical} mention into one concrete proof point with a task, context, and measurable result."
        artifact = "A quantified resume bullet, work sample, or interview story."
        prompt = f"What did you do with {canonical}, for whom, and what changed because of it?"
        horizon, effort = "before applying", "15–30 minutes"
    elif status == "transferable":
        translation_skills = {
            "skill.people_analytics",
            "skill.hr_data",
            "skill.stakeholder_communication",
        }
        if requirement.get("skill_id") in translation_skills:
            gap_type = "translation_gap"
            action_type = "translate_experience"
            action = f"Rewrite one existing example in the employer's language for {canonical}, naming the task, audience, and result without claiming identical experience."
            artifact = "A role-specific resume bullet and a short interview story."
            prompt = f"Which existing example can be translated into {canonical} language, and what part still needs proof?"
            horizon, effort = "before applying", "30–60 minutes"
        else:
            gap_type = "bridge_gap"
            action_type = "build_bridge_project"
            action = f"Build a small bridge example using {canonical}, then explain which existing evidence transfers and what remains new."
            artifact = "A focused portfolio example with a short transfer note."
            prompt = f"Which adjacent project can demonstrate {canonical} without overstating equivalence?"
            horizon, effort = "short term", "1–2 weeks"
    else:
        gap_type = "foundation_gap"
        action_type = "build_foundation"
        action = f"Create a structured learning plan for {canonical} and finish with a small work sample before treating it as a core qualification."
        artifact = "A learning log plus a small, reviewable work sample."
        prompt = (
            f"What is the smallest real task that would let you practice {canonical}?"
        )
        horizon, effort = "medium term", "2–6 weeks"
    return {
        "requirement_id": requirement["requirement_id"],
        "canonical_skill": canonical,
        "gap_type": gap_type,
        "action_type": action_type,
        "importance_level": importance,
        "impact_score": round(impact, 3),
        "priority": "high" if impact >= 0.45 else "medium" if impact >= 0.20 else "low",
        "time_horizon": horizon,
        "estimated_effort": effort,
        "action": action,
        "expected_artifact": artifact,
        "evidence_prompt": prompt,
        "basis": "This is a transparent preparation recommendation, not a predicted hiring effect.",
    }


def _readiness_status(score: int, blocking: list[dict[str, Any]]) -> str:
    if any(item["status"] == "not_met" for item in blocking):
        return "blocked_by_constraint"
    if blocking:
        return "verify_before_applying"
    if score >= 75:
        return "apply_and_refine"
    if score >= 50:
        return "apply_after_targeted_proof"
    return "build_evidence_before_prioritizing"


def analyze_fit(
    job_text: str,
    candidate_text: str,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    requirements = extract_requirements(job_text)
    candidate_evidence = _normalize_evidence(
        evidence if evidence is not None else evidence_from_text(candidate_text)
    )
    active_evidence = [item for item in candidate_evidence if not item.get("negated")]
    evidence_by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in active_evidence:
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
                "matching_method": "candidate_constraint_rule",
            }
            hard_constraints.append(item)
            assessments.append(item)
            continue
        skill_requirement_count += 1
        assessment = _match_evidence(
            requirement, evidence_by_skill, evidence_by_category
        )
        if assessment["status"] == "direct":
            direct_count += 1
        weight = _number(requirement["importance_weight"], 0.2)
        weighted_total += weight * _number(assessment["match_score"])
        weight_total += weight
        item = {
            **requirement,
            **{key: value for key, value in assessment.items() if key != "evidence"},
        }
        assessments.append(item)
        gap = _gap_for(requirement, assessment)
        if gap:
            gaps.append(gap)

    soft_fit = round(100 * weighted_total / weight_total) if weight_total else 0
    job_clarity = min(1.0, len(requirements) / 6) if requirements else 0.0
    candidate_quality = (
        sum(_evidence_score(item) for item in active_evidence) / len(active_evidence)
        if active_evidence
        else 0.0
    )
    signal_coverage = (
        sum(
            1.0
            if item["status"] == "direct"
            else 0.55
            if item["status"] == "transferable"
            else 0.0
            for item in assessments
            if not item["hard_constraint"]
        )
        / skill_requirement_count
        if skill_requirement_count
        else 0.0
    )
    assessment_confidence = round(
        100 * (0.35 * job_clarity + 0.35 * candidate_quality + 0.30 * signal_coverage)
    )

    capability_signal = (
        sum(
            1.0
            if item["status"] == "direct"
            else 0.82
            if item["status"] == "direct_weak"
            else 0.60
            if item["status"] == "transferable"
            else 0.0
            for item in assessments
            if not item["hard_constraint"]
        )
        / skill_requirement_count
        if skill_requirement_count
        else 0.0
    )
    proof_signal = (
        sum(
            _number(item.get("evidence_strength"))
            for item in assessments
            if not item["hard_constraint"]
        )
        / skill_requirement_count
        if skill_requirement_count
        else 0.0
    )
    must_items = [
        item
        for item in assessments
        if item.get("importance_level") == "must" and not item["hard_constraint"]
    ]
    must_match = (
        sum(_number(item.get("match_score")) for item in must_items) / len(must_items)
        if must_items
        else soft_fit / 100
    )
    blocking = [item for item in hard_constraints if item["status"] != "met"]
    gate_signal = (
        0.0
        if any(item["status"] == "not_met" for item in blocking)
        else 0.35
        if blocking
        else 1.0
    )
    readiness_score = round(
        100 * (0.50 * must_match + 0.30 * proof_signal + 0.20 * gate_signal)
    )
    readiness = _readiness_status(readiness_score, blocking)

    if any(item["status"] == "not_met" for item in blocking):
        decision = "blocked_by_constraint"
        decision_label = "A hard requirement appears unmet; resolve it before prioritizing this application."
    elif blocking:
        decision = "verify_before_applying"
        decision_label = "Verify the unresolved hard requirement before relying on the soft evidence score."
    elif soft_fit >= 80:
        decision = "strong_evidence_overlap"
        decision_label = "Strong evidence overlap; focus on proof packaging and role-specific framing."
    elif soft_fit >= 60:
        decision = "targeted_proof_needed"
        decision_label = "Promising overlap; build targeted proof before treating the role as a priority."
    else:
        decision = "evidence_building_needed"
        decision_label = (
            "Several important requirements need evidence or structured preparation."
        )

    for item in blocking:
        gaps.append(
            {
                "requirement_id": item["requirement_id"],
                "canonical_skill": item["canonical_skill"],
                "gap_type": "verification_gap",
                "action_type": "verify_constraint",
                "importance_level": "must",
                "impact_score": 1.0,
                "priority": "high",
                "time_horizon": "before applying",
                "estimated_effort": "5–15 minutes",
                "action": f"Verify or address the application gate: {item['canonical_skill']}.",
                "expected_artifact": "A confirmed eligibility statement or supporting document kept by the candidate.",
                "evidence_prompt": f"Can you confirm the exact status of {item['canonical_skill']} for this role and location?",
                "basis": "A hard requirement is separate from skill overlap and cannot be offset by a high soft score.",
            }
        )
    gaps.sort(
        key=lambda item: (
            -_number(item.get("impact_score")),
            item.get("canonical_skill", ""),
        )
    )
    return {
        "schema_version": "career_fit.v0.2",
        "product": "Career Fit",
        "mode": "single_job",
        "requirements": assessments,
        "evidence": candidate_evidence,
        "hard_constraints": hard_constraints,
        "gaps": gaps,
        "next_actions": gaps[:6],
        "summary": {
            "evidence_fit_score": soft_fit,
            "role_fit_score": soft_fit,
            "application_readiness_score": readiness_score,
            "capability_signal_score": round(100 * capability_signal),
            "proof_signal_score": round(100 * proof_signal),
            "assessment_confidence": assessment_confidence,
            "readiness_status": readiness,
            "decision": decision,
            "decision_label": decision_label,
            "requirement_count": len(requirements),
            "skill_requirement_count": skill_requirement_count,
            "hard_constraint_count": len(hard_constraints),
            "blocking_constraint_count": len(blocking),
            "direct_evidence_count": direct_count,
            "evidence_count": len(active_evidence),
            "excluded_evidence_count": len(candidate_evidence) - len(active_evidence),
        },
        "interpretation": {
            "capability": "Capability Signal describes overlap between the supplied experience and the role's skill language. Transferable evidence is a lead, not proof of equivalence.",
            "proof": "Proof Signal describes how concrete and reviewable the supplied evidence is. A low signal can mean an evidence-packaging problem rather than an ability problem.",
            "readiness": "Application Readiness is a preparation triage measure that combines must-have evidence, proof strength, and unresolved gates. It is not a hiring probability.",
            "confidence": "Information Confidence reflects the clarity and completeness of the supplied texts. It is not a calibrated statistical probability.",
            "actions": "Actions prioritize the next useful proof or verification step under the available evidence; they do not estimate a causal hiring effect.",
        },
        "analysis_notes": [
            "Negated skill statements are retained for auditability and excluded from matching.",
            "Missing evidence is not proof that a candidate lacks the underlying ability.",
            "Hard constraints are reported separately because soft skill overlap cannot offset an unresolved gate.",
        ],
    }
