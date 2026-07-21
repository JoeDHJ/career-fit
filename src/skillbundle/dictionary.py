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


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def load_dictionary(path: Path | None = None) -> tuple[str, list[DictionaryEntry]]:
    path = path or ROOT / "config" / "seed_dictionary_en.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = [
        DictionaryEntry(
            item["skill_id"],
            item["canonical"],
            tuple(item["aliases"]),
            item["category_code"],
        )
        for item in payload["entries"]
    ]
    return payload["version"], entries


def _pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias.strip())
    return re.compile(rf"(?<![\w]){escaped}(?![\w])", re.IGNORECASE)


def extract(text: str, dictionary_path: Path | None = None) -> list[dict[str, object]]:
    version, entries = load_dictionary(dictionary_path)
    candidates = []
    for entry in entries:
        aliases = sorted(set((entry.canonical, *entry.aliases)), key=len, reverse=True)
        for alias in aliases:
            for match in _pattern(alias).finditer(text):
                candidates.append(
                    {
                        "text": match.group(0),
                        "start": match.start(),
                        "end": match.end(),
                        "skill_id": entry.skill_id,
                        "canonical": entry.canonical,
                        "source_taxonomy": "seed_dictionary_en",
                        "source_skill_id": entry.skill_id,
                        "analysis_category_code": entry.category_code,
                        "mapping_method": "dictionary_exact",
                        "confidence": 0.99,
                        "review_status": "baseline_unreviewed",
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
