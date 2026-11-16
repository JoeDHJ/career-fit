"""Refresh a small attributed public snapshot; core demo never requires network."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from html.parser import HTMLParser
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ONET = "https://www.onetcenter.org/dl_files/database/db_31_0_csv/"
BLS = "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm"
CODES = {
    "13-1071": "Human resources specialists",
    "15-2031": "Operations research analysts",
    "15-2051": "Data scientists",
}


def fetch(url: str) -> bytes:
    with urlopen(
        Request(
            url, headers={"User-Agent": "CareerFit public data case (dui@szu.edu.cn)"}
        ),
        timeout=60,
    ) as response:
        return response.read(12_000_000)


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in {"td", "th"}:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row:
            self.rows.append(self.row)


def main():
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sources = []
    skills = []
    for filename in ("essential_skills.csv", "transferable_skills.csv"):
        url = ONET + filename
        raw = fetch(url)
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        for row in rows:
            code = row["O*NET-SOC Code"]
            if code in {c + ".00" for c in CODES} and row["Scale ID"] == "IM":
                skills.append(
                    {
                        "occupation_id": code,
                        "skill_id": row["Element ID"],
                        "native_skill_id": row["Element ID"],
                        "skill_taxonomy": "O*NET Content Model",
                        "skill_taxonomy_version": "31.0",
                        "label": row["Element Name"],
                        "importance": float(row["Data Value"]),
                        "scale": "IM (1–5)",
                        "source_id": "onet31-" + filename.removesuffix(".csv"),
                        "observation_date": row.get("Date"),
                        "not_relevant": row.get("Not Relevant"),
                        "recommend_suppress": row.get("Recommend Suppress"),
                    }
                )
        sources.append(
            {
                "source_id": "onet31-" + filename.removesuffix(".csv"),
                "source_url": url,
                "retrieved_at": stamp,
                "source_vintage": "O*NET 31.0 (August 2026)",
                "geography": "US",
                "unit_of_observation": "O*NET-SOC 2019 occupation × skill importance",
                "period": "occupation-specific survey dates",
                "currency": None,
                "price_year": None,
                "schema_version": "portfolio.v1",
                "status": "estimated",
                "rows_in_source": len(rows),
                "download_bytes": len(raw),
                "license": "CC BY 4.0; U.S. Department of Labor/Employment and Training Administration; National Center for O*NET Development",
            }
        )
    raw = fetch(BLS)
    parser = Table()
    html = raw.decode("utf-8")
    if "2025–35" not in html and "2025&ndash;35" not in html and "2025-35" not in html:
        # Do not silently mix vintages when the upstream page changes.
        raise ValueError(
            "Expected BLS 2025–35 vintage; review the source before adapting"
        )
    parser.feed(html)
    occupations = []
    for row in parser.rows:
        if len(row) < 12 or row[1] not in CODES:
            continue

        def number(i):
            return float(row[i].replace(",", ""))

        occupations.append(
            {
                "occupation_id": row[1],
                "native_id": row[1],
                "taxonomy": "SOC",
                "taxonomy_vintage": "2018",
                "title": row[0],
                "geography": "US",
                "source_id": "bls-ep-2025-2035",
                "employment": round(number(3) * 1000),
                "projected_employment": round(number(4) * 1000),
                "projected_change_pct": number(8),
                "annual_openings": round(number(10) * 1000),
                "median_annual_wage": number(11),
                "currency": "USD",
                "price_year": 2025,
                "period": "2025–2035",
                "employment_status": "estimated",
                "projection_status": "estimated",
                "wage_status": "estimated",
            }
        )
    if len(occupations) != len(CODES) or len(skills) < 90:
        raise ValueError("Public source coverage changed; inspect source schemas")
    sources.append(
        {
            "source_id": "bls-ep-2025-2035",
            "source_url": BLS,
            "retrieved_at": stamp,
            "source_vintage": "Table 1.2, 2025–2035 (August 2026)",
            "geography": "US",
            "unit_of_observation": "SOC 2018 occupation",
            "period": "2025–2035",
            "currency": "USD",
            "price_year": 2025,
            "schema_version": "portfolio.v1",
            "status": "estimated",
            "download_bytes": len(raw),
            "rows_in_snapshot": len(occupations),
            "license": "U.S. government public data",
        }
    )
    payload = {
        "schema_version": "portfolio.v1",
        "snapshot_id": "career-fit-public-2026-11-16",
        "sources": sources,
        "occupations": occupations,
        "skills": skills,
        "crosswalk": {
            "type": "exact parent SOC for these three .00 occupations",
            "from": "O*NET-SOC 2019, database 31.0",
            "to": "SOC 2018",
            "weight": 1.0,
            "coverage": "3/3 selected occupations; not a general crosswalk",
            "aggregation": "No many-to-many aggregation",
        },
    }
    target = ROOT / "src/skillbundle/resources/public_context.json"
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "path": str(target),
                "occupations": len(occupations),
                "skills": len(skills),
                "sources": len(sources),
            }
        )
    )


if __name__ == "__main__":
    main()
