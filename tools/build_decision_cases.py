"""Build business/practice cases with observed sources and explicit scenario inputs."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from skillbundle.capital_reports import capital_markdown
from skillbundle.career import analyze_fit
from skillbundle.investment import plan_investment
from skillbundle.market import public_snapshot
from skillbundle.resources import read_resource_text
from skillbundle.workforce import allocate_workforce

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src/skillbundle/resources"


def save(path, payload):
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    jobs = json.loads(read_resource_text("role_evidence.json"))
    resources = json.loads(read_resource_text("learning_resources.json"))["resources"]
    # Historical learning case: this advert is closed, not a live application recommendation.
    source = next(s for s in jobs["sources"] if s["source_id"] == "nhs-7087716")
    analyst = {
        "input_status": "Fictional career-switching analyst; archived actual NHS role and official learning resources; practice costs/effects are scenarios",
        "as_of": "2026-11-16",
        "currency": "USD",
        "price_year": 2026,
        "budget": 100,
        "hours": 64,
        "weekly_hours": 5,
        "hourly_value": 20,
        "preparation_hours": 6,
        "occupation_id": "",
        "geography": "UK",
        "jd_source": source,
        "analysis_input": {
            "job_text": "Historical learning case, not an open application: Data Analyst, People & Culture Directorate. Advanced Microsoft Excel is required. Responsibilities include data analysis, data quality, comprehensive reports and stakeholder communication supporting workforce information and planning. SQL or reporting-tool experience is mentioned. Experience in an information analyst and reporting environment is required. Review the full employer criteria before any future application.",
            "candidate_text": "FICTIONAL learner B, constructed for the case. Built Python research projects and public employment-data visualizations, wrote an academic research report and volunteered to maintain a community group's spreadsheets. Has not used production SQL or worked directly with HR data. Wants to translate research into workforce reporting.",
            "review": {
                "scope": "role_requirements",
                "applied": True,
                "added_requirements": [
                    {"text": "Data quality", "importance_level": "must"}
                ],
            },
            "evidence": [
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "analysis_category_code": "specific_software_skill",
                    "evidence_type": "research_project",
                    "source_text": "Fictional public-data Python notebook with reproducible tables",
                    "result": "Runnable notebook and data checks",
                    "duration_months": 6,
                    "recency_years": 0,
                },
                {
                    "skill_id": "skill.data_visualization",
                    "canonical_skill": "Data visualization",
                    "analysis_category_code": "cognitive_skill",
                    "evidence_type": "portfolio",
                    "source_text": "Fictional employment charts with source notes",
                    "result": "Three charts with denominators",
                    "duration_months": 3,
                    "recency_years": 0,
                },
            ],
        },
        "confirmed_prerequisites": [],
        "courses": [],
    }
    # User-reviewed catalog mapping: provider resources do not themselves validate proficiency.
    for resource in resources:
        item = deepcopy(resource)
        item["eligibility"] = "met" if item["id"] != "ou-python" else "unknown"
        item["entry_confirmation"] = (
            "Scenario: learner has checked software/access and entry conditions"
            if item["eligibility"] == "met"
            else "Provider software/quiz issues remain unresolved"
        )
        analyst["courses"].append(item)
    # Add an explicit proof/translation option, a genuine alternative to buying training.
    analyst["courses"].append(
        {
            "id": "proof-existing",
            "title": "Translate existing research into a workforce briefing",
            "hours": 6,
            "fee": 0,
            "skills": ["skill.communication", "skill.stakeholder_communication"],
            "prerequisites": [],
            "eligibility": "met",
            "option_kind": "proof",
            "artifact": "Two-page workforce memo using an existing public-data analysis",
            "completion_criterion": "A reviewer identifies the business question, main finding, assumptions and next action",
            "outcome_status": "Analyst-authored practice option; not a provider promise",
        }
    )
    reviewed = analyst["analysis_input"]
    analysis = analyze_fit(
        reviewed["job_text"],
        reviewed["candidate_text"],
        reviewed["evidence"],
        reviewed["review"],
    )
    quality = next(
        r for r in analysis["requirements"] if r["canonical_skill"] == "Data quality"
    )
    analyst["reviewed_requirements"] = analysis["requirements"]
    analyst["courses"].append(
        {
            "id": "quality-practice",
            "title": "Reconcile a workforce data extract",
            "hours": 12,
            "fee": 0,
            "skills": [quality["skill_id"], "skill.data_analysis"],
            "skill_labels": {quality["skill_id"]: quality["canonical_skill"]},
            "prerequisites": ["software.sql"],
            "eligibility": "met",
            "option_kind": "practice",
            "artifact": "SQL checks, reconciled headcount table and management memo; use examples/practice",
            "completion_criterion": "Detect duplicate snapshots, missing IDs and invalid FTE; reconcile denominators and explain the decision impact",
            "outcome_status": "Analyst-authored 12-hour planning assumption; completion requires task assessment",
        }
    )
    save(RES / "analyst_learning_demo.json", analyst)
    base = json.loads(read_resource_text("workforce_demo.json"))
    medium = deepcopy(base)
    medium.update(
        solver="milp",
        require_consent=True,
        horizon_days=60,
        budget=35000,
        hours_budget=120,
        price_year=2026,
        input_status="Synthetic 30-employee business case; actual O*NET importance weights; scenario vacancies, consent, costs, learning effects and lead times",
        as_of="2026-11-16",
    )
    medium["employees"] = []
    for group in range(5):
        for index, employee in enumerate(base["employees"]):
            e = deepcopy(employee)
            e.update(
                id=f"E{group * 6 + index + 1:02d}",
                backfill_cost=400 + 50 * index,
                consent="unknown" if index == 5 else "met",
            )
            e["eligibility"]["data"] = "met" if index in {0, 2} else "unknown"
            medium["employees"].append(e)
    for role in medium["roles"]:
        role.update(
            positions=4,
            priority=2 if role["id"] == "ops" else 1,
            vacancy_daily_cost=200 if role["id"] == "ops" else 150,
            external_lead_days=30 if role["id"] == "ops" else 25,
            internal_lead_days=7,
        )
    importance = {
        s["skill_id"]: s["importance"]
        for s in public_snapshot()["skills"]
        if s["occupation_id"] == "15-2051.00"
    }
    medium["roles"].append(
        {
            "id": "data",
            "title": "Workforce data science role",
            "occupation_id": "15-2051.00",
            "positions": 4,
            "priority": 3,
            "requirements": {
                s: {"minimum": v, "weight": importance[s]}
                for s, v in {
                    "2.A.1.e": 0.8,
                    "2.A.2.a": 0.8,
                    "2.A.1.d": 0.65,
                    "2.B.4.h": 0.7,
                }.items()
            },
            "external_cost": 14000,
            "external_eligible": "met",
            "external_lead_days": 40,
            "internal_lead_days": 7,
            "vacancy_daily_cost": 400,
        }
    )
    for t in medium["training"]:
        t.update(capacity=2, lead_days=14 if t["id"] == "systems" else 21)
    medium["training"].append(
        {
            "id": "science",
            "title": "Applied workforce analysis practicum",
            "hours": 40,
            "fee": 1200,
            "outcomes": {"2.A.1.e": 0.85, "2.A.2.a": 0.85, "2.B.4.h": 0.75},
            "prerequisites": {"2.A.1.e": 0.65, "2.A.2.a": 0.7},
            "capacity": 2,
            "eligibility": "met",
            "lead_days": 28,
            "artifact": "Reproducible workforce analysis and reviewed management memo",
            "completion_criterion": "Assessor confirms the scenario competency thresholds on a common task rubric",
        }
    )
    save(RES / "workforce_business_demo.json", medium)
    folder = ROOT / "examples/evidence_decisions"
    folder.mkdir(exist_ok=True)
    summaries = {}
    for name, data, function in (
        ("analyst", analyst, plan_investment),
        ("business", medium, allocate_workforce),
    ):
        result = function(data)
        save(folder / (name + "_input.json"), data)
        save(folder / (name + "_result.json"), result)
        (folder / (name + "_brief.md")).write_text(
            capital_markdown(result), encoding="utf-8"
        )
        summaries[name] = result
        print(
            name,
            result.get("best_plan") or result.get("scenarios", {}).get("hybrid"),
            flush=True,
        )
    sensitivity = []
    for field, values in (
        ("hours_budget", [0, 80, 120, 160]),
        ("training_effect_multiplier", [0.75, 1, 1.25]),
        ("backfill_per_employee", [0, 1500, 5000]),
    ):
        for value in values:
            case = deepcopy(medium)
            if field == "backfill_per_employee":
                for employee in case["employees"]:
                    employee["backfill_cost"] = value
            else:
                case[field] = value
            result = allocate_workforce(case)
            sensitivity.append(
                {
                    "changed_input": field,
                    "value": value,
                    "hybrid": result["scenarios"]["hybrid"],
                    "no_training": result["scenarios"]["no_training"],
                    "comparison": result["comparison"],
                }
            )
    save(folder / "business_sensitivity.json", sensitivity)
    save(
        RES / "decision_case_results.json",
        {
            "analyst": summaries["analyst"],
            "business": summaries["business"],
            "business_sensitivity": sensitivity,
        },
    )


if __name__ == "__main__":
    main()
