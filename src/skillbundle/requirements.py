from __future__ import annotations

import re

from .dictionary import extract


IMPORTANCE_WEIGHTS = {
    "must": 1.0,
    "strongly_preferred": 0.7,
    "preferred": 0.4,
    "inferred": 0.2,
}

REQUIRED_MARKERS = re.compile(
    r"\b(must|required|required to|minimum|mandatory|need to|needs to)\b",
    re.IGNORECASE,
)
STRONG_MARKERS = re.compile(
    r"\b(strongly preferred|highly preferred|essential)\b", re.IGNORECASE
)
PREFERRED_MARKERS = re.compile(
    r"\b(preferred|preferably|plus|bonus|nice to have)\b", re.IGNORECASE
)


def _importance(context: str) -> str:
    if REQUIRED_MARKERS.search(context):
        return "must"
    if STRONG_MARKERS.search(context):
        return "strongly_preferred"
    if PREFERRED_MARKERS.search(context):
        return "preferred"
    return "inferred"


def _context(text: str, start: int, end: int, window: int = 90) -> str:
    return text[max(0, start - window) : min(len(text), end + window)]


def _local_clause(text: str, start: int, end: int) -> str:
    """Return the sentence/line containing a mention for local cue matching."""
    boundaries = ".!?;\n"
    left = max((text.rfind(mark, 0, start) for mark in boundaries), default=-1) + 1
    right_candidates = [text.find(mark, end) for mark in boundaries]
    right_candidates = [value for value in right_candidates if value >= 0]
    right = min(right_candidates, default=len(text))
    return text[left:right].strip()


def _constraint(
    requirement_id: str,
    requirement_type: str,
    canonical: str,
    source_text: str,
    **extra: object,
) -> dict[str, object]:
    return {
        "requirement_id": requirement_id,
        "requirement_type": requirement_type,
        "canonical_skill": canonical,
        "original_text": source_text,
        "importance_level": "must",
        "importance_weight": IMPORTANCE_WEIGHTS["must"],
        "hard_constraint": True,
        "extraction_method": "constraint_rule",
        **extra,
    }


def extract_requirements(text: str) -> list[dict[str, object]]:
    """Extract transparent v0.1 job requirements from a job description.

    Skill requirements use the existing dictionary baseline. A small rule layer
    captures high-stakes admission constraints separately so a strong soft score
    cannot hide a missing license, authorization, degree, or experience floor.
    """
    requirements: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(extract(text), start=1):
        context = _context(text, int(item["start"]), int(item["end"]))
        level = _importance(
            _local_clause(text, int(item["start"]), int(item["end"])) or context
        )
        key = ("skill", str(item["skill_id"]))
        if key in seen:
            continue
        seen.add(key)
        requirements.append(
            {
                "requirement_id": f"req-{index:03d}",
                "requirement_type": "skill",
                "canonical_skill": item["canonical"],
                "skill_id": item["skill_id"],
                "analysis_category_code": item["analysis_category_code"],
                "original_text": item["text"],
                "source_context": context,
                "importance_level": level,
                "importance_weight": IMPORTANCE_WEIGHTS[level],
                "hard_constraint": False,
                "extraction_method": item["mapping_method"],
                "extraction_confidence": item["confidence"],
            }
        )

    def add_constraint(
        requirement_type: str,
        canonical: str,
        match: re.Match[str],
    ) -> None:
        key = (requirement_type, canonical.casefold())
        if key in seen:
            return
        seen.add(key)
        requirements.append(
            _constraint(
                f"constraint-{len(requirements) + 1:03d}",
                requirement_type,
                canonical,
                match.group(0).strip(),
                source_context=_context(text, match.start(), match.end()),
            )
        )

    for match in re.finditer(
        r"[^.!?;\n]*\b(?:license|licence|certification|certificate)\b[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        if REQUIRED_MARKERS.search(match.group(0)):
            label = re.search(
                r"license|licence|certification|certificate", match.group(0), re.I
            )
            add_constraint("professional_license", label.group(0), match)

    for match in re.finditer(
        r"[^.!?;\n]*\b(?:authorized to work|work authorization|work permit|visa sponsorship|eligible to work)\b[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        add_constraint("work_authorization", "Work authorization", match)

    for match in re.finditer(
        r"[^.!?;\n]*\b(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|doctorate)\b"
        r"[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        if REQUIRED_MARKERS.search(match.group(0)):
            label = re.search(
                r"bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|doctorate",
                match.group(0),
                re.I,
            )
            add_constraint("education", label.group(0), match)

    for match in re.finditer(
        r"\b(\d+)\+?\s+years?\s+(?:of\s+)?experience\b[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        add_constraint(
            "experience_floor", f"{match.group(1)}+ years of experience", match
        )
    return requirements
