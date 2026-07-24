from __future__ import annotations

import itertools
import json
from pathlib import Path

from .resources import read_resource_text


ROOT = Path(__file__).resolve().parents[2]


def load_taxonomy(path: Path | None = None) -> dict[str, object]:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    source_path = ROOT / "config" / "taxonomy_10_ai.json"
    text = (
        source_path.read_text(encoding="utf-8")
        if source_path.exists()
        else read_resource_text("taxonomy_10_ai.json")
    )
    return json.loads(text)


def category_map(path: Path | None = None) -> dict[str, dict[str, object]]:
    return {item["code"]: item for item in load_taxonomy(path)["categories"]}


def pair_codes(path: Path | None = None) -> list[str]:
    codes = [item["code"] for item in load_taxonomy(path)["categories"]]
    return ["__".join(pair) for pair in itertools.combinations(codes, 2)]
