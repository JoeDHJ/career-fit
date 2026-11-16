"""Compile analyst-coded primary-source observations; never claim independent labels."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src/skillbundle/resources"
STAMP = "2026-11-16"


def source(sid, url, geography, unit, vintage, access="direct"):
    return {
        "source_id": sid,
        "source_url": url,
        "retrieved_at": STAMP,
        "retrieval_precision": "day",
        "source_vintage": vintage,
        "geography": geography,
        "unit_of_observation": unit,
        "period": vintage,
        "currency": None,
        "price_year": None,
        "schema_version": "portfolio.v1",
        "status": "observed",
        "access_state": access,
    }


def main():
    records = [
        (
            "amazon-10569918",
            "Amazon",
            "Talent Intelligence Analyst",
            "talent_intelligence",
            "senior",
            "US",
            "https://www.amazon.jobs/en/jobs/10569918/talent-intelligence-analyst-global-specialty-recruiting",
            "direct",
            "Observed 2026-11-16; live posting content",
            "Research talent markets across locations, triangulate sources, automate dashboards and communicate strategy to leaders. Recruiting/CRM tools and complex spreadsheets are preferred.",
            [
                ("research", "responsibility"),
                ("reporting", "responsibility"),
                ("bi", "responsibility"),
                ("excel", "preferred"),
                ("hr_systems", "preferred"),
            ],
            [
                "5+ years executive leadership advising",
                "7+ years corporate/search recruiting",
                "Bachelor's degree or higher",
            ],
        ),
        (
            "apple-200682909-1418",
            "Apple",
            "People Analytics Full Stack Developer",
            "people_analytics_engineering",
            "senior",
            "IE",
            "https://jobs.apple.com/en-us/details/200682909-1418/people-analytics-full-stack-developer",
            "official_indexed_description",
            "Posted 2026-10-02; indexed official description checked 2026-11-16; direct page is a script shell",
            "Build SQL/Snowflake data models, Python services, dashboards and refresh pipelines. Operate Linux services and communicate data definitions and findings to senior partners.",
            [
                ("sql", "required"),
                ("python", "required"),
                ("bi", "responsibility"),
                ("data_quality", "responsibility"),
                ("reporting", "responsibility"),
            ],
            [
                "Demonstrated SQL/Snowflake and Python delivery",
                "Independent Linux operation",
            ],
        ),
        (
            "nhs-7087716",
            "Tees, Esk and Wear Valleys NHS Trust",
            "Data Analyst - People & Culture",
            "people_analytics",
            "analyst",
            "UK",
            "https://apps.trac.jobs/job-advert/7087716?ShowJobAdvert=&feedid=9002",
            "direct_archived",
            "Closed 2025-03-25; official employer ATS description inspected 2026-11-16",
            "Support workforce information and statutory submissions. Advanced spreadsheet use, information analysis, comprehensive reporting, data quality and task prioritization are described. SQL/reporting-tool experience appears in the person specification.",
            [
                ("excel", "required"),
                ("reporting", "responsibility"),
                ("data_quality", "responsibility"),
                ("sql", "mentioned"),
                ("hr_systems", "responsibility"),
            ],
            [
                "Experience in an information-analysis/reporting environment",
                "Employer-specific application and work-eligibility checks",
            ],
        ),
        (
            "nhs-7657488",
            "Lancashire Teaching Hospitals NHS Foundation Trust",
            "Senior Workforce Information Analyst",
            "workforce_planning",
            "senior_analyst",
            "UK",
            "https://apps.trac.jobs/job-advert/7657488?FromJobsNHS=1&ShowJobAdvert=",
            "direct_archived",
            "Closed 2026-04-13; official employer ATS description inspected 2026-11-16",
            "Support workforce and financial planning, SQL extraction, advanced spreadsheets and dashboards. ESR/workforce-system knowledge is essential; Power BI and workforce-planning experience appear as desirable criteria.",
            [
                ("sql", "required"),
                ("excel", "required"),
                ("bi", "responsibility"),
                ("reporting", "required"),
                ("hr_systems", "required"),
                ("forecasting", "preferred"),
            ],
            [
                "Relevant degree or equivalent relevant experience",
                "Significant workforce-information experience",
                "Background-check process",
            ],
        ),
        (
            "workday-JR-0108449",
            "Workday",
            "People Analytics Analyst",
            "people_analytics",
            "analyst",
            "US",
            "https://workday.wd5.myworkdayjobs.com/Workday/job/USA-CA-Pleasanton/People-Analytics-Analyst_JR-0108449-1",
            "official_indexed_description",
            "Dated indexed employer ATS description; checked 2026-11-16; current vacancy status unverified",
            "Partner with People centers of excellence to build analytical insights. Scripting/query languages including Python, R and SQL are described as a bonus.",
            [
                ("reporting", "responsibility"),
                ("sql", "preferred"),
                ("python", "preferred"),
            ],
            ["Full qualification details require checking the current employer page"],
        ),
        (
            "walmart-R-2643323",
            "Walmart",
            "Senior Director, Data Analytics - Workforce Planning",
            "workforce_planning",
            "director",
            "US",
            "https://careers.walmart.com/us/en/jobs/R-2643323",
            "official_indexed_description",
            "Official indexed description checked 2026-11-16; direct URL now redirects to job-not-found",
            "Frame workforce/business problems, translate workforce intelligence into practical recommendations and embed evidence into business decisions. The technical qualification list includes SQL, Python and BI tools.",
            [
                ("reporting", "responsibility"),
                ("forecasting", "responsibility"),
                ("sql", "mentioned"),
                ("python", "mentioned"),
                ("bi", "mentioned"),
            ],
            [
                "Senior leadership/supervisory and industry experience",
                "Extensive analytics experience; inspect full qualification alternatives",
            ],
        ),
        (
            "walmart-R-2637733",
            "Walmart",
            "Manager, Workforce Management Financial Planning",
            "workforce_planning",
            "manager",
            "US",
            "https://careers.walmart.com/us/en/jobs/R-2637733",
            "official_indexed_description",
            "Official indexed description checked 2026-11-16; direct URL now redirects to job-not-found",
            "Lead financial planning and budget management for a workforce-management organization working on forecasting, capacity planning, scheduling and workforce analytics.",
            [("forecasting", "responsibility"), ("reporting", "responsibility")],
            [
                "Manager-level financial/workforce planning experience; full details need rechecking"
            ],
        ),
        (
            "nhs-6997514",
            "University Hospitals of Derby and Burton NHS Foundation Trust",
            "Insight Analyst",
            "adjacent_analytics",
            "unspecified",
            "UK",
            "https://apps.trac.jobs/job-advert/6997514?ShowJobAdvert=&feedid=365&set-locale=en-gb",
            "official_indexed_archived",
            "Archived official employer ATS description checked 2026-11-16",
            "Provide routine and ad-hoc analysis for planning and performance. Person specification names basic analytical-tool knowledge/training such as SQL Server, Excel, Power BI or QlikView, with qualification/equivalent-experience routes.",
            [
                ("sql", "mentioned"),
                ("excel", "mentioned"),
                ("bi", "mentioned"),
                ("reporting", "responsibility"),
            ],
            [
                "Published qualification or equivalent-experience route",
                "Full current employer criteria need checking",
            ],
        ),
    ]
    labels = {
        "sql": "SQL",
        "python": "Python",
        "excel": "Spreadsheets / Excel",
        "bi": "BI / dashboards",
        "reporting": "Decision reporting / stakeholder communication",
        "data_quality": "Data quality",
        "forecasting": "Planning / forecasting",
        "hr_systems": "HR / workforce systems",
        "research": "Market research",
    }
    jobs = []
    sources = []
    for (
        sid,
        employer,
        title,
        family,
        seniority,
        geo,
        url,
        access,
        vintage,
        description,
        skills,
        gates,
    ) in records:
        sources.append(source(sid, url, geo, "job description", vintage, access))
        jobs.append(
            {
                "job_id": sid,
                "native_id": sid,
                "employer": employer,
                "title": title,
                "family": family,
                "seniority": seniority,
                "geography": geo,
                "source_id": sid,
                "paraphrase": description,
                "coded_requirements": [
                    {"skill": s, "label": labels[s], "level": level}
                    for s, level in skills
                ],
                "qualification_notes": gates,
                "coding_method": "Analyst-coded paraphrase of the stated primary-source material; not independently human-labeled ground truth",
            }
        )
    packet = {
        "schema_version": "portfolio.v1",
        "snapshot_id": "career-fit-role-sample-2026-11-16",
        "sources": sources,
        "jobs": jobs,
        "sampling": "Purposive eight-description portfolio sample across US/UK/Ireland and several seniority levels; includes closed/indexed descriptions. It is neither a representative market sample nor a vacancy-count time series.",
        "missing_semantics": "A skill not coded is unobserved in this sample coding, not proof that the employer does not require it.",
        "skill_taxonomy": {
            "name": "Career Fit role-sample coding",
            "version": "1",
            "labels": labels,
        },
    }
    (RES / "role_evidence.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    resources = [
        (
            "ou-excel",
            "The Open University",
            "Data analysis: visualisations in Excel",
            "https://www.open.edu/openlearn/science-maths-technology/data-analysis-visualisations-excel/content-section-0",
            ["software.excel", "skill.data_visualization"],
            6,
            6,
            4,
            "Excel or compatible spreadsheet access",
            "Create a reconciled pivot summary and chart from public occupation data",
            "Reviewer reconciles totals and explains the denominator and chart choice",
            None,
        ),
        (
            "ou-python",
            "The Open University",
            "Learn to code for data analysis",
            "https://www.open.edu/openlearn/digital-computing/learn-code-data-analysis/content-section-overview",
            ["software.python"],
            24,
            24,
            8,
            "Python/Jupyter setup; provider reports software/quiz issues",
            "Runnable public-data cleaning notebook with checks and source notes",
            "A fresh local run reproduces the table and catches malformed data",
            "Provider flags software/quiz issues; confirm a workable local environment before relying on this path",
        ),
        (
            "ms-sql",
            "Microsoft Learn",
            "Query and modify data with Transact-SQL",
            "https://learn.microsoft.com/en-us/training/paths/get-started-querying-with-transact-sql/",
            ["software.sql"],
            None,
            6,
            6,
            "Familiarity with tabular data; local SQL environment or suitable learning environment",
            "SQL queries joining three public/synthetic tables with reconciliation checks",
            "Reviewer verifies joins, missing values and grouped totals against a hand example",
            "Provider duration not visible in the retrieved path; six study hours is an editable planning assumption",
        ),
        (
            "ms-bi",
            "Microsoft Learn",
            "Get started building with Power BI",
            "https://learn.microsoft.com/en-us/training/modules/get-started-with-power-bi/",
            ["software.power_bi", "skill.data_visualization"],
            None,
            3,
            7,
            "Compatible Power BI access; account/software/service costs may be separate",
            "A decision dashboard with definitions and accessible chart labels",
            "Reviewer can locate sources, filter the sample and interpret coverage correctly",
            "Provider duration not visible; three study hours and seven practice hours are editable assumptions",
        ),
        (
            "ou-communication",
            "The Open University",
            "Effective communication in the workplace",
            "https://www.open.edu/openlearn/money-business/effective-communication-the-workplace/content-section-overview",
            ["skill.communication", "skill.stakeholder_communication"],
            24,
            24,
            4,
            "Self-paced study; optional free account for participation record",
            "A two-page workforce decision memo and five-minute briefing",
            "Reviewer identifies the decision, evidence, assumptions and recommended next step",
            None,
        ),
    ]
    catalog = []
    for (
        rid,
        provider,
        title,
        url,
        skills,
        observed,
        learning,
        practice,
        prerequisite,
        artifact,
        criterion,
        caution,
    ) in resources:
        catalog.append(
            {
                "id": rid,
                "provider": provider,
                "title": title,
                "skills": skills,
                "provider_hours": observed,
                "provider_fee": 0,
                "provider_fee_scope": "Self-study content access only; excludes certification exams, software subscriptions, equipment and connectivity",
                "learning_hours_assumption": learning,
                "practice_hours_assumption": practice,
                "hours": learning + practice,
                "fee": 0,
                "prerequisites": [],
                "eligibility": "unknown",
                "entry_conditions": prerequisite,
                "artifact": artifact,
                "completion_criterion": criterion,
                "caution": caution,
                "source": source(
                    rid,
                    url,
                    "Online; access may vary",
                    "learning resource",
                    "Provider page checked 2026-11-16",
                ),
                "fee_source": "https://learn.microsoft.com/en-gb/training/support/faq"
                if provider == "Microsoft Learn"
                else url,
                "outcome_status": "Proposed work-sample target; provider content does not establish individual proficiency or employment returns",
            }
        )
    (RES / "learning_resources.json").write_text(
        json.dumps(
            {
                "schema_version": "career_fit.learning_resources.v1",
                "retrieved_on": STAMP,
                "resources": catalog,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "Compiled",
        len(jobs),
        "official description observations and",
        len(catalog),
        "official learning resources",
    )


if __name__ == "__main__":
    main()
