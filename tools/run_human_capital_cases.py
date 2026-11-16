"""Reproduce all public-data human-capital case artifacts without network."""

from __future__ import annotations

import json
from pathlib import Path

from skillbundle.capital_reports import capital_markdown
from skillbundle.investment import plan_investment
from skillbundle.resources import read_resource_text
from skillbundle.workforce import allocate_workforce

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / "examples/human_capital"
    target.mkdir(parents=True, exist_ok=True)
    for name, function in (
        ("investment", plan_investment),
        ("workforce", allocate_workforce),
    ):
        payload = json.loads(read_resource_text(name + "_demo.json"))
        payload["as_of"] = "2026-11-16"
        result = function(payload)
        (target / (name + "_input.json")).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (target / (name + "_result.json")).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (target / (name + "_brief.md")).write_text(
            capital_markdown(result), encoding="utf-8"
        )
        print(name, "->", target)
    personal = json.loads(read_resource_text("investment_demo.json"))
    workforce = json.loads(read_resource_text("workforce_demo.json"))
    personal_sensitivity = []
    for hours in (40, 68, 90, 110):
        for budget in (150, 320, 600):
            data = {**personal, "as_of": "2026-11-16", "hours": hours, "budget": budget}
            result = plan_investment(data)
            plan = result["best_plan"]
            personal_sensitivity.append(
                {
                    "available_hours": hours,
                    "cash_budget": budget,
                    "course_ids": plan["course_ids"],
                    "cash_cost": plan["cash_cost"],
                    "economic_cost": plan["economic_cost"],
                    "target_weight": plan["target_weight_covered"],
                }
            )
    organization_sensitivity = []
    for hours in (0, 24, 56):
        for budget in (1400, 10000, 30000):
            data = {
                **workforce,
                "as_of": "2026-11-16",
                "hours_budget": hours,
                "budget": budget,
            }
            result = allocate_workforce(data)
            organization_sensitivity.append(
                {
                    "released_hours": hours,
                    "cash_budget": budget,
                    "hybrid": result["scenarios"]["hybrid"],
                    "no_training": result["scenarios"]["no_training"],
                    "comparison": result["comparison"],
                }
            )
    (target / "sensitivity.json").write_text(
        json.dumps(
            {"personal": personal_sensitivity, "workforce": organization_sensitivity},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
