from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

from .dictionary import extract
from .requirements import (
    IMPORTANCE_WEIGHTS,
    education_level,
    experience_claims,
    extract_requirements,
)
from .taxonomy import category_map


EVIDENCE_WEIGHTS = {
    "work": 0.95,
    "research_project": 0.90,
    "portfolio": 0.80,
    "github_project": 0.80,
    "course": 0.60,
    "certificate": 0.55,
    "self_reported": 0.15,
    "unknown": 0.20,
}

CLAIM_ONLY_EVIDENCE_TYPES = {"self_reported", "unknown"}
VALID_EVIDENCE_TYPES = set(EVIDENCE_WEIGHTS)
VALID_IMPORTANCE_LEVELS = set(IMPORTANCE_WEIGHTS)

STATUS_LABELS = {
    "direct": "Direct evidence",
    "direct_weak": "Mentioned, proof is thin",
    "claimed": "Claimed capability, proof not supplied",
    "transferable": "Transferable evidence",
    "transferable_claimed": "Transferable claim, proof not supplied",
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
    "skill.communication": {
        "skill.customer_service",
        "skill.research",
        "skill.supervision",
        "skill.teaching",
    },
    "skill.project_management": {
        "skill.logistics",
        "skill.scheduling",
        "skill.supervision",
        "skill.customer_service",
    },
    "skill.logistics": {
        "skill.scheduling",
        "skill.project_management",
        "skill.process_improvement",
    },
    "skill.design": {"skill.research", "skill.research_design"},
    "skill.research_design": {"skill.research", "skill.design"},
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
VALID_CANDIDATE_LANGUAGES = {"auto", "en", "es", "zh", "other"}
_CANDIDATE_ACTION_CUES = re.compile(
    r"\b(?:built|created|developed|designed|implemented|led|managed|delivered|"
    r"analyzed|automated|improved|used|researched|coordinated|wrote|maintained|"
    r"deployed|taught|supervised|conducted|measured|produced|supported|owned|"
    r"optimized|worked|tracked|scheduled|answered|helped|resolved|briefed|"
    r"presented|explained|trained|budgeted|planned|gathered|framed|prioritized|"
    r"documented|learned|moved|move|checked|check|told|tell|served|operated|"
    r"prepared|communicated|provided|cared|reviewed|discharged)\b",
    re.IGNORECASE,
)
_CANDIDATE_CONTEXT_CUES = re.compile(
    r"\b(?:project|pipeline|dashboard|dataset|workflow|system|application|"
    r"report|research|role|team|client|user|record|result|outcome|experience|"
    r"year|month|customer|order|truck|call|visitor|shipment|inventory|budget|"
    r"cost|expense|patient|technician|content|finding|recommendation|bug|issue|"
    r"part|campaign|data|family|school|leader|administrator|student|staff|vendor|"
    r"case|schedule|resume|library|pull request|release|contributor|care|"
    r"computer)\w*\b|%|\b\d+(?:\.\d+)?\b",
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
        if status in {"missing", "unknown", "claimed", "transferable_claimed"}
    ]
    transferable = [
        name
        for name, status in zip(names, (left_status, right_status))
        if status in {"transferable", "transferable_claimed"}
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
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _finite_non_negative(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be a finite number")
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _recency_score(item: dict[str, Any]) -> float:
    years = item.get("recency_years")
    if years in (None, ""):
        return 0.45 if item.get("evidence_type") in CLAIM_ONLY_EVIDENCE_TYPES else 0.70
    value = max(0.0, _number(years))
    if value <= 2:
        return 1.0
    if value <= 5:
        return 0.80
    return 0.60


def _depth_score(item: dict[str, Any]) -> float:
    months = item.get("duration_months")
    if months in (None, ""):
        return 0.25 if item.get("evidence_type") in CLAIM_ONLY_EVIDENCE_TYPES else 0.65
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
    if evidence_type not in CLAIM_ONLY_EVIDENCE_TYPES and (
        item.get("measurable_result") or item.get("result")
    ):
        base = min(1.0, base + 0.08)
    return base


def _is_claim_only(item: dict[str, Any]) -> bool:
    return str(item.get("evidence_type", "unknown")) in CLAIM_ONLY_EVIDENCE_TYPES


def _aggregate_evidence(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate evidence monotonically so a weak extra claim cannot erase proof."""

    if not items:
        return {
            "strength": 0.0,
            "recency": 0.0,
            "depth": 0.0,
            "primary_evidence_id": None,
            "method": "none",
        }
    ranked = sorted(
        items,
        key=lambda item: (
            -_evidence_score(item),
            -_recency_score(item),
            -_depth_score(item),
            str(item.get("evidence_id", "")),
        ),
    )
    primary = ranked[0]
    supporting = ranked[1:3]
    strength = min(
        1.0,
        _evidence_score(primary)
        + sum(_evidence_score(item) for item in supporting) * 0.15,
    )
    return {
        "strength": round(strength, 3),
        "recency": round(max(_recency_score(item) for item in ranked), 3),
        "depth": round(max(_depth_score(item) for item in ranked), 3),
        "primary_evidence_id": primary.get("evidence_id"),
        "method": "primary_plus_top_two_supporting",
    }


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


def _normalize_evidence(
    evidence: list[dict[str, Any]], *, user_supplied: bool = True
) -> list[dict[str, Any]]:
    if not isinstance(evidence, list) or len(evidence) > 100:
        raise ValueError("evidence must be a list with at most 100 items")
    normalized = []
    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            raise ValueError("each evidence item must be an object")
        allowed_fields = {
            "evidence_id",
            "skill_id",
            "canonical_skill",
            "analysis_category_code",
            "evidence_type",
            "source_text",
            "result",
            "measurable_result",
            "duration_months",
            "recency_years",
            "source_name",
            "mapping_method",
            "extraction_confidence",
            "source_taxonomy",
            "source_skill_id",
            "review_status",
            "dictionary_version",
            "evidence_status",
            "verification_status",
            "negated",
        }
        copied = {key: item[key] for key in allowed_fields if key in item}
        copied.setdefault("evidence_id", f"evidence-{index:03d}")
        copied.setdefault("evidence_type", "unknown")
        copied.setdefault("negated", False)
        if copied["evidence_type"] not in VALID_EVIDENCE_TYPES:
            raise ValueError("unsupported evidence type")
        if copied.get("skill_id") is None and copied.get("canonical_skill"):
            matched = extract(str(copied["canonical_skill"]))
            if matched:
                copied["skill_id"] = matched[0]["skill_id"]
                copied["analysis_category_code"] = matched[0]["analysis_category_code"]
        if not str(copied.get("skill_id", "")).strip() or not str(
            copied.get("canonical_skill", "")
        ).strip():
            raise ValueError("each evidence item needs skill_id and canonical_skill")
        raw_source_text = copied.get("source_text")
        if not isinstance(raw_source_text, str):
            raise ValueError("each evidence item needs a text source_text")
        source_text = raw_source_text.strip()
        if not source_text:
            raise ValueError("each evidence item needs source_text")
        copied["source_text"] = source_text[:500]
        copied["result"] = str(copied.get("result", "")).strip()[:500]
        copied["measurable_result"] = str(
            copied.get("measurable_result", "")
        ).strip()[:500]
        if user_supplied:
            copied["evidence_status"] = (
                "user_confirmed_self_report"
                if copied["evidence_type"] in CLAIM_ONLY_EVIDENCE_TYPES
                else "user_declared_structured_evidence"
            )
            copied["verification_status"] = "user_declared"
            copied["review_status"] = "user_supplied"
        for numeric_field in ("duration_months", "recency_years"):
            if copied.get(numeric_field) not in (None, ""):
                copied[numeric_field] = _finite_non_negative(
                    copied[numeric_field], numeric_field
                )
        normalized.append(copied)
    return normalized


def _negative_gate_statement(text: str, terms: str) -> bool:
    return bool(
        re.search(
            rf"\b(no|without|not|lack(?:s|ing)?)\b[^.!?;\n]{{0,45}}\b(?:{terms})\b",
            text.casefold(),
        )
    )


_FUTURE_MODAL_PATTERN = (
    r"(?:will|would|could|can|may|might|expect(?:s|ed)?|"
    r"plan(?:s|ned)?|hope(?:s|d)?|intend(?:s|ed)?|aim(?:s|ed)?)"
)
_FUTURE_TIME_PATTERN = (
    r"(?:by\s+(?:20\d{2}|next\s+\w+|[a-z]+\s+20\d{2}|"
    r"the\s+end\s+of\s+\w+)|next\s+\w+|this\s+\w+|"
    r"in\s+(?:20\d{2}|\d+\s+(?:day|week|month|year)s?)|later)"
)
_CONDITIONAL_PATTERN = (
    r"(?:if|unless|once|when|pending|subject\s+to|waiting\s+for|"
    r"applied\s+for|in\s+progress)"
)
_HISTORICAL_GATE_PATTERN = (
    r"(?:was|were|used\s+to|previously|formerly|once|had|held)"
)
_INVALID_GATE_PATTERN = (
    r"(?:expired|revoked|inactive|invalid|no\s+longer|"
    r"not\s+(?:currently|current|valid|active|authorized|eligible|permitted)|"
    r"no\s+current|without|lack(?:s|ing)?)"
)
_CURRENT_GATE_VERB_PATTERN = r"(?:am|is|are|have|has|hold|holds|possess|possesses)"
_LICENSE_SUBJECT_PATTERN = (
    r"(?:license|licence|licensed|licensing|certified|certification)"
)
_AUTHORIZATION_SUBJECT_PATTERN = (
    r"(?:authorized(?:\s+to\s+work)?|eligible(?:\s+to\s+work)?|"
    r"right\s+to\s+work|(?:work\s+)?authorization|permit|valid\s+visa)"
)


def _future_or_conditional_parts(before: str, after: str) -> bool:
    """Identify claims that describe a future or conditional gate state."""

    before_lower = before.casefold()
    after_lower = after.casefold()
    local_before = re.split(
        r"(?:,|\b(?:and|but|however|although)\b)", before_lower
    )[-1]
    local_after = re.split(
        r"\b(?:and|but|however|although)\b", after_lower, maxsplit=1
    )[0]
    leading_future_time = bool(
        re.match(rf"\s*\b{_FUTURE_TIME_PATTERN}\b", before_lower)
    )
    leading_condition = bool(
        re.match(
            rf"\s*\b{_CONDITIONAL_PATTERN}\b[^.!?;\n,]*,",
            before_lower,
        )
    )
    return bool(
        re.search(rf"\b{_FUTURE_MODAL_PATTERN}\b", local_before)
        or re.search(rf"\b{_CONDITIONAL_PATTERN}\b", local_before)
        or re.search(rf"\b{_CONDITIONAL_PATTERN}\b", local_after)
        or leading_condition
        or leading_future_time
        or re.search(rf"\b{_FUTURE_TIME_PATTERN}\b", local_after)
    )


def _future_or_conditional_subject(text: str, subject_pattern: str) -> bool:
    """Return whether a subject is asserted only in a future/conditional state."""

    for before, after, _ in _subject_contexts(text, subject_pattern):
        if _future_or_conditional_parts(before, after):
            return True
    return False


def _subject_contexts(
    text: str, subject_pattern: str
) -> list[tuple[str, str, str]]:
    """Return local before/after clauses and their full sentence for each subject."""

    lowered = text.casefold()
    contexts: list[tuple[str, str, str]] = []
    for match in re.finditer(rf"\b(?:{subject_pattern})\b", lowered):
        sentence_start = max(
            lowered.rfind(mark, 0, match.start()) for mark in ".!?;\n"
        ) + 1
        sentence_end_candidates = [
            lowered.find(mark, match.end()) for mark in ".!?;\n"
        ]
        sentence_end_candidates = [
            value for value in sentence_end_candidates if value >= 0
        ]
        sentence_end = min(sentence_end_candidates, default=len(lowered))
        contexts.append(
            (
                lowered[sentence_start:match.start()],
                lowered[match.end():sentence_end],
                lowered[sentence_start:sentence_end],
            )
        )
    return contexts


def _subject_has_state(
    text: str,
    subject_pattern: str,
    state_pattern: str,
    *,
    include_full_after: bool = False,
) -> bool:
    """Find a historical or invalid state attached to a gate subject."""

    state_re = re.compile(rf"\b(?:{state_pattern})\b")
    for before, after, sentence in _subject_contexts(text, subject_pattern):
        local_before = re.split(
            r"(?:,|\b(?:and|but|however|although)\b)", before
        )[-1]
        local_after = re.split(
            r"\b(?:and|but|however|although)\b", after, maxsplit=1
        )[0]
        if state_re.search(local_before) or state_re.search(local_after):
            return True
        if include_full_after and state_re.search(sentence):
            return True
    return False


def _subject_has_current_assertion(text: str, subject_pattern: str) -> bool:
    """Return whether the subject has a present-tense assertion."""

    current_re = re.compile(rf"\b{_CURRENT_GATE_VERB_PATTERN}\b")
    historical_re = re.compile(rf"\b{_HISTORICAL_GATE_PATTERN}\b")
    for before, after, _ in _subject_contexts(text, subject_pattern):
        local_before = re.split(
            r"(?:,|\b(?:and|but|however|although)\b)", before
        )[-1]
        local_after = re.split(
            r"\b(?:and|but|however|although)\b", after, maxsplit=1
        )[0]
        if historical_re.search(local_before):
            continue
        if current_re.search(local_before) or current_re.search(local_after):
            return True
    return False


def _future_or_conditional_experience(
    candidate_text: str, claim: dict[str, object]
) -> bool:
    """Check the clause surrounding an experience claim for temporal uncertainty."""

    lowered = candidate_text.casefold()
    start = int(claim["start"])
    end = int(claim["end"])
    sentence_start = max(
        lowered.rfind(mark, 0, start) for mark in ".!?\n"
    ) + 1
    sentence_end_candidates = [lowered.find(mark, end) for mark in ".!?\n"]
    sentence_end_candidates = [value for value in sentence_end_candidates if value >= 0]
    sentence_end = min(sentence_end_candidates, default=len(lowered))
    return _future_or_conditional_parts(
        lowered[sentence_start:start], lowered[end:sentence_end]
    )


def _negative_experience_claim(
    candidate_text: str,
    claim: dict[str, object],
    required_area: str | None,
) -> bool:
    """Identify a qualifying-looking experience claim that is explicitly negated."""

    lowered = candidate_text.casefold()
    start = int(claim["start"])
    end = int(claim["end"])
    sentence_start = max(
        lowered.rfind(mark, 0, start) for mark in ".!?\n"
    ) + 1
    sentence_end_candidates = [lowered.find(mark, end) for mark in ".!?\n"]
    sentence_end_candidates = [value for value in sentence_end_candidates if value >= 0]
    sentence_end = min(sentence_end_candidates, default=len(lowered))
    before = lowered[sentence_start:start]
    sentence = lowered[sentence_start:sentence_end]
    following_end_candidates = [
        lowered.find(mark, sentence_end + 1) for mark in ".!?\n"
    ]
    following_end_candidates = [
        value for value in following_end_candidates if value >= 0
    ]
    following_end = min(following_end_candidates, default=len(lowered))
    following = re.sub(
        r"^\s*[.!?]\s*", "", lowered[sentence_end:following_end], count=1
    )
    threshold_phrase = re.search(
        r"\b(?:no\s+(?:less|fewer)\s+than|not\s+(?:less|fewer)\s+than|"
        r"not\s+only)\b",
        before,
    )
    insufficient_phrase = re.search(
        r"\b(?:less|fewer)\s+than\b|\b(?:under|below|short\s+of)\b",
        before,
    )
    if insufficient_phrase and not threshold_phrase:
        return True
    if not threshold_phrase and re.search(
        r"\b(?:no|without|not|never|don't|do not|doesn't|does not|"
        r"lack(?:s|ing)?|failed to)\b(?:\s+\w+){0,8}\s*$",
        before,
    ):
        return True
    if required_area and not threshold_phrase:
        area_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", required_area.casefold())
            if len(token) > 2
        ]
        if area_tokens:
            area_pattern = r"\s+".join(re.escape(token) for token in area_tokens)
            if re.search(
                rf"\b(?:no|without|not|never|lack(?:s|ing)?)\b"
                rf"[^.!?;\n]{{0,45}}\b{area_pattern}\b",
                sentence,
            ):
                return True
    post_claim_negative = re.compile(
        r"\b(?:none|nothing)\b|"
        r"\bnot\s+(?:relevant|qualifying|qualified|applicable)\b|"
        r"\b(?:do|does|did)\s+not\s+meet\b|"
        r"\bnot\s+meet(?:ing)?\s+(?:the\s+)?requirement\b",
    )
    if post_claim_negative.search(sentence):
        return True
    if re.match(r"(?:it|this|that|none|nothing|i)\b", following) and post_claim_negative.search(
        following
    ):
        return True
    return False


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


EDUCATION_LABEL_RE = re.compile(
    r"\b(?:bachelor(?:'s)?|master(?:'s)?|ph\.?\s*d\.?|doctorate|doctoral)\b",
    re.IGNORECASE,
)
EDUCATION_CONTRAST_RE = re.compile(r"\b(?:but|however|although|and)\b", re.IGNORECASE)


def _education_occurrences(candidate_text: str) -> list[tuple[int, str, str]]:
    """Return (level, state, local clause) without treating negated degrees as earned."""

    occurrences: list[tuple[int, str, str]] = []
    for match in EDUCATION_LABEL_RE.finditer(candidate_text):
        level = education_level(match.group(0))
        if level is None:
            continue
        boundaries = ".!?;\n"
        left = max(
            (candidate_text.rfind(mark, 0, match.start()) for mark in boundaries),
            default=-1,
        ) + 1
        right_candidates = [candidate_text.find(mark, match.end()) for mark in boundaries]
        right_candidates = [value for value in right_candidates if value >= 0]
        right = min(right_candidates, default=len(candidate_text))
        clause = candidate_text[left:right].strip()
        relative_start = match.start() - left
        relative_end = match.end() - left
        before = clause[:relative_start]
        after = clause[relative_end:]
        before = EDUCATION_CONTRAST_RE.split(before)[-1]
        after = EDUCATION_CONTRAST_RE.split(after)[0]
        negated = bool(
            re.search(
                r"\b(?:no|without|not|never|don't|do not|doesn't|does not|"
                r"lack(?:s|ing)?|failed to)\b(?:\s+\w+){0,6}\s*$",
                before.casefold(),
            )
            or re.search(
                r"^\s*(?:degree|qualification)?\s*(?:is\s+)?"
                r"(?:not|never|incomplete|unfinished|required)\b",
                after.casefold(),
            )
        )
        in_progress = bool(
            re.search(
                r"\b(?:pursuing|working toward|working on|in progress|currently enrolled|"
                r"expected)\b",
                f"{before} {after}".casefold(),
            )
            or _future_or_conditional_parts(before, after)
        )
        state = "negative" if negated else "in_progress" if in_progress else "positive"
        occurrences.append((level, state, clause))
    if re.search(r"\b(?:no|without)\s+(?:college\s+)?degree\b", candidate_text, re.I):
        occurrences.append((0, "negative", candidate_text))
    return occurrences


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
        terms = r"license|licence|licensed|licensing|certification|certified"
        if _negative_gate_statement(lowered, terms):
            return "not_met"
        if _subject_has_state(
            lowered,
            _LICENSE_SUBJECT_PATTERN,
            _INVALID_GATE_PATTERN,
            include_full_after=True,
        ):
            return "not_met"
        if _future_or_conditional_subject(
            lowered, _LICENSE_SUBJECT_PATTERN
        ):
            return "unknown"
        current_license = _subject_has_current_assertion(
            lowered, _LICENSE_SUBJECT_PATTERN
        )
        historical_license = _subject_has_state(
            lowered, _LICENSE_SUBJECT_PATTERN, _HISTORICAL_GATE_PATTERN
        )
        exact_terms = [
            token
            for token in re.findall(r"[a-z0-9]+", label.casefold())
            if token
            not in {"a", "an", "the", "active", "valid", "current", "professional"}
        ]
        if not exact_terms:
            return "unknown"
        token_patterns = {
            "nursing": r"nurs(?:e|ing)",
            "nurse": r"nurs(?:e|ing)",
            "licence": r"licen[cs](?:e|ed|ing)?",
            "license": r"licen[cs](?:e|ed|ing)?",
        }
        if all(
            re.search(rf"\b{token_patterns.get(token, re.escape(token))}\b", lowered)
            for token in exact_terms
        ):
            if historical_license and not current_license:
                return "unknown"
            return "met"
        return "unknown"

    if requirement_type == "background_check":
        negative_background = re.search(
            r"(?:\b(?:cannot|can't|unable to|will not|won't|not|never|"
            r"failed?|fail(?:ure)? to)\b[^.!?;\n]{0,60}"
            r"\b(?:pass(?:ed)?|clear(?:ed)?|background check|background screening)\b|"
            r"\b(?:background check|background screening)\b[^.!?;\n]{0,60}"
            r"\b(?:not|never|failed?|fail(?:ure)?|incomplete|unfinished)\b)",
            lowered,
        )
        future_background = re.search(
            r"\b(?:can|could|will|would|am able to|able to)\s+"
            r"(?:pass|clear|complete)\s+(?:a\s+|the\s+|one\b)",
            lowered,
        )
        future_background = bool(
            future_background
            or _future_or_conditional_subject(
                lowered,
                r"(?:background\s+(?:check|screening)|(?:clean|no)\s+record)",
            )
        )
        if negative_background and future_background:
            return "unknown"
        if negative_background:
            return "not_met"
        if future_background:
            return "unknown"
        if re.search(
            r"(?:\b(?:passed|cleared|successfully completed|"
            r"completed)\b[^.!?;\n]{0,50}\b(?:a\s+)?(?:background check|"
            r"background screening)\b|\b(?:background check|background screening)\b"
            r"[^.!?;\n]{0,50}\b(?:passed|cleared|completed)\b|"
            r"\b(?:no record|clean record)\b)",
            lowered,
        ):
            return "met"
        return "unknown"

    if requirement_type == "work_authorization":
        if re.search(
            r"\b(?:not authorized|not eligible|not permitted|no right to work|"
            r"no work authorization|without authorization|"
            r"lack(?:s|ing)?\s+(?:any\s+)?(?:work\s+)?authorization|"
            r"(?:do not|don't|does not|doesn't)\s+have\s+(?:any\s+)?"
            r"(?:work\s+)?(?:authorization|permit|visa)|"
            r"(?:do not|don't|does not|doesn't|cannot|can't|unable to)\s+"
            r"(?:hold|possess)\s+(?:a\s+)?(?:valid\s+)?"
            r"(?:work\s+)?(?:authorization|permit|visa)|"
            r"cannot work|unable to work|"
            r"no valid visa|no longer authorized|not currently authorized)\b",
            lowered,
        ):
            return "not_met"
        invalid_authorization = _subject_has_state(
            lowered,
            _AUTHORIZATION_SUBJECT_PATTERN,
            _INVALID_GATE_PATTERN,
            include_full_after=True,
        )
        if invalid_authorization:
            return "not_met"
        pending_authorization = re.search(
            r"\b(?:need|needs|require|requires|will need|waiting for|applied for|"
            r"pending)\b[^.!?;\n]{0,55}\b(?:work\s+)?(?:authorization|permit|visa)\b|"
            r"\b(?:authorization|permit|visa)\b[^.!?;\n]{0,35}"
            r"\b(?:pending|in progress|being processed|not stated|not mentioned)\b",
            lowered,
        )
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
        future_authorization = _future_or_conditional_subject(
            lowered, _AUTHORIZATION_SUBJECT_PATTERN
        )
        current_authorization = _subject_has_current_assertion(
            lowered, _AUTHORIZATION_SUBJECT_PATTERN
        )
        historical_authorization = _subject_has_state(
            lowered, _AUTHORIZATION_SUBJECT_PATTERN, _HISTORICAL_GATE_PATTERN
        )
        if no_sponsorship and (
            contradictory_sponsorship or pending_authorization or future_authorization
        ):
            return "unknown"
        if no_sponsorship:
            return "met"
        if pending_authorization:
            return "unknown"
        if future_authorization:
            return "unknown"
        if historical_authorization and not current_authorization:
            return "unknown"
        if re.search(
            r"\b(?:does not state|not stated|not mentioned|no mention)\b"
            r"[^.!?;\n]{0,45}\b(?:authorization|authorized|permit|visa|right to work)\b",
            lowered,
        ):
            return "unknown"
        if re.search(
            r"\b(?:requires sponsorship|needs sponsorship)\b",
            lowered,
        ):
            return "not_met"
        if re.search(
            r"\b(?:authorized to work|eligible to work|right to work|"
            r"(?:have|has|hold|holds|possess|possesses)\s+(?:a\s+)?"
            r"(?:(?:valid|current|active)\s+)?(?:work\s+)?"
            r"(?:authorization|permit)|valid visa|"
            r"does not require sponsorship|no sponsorship required)\b",
            lowered,
        ):
            return "met"
        return "unknown"

    if requirement_type == "education":
        required_level = requirement.get("education_level") or education_level(
            str(requirement.get("canonical_skill", ""))
        )
        if required_level is None:
            return "unknown"
        required_field = (
            str(requirement.get("education_field"))
            if requirement.get("education_field")
            else None
        )
        occurrences = _education_occurrences(candidate_text)
        positive = [item for item in occurrences if item[1] == "positive"]
        in_progress = [item for item in occurrences if item[1] == "in_progress"]
        negative = [item for item in occurrences if item[1] == "negative"]
        qualifying = [
            item
            for item in positive
            if item[0] >= required_level
            and (
                not required_field
                or _education_field_matches(required_field, item[2])
            )
        ]
        if qualifying:
            return "met"
        if any(item[0] >= required_level for item in in_progress):
            return "unknown"
        if any(item[0] >= required_level for item in negative):
            return "not_met"
        if any(item[0] >= required_level for item in positive):
            return "unknown"
        if positive:
            return "not_met"
        return "unknown"

    if requirement_type == "experience_floor":
        required = int(requirement.get("required_years", 0))
        required_area = requirement.get("experience_area")
        negative_claim_found = False
        for claim in experience_claims(lowered):
            years = int(claim["years"])
            candidate_area = str(claim["area"]) if claim.get("area") else None
            if years >= required and _experience_area_matches(
                str(required_area) if required_area else None,
                candidate_area or str(claim["source_text"]),
            ):
                if _future_or_conditional_experience(lowered, claim):
                    continue
                if _negative_experience_claim(
                    lowered,
                    claim,
                    str(required_area) if required_area else None,
                ):
                    negative_claim_found = True
                    continue
                return "met"
        if negative_claim_found:
            return "not_met"
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
    selected: list[dict[str, Any]] = []
    scoring_items: list[dict[str, Any]] = []
    if direct:
        selected = direct
        scoring_items = [item for item in direct if not _is_claim_only(item)]
        if scoring_items:
            coverage, status, proficiency = 1.0, "direct", 0.85
        else:
            coverage, status, proficiency = 0.35, "claimed", 0.50
    else:
        transferable = []
        for candidate_id in TRANSFER_SKILL_IDS.get(skill_id, set()):
            transferable.extend(
                item
                for item in evidence_by_skill.get(candidate_id, [])
                if not item.get("negated")
            )
        if transferable:
            selected = transferable
            scoring_items = [item for item in transferable if not _is_claim_only(item)]
            if scoring_items:
                coverage, status, proficiency = 0.55, "transferable", 0.65
            else:
                coverage, status, proficiency = 0.30, "transferable_claimed", 0.45
            matching_method = "reviewable_transfer_crosswalk"
        else:
            coverage, status, proficiency = 0.0, "missing", 0.0
    aggregate = _aggregate_evidence(scoring_items or selected)
    evidence = aggregate["strength"]
    recency = aggregate["recency"]
    depth = aggregate["depth"]
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
        "reviewable_evidence_ids": [
            item["evidence_id"] for item in scoring_items
        ],
        "claimed_evidence_ids": [
            item["evidence_id"] for item in selected if _is_claim_only(item)
        ],
        "primary_evidence_id": aggregate["primary_evidence_id"],
        "evidence_aggregation": aggregate["method"],
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
    if status in ("claimed", "direct_weak"):
        gap_type = "proof_gap"
        action_type = "package_proof"
        action = f"Turn your {canonical} claim into one concrete proof point with a task, context, and measurable result."
        artifact = "A quantified resume bullet, work sample, or interview story."
        prompt = f"What did you do with {canonical}, for whom, and what changed because of it?"
        horizon, effort = "before applying", "15–30 minutes"
    elif status in ("transferable", "transferable_claimed"):
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


def _application_positioning_action() -> dict[str, Any]:
    """Give a fully evidenced candidate a useful final application step."""

    return {
        "requirement_id": "application-positioning",
        "canonical_skill": "Role-specific positioning",
        "gap_type": "application_plan",
        "action_type": "tailor_application",
        "importance_level": "must",
        "priority": "medium",
        "time_horizon": "before applying",
        "estimated_effort": "20–40 minutes",
        "action": "Tailor your resume and interview story to this role's scope, showing one recent result and why this role is the right next step.",
        "expected_artifact": "A role-specific resume version plus a concise motivation story.",
        "evidence_prompt": "Which recent result best shows the value you would bring to this role, and why is this scope right for you now?",
        "basis": "All extracted requirements currently have supplied evidence; the remaining preparation need is role-specific framing, not a prediction of hiring outcome.",
    }


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


def _candidate_language_profile(
    candidate_text: str, candidate_language: str | None
) -> dict[str, Any]:
    requested = str(candidate_language or "auto").strip().casefold()
    if requested not in VALID_CANDIDATE_LANGUAGES:
        raise ValueError(
            "candidate_language must be auto, en, es, zh, or other"
        )
    if requested == "auto":
        if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", candidate_text):
            detected = "zh_or_cjk"
        elif re.search(r"[áéíóúüñ¿¡àèìòùâêîôûç]", candidate_text, re.IGNORECASE):
            detected = "likely_non_english_or_mixed"
        elif re.search(
            r"\b(?:experiencia|trabaj(?:e|o|é)|clientes|informes|habilidades|"
            r"erfahrung|kenntnisse|kunden|entwickelt|trabalh(?:ei|o)|"
            r"habilidades|clientes)\b",
            candidate_text,
            re.IGNORECASE,
        ):
            detected = "likely_non_english_or_mixed"
        else:
            detected = "english_or_mixed"
    else:
        detected = requested
    requires_language_review = detected not in {"en", "english_or_mixed"}
    return {
        "requested": requested,
        "detected": detected,
        "rule_based_dictionary": "English seed dictionary plus English O*NET labels",
        "requires_language_review": requires_language_review,
        "note": (
            "Some profile content may not be mapped by the current English dictionary. "
            "Review the extracted evidence, add structured examples, or translate the profile before relying on a complete role picture."
            if requires_language_review
            else "The current rule-based dictionary is designed for English skill labels; confirm any mixed-language terms during review."
        ),
    }


def _review_list(value: object, field_name: str, limit: int = 30) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{field_name} must be a list with at most {limit} items")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name} must contain objects")
    return [dict(item) for item in value]


def _custom_requirement(text: str, requirement_number: int, importance_level: str) -> dict[str, Any]:
    """Create a user-labeled skill when the dictionary has no safe match."""

    return {
        "requirement_id": f"user-req-{requirement_number:03d}",
        "requirement_type": "skill",
        "canonical_skill": text[:160],
        "skill_id": f"user.custom.{requirement_number:03d}",
        "analysis_category_code": "",
        "original_text": text[:160],
        "source_context": text[:200],
        "importance_level": importance_level,
        "importance_weight": IMPORTANCE_WEIGHTS[importance_level],
        "hard_constraint": False,
        "extraction_method": "user_added_custom",
        "extraction_confidence": 1.0,
        "source_taxonomy": "user_supplied",
        "source_skill_id": None,
        "review_status": "user_added",
        "match_mode": "manual",
        "dictionary_version": "user_supplied",
    }


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
        requirement_text = str(raw["text"]).strip()
        if len(requirement_text) > 200:
            raise ValueError("added requirement text must be at most 200 characters")
        importance_level = str(raw.get("importance_level", "must"))
        if importance_level not in VALID_IMPORTANCE_LEVELS:
            raise ValueError("added requirement importance must be must, strongly_preferred, preferred, or inferred")
        extracted = extract_requirements(requirement_text)
        additions = extracted[:3]
        if not additions:
            additions = [_custom_requirement(requirement_text, len(kept) + 1, importance_level)]
        for item in additions:
            if item.get("skill_id") in existing_skills:
                continue
            copied = dict(item)
            copied["requirement_id"] = f"user-req-{len(kept) + 1:03d}"
            copied["extraction_method"] = (
                "user_added_constraint"
                if copied.get("hard_constraint")
                else "user_added"
            )
            copied["extraction_confidence"] = 1.0
            copied["review_status"] = (
                "user_added_constraint"
                if copied.get("hard_constraint")
                else "user_added"
            )
            copied["source_context"] = requirement_text
            copied["importance_level"] = importance_level
            copied["importance_weight"] = IMPORTANCE_WEIGHTS[importance_level]
            kept.append(copied)
            existing_skills.add(str(copied.get("skill_id")))
            changes.append(
                {
                    "action": "added_requirement",
                    "requirement_id": copied["requirement_id"],
                    "skill_id": copied.get("skill_id"),
                    "importance_level": importance_level,
                }
            )

    importance_overrides = review.get("importance_overrides", {})
    if importance_overrides in (None, {}):
        importance_overrides = {}
    if not isinstance(importance_overrides, dict) or len(importance_overrides) > 30:
        raise ValueError("importance_overrides must be an object")
    for requirement_id, importance_level in importance_overrides.items():
        item = next(
            (candidate for candidate in kept if candidate["requirement_id"] == str(requirement_id)),
            None,
        )
        if item is None or item.get("hard_constraint"):
            raise ValueError("importance override must target a soft requirement")
        if importance_level not in VALID_IMPORTANCE_LEVELS:
            raise ValueError("importance must be must, strongly_preferred, preferred, or inferred")
        item["importance_level"] = importance_level
        item["importance_weight"] = IMPORTANCE_WEIGHTS[importance_level]
        item["review_status"] = "user_confirmed"
        changes.append(
            {
                "action": "confirmed_importance",
                "requirement_id": str(requirement_id),
                "importance_level": importance_level,
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
        raw_source_text = row.get("source_text")
        if not isinstance(raw_source_text, str):
            raise ValueError("each added evidence item needs a text source_text")
        source_text = raw_source_text.strip()
        skill_id = str(row.get("skill_id", "")).strip()
        canonical = str(row.get("canonical_skill", "")).strip()
        if not source_text or not skill_id or not canonical:
            raise ValueError("each added evidence item needs skill_id, canonical_skill, and source_text")
        evidence_type = str(row.get("evidence_type", "self_reported"))
        if evidence_type not in VALID_EVIDENCE_TYPES:
            raise ValueError("unsupported evidence type")
        duration = row.get("duration_months")
        recency = row.get("recency_years")
        if duration not in (None, ""):
            duration = _finite_non_negative(duration, "duration_months")
        if recency not in (None, ""):
            recency = _finite_non_negative(recency, "recency_years")
        output.append(
            {
                "evidence_id": f"user-evidence-{index:03d}",
                "skill_id": skill_id,
                "canonical_skill": canonical,
                "analysis_category_code": str(row.get("analysis_category_code", "")),
                "evidence_type": evidence_type,
                "source_text": source_text[:500],
                "result": str(row.get("result", "")).strip()[:500],
                "measurable_result": str(row.get("measurable_result", "")).strip()[:500],
                "duration_months": duration,
                "recency_years": recency,
                "source_name": str(row.get("source_name", "")).strip()[:120],
                "mapping_method": "user_added_evidence",
                "extraction_confidence": 1.0,
                "evidence_status": (
                    "user_confirmed_self_report"
                    if evidence_type in CLAIM_ONLY_EVIDENCE_TYPES
                    else "user_declared_structured_evidence"
                ),
                "verification_status": "user_declared",
                "negated": False,
            }
        )
    return output


def _coverage_components(
    requirements: list[dict[str, Any]],
    active_evidence: list[dict[str, Any]],
    signal_coverage: float,
    claimed_coverage: float,
) -> dict[str, Any]:
    hard = [item for item in requirements if item.get("hard_constraint")]
    known_hard = [item for item in hard if item.get("status") in {"met", "not_met"}]
    soft_count = sum(1 for item in requirements if not item.get("hard_constraint"))
    reviewable_count = sum(
        1
        for item in requirements
        if not item.get("hard_constraint")
        and item.get("status") in {"direct", "direct_weak", "transferable"}
    )
    claimed_count = sum(
        1
        for item in requirements
        if not item.get("hard_constraint")
        and item.get("status") in {"claimed", "transferable_claimed"}
    )
    return {
        # Kept as a null compatibility field. It used to imply that two
        # extracted requirements meant the whole posting was complete.
        "input_completeness_score": None,
        "requirements_identified": len(requirements),
        "minimum_input_threshold": (
            "met" if len(requirements) >= MIN_REQUIREMENTS_FOR_SCORING else "not_met"
        ),
        "soft_requirement_count": soft_count,
        "requirements_with_reviewable_evidence": reviewable_count,
        "requirements_with_claimed_evidence": claimed_count,
        "evidence_coverage_score": round(100 * signal_coverage),
        "claimed_evidence_coverage_score": round(100 * claimed_coverage),
        "eligibility_verification_score": round(
            100 * len(known_hard) / len(hard)
        )
        if hard
        else None,
        "eligibility_status": (
            "no_gate_detected"
            if not hard
            else "unresolved"
            if len(known_hard) < len(hard)
            else "verified"
        ),
        "evidence_item_count": len(active_evidence),
        "requirement_count": len(requirements),
    }


def _redact_pre_review_scores(result: dict[str, Any]) -> None:
    """Keep derived fit numbers out of provisional API responses.

    The browser also hides these values, but the server contract must be safe
    for CLI users and downstream clients that do not share the browser state.
    """

    numeric_fields = {
        "match_score",
        "coverage",
        "evidence_strength",
        "impact_score",
        "importance_weight",
        "extraction_confidence",
    }
    for collection_name in ("requirements", "hard_constraints"):
        for item in result.get(collection_name, []):
            for field in numeric_fields:
                if field in item:
                    item[field] = None
    for item in result.get("gaps", []):
        if "impact_score" in item:
            item["impact_score"] = None
    summary = result.get("summary")
    if isinstance(summary, dict):
        for field in (
            "evidence_coverage_score",
            "claimed_evidence_coverage_score",
            "eligibility_verification_score",
        ):
            if field in summary:
                summary[field] = None
    for item in result.get("evidence", []):
        if "extraction_confidence" in item:
            item["extraction_confidence"] = None
    fingerprint = result.get("role_fingerprint")
    if not isinstance(fingerprint, dict):
        return
    for category in fingerprint.get("categories", []):
        for field in ("required_weight", "evidence_coverage", "gap_score"):
            if field in category:
                category[field] = None
    fingerprint["mismatch_dimensions"] = []
    for bundle in fingerprint.get("skill_bundles", []):
        for field in ("priority_score", "bundle_match_score"):
            if field in bundle:
                bundle[field] = None
        if "is_supported" in bundle:
            bundle["is_supported"] = None


def analyze_fit(
    job_text: str,
    candidate_text: str,
    evidence: list[dict[str, Any]] | None = None,
    review: dict[str, Any] | None = None,
    candidate_language: str | None = "auto",
) -> dict[str, Any]:
    job_text = _require_non_empty_text(job_text, "job_text")
    candidate_text = _require_non_empty_text(candidate_text, "candidate_text")
    language_profile = _candidate_language_profile(candidate_text, candidate_language)
    requirements, review_overrides, review_changes = _apply_review(
        extract_requirements(job_text), review
    )
    candidate_evidence = _normalize_evidence(
        evidence if evidence is not None else evidence_from_text(candidate_text),
        user_supplied=evidence is not None,
    )
    candidate_evidence.extend(_user_added_evidence(review))
    active_evidence = [item for item in candidate_evidence if not item.get("negated")]
    explicit_evidence_supplied = bool(evidence) or any(
        str(item.get("evidence_status", "")).startswith("user_")
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
        if assessment["status"] in {"direct", "direct_weak"}:
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
            if item["status"] in {"direct", "direct_weak"}
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
    claimed_coverage = (
        sum(
            0.30
            if item["status"] in {"claimed", "transferable_claimed"}
            else 0.0
            for item in assessments
            if not item["hard_constraint"]
        )
        / skill_requirement_count
        if skill_requirement_count
        else 0.0
    )
    coverage = _coverage_components(
        assessments, active_evidence, signal_coverage, claimed_coverage
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
    if language_profile["requires_language_review"] and not active_evidence:
        analysis_reasons.append(
            "The profile language may not be fully covered by the current English dictionary; add structured evidence or translate the profile before relying on a score."
        )
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
                "action": "You do not need a resume yet. Answer three short questions: what task did you do, what tool or setting did you use, and what changed or who benefited? Then review the extracted requirements before using any score.",
                "expected_artifact": "Three plain-language answers that describe one concrete candidate example, plus at least two named job requirements.",
                "evidence_prompt": "What task did you do, where did it happen, and what changed because of it?",
                "basis": "The supplied text does not contain enough structured information for a reliable fit score.",
            },
        )
    review_scope = (
        str(review.get("scope", "role_requirements"))
        if review is not None
        else None
    )
    review_applied = review is not None and review.get("applied") is True
    reviewed = review_applied and review_scope == "role_requirements"
    candidate_evidence_reviewed = (
        review_applied and review_scope == "candidate_evidence"
    )
    score_visible = reviewed and not analysis_reasons
    review_status = (
        "user_confirmed"
        if reviewed
        else "candidate_evidence_confirmed"
        if candidate_evidence_reviewed
        else "provisional"
    )
    summary_scores: dict[str, Any] = {
        "evidence_fit_score": soft_fit if score_visible else None,
        "role_fit_score": soft_fit if score_visible else None,
        "application_readiness_score": readiness_score if score_visible else None,
        "capability_signal_score": round(100 * capability_signal)
        if score_visible
        else None,
        "proof_signal_score": round(100 * proof_signal) if score_visible else None,
    }
    if not scoring_available:
        readiness = "insufficient_information"
        decision = "insufficient_information"
        decision_label = (
            "Cannot form a reliable analysis yet. Review the input requirements and add more evidence before relying on a score."
        )
    elif not reviewed:
        readiness = "review_required"
        decision = "review_required"
        decision_label = (
            "Review the extracted requirements, importance, evidence, and eligibility gates before relying on a score."
        )
    next_actions = gaps[:6]
    if scoring_available and not next_actions:
        next_actions = [_application_positioning_action()]
    role_fingerprint = _role_fingerprint(assessments, active_evidence)
    result = {
        "schema_version": "career_fit.v0.5",
        "product": "Career Fit",
        "mode": "single_job",
        "requirements": assessments,
        "evidence": candidate_evidence,
        "hard_constraints": hard_constraints,
        "gaps": gaps,
        "next_actions": next_actions,
        "review": {
            "status": review_status,
            "changes": review_changes,
            "requires_user_confirmation": not reviewed,
            "scope": review_scope or "role_requirements",
            "instructions": "Confirm hard constraints, correct importance, remove false requirements, add missing requirements, and label each evidence item before relying on the report.",
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
            "analysis_status": (
                "insufficient_information"
                if not scoring_available
                else "scored"
                if reviewed
                else "review_required"
            ),
            "analysis_reasons": analysis_reasons,
            "review_status": review_status,
            "review_required": not reviewed,
            "score_visibility": "visible" if score_visible else "hidden",
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
            "candidate_language": language_profile,
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
    if language_profile["requires_language_review"]:
        result["analysis_notes"].append(language_profile["note"])
    if not score_visible:
        _redact_pre_review_scores(result)
    return result


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
    review: dict[str, Any] | None = None,
    candidate_language: str | None = "auto",
) -> dict[str, Any]:
    """Rank a small set of target roles using the same auditable fit engine.

    The result is a preparation priority, not a hiring or income forecast. Roles
    are ordered by application readiness, then evidence fit and evidence coverage.
    A candidate-evidence review can be carried into this comparison, but each
    role's extracted requirements still need their own confirmation before a
    user relies on a role-specific result.
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
    if (
        not isinstance(review, dict)
        or str(review.get("scope", "")) != "candidate_evidence"
        or review.get("applied") is not True
    ):
        raise ValueError(
            "compare_roles requires an applied candidate_evidence review so the candidate evidence state is explicit"
        )
    if any(
        review.get(field)
        for field in (
            "removed_requirement_ids",
            "added_requirements",
            "importance_overrides",
            "constraint_status_overrides",
        )
    ):
        raise ValueError(
            "candidate_evidence review cannot modify role requirements; review each role separately"
        )

    if not isinstance(evidence, list) or not evidence:
        raise ValueError(
            "compare_roles requires user-declared candidate evidence; automatic profile extraction is not enough"
        )
    reviewed_evidence = [
        item
        for item in evidence
        if isinstance(item, dict)
        and str(item.get("evidence_status", ""))
        in {"user_declared_structured_evidence", "user_confirmed_self_report"}
        and str(item.get("verification_status", "")) == "user_declared"
    ]
    if not reviewed_evidence:
        raise ValueError(
            "compare_roles requires user-declared candidate evidence; automatic profile extraction is not enough"
        )

    entries = []
    for index, job_text in enumerate(cleaned, start=1):
        analysis = analyze_fit(
            job_text, candidate_text, reviewed_evidence, review, candidate_language
        )
        summary = analysis["summary"]
        preliminary_review = dict(review)
        preliminary_review["scope"] = "role_requirements"
        preliminary_summary = analyze_fit(
            job_text,
            candidate_text,
            reviewed_evidence,
            preliminary_review,
            candidate_language,
        )["summary"]
        entries.append(
            {
                "role_id": f"role-{index:02d}",
                "role_label": _role_label(job_text, index),
                "role_text": job_text,
                "summary": summary,
                "priority_basis": "Preliminary comparison: " + _priority_basis(preliminary_summary),
                "top_action": analysis["next_actions"][0]
                if analysis["next_actions"]
                else None,
                "top_mismatch": analysis["role_fingerprint"]["mismatch_dimensions"][0]
                if analysis["role_fingerprint"]["mismatch_dimensions"]
                else None,
                "top_bundle": None,
                "analysis": analysis,
                "_sort_summary": preliminary_summary,
            }
        )

    entries.sort(
        key=lambda item: (
            -float(
                item["_sort_summary"].get("application_readiness_score")
                if item["_sort_summary"].get("application_readiness_score") is not None
                else -1
            ),
            -float(
                item["_sort_summary"].get("evidence_fit_score")
                if item["_sort_summary"].get("evidence_fit_score") is not None
                else -1
            ),
            -float(
                item["_sort_summary"].get("evidence_coverage_score")
                if item["_sort_summary"].get("evidence_coverage_score") is not None
                else -1
            ),
            str(item["role_label"]).casefold(),
        )
    )
    for rank, item in enumerate(entries, start=1):
        item["priority_rank"] = rank
        item.pop("_sort_summary", None)
    return {
        "schema_version": "career_fit.compare.v0.3",
        "product": "Career Fit",
        "mode": "role_comparison",
        "role_count": len(entries),
        "roles": entries,
        "interpretation": {
            "priority": "Roles are ordered by preparation readiness, then evidence fit and reviewable evidence coverage. This is not a hiring-probability ranking.",
            "transfer": "Transferable evidence remains visible as a bridge and is never treated as direct equivalence.",
            "missing": "A lower-ranked role may reflect missing proof or an unresolved gate rather than lower underlying ability.",
            "review": "Candidate evidence can be reused across roles after review, but role requirements and hard gates should be confirmed in the selected role view.",
        },
    }
