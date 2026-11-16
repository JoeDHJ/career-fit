"""Reproducible SQL over the explicitly bounded employer/resource sample."""

from __future__ import annotations

import json
import sqlite3

from .resources import read_resource_text

SCHEMA = """
CREATE TABLE jobs(job_id TEXT PRIMARY KEY, employer TEXT, family TEXT, seniority TEXT, geography TEXT, access_state TEXT);
CREATE TABLE requirements(job_id TEXT, skill TEXT, label TEXT, level TEXT, PRIMARY KEY(job_id,skill), FOREIGN KEY(job_id) REFERENCES jobs(job_id));
CREATE TABLE learning(resource_id TEXT PRIMARY KEY, provider TEXT, title TEXT, provider_hours REAL, provider_fee REAL, planning_hours REAL);
"""
QUERIES = {
    "skill_mentions": "SELECT skill, label, COUNT(DISTINCT job_id) AS descriptions, SUM(level='required') AS explicitly_required, SUM(level='preferred') AS preferred FROM requirements GROUP BY skill,label ORDER BY descriptions DESC,skill",
    "family_skills": "SELECT j.family, r.label, COUNT(*) AS descriptions FROM jobs j JOIN requirements r USING(job_id) GROUP BY j.family,r.label ORDER BY j.family,descriptions DESC,r.label",
    "sample_coverage": "SELECT geography,access_state,COUNT(*) AS descriptions FROM jobs GROUP BY geography,access_state ORDER BY geography,access_state",
    "seniority": "SELECT seniority,COUNT(*) AS descriptions FROM jobs GROUP BY seniority ORDER BY descriptions DESC,seniority",
    "resource_completeness": "SELECT COUNT(*) AS resources, SUM(provider_hours IS NOT NULL) AS observed_duration, SUM(provider_hours IS NULL) AS duration_needs_assumption, SUM(provider_fee=0) AS free_content_access FROM learning",
}


def build_research(database: str = ":memory:") -> dict:
    packet = json.loads(read_resource_text("role_evidence.json"))
    catalog = json.loads(read_resource_text("learning_resources.json"))
    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript(
            "DROP TABLE IF EXISTS requirements; DROP TABLE IF EXISTS jobs; DROP TABLE IF EXISTS learning;"
            + SCHEMA
        )
        sources = {s["source_id"]: s for s in packet["sources"]}
        for job in packet["jobs"]:
            con.execute(
                "INSERT INTO jobs VALUES(?,?,?,?,?,?)",
                (
                    job["job_id"],
                    job["employer"],
                    job["family"],
                    job["seniority"],
                    job["geography"],
                    sources[job["source_id"]]["access_state"],
                ),
            )
            con.executemany(
                "INSERT INTO requirements VALUES(?,?,?,?)",
                [
                    (job["job_id"], r["skill"], r["label"], r["level"])
                    for r in job["coded_requirements"]
                ],
            )
        con.executemany(
            "INSERT INTO learning VALUES(?,?,?,?,?,?)",
            [
                (
                    r["id"],
                    r["provider"],
                    r["title"],
                    r["provider_hours"],
                    r["provider_fee"],
                    r["hours"],
                )
                for r in catalog["resources"]
            ],
        )
        con.commit()
        results = {
            name: [dict(row) for row in con.execute(query)]
            for name, query in QUERIES.items()
        }
        return {
            "schema_version": "career_fit.research.v1",
            "sample_size": len(packet["jobs"]),
            "employers": len({j["employer"] for j in packet["jobs"]}),
            "sampling": packet["sampling"],
            "missing_semantics": packet["missing_semantics"],
            "queries": QUERIES,
            "results": results,
            "jobs": packet["jobs"],
            "sources": packet["sources"],
            "learning_resources": catalog["resources"],
            "interpretation": "Counts describe the coded eight-description sample only. Archived and indexed material is shown separately; no market trend, vacancy total or individual return is estimated.",
        }
    finally:
        con.close()
