from __future__ import annotations

from difflib import SequenceMatcher

from .dictionary import DictionaryEntry, load_dictionary, normalize_text


def normalize_label(label: str, threshold: float = 0.92) -> dict[str, object]:
    """Resolve a label to the public seed dictionary or return an explicit NIL."""
    version, entries = load_dictionary()
    query = normalize_text(label)
    exact = []
    for entry in entries:
        labels = (entry.canonical, *entry.aliases)
        if any(normalize_text(candidate) == query for candidate in labels):
            exact.append(entry)
    if exact:
        entry = exact[0]
        return {
            "label": label,
            "skill_id": entry.skill_id,
            "canonical": entry.canonical,
            "analysis_category_code": entry.category_code,
            "mapping_method": "dictionary_exact",
            "confidence": 0.99,
            "dictionary_version": version,
            "nil": False,
        }
    best: tuple[float, DictionaryEntry] | None = None
    for entry in entries:
        for candidate in (entry.canonical, *entry.aliases):
            similarity = SequenceMatcher(None, query, normalize_text(candidate)).ratio()
            if best is None or similarity > best[0]:
                best = (similarity, entry)
    if best and best[0] >= threshold:
        similarity, entry = best
        return {
            "label": label,
            "skill_id": entry.skill_id,
            "canonical": entry.canonical,
            "analysis_category_code": entry.category_code,
            "mapping_method": "dictionary_fuzzy_candidate",
            "confidence": round(similarity, 4),
            "dictionary_version": version,
            "nil": False,
            "requires_review": True,
        }
    return {
        "label": label,
        "skill_id": "NIL",
        "canonical": None,
        "analysis_category_code": None,
        "mapping_method": "unresolved_nil",
        "confidence": 0.0,
        "dictionary_version": version,
        "nil": True,
        "requires_review": True,
    }
