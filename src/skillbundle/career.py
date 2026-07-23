from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

from .dictionary import extract
from .requirements import (
    IMPORTANCE_WEIGHTS,
    education_level,
    extract_requirements,
    parse_number,
)
from .taxonomy import category_map


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
# Broad category membership is useful for the role fingerprint, but it is not
# strong enough to count as evidence for the core fit score. Only explicit,
# versioned skill crosswalks above can produce transferable evidence.
MIN_REQUIREMENTS_FOR_SCORING = 2
MIN_JOB_TEXT_LENGTH = 20
MIN_CANDIDATE_TEXT_LENGTH = 20
VALID_CONSTRAINT_STATUSES = {"met", "not_met", "unknown"}
_CANDIDATE_ACTION_CUES = re.compile(
    r"\b(?:built|created|developed|designed|implemented|led|managed|delivered|"
    r"analyzed|automated|improved|used|researched|coordinated|wrote|maintained|"
    r"deployed|taught|supervised|conducted|measured|produced|supported|owned|"
    r"optimized|worked)\b",
    re.IGNORECASE,
)
_CANDIDATE_CONTEXT_CUES = re.compile(
    r"\b(?:project|pipeline|dashboard|dataset|workflow|system|application|"
    r"report|research|role|team|client|user|record|result|outcome|experience|"
    r"year|month)\w*\b|%|\b\d+(?:\.\d+)?\b",
    re.IGNORECASE,
)


def _category_profile(
    requirements: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Summarize a role and candidate profile across the analytical taxonomy.

    The profile is intentionally a descriptive mismatch view. It does not treat
    a category as a substitute for a named skill, and it keeps categories with
    no evidence visible so a user can distinguish a real gap from missing text.
    """
    taxonomy = category_map()
    required_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    evidence_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in requirements:
        if not item.get("hard_constraint") and item.get("analysis_category_code"):
            required_by_category[str(item["analysis_category_code"])].append(item)
    for item in evidence:
        if item.get("analysis_category_code") and not item.get("negated"):
            evidence_by_category[str(item["analysis_category_code"])].append(item)

    codes = sorted(
        set(required_by_category) | set(evidence_by_category),
        key=lambda code: (
            -sum(
                _number(item.get("importance_weight"))
                for item in required_by_category[code]
            ),
            str(taxonomy.get(code, {}).get("name", code)),
        ),
    )
    profiles = []
    for code in codes:
        items = required_by_category[code]
        weight = sum(_number(item.get("importance_weight")) for item in items)
        matched = sum(
            _number(item.get("match_score")) * _number(item.get("importance_weight"))
            for item in items
        )
        coverage = matched / weight if weight else 0.0
        status_counts = Counter(str(item.get("status", "unknown")) for item in items)
        profiles.append(
            {
                "category_code": code,
                "category_name": taxonomy.get(code, {}).get("name", code),
                "definition": taxonomy.get(code, {}).get("definition", ""),
                "required_count": len(items),
                "required_weight": round(weight, 3),
                "matched_count": sum(
                    status_counts.get(status, 0)
                    for status in ("direct", "direct_weak", "transferable")
                ),
                "direct_count": status_counts.get("direct", 0),
                "transferable_count": status_counts.get("transferable", 0),
                "missing_count": status_counts.get("missing", 0),
                "evidence_count": len(evidence_by_category[code]),
                "evidence_coverage": round(coverage, 3),
                "gap_score": round(max(0.0, 1.0 - coverage), 3),
                "status_counts": dict(status_counts),
            }
        )
    return profiles


def _bundle_action(
    left: dict[str, Any], right: dict[str, Any], left_status: str, right_status: str
) -> tuple[str, str]:
    names = (str(left["canonical_skill"]), str(right["canonical_skill"]))
    missing = [
        name
        for name, status in zip(names, (left_status, right_status))
        if status in {"missing", "unknown"}
    ]
    transferable = [
        name
        for name, status in zip(names, (left_status, right_status))
        if status == "transferable"
    ]
    if len(missing) == 2:
        return (
            "foundation_gap",
            f"Build one small work sample that demonstrates {names[0]} and {names[1]} together.",
        )
    if missing:
        return (
            "proof_gap",
            f"Add reviewable proof for {missing[0]} in a task that also uses {names[1] if missing[0] == names[0] else names[0]}.",
        )
    if transferable:
        return (
            "translation_gap",
            f"Translate {transferable[0]} into a concrete result alongside {names[1] if transferable[0] == names[0] else names[0]}.",
        )
    return (
        "bundle_strength",
        f"Show the context and result that connect {names[0]} with {names[1]}.",
    )


def _skill_bundles(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the most decision-relevant skill pairs within one posting.

    These are co-occurring requirements in the supplied role, not estimates of
    market complementarity or wage value. Pair actions are deliberately framed
    as portfolio and translation suggestions for job seekers.
    """
    skills = [item for item in requirements if item.get("requirement_type") == "skill"]
    pairs = []
    seen: set[tuple[str, str]] = set()
    for left, right in combinations(skills, 2):
        ids = tuple(sorted((str(left.get("skill_id")), str(right.get("skill_id")))))
        if ids in seen or ids[0] == ids[1]:
            continue
        seen.add(ids)
        left_status = str(left.get("status", "unknown"))
        right_status = str(right.get("status", "unknown"))
        gap_type, action = _bundle_action(left, right, left_status, right_status)
        priority = min(
            _number(left.get("importance_weight"), 0.2),
            _number(right.get("importance_weight"), 0.2),
        )
        match = min(_number(left.get("match_score")), _number(right.get("match_score")))
        pairs.append(
            {
                "bundle_id": "__".join(ids),
                "skills": [left.get("canonical_skill"), right.get("canonical_skill")],
                "categories": sorted(
                    {
                        str(left.get("analysis_category_code")),
                        str(right.get("analysis_category_code")),
                    }
                ),
                "statuses": [left_status, right_status],
                "priority_score": round(priority, 3),
                "bundle_match_score": round(match, 3),
                "gap_type": gap_type,
                "action": action,
                "is_supported": left_status in {"direct", "direct_weak"}
                and right_status in {"direct", "direct_weak"},
            }
        )
    pairs.sort(
        key=lambda item: (
            -item["priority_score"],
            item["bundle_match_score"],
            item["bundle_id"],
        )
    )
    return pairs[:10]


def _role_fingerprint(
    requirements: list[dict[str, Any]], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    profiles = _category_profile(requirements, evidence)
    dimensions = sorted(
        (item for item in profiles if item["required_count"] and item["gap_score"] > 0),
        key=lambda item: (
            -item["required_weight"] * item["gap_score"],
            item["category_name"],
        ),
    )
    return {
        "taxonomy_id": "deming_kahn_10_ai",
        "taxonomy_version": "v1.0.0",
        "method": "Requirement categories are descriptive dimensions. Named skills remain the unit of evidence and transfer.",
        "categories": profiles,
        "mismatch_dimensions": [
            {
                "category_code": item["category_code"],
                "category_name": item["category_name"],
                "gap_score": item["gap_score"],
                "required_count": item["required_count"],
                "evidence_coverage": item["evidence_coverage"],
            }
            for item in dimensions[:5]
        ],
        "skill_bundles": _skill_bundles(requirements),
        "caveat": "A category profile shows where the supplied texts overlap. It is not a measure of innate ability, hiring probability, or employer preference beyond this posting.",
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
    if not isinstance(evidence, list) or len(evidence) > 100:
        raise ValueError("evidence must be a list with at most 100 items")
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


def _negative_gate_statement(text: str, terms: str) -> bool:
    return bool(
        re.search(
            rf"\b(no|without|not|lack(?:s|ing)?)\b[^.!?;\n]{{0,45}}\b(?:{terms})\b",
            text.casefold(),
        )
    )


def _education_field_matches(required_field: str | None, candidate_text: str) -> bool:
    if not required_field:
        return True
    required_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", required_field.casefold())
        if len(token) > 2
    }
    candidate_lower = candidate_text.casefold()
    return bool(required_tokens) and required_tokens.issubset(
        set(re.findall(r"[a-z0-9]+", candidate_lower))
    )


def _experience_area_matches(required_area: str | None, candidate_clause: str) -> bool:
    if not required_area:
        return True
    stopwords = {
        "and",
        "of",
        "the",
        "in",
        "with",
        "related",
        "professional",
        "years",
        "year",
        "experience",
    }
    required_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", required_area.casefold())
        if len(token) > 2 and token not in stopwords
    }
    candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate_clause.casefold()))
    return bool(required_tokens) and required_tokens.issubset(candidate_tokens)


def _constraint_status(requirement: dict[str, Any], candidate_text: str) -> str:
    """Return a conservative gate status; ambiguous text stays unknown."""

    lowered = candidate_text.casefold()
    requirement_type = requirement["requirement_type"]
    if requirement_type == "professional_license":
        label = str(requirement.get("canonical_skill", "license"))
        terms = r"license|licence|certification|certified"
        if _negative_gate_statement(lowered, terms):
            return "not_met"
        exact_terms = [
            token
            for token in re.findall(r"[a-z0-9]+", label.casefold())
            if token not in {"a", "an", "the", "valid", "current", "professional"}
        ]
        if not exact_terms:
            return "unknown"
        if all(re.search(rf"\b{re.escape(token)}\b", lowered) for token in exact_terms):
            return "met"
        return "unknown"

    if requirement_type == "work_authorization":
        if re.search(
            r"\b(?:not authorized|no work authorization|without authorization|"
            r"lack(?:s|ing)?\s+(?:any\s+)?(?:work\s+)?authorization|"
            r"(?:do not|don't|does not|doesn't)\s+have\s+(?:any\s+)?"
            r"(?:work\s+)?authorization|cannot work|unable to work|no valid visa)\b",
            lowered,
        ):
            return "not_met"
        if re.search(
            r"\b(?:does not state|not stated|not mentioned|no mention)\b"
            r"[^.!?;\n]{0,45}\b(?:authorization|authorized|permit|visa|right to work)\b",
            lowered,
        ):
            return "unknown"
        no_sponsorship = re.search(
            r"\b(?:i\s+)?(?:do not|don't|does not|doesn't)\s+"
            r"(?:need|require)(?:s)?\s+(?:any\s+)?sponsorship\b|"
            r"\bno sponsorship required\b",
            lowered,
        )
        contradictory_sponsorship = re.search(
            r"\b(?:but|however|although)\b[^.!?;\n]{0,80}"
            r"\b(?:need|needs|require|requires)\s+sponsorship\b",
            lowered,
        )
        if no_sponsorship and contradictory_sponsorship:
            return "unknown"
        if no_sponsorship:
            return "met"
        if re.search(
            r"\b(?:requires sponsorship|needs sponsorship)\b",
            lowered,
        ):
            return "not_met"
        if re.search(
            r"\b(?:authorized to work|authorization to work|work authorization|eligible to work|"
            r"right to work|work permit|valid visa|does not require sponsorship|no sponsorship required)\b",
            lowered,
        ):
            return "met"
        return "unknown"

    if requirement_type == "education":
        if _negative_gate_statement(
            lowered, r"bachelor|master|ph\.?d|doctorate|doctoral"
        ):
            return "not_met"
        required_level = requirement.get("education_level") or education_level(
            str(requirement.get("canonical_skill", ""))
        )
        candidate_level = education_level(lowered)
        if required_level is None or candidate_level is None:
            return "unknown"
        if not _education_field_matches(
            str(requirement.get("education_field"))
            if requirement.get("education_field")
            else None,
            lowered,
        ):
            return "unknown"
        return "met" if candidate_level >= required_level else "not_met"

    if requirement_type == "experience_floor":
        required = int(requirement.get("required_years", 0))
        required_area = requirement.get("experience_area")
        for match in re.finditer(
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\+?\s+"
            r"years?\s+(?:of\s+)?(?P<area>[^.!?;\n]{0,100}?)\bexperience\b[^.!?;\n]*",
            lowered,
        ):
            years = parse_number(match.group(1)) or 0
            if years >= required and _experience_area_matches(
                str(required_area) if required_area else None, match.group(0)
            ):
                return "met"
        return "unknown"

    return "unknown"


def _match_evidence(
    requirement: dict[str, Any],
    evidence_by_skill: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    skill_id = str(requirement.get("skill_id"))
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


def _require_non_empty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty text input")
    return value


def _has_substantive_candidate_text(value: str) -> bool:
    return bool(
        len(value.strip()) >= MIN_CANDIDATE_TEXT_LENGTH
        and _CANDIDATE_ACTION_CUES.search(value)
        and _CANDIDATE_CONTEXT_CUES.search(value)
    )


def _review_list(value: object, field_name: str, limit: int = 30) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{field_name} must be a list with at most {limit} items")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must contain objects")
    return [dict(item) for item in value]


def _apply_review(
    requirements: list[dict[str, Any]],
    review: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    """Apply explicit user corrections without allowing silent score edits."""

    if review is None:
        return requirements, {}, []
    if not isinstance(review, dict):
        raise TypeError("review must be an object")
    by_id = {str(item["requirement_id"]): item for item in requirements}
    removed = review.get("removed_requirement_ids", [])
    if not isinstance(removed, list) or len(removed) > 30:
        raise ValueError("removed_requirement_ids must be a list with at most 30 items")
    removed_ids = {str(value) for value in removed}
    unknown_ids = removed_ids - set(by_id)
    if unknown_ids:
        raise ValueError("removed_requirement_ids contains an unknown requirement")
    kept = [item for item in requirements if str(item["requirement_id"]) not in removed_ids]
    changes: list[dict[str, Any]] = [
        {"action": "removed_requirement", "requirement_id": item}
        for item in sorted(removed_ids)
    ]

    added = review.get("added_requirements", [])
    if not isinstance(added, list) or len(added) > 10:
        raise ValueError("added_requirements must be a list with at most 10 items")
    existing_skills = {
        str(item.get("skill_id")) for item in kept if item.get("skill_id")
    }
    for raw in added:
        if not isinstance(raw, dict) or not str(raw.get("text", "")).strip():
            raise ValueError("each added requirement needs non-empty text")
        extracted = extract_requirements(str(raw["text"]).strip())
        soft = [item for item in extracted if not item.get("hard_constraint")]
        if not soft:
            raise ValueError("added requirements must identify a known soft skill")
        for item in soft[:3]:
            if item.get("skill_id") in existing_skills:
                continue
            copied = dict(item)
            copied["requirement_id"] = f"user-req-{len(kept) + 1:03d}"
            copied["extraction_method"] = "user_added"
            copied["extraction_confidence"] = 1.0
            copied["review_status"] = "user_added"
            copied["source_context"] = str(raw["text"]).strip()
            kept.append(copied)
            existing_skills.add(str(copied.get("skill_id")))
            changes.append(
                {
                    "action": "added_requirement",
                    "requirement_id": copied["requirement_id"],
                    "skill_id": copied.get("skill_id"),
                }
            )

    overrides = review.get("constraint_status_overrides", {})
    if overrides in (None, {}):
        overrides = {}
    if not isinstance(overrides, dict) or len(overrides) > 30:
        raise ValueError("constraint_status_overrides must be an object")
    for requirement_id, status in overrides.items():
        item = next(
            (candidate for candidate in kept if candidate["requirement_id"] == str(requirement_id)),
            None,
        )
        if item is None or not item.get("hard_constraint"):
            raise ValueError("constraint status override must target a hard requirement")
        if status not in VALID_CONSTRAINT_STATUSES:
            raise ValueError("constraint status must be met, not_met, or unknown")
        item["review_status"] = "user_confirmed"
        item["user_confirmed_status"] = status
        changes.append(
            {
                "action": "confirmed_constraint",
                "requirement_id": str(requirement_id),
                "status": status,
            }
        )
    return kept, {str(key): str(value) for key, value in overrides.items()}, changes


def _user_added_evidence(review: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not review:
        return []
    rows = _review_list(review.get("added_evidence", []), "added_evidence", 30)
    output = []
    for index, row in enumerate(rows, start=1):
        source_text = str(row.get("source_text", "")).strip()
        skill_id = str(row.get("skill_id", "")).strip()
        canonical = str(row.get("canonical_skill", "")).strip()
        if not source_text or not skill_id or not canonical:
            raise ValueError("each added evidence item needs skill_id, canonical_skill, and source_text")
        output.append(
            {
                "evidence_id": f"user-evidence-{index:03d}",
                "skill_id": skill_id,
                "canonical_skill": canonical,
                "analysis_category_code": str(row.get("analysis_category_code", "")),
                "evidence_type": "self_reported",
                "source_text": source_text[:500],
                "mapping_method": "user_added_evidence",
                "extraction_confidence": 1.0,
                "evidence_status": "user_confirmed_self_report",
                "negated": False,
            }
        )
    return output


def _coverage_components(
    requirements: list[dict[str, Any]],
    active_evidence: list[dict[str, Any]],
    signal_coverage: float,
) -> dict[str, int]:
    hard = [item for item in requirements if item.get("hard_constraint")]
    known_hard = [item for item in hard if item.get("status") in {"met", "not_met"}]
    return {
        "input_completeness_score": round(
            100 * min(1.0, len(requirements) / MIN_REQUIREMENTS_FOR_SCORING)
        ),
        "evidence_coverage_score": round(100 * signal_coverage),
        "eligibility_verification_score": round(
            100 * len(known_hard) / len(hard)
        )
        if hard
        else 100,
        "evidence_item_count": len(active_evidence),
        "requirement_count": len(requirements),
    }


def analyze_fit(
    job_text: str,
    candidate_text: str,
    evidence: list[dict[str, Any]] | None = None,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job_text = _require_non_empty_text(job_text, "job_text")
    candidate_text = _require_non_empty_text(candidate_text, "candidate_text")
    requirements, review_overrides, review_changes = _apply_review(
        extract_requirements(job_text), review
    )
    candidate_evidence = _normalize_evidence(
        evidence if evidence is not None else evidence_from_text(candidate_text)
    )
    candidate_evidence.extend(_user_added_evidence(review))
    active_evidence = [item for item in candidate_evidence if not item.get("negated")]
    explicit_evidence_supplied = bool(evidence) or any(
        item.get("evidence_status") == "user_confirmed_self_report"
        for item in active_evidence
    )
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
            status = review_overrides.get(
                str(requirement["requirement_id"]),
                _constraint_status(requirement, candidate_text),
            )
            item = {
                **requirement,
                "status": status,
                "status_label": STATUS_LABELS[status],
                "match_score": 1.0 if status == "met" else 0.0,
                "evidence_ids": [],
                "matching_method": (
                    "user_confirmed_constraint"
                    if str(requirement["requirement_id"]) in review_overrides
                    else "candidate_constraint_rule"
                ),
            }
            hard_constraints.append(item)
            assessments.append(item)
            continue
        skill_requirement_count += 1
        assessment = _match_evidence(
            requirement, evidence_by_skill
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
    coverage = _coverage_components(requirements, active_evidence, signal_coverage)

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
    analysis_reasons = []
    if len(requirements) < MIN_REQUIREMENTS_FOR_SCORING:
        analysis_reasons.append(
            f"Only {len(requirements)} requirement(s) were identified; at least {MIN_REQUIREMENTS_FOR_SCORING} are needed for a reliable score."
        )
    if len(job_text.strip()) < MIN_JOB_TEXT_LENGTH:
        analysis_reasons.append("The job description is too short to support a reliable analysis.")
    if not _has_substantive_candidate_text(candidate_text) and not explicit_evidence_supplied:
        analysis_reasons.append(
            "The candidate profile needs a concrete action, context, or result to support a reliable evidence assessment."
        )
    if not active_evidence:
        analysis_reasons.append("No candidate evidence was identified.")
    scoring_available = not analysis_reasons
    if not scoring_available:
        gaps.insert(
            0,
            {
                "requirement_id": "input-review",
                "canonical_skill": "Input review",
                "gap_type": "input_gap",
                "action_type": "complete_inputs",
                "importance_level": "must",
                "impact_score": 1.0,
                "priority": "high",
                "time_horizon": "before relying on the report",
                "estimated_effort": "2–5 minutes",
                "action": "Add a fuller job description and candidate evidence, then review the extracted requirements before using any score.",
                "expected_artifact": "At least two named job requirements and one concrete candidate example.",
                "evidence_prompt": "Which task, tool, result, or eligibility fact should be added?",
                "basis": "The supplied text does not contain enough structured information for a reliable fit score.",
            },
        )
    review_status = "user_confirmed" if review else "provisional"
    summary_scores: dict[str, Any] = {
        "evidence_fit_score": soft_fit if scoring_available else None,
        "role_fit_score": soft_fit if scoring_available else None,
        "application_readiness_score": readiness_score if scoring_available else None,
        "capability_signal_score": round(100 * capability_signal)
        if scoring_available
        else None,
        "proof_signal_score": round(100 * proof_signal) if scoring_available else None,
    }
    if not scoring_available:
        readiness = "insufficient_information"
        decision = "insufficient_information"
        decision_label = (
            "Cannot form a reliable analysis yet. Review the input requirements and add more evidence before relying on a score."
        )
    role_fingerprint = _role_fingerprint(assessments, active_evidence)
    return {
        "schema_version": "career_fit.v0.4",
        "product": "Career Fit",
        "mode": "single_job",
        "requirements": assessments,
        "evidence": candidate_evidence,
        "hard_constraints": hard_constraints,
        "gaps": gaps,
        "next_actions": gaps[:6],
        "review": {
            "status": review_status,
            "changes": review_changes,
            "requires_user_confirmation": True,
            "instructions": "Confirm hard constraints, remove false requirements, add missing requirements, and add self-reported evidence before relying on the report.",
        },
        "review_queue": [
            {
                "requirement_id": item["requirement_id"],
                "canonical_skill": item["canonical_skill"],
                "skill_id": item.get("skill_id"),
                "analysis_category_code": item.get("analysis_category_code"),
                "requirement_type": item["requirement_type"],
                "hard_constraint": bool(item.get("hard_constraint")),
                "status": item.get("status", "unknown"),
                "original_text": item.get("original_text", ""),
            }
            for item in assessments
        ],
        "role_fingerprint": role_fingerprint,
        "summary": {
            **summary_scores,
            **coverage,
            "analysis_status": "scored" if scoring_available else "insufficient_information",
            "analysis_reasons": analysis_reasons,
            "review_status": review_status,
            "review_required": True,
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
            "coverage": "Coverage components describe how much of the supplied job, evidence, and eligibility information was mapped. They are not confidence probabilities and are not calibrated model reliability estimates.",
            "actions": "Actions prioritize the next useful proof or verification step under the available evidence; they do not estimate a causal hiring effect.",
            "dimensions": "The role fingerprint shows multidimensional requirement overlap. It keeps named skills separate from broad categories and does not measure latent ability.",
            "bundles": "Skill bundles are requirements that appear together in this posting. They are useful for choosing one integrated proof artifact, not for estimating the market value of a combination.",
        },
        "analysis_notes": [
            "Negated skill statements are retained for auditability and excluded from matching.",
            "Missing evidence is not proof that a candidate lacks the underlying ability.",
            "Hard constraints are reported separately because soft skill overlap cannot offset an unresolved gate.",
        ],
    }


def _role_label(job_text: str, index: int) -> str:
    lines = [line.strip() for line in job_text.splitlines() if line.strip()]
    if not lines:
        return f"Target role {index}"
    first = lines[0]
    if ":" in first and first.casefold().split(":", 1)[0] in {
        "role",
        "title",
        "position",
    }:
        first = first.split(":", 1)[1].strip()
    return first[:100] or f"Target role {index}"


def _priority_basis(summary: dict[str, Any]) -> str:
    decision = summary.get("decision")
    if decision == "insufficient_information":
        return "Add and confirm enough job requirements and candidate evidence before comparing this role."
    if decision == "strong_evidence_overlap":
        return "Closest current preparation match; focus on proof packaging."
    if decision == "targeted_proof_needed":
        return "Promising target; build the highest-priority proof before investing further."
    if decision == "verify_before_applying":
        return "Resolve an eligibility question before prioritizing this application."
    if decision == "blocked_by_constraint":
        return "An apparent eligibility barrier should be resolved first."
    return "Build evidence before treating this role as a priority."


def compare_roles(
    roles: list[str],
    candidate_text: str,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rank a small set of target roles using the same auditable fit engine.

    The result is a preparation priority, not a hiring or income forecast. Roles
    are ordered by application readiness, then evidence fit and mapped input
    coverage so ties are deterministic without inventing a confidence score.
    """
    if not isinstance(roles, list):
        raise TypeError("roles must be a list of job-description strings")
    cleaned = []
    for role in roles:
        if not isinstance(role, str):
            raise TypeError("roles must contain job-description strings")
        if role.strip():
            cleaned.append(role.strip())
    if len(cleaned) < 2:
        raise ValueError("compare_roles requires at least two non-empty roles")
    if len(cleaned) > 3:
        raise ValueError("compare_roles supports at most three roles")

    entries = []
    for index, job_text in enumerate(cleaned, start=1):
        analysis = analyze_fit(job_text, candidate_text, evidence)
        summary = analysis["summary"]
        entries.append(
            {
                "role_id": f"role-{index:02d}",
                "role_label": _role_label(job_text, index),
                "role_text": job_text,
                "summary": summary,
                "priority_basis": _priority_basis(summary),
                "top_action": analysis["next_actions"][0]
                if analysis["next_actions"]
                else None,
                "top_mismatch": analysis["role_fingerprint"]["mismatch_dimensions"][0]
                if analysis["role_fingerprint"]["mismatch_dimensions"]
                else None,
                "top_bundle": analysis["role_fingerprint"]["skill_bundles"][0]
                if analysis["role_fingerprint"]["skill_bundles"]
                else None,
                "analysis": analysis,
            }
        )

    entries.sort(
        key=lambda item: (
            -float(
                item["summary"].get("application_readiness_score")
                if item["summary"].get("application_readiness_score") is not None
                else -1
            ),
            -float(
                item["summary"].get("evidence_fit_score")
                if item["summary"].get("evidence_fit_score") is not None
                else -1
            ),
            -float(
                item["summary"].get("evidence_coverage_score")
                if item["summary"].get("evidence_coverage_score") is not None
                else -1
            ),
            -float(
                item["summary"].get("input_completeness_score")
                if item["summary"].get("input_completeness_score") is not None
                else -1
            ),
            str(item["role_label"]).casefold(),
        )
    )
    for rank, item in enumerate(entries, start=1):
        item["priority_rank"] = rank
    return {
        "schema_version": "career_fit.compare.v0.2",
        "product": "Career Fit",
        "mode": "role_comparison",
        "role_count": len(entries),
        "roles": entries,
        "interpretation": {
            "priority": "Roles are ordered by preparation readiness, then evidence fit and mapped input coverage. This is not a hiring-probability ranking.",
            "transfer": "Transferable evidence remains visible as a bridge and is never treated as direct equivalence.",
            "missing": "A lower-ranked role may reflect missing proof or an unresolved gate rather than lower underlying ability.",
        },
    }
