from __future__ import annotations

import json
from pathlib import Path

from skillbundle.research import SCHEMA, QUERIES, build_research

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = build_research(str(ROOT / "data/processed/career_intelligence.sqlite"))
    (ROOT / "src/skillbundle/resources/research_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    folder = ROOT / "examples/evidence_research"
    folder.mkdir(exist_ok=True)
    (folder / "queries.sql").write_text(
        SCHEMA
        + "\n"
        + "\n\n".join(
            "-- " + name + "\n" + query + ";" for name, query in QUERIES.items()
        ),
        encoding="utf-8",
    )
    lines = [
        "# Official-role and learning-resource evidence",
        "",
        result["sampling"],
        "",
        "The requirements are analyst-coded paraphrases, not independent human labels. A non-mention is unobserved, not evidence of absence. Qualification notes remain separate from skill counts.",
        "",
        "| Coded requirement | Descriptions mentioning it / 8 | Explicitly required | Preferred |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in result["results"]["skill_mentions"]:
        lines.append(
            f"| {row['label']} | {row['descriptions']} | {row['explicitly_required']} | {row['preferred']} |"
        )
    lines += ["", "## Source coverage", ""] + [
        f"- {r['geography']}, {r['access_state']}: {r['descriptions']} descriptions."
        for r in result["results"]["sample_coverage"]
    ]
    lines += [
        "",
        "## Learning resources",
        "",
        "| Resource | Provider duration (hours) | Planned total (hours) | Content fee |",
        "| --- | ---: | ---: | ---: |",
    ]
    for r in result["learning_resources"]:
        lines.append(
            f"| [{r['title']}]({r['source']['source_url']}) | {r['provider_hours'] if r['provider_hours'] is not None else 'Not observed'} | {r['hours']} | 0 (content only) |"
        )
    lines += [
        "",
        "Practice hours and missing learning durations are scenario assumptions. Software/exams/equipment are excluded from content fees. Provider Python-course software issues are retained in the resource note.",
        "",
        "## Official employer sources",
        "",
    ] + [
        f"- [{s['source_id']}]({s['source_url']}): {s['source_vintage']}; {s['access_state']}."
        for s in result["sources"]
    ]
    (ROOT / "docs/role-resource-research.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("SQL research complete:", result["results"]["skill_mentions"])


if __name__ == "__main__":
    main()
