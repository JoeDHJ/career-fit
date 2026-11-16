"""Build fictional-person cases from attributed public occupational observations."""

from __future__ import annotations

import json
from pathlib import Path

from skillbundle.career import analyze_fit
from skillbundle.market import public_snapshot

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "src/skillbundle/resources"


def save(name, data):
    (RESOURCES / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    job = (
        "Talent Intelligence Analyst, Global Specialty Recruiting, Amazon, Seattle or New York. "
        "Reviewed paraphrase of official posting 10569918, retrieved 2026-11-16. "
        "Responsibilities include market research across locations and competitors, quantitative and qualitative research, "
        "executive communication, data visualization, strategy documents, self-service dashboards, automated workflows and AI tools. "
        "Synthesize market trends and triangulate sources; advise recruiting, HR, finance and business leaders. "
        "Manage multiple projects and communicate delivery timelines independently. "
        "Must have 5 years of executive leadership advising experience. "
        "Must have 7 years of corporate recruiting experience focused on passive engineering candidates in technology markets. "
        "Must have a bachelor's degree or higher. "
        "Preferred: executive search experience, recruiting and people-related tools, CRM systems, and complex spreadsheets."
    )
    candidate = (
        "FICTIONAL CANDIDATE A, constructed for this demonstration, not Haojian Dui's resume. "
        "A labor economist with a master's degree and three years of academic research experience. "
        "Built Python data pipelines, analyzed employment datasets, wrote research reports and presented results to policy audiences. "
        "No corporate recruiting experience and no executive leadership advising experience. "
        "Has not used CRM systems or complex spreadsheets professionally. "
        "Interested in translating research into talent-market intelligence; has not built a self-service dashboard."
    )
    evidence = [
        {
            "evidence_id": "fictional-python",
            "skill_id": "software.python",
            "canonical_skill": "Python",
            "analysis_category_code": "specific_software_skill",
            "evidence_type": "research_project",
            "source_text": "Fictional work sample: built a Python employment-data pipeline",
            "measurable_result": "A runnable public-data notebook",
            "duration_months": 18,
            "recency_years": 1,
        },
        {
            "evidence_id": "fictional-writing",
            "skill_id": "skill.writing",
            "canonical_skill": "Writing",
            "analysis_category_code": "writing_skill",
            "evidence_type": "research_project",
            "source_text": "Fictional work sample: wrote a labor-market research memo",
            "measurable_result": "A two-page evidence brief",
            "duration_months": 12,
            "recency_years": 1,
        },
        {
            "evidence_id": "fictional-research",
            "skill_id": "skill.research",
            "canonical_skill": "Research",
            "analysis_category_code": "cognitive_skill",
            "evidence_type": "research_project",
            "source_text": "Fictional work sample: triangulated public employment sources",
            "measurable_result": "Source registry with two datasets",
            "duration_months": 24,
            "recency_years": 1,
        },
    ]
    provisional = analyze_fit(job, candidate, evidence)
    constraints = {
        r["requirement_id"]: "not_met"
        for r in provisional["requirements"]
        if r.get("hard_constraint") and r["requirement_type"] == "experience_floor"
    }
    removed = [
        r["requirement_id"]
        for r in provisional["requirements"]
        if r.get("skill_id") == "skill.leadership"
    ]
    analysis_input = {
        "job_text": job,
        "candidate_text": candidate,
        "evidence": evidence,
        "review": {
            "scope": "role_requirements",
            "applied": True,
            "constraint_status_overrides": constraints,
            "removed_requirement_ids": removed,
            "added_requirements": [
                {"text": "Complex spreadsheets", "importance_level": "preferred"},
                {"text": "CRM systems", "importance_level": "preferred"},
            ],
        },
    }
    reviewed = analyze_fit(job, candidate, evidence, analysis_input["review"])
    spreadsheet_id = next(
        r["skill_id"]
        for r in reviewed["requirements"]
        if r["canonical_skill"] == "Complex spreadsheets"
    )
    demo = {
        "input_status": "fictional_candidate_and_training_assumptions; real_JD_paraphrase",
        "analysis_input": analysis_input,
        "budget": 600,
        "hours": 90,
        "weekly_hours": 7,
        "preparation_hours": 6,
        "currency": "USD",
        "hourly_value": 20,
        "occupation_id": "13-1071",
        "geography": "US-WA-Seattle",
        "confirmed_prerequisites": ["software.python"],
        "courses": [
            {
                "id": "dashboard",
                "title": "Talent-market dashboard work sample",
                "hours": 32,
                "fee": 120,
                "skills": ["skill.data_visualization"],
                "prerequisites": ["software.python"],
                "eligibility": "met",
                "artifact": "Interactive occupation comparison with source dates and missing-data states",
                "completion_criterion": "Reproduce three occupation totals and explain each chart's population and period",
            },
            {
                "id": "spreadsheet",
                "title": "Spreadsheet scenario model",
                "hours": 20,
                "fee": 80,
                "skills": [spreadsheet_id],
                "skill_labels": {spreadsheet_id: "Complex spreadsheets"},
                "prerequisites": [],
                "eligibility": "met",
                "artifact": "A training-versus-hiring cost workbook using synthetic people",
                "completion_criterion": "A reviewer can reconcile fees, released hours and all scenario totals",
            },
            {
                "id": "stakeholder",
                "title": "Executive research translation sprint",
                "hours": 18,
                "fee": 60,
                "skills": ["skill.communication"],
                "prerequisites": [],
                "eligibility": "met",
                "artifact": "One-page talent-market decision memo and five-minute briefing",
                "completion_criterion": "Separate observations from scenarios and answer two reviewer objections",
            },
            {
                "id": "ai",
                "title": "AI-assisted research verification sprint",
                "hours": 24,
                "fee": 180,
                "skills": ["ai.artificial_intelligence"],
                "prerequisites": ["software.python"],
                "eligibility": "met",
                "artifact": "A source-linked research workflow with a manually checked error log",
                "completion_criterion": "A human verifies every factual statement in the final memo",
            },
            {
                "id": "advanced",
                "title": "Advanced dashboard deployment",
                "hours": 40,
                "fee": 350,
                "skills": ["skill.data_visualization", "skill.project_management"],
                "prerequisites": ["skill.data_visualization"],
                "eligibility": "met",
                "artifact": "Locally served dashboard and operations checklist",
                "completion_criterion": "Fresh installation and malformed-input checks pass",
            },
            {
                "id": "coaching",
                "title": "Recruiting leadership seminar",
                "hours": 24,
                "fee": 500,
                "skills": ["skill.leadership"],
                "prerequisites": [],
                "eligibility": "unknown",
                "artifact": "Reviewed practice case",
                "completion_criterion": "Confirm provider entry requirements before purchase",
            },
        ],
        "jd_source": {
            "source_id": "amazon-10569918",
            "source_url": "https://www.amazon.jobs/en/jobs/10569918/talent-intelligence-analyst-global-specialty-recruiting",
            "retrieved_at": "2026-11-16",
            "source_vintage": "Official posting observed 2026-11-16",
            "geography": "US-WA-Seattle; US-NY-New York",
            "unit_of_observation": "job posting",
            "period": "2026-11-16",
            "status": "observed",
            "schema_version": "portfolio.v1",
            "content": "Decision-relevant paraphrase, not a verbatim copy; no claim that the dictionary captures every requirement",
        },
    }
    save("investment_demo.json", demo)
    snapshot = public_snapshot()
    # Exact O*NET .00 skills; weights remain on the published IM 1–5 scale.
    skill_ids = ["2.A.1.e", "2.A.2.a", "2.A.1.d", "2.B.4.h"]
    weights = {
        (s["occupation_id"], s["skill_id"]): s["importance"] for s in snapshot["skills"]
    }
    roles = []
    for rid, title, code, minimums, cost in [
        ("ops", "Operations analysis role", "15-2031.00", [0.7, 0.7, 0.6, 0.6], 8000),
        (
            "people",
            "People reporting role",
            "13-1071.00",
            [0.45, 0.65, 0.7, 0.65],
            7000,
        ),
    ]:
        roles.append(
            {
                "id": rid,
                "title": title,
                "occupation_id": code,
                "positions": 2,
                "requirements": {
                    s: {"minimum": m, "weight": weights[(code, s)]}
                    for s, m in zip(skill_ids, minimums)
                },
                "external_cost": cost,
                "external_eligible": "met",
            }
        )
    staff = []
    for eid, levels, hours, hourly, eligibility in [
        ("E01", [0.8, 0.8, 0.7, 0.4], 40, 30, {"ops": "met", "people": "met"}),
        ("E02", [0.5, 0.7, 0.8, 0.5], 40, 28, {"ops": "met", "people": "met"}),
        ("E03", [0.75, 0.75, 0.65, 0.7], 20, 35, {"ops": "met", "people": "unknown"}),
        ("E04", [0.5, 0.7, 0.8, 0.7], 30, 25, {"ops": "met", "people": "met"}),
        ("E05", [0.4, 0.6, 0.6, 0.4], 16, 24, {"ops": "unknown", "people": "met"}),
        ("E06", [0.7, 0.7, 0.7, 0.5], 24, 32, {"ops": "not_met", "people": "unknown"}),
    ]:
        staff.append(
            {
                "id": eid,
                "skills": dict(zip(skill_ids, levels)),
                "available_hours": hours,
                "hourly_cost": hourly,
                "eligibility": eligibility,
            }
        )
    workforce = {
        "input_status": "synthetic_employee_cohort_and_costs; actual_ONET_importance_weights",
        "review_confirmed": True,
        "currency": "USD",
        "budget": 10000,
        "hours_budget": 56,
        "roles": roles,
        "employees": staff,
        "training": [
            {
                "id": "systems",
                "title": "Systems evaluation practicum",
                "hours": 24,
                "fee": 600,
                "outcomes": {"2.B.4.h": 0.7},
                "prerequisites": {"2.A.2.a": 0.65},
                "capacity": 1,
                "eligibility": "met",
                "artifact": "Tested workforce dashboard and decision-log walkthrough",
                "completion_criterion": "Human assessor confirms systems-evaluation threshold using a common rubric",
            },
            {
                "id": "math",
                "title": "Operations mathematics bridge",
                "hours": 32,
                "fee": 800,
                "outcomes": {"2.A.1.e": 0.75, "2.B.4.h": 0.65},
                "prerequisites": {"2.A.2.a": 0.65},
                "capacity": 1,
                "eligibility": "met",
                "artifact": "Hand-checked allocation model and sensitivity memo",
                "completion_criterion": "Independent reviewer reproduces the optimum and verifies feasibility",
            },
        ],
        "public_reference": {
            "schema_version": "portfolio.v1",
            "snapshot_id": snapshot["snapshot_id"],
            "source_ids": [s["source_id"] for s in snapshot["sources"]],
            "mapping": "Four exact O*NET skill IDs in each of two .00 occupations. Published importance weights inform priorities; all competency levels, vacancies, qualification flags and costs are scenario inputs.",
            "skill_labels": {
                s["skill_id"]: s["label"]
                for s in snapshot["skills"]
                if s["skill_id"] in skill_ids
            },
        },
    }
    save("workforce_demo.json", workforce)
    print(
        "Built two attributed scenario inputs; candidate and employees are fictional."
    )


if __name__ == "__main__":
    main()
