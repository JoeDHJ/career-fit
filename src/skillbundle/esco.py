from __future__ import annotations

import csv
from pathlib import Path


def load_esco_skills(path: Path) -> list[dict[str, object]]:
    """Load an ESCO skills CSV exported from the official API/download flow."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        rows = csv.DictReader(handle, dialect=dialect)
        output = []
        for row in rows:
            concept_id = (
                row.get("conceptUri")
                or row.get("concept uri")
                or row.get("URI")
                or row.get("uri")
                or ""
            )
            preferred = (
                row.get("preferredLabel")
                or row.get("preferred label")
                or row.get("preferredLabel_en")
                or ""
            )
            if not concept_id and not preferred:
                continue
            output.append(
                {
                    "source_taxonomy": "ESCO",
                    "taxonomy_version": "1.2.1",
                    "source_skill_id": concept_id,
                    "preferred_label": preferred,
                    "alt_labels": row.get("altLabels")
                    or row.get("alternative labels")
                    or "",
                    "mapping_status": "unmapped_until_review",
                }
            )
    return output
