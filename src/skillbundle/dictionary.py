from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DictionaryEntry:
    skill_id: str
    canonical: str
    aliases: tuple[str, ...]
    category_code: str
    source_taxonomy: str = "career_fit_seed_en"
    mapping_method: str = "dictionary_exact"
    confidence: float = 0.99
    review_status: str = "baseline_unreviewed"
    match_mode: str = "exact"
    context_terms: tuple[str, ...] = ()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def load_dictionary(path: Path | None = None) -> tuple[str, list[DictionaryEntry]]:
    path = path or ROOT / "config" / "seed_dictionary_en.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = [_entry_from_json(item) for item in payload["entries"]]
    version = str(payload["version"])
    default_path = ROOT / "config" / "seed_dictionary_en.json"
    if path.resolve() == default_path.resolve():
        enrichment_path = ROOT / "config" / "onet_enrichment_en.json"
        if enrichment_path.exists():
            enrichment = json.loads(enrichment_path.read_text(encoding="utf-8"))
            version = f"{version}+{enrichment.get('version', 'enrichment')}"
            existing_terms = {
                normalize_text(term)
                for entry in entries
                for term in (entry.canonical, *entry.aliases)
            }
            for item in enrichment.get("entries", []):
                terms = (item["canonical"], *item.get("aliases", []))
                if any(normalize_text(term) in existing_terms for term in terms):
                    continue
                entries.append(_entry_from_json(item))
                existing_terms.update(normalize_text(term) for term in terms)
    return version, entries


def _entry_from_json(item: dict[str, object]) -> DictionaryEntry:
    return DictionaryEntry(
        str(item["skill_id"]),
        str(item["canonical"]),
        tuple(str(alias) for alias in item.get("aliases", [])),
        str(item["category_code"]),
        str(item.get("source_taxonomy", "career_fit_seed_en")),
        str(item.get("mapping_method", "dictionary_exact")),
        float(item.get("confidence", 0.99)),
        str(item.get("review_status", "baseline_unreviewed")),
        str(item.get("match_mode", "exact")),
        tuple(str(term) for term in item.get("context_terms", [])),
    )


def _pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.strip())
    return re.compile(rf"(?<![\w]){escaped}(?![\w])", re.IGNORECASE)


def _has_context(text: str, start: int, end: int, terms: tuple[str, ...]) -> bool:
    window = normalize_text(text[max(0, start - 90) : min(len(text), end + 90)])
    return any(_pattern(term).search(window) is not None for term in terms)


def extract(text: str, dictionary_path: Path | None = None) -> list[dict[str, object]]:
    version, entries = load_dictionary(dictionary_path)
    candidates = []
    for entry in entries:
        aliases = sorted(set((entry.canonical, *entry.aliases)), key=len, reverse=True)
        for alias in aliases:
            for match in _pattern(alias).finditer(text):
                if entry.match_mode == "context_required" and not _has_context(
                    text, match.start(), match.end(), entry.context_terms
                ):
                    continue
                candidates.append(
                    {
                        "text": match.group(0),
                        "start": match.start(),
                        "end": match.end(),
                        "skill_id": entry.skill_id,
                        "canonical": entry.canonical,
                        "source_taxonomy": entry.source_taxonomy,
                        "source_skill_id": entry.skill_id,
                        "analysis_category_code": entry.category_code,
                        "mapping_method": entry.mapping_method,
                        "confidence": entry.confidence,
                        "review_status": entry.review_status,
                        "match_mode": entry.match_mode,
                        "dictionary_version": version,
                    }
                )
    selected: list[dict[str, object]] = []
    for candidate in sorted(
        candidates, key=lambda item: (-(item["end"] - item["start"]), item["start"])
    ):
        if any(
            not (candidate["end"] <= item["start"] or candidate["start"] >= item["end"])
            for item in selected
        ):
            continue
        selected.append(candidate)
    return sorted(selected, key=lambda item: (item["start"], item["end"]))
