from __future__ import annotations

import argparse
import csv
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


ESSENTIAL_CATEGORIES = {
    "Reading Comprehension": "cognitive_skill",
    "Active Listening": "social_skill",
    "Writing": "writing_skill",
    "Speaking": "social_skill",
    "Mathematics": "cognitive_skill",
    "Science": "cognitive_skill",
    "Critical Thinking": "cognitive_skill",
    "Active Learning": "character_skill",
    "Learning Strategies": "character_skill",
    "Monitoring": "cognitive_skill",
}
TRANSFERABLE_CATEGORIES = {
    "Social Perceptiveness": "social_skill",
    "Coordination": "social_skill",
    "Persuasion": "social_skill",
    "Negotiation": "social_skill",
    "Instructing": "people_management_skill",
    "Service Orientation": "customer_project_management_skill",
    "Complex Problem Solving": "cognitive_skill",
    "Operations Analysis": "cognitive_skill",
    "Technology Design": "cognitive_skill",
    "Equipment Selection": "cognitive_skill",
    "Installation": "general_computer_skill",
    "Programming": "cognitive_skill",
    "Operations Monitoring": "cognitive_skill",
    "Operation and Control": "cognitive_skill",
    "Equipment Maintenance": "cognitive_skill",
    "Troubleshooting": "cognitive_skill",
    "Repairing": "cognitive_skill",
    "Quality Control Analysis": "cognitive_skill",
    "Judgment and Decision Making": "cognitive_skill",
    "Systems Analysis": "cognitive_skill",
    "Systems Evaluation": "cognitive_skill",
    "Time Management": "customer_project_management_skill",
    "Management of Financial Resources": "financial_skill",
    "Management of Material Resources": "customer_project_management_skill",
    "Management of Personnel Resources": "people_management_skill",
}
KNOWLEDGE_CATEGORIES = {
    "Administration and Management": "customer_project_management_skill",
    "Administrative": "customer_project_management_skill",
    "Economics and Accounting": "financial_skill",
    "Sales and Marketing": "customer_project_management_skill",
    "Customer and Personal Service": "customer_project_management_skill",
    "Personnel and Human Resources": "people_management_skill",
    "Production and Processing": "cognitive_skill",
    "Food Production": "cognitive_skill",
    "Computers and Electronics": "general_computer_skill",
    "Engineering and Technology": "cognitive_skill",
    "Design": "cognitive_skill",
    "Building and Construction": "cognitive_skill",
    "Mechanical": "cognitive_skill",
    "Mathematics": "cognitive_skill",
    "Physics": "cognitive_skill",
    "Chemistry": "cognitive_skill",
    "Biology": "cognitive_skill",
    "Psychology": "cognitive_skill",
    "Sociology and Anthropology": "cognitive_skill",
    "Geography": "cognitive_skill",
    "Medicine and Dentistry": "cognitive_skill",
    "Therapy and Counseling": "social_skill",
    "Education and Training": "people_management_skill",
    "English Language": "writing_skill",
    "Foreign Language": "social_skill",
    "Fine Arts": "cognitive_skill",
    "History and Archeology": "cognitive_skill",
    "Philosophy and Theology": "cognitive_skill",
    "Public Safety and Security": "character_skill",
    "Law and Government": "cognitive_skill",
    "Telecommunications": "specific_software_skill",
    "Communications and Media": "writing_skill",
    "Transportation": "cognitive_skill",
}
ALIAS_RULES = {
    "Microsoft Excel": ["Excel"],
    "Microsoft Word": ["Word"],
    "Microsoft PowerPoint": ["PowerPoint"],
    "Microsoft Outlook": ["Outlook"],
    "Microsoft Access": ["Access"],
    "Microsoft Project": ["Project"],
    "Microsoft SharePoint": ["SharePoint"],
    "Structured query language SQL": ["SQL"],
    "Microsoft SQL Server": ["SQL Server"],
    "Oracle Java": ["Java"],
    "The MathWorks MATLAB": ["MATLAB"],
    "Amazon Web Services AWS software": ["AWS", "Amazon Web Services"],
    "Microsoft Azure software": ["Azure", "Microsoft Azure"],
    "Google Analytics": ["Google Analytics"],
    "Atlassian JIRA": ["Jira"],
    "ESRI ArcGIS software": ["ArcGIS"],
    "IBM SPSS Statistics": ["SPSS"],
    "Extensible markup language XML": ["XML"],
    "Hypertext markup language HTML": ["HTML"],
}
AMBIGUOUS_ALIASES = {
    "access",
    "excel",
    "google analytics",
    "outlook",
    "powerpoint",
    "project",
    "word",
}
CONTEXT_REQUIRED_SOFTWARE = {
    "chef": ["software", "devops", "infrastructure", "configuration", "cookbook"],
    "facebook": ["social media", "advertising", "ads", "campaign", "marketing"],
    "go": ["golang", "programming", "backend", "language", "developer", "services"],
    "google": ["cloud", "analytics", "ads", "workspace", "sheets", "platform"],
    "react": ["javascript", "frontend", "front-end", "framework", "component", "web"],
    "slack": ["workspace", "messaging", "channel", "collaboration", "software"],
    "swift": ["ios", "apple", "xcode", "mobile", "programming", "language", "app"],
    "tiktok": ["social media", "advertising", "ads", "campaign", "marketing"],
    "zoom": ["meeting", "video", "webinar", "conference", "software"],
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _rows_from_zip(path: Path, filename: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        match = next(
            name
            for name in archive.namelist()
            if name.casefold().endswith(filename.casefold())
        )
        with archive.open(match) as handle:
            return list(
                csv.DictReader(
                    io.TextIOWrapper(handle, encoding="utf-8-sig"), delimiter="\t"
                )
            )


def _rows_from_dir(root: Path, filename: str) -> list[dict[str, str]]:
    path = next(root.rglob(filename))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _source_rows(source: Path, filename: str) -> list[dict[str, str]]:
    return (
        _rows_from_zip(source, filename)
        if source.suffix.casefold() == ".zip"
        else _rows_from_dir(source, filename)
    )


def _element_entries(
    rows: list[dict[str, str]], categories: dict[str, str], filename: str
) -> list[dict[str, object]]:
    entries = {}
    for row in rows:
        name = row.get("Element Name", "").strip()
        category = categories.get(name)
        if not name or not category or name in entries:
            continue
        entries[name] = {
            "skill_id": f"onet.{_slug(filename.removesuffix('.txt'))}.{_slug(name)}",
            "canonical": name,
            "aliases": [],
            "category_code": category,
            "source_taxonomy": "onet_30_3",
            "source_file": filename,
            "source_element_id": row.get("Element ID", "").strip(),
            "mapping_method": "onet_element_exact",
            "confidence": 0.95,
            "review_status": "onet_exact_label_baseline",
        }
    return list(entries.values())


def _software_entries(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    examples = {}
    for row in rows:
        example = row.get("Workplace Example", "").strip()
        if (
            len(example) < 2
            or row.get("Hot Technology") != "Y"
            and row.get("In Demand") != "Y"
        ):
            continue
        examples.setdefault(example, []).append(row)
    entries = []
    for example, matches in sorted(
        examples.items(), key=lambda item: item[0].casefold()
    ):
        source = Counter(
            (row.get("Element ID", "").strip(), row.get("Element Name", "").strip())
            for row in matches
        ).most_common(1)[0][0]
        entries.append(
            {
                "skill_id": f"onet.software.{_slug(example)}",
                "canonical": example,
                "aliases": [
                    alias
                    for alias in ALIAS_RULES.get(example, [])
                    if alias.casefold() != example.casefold()
                    and alias.casefold() not in AMBIGUOUS_ALIASES
                ],
                "category_code": "specific_software_skill",
                "source_taxonomy": "onet_30_3",
                "source_file": "Software Skills.txt",
                "source_element_id": source[0],
                "mapping_method": "onet_hot_or_in_demand_exact",
                "confidence": 0.95,
                "review_status": "onet_exact_label_baseline",
                "match_mode": (
                    "context_required"
                    if example.casefold() in CONTEXT_REQUIRED_SOFTWARE
                    else "exact"
                ),
                "context_terms": CONTEXT_REQUIRED_SOFTWARE.get(example.casefold(), []),
            }
        )
    return entries


def build(source: Path) -> dict[str, object]:
    entries = []
    entries.extend(
        _element_entries(
            _source_rows(source, "Essential Skills.txt"),
            ESSENTIAL_CATEGORIES,
            "Essential Skills.txt",
        )
    )
    entries.extend(
        _element_entries(
            _source_rows(source, "Transferable Skills.txt"),
            TRANSFERABLE_CATEGORIES,
            "Transferable Skills.txt",
        )
    )
    entries.extend(
        _element_entries(
            _source_rows(source, "Knowledge.txt"), KNOWLEDGE_CATEGORIES, "Knowledge.txt"
        )
    )
    entries.extend(_software_entries(_source_rows(source, "Software Skills.txt")))
    unique = {}
    for entry in entries:
        unique.setdefault(entry["canonical"].casefold(), entry)
    return {
        "enrichment_id": "career_fit_onet_enrichment_en",
        "version": "onet-30.3-derived-v2",
        "source": {
            "provider": "O*NET Resource Center / USDOL ETA",
            "version": "30.3",
            "license": "CC BY 4.0",
            "selection": "All mapped Essential, Transferable, and Knowledge elements plus Software Skills marked Hot Technology or In Demand.",
        },
        "category_standard": "deming_kahn_10_ai.v1.0.0",
        "entries": sorted(
            unique.values(), key=lambda item: item["canonical"].casefold()
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onet-source", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("config/onet_enrichment_en.json")
    )
    args = parser.parse_args()
    payload = build(args.onet_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"output": str(args.output), "entries": len(payload["entries"])},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
