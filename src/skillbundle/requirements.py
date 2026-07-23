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

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

EDUCATION_LEVELS = {
    "bachelor": 1,
    "master": 2,
    "ph.d.": 3,
    "phd": 3,
    "doctorate": 3,
    "doctoral": 3,
}


def parse_number(value: str) -> int | None:
    value = value.casefold().strip()
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS.get(value)


def education_level(value: str) -> int | None:
    """Return an ordered education level for conservative gate checks."""

    lowered = value.casefold().replace("’", "'")
    if re.search(r"\bph\.?\s*d\.?\b", lowered):
        return 3
    levels = [
        level
        for label, level in EDUCATION_LEVELS.items()
        if re.search(rf"\b{re.escape(label)}\b", lowered)
    ]
    return max(levels) if levels else None


def _clean_constraint_label(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" ,.-:")
    value = re.sub(
        r"^(?:a|an|the|valid|current|active|relevant|professional)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return value


def _license_label(clause: str) -> str:
    match = re.search(
        r"\b([A-Za-z0-9][A-Za-z0-9&./ -]{0,60}?\b(?:license|licence|certification|certificate))\b",
        clause,
        re.IGNORECASE,
    )
    return _clean_constraint_label(match.group(1)) if match else "license"


def _education_field(clause: str, label: re.Match[str]) -> str | None:
    tail = clause[label.end() :]
    match = re.search(
        r"\b(?:in|of)\s+([A-Za-z][A-Za-z0-9&./ -]{1,60}?)(?=\s+(?:is|required|preferred|mandatory|minimum|or\b)|[.,;]|$)",
        tail,
        re.IGNORECASE,
    )
    if not match:
        return None
    field = re.sub(r"\s+", " ", match.group(1)).strip(" ,.-")
    return field or None


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
    """Return the sentence or line containing a mention for local cue matching."""
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
    """Extract auditable skill requirements and high-stakes admission gates.

    The rule layer is intentionally explicit. It captures work authorization,
    education, professional licenses, and experience floors separately so a
    strong soft match cannot hide an unresolved application gate.
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
                "source_taxonomy": item["source_taxonomy"],
                "source_skill_id": item["source_skill_id"],
                "review_status": item["review_status"],
                "match_mode": item["match_mode"],
                "dictionary_version": item["dictionary_version"],
            }
        )

    def add_constraint(
        requirement_type: str,
        canonical: str,
        match: re.Match[str],
        **extra: object,
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
                review_required=True,
                **extra,
            )
        )

    for match in re.finditer(
        r"[^.!?;\n]*\b(?:license|licence|certification|certificate)\b[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        if REQUIRED_MARKERS.search(match.group(0)):
            add_constraint(
                "professional_license",
                _license_label(match.group(0)),
                match,
            )

    for match in re.finditer(
        r"[^.!?;\n]*\b(?:authorized to work|authorization to work|work authorization|"
        r"work permit|eligible to work|right to work|visa sponsorship|requires? sponsorship)\b"
        r"[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        add_constraint("work_authorization", "Work authorization", match)

    for match in re.finditer(
        r"[^.!?;\n]*\b(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|doctorate|doctoral)\b"
        r"[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        if REQUIRED_MARKERS.search(match.group(0)):
            label = re.search(
                r"bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|doctorate|doctoral",
                match.group(0),
                re.I,
            )
            if label:
                add_constraint(
                    "education",
                    label.group(0),
                    match,
                    education_level=education_level(label.group(0)),
                    education_field=_education_field(match.group(0), label),
                )

    for match in re.finditer(
        r"\b(?P<number>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\+?\s+"
        r"years?\s+(?:of\s+)?(?P<area>[^.!?;\n]{0,80}?)\bexperience\b[^.!?;\n]*",
        text,
        re.IGNORECASE,
    ):
        years = parse_number(match.group("number"))
        if years is None:
            continue
        area = re.sub(r"\s+", " ", match.group("area")).strip(" ,.-")
        canonical = f"{years}+ years"
        if area:
            canonical += f" of {area} experience"
        else:
            canonical += " of experience"
        add_constraint(
            "experience_floor",
            canonical,
            match,
            required_years=years,
            experience_area=area or None,
        )
    return requirements
