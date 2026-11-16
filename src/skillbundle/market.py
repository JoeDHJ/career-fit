"""Offline-first public occupation context through the portfolio.v1 contract."""

from __future__ import annotations

from datetime import date, datetime
import json
import math

from .resources import read_resource_text


def public_snapshot() -> dict:
    return json.loads(read_resource_text("public_context.json"))


def validate_snapshot(snapshot: dict) -> None:
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("schema_version") != "portfolio.v1"
    ):
        raise ValueError("market snapshot must use schema_version portfolio.v1")
    sources = snapshot.get("sources")
    occupations = snapshot.get("occupations")
    if not isinstance(sources, list) or not isinstance(occupations, list):
        raise ValueError("market snapshot requires sources and occupations lists")
    source_ids = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("each market source must be an object")
        for field in (
            "source_id",
            "source_url",
            "retrieved_at",
            "source_vintage",
            "geography",
            "unit_of_observation",
            "period",
            "schema_version",
            "status",
        ):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"market source missing {field}")
        if source["schema_version"] != "portfolio.v1" or source["status"] not in {
            "observed",
            "estimated",
            "scenario",
        }:
            raise ValueError("invalid market source schema or status")
        datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00"))
        if source["source_id"] in source_ids:
            raise ValueError("duplicate market source_id")
        source_ids.add(source["source_id"])
    seen = set()
    for row in occupations:
        if not isinstance(row, dict):
            raise ValueError("occupation rows must be objects")
        for field in (
            "occupation_id",
            "native_id",
            "taxonomy",
            "taxonomy_vintage",
            "geography",
            "source_id",
            "title",
            "period",
        ):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"market occupation missing {field}")
        key = (
            row["taxonomy"],
            row["taxonomy_vintage"],
            row["occupation_id"],
            row["geography"],
        )
        if key in seen or row["source_id"] not in source_ids:
            raise ValueError("duplicate occupation or unknown market source")
        seen.add(key)
        for field in (
            "employment",
            "projected_employment",
            "annual_openings",
            "median_annual_wage",
            "projected_change_pct",
        ):
            value = row.get(field)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or (field != "projected_change_pct" and value < 0)
            ):
                raise ValueError(f"invalid market value: {field}")
        if row.get("median_annual_wage") is not None and (
            not row.get("currency") or not row.get("price_year")
        ):
            raise ValueError("wages require currency and price_year")
    skills = snapshot.get("skills", [])
    if not isinstance(skills, list):
        raise ValueError("market skills must be a list")
    seen_skills = set()
    for skill in skills:
        if not isinstance(skill, dict) or any(
            not isinstance(skill.get(k), str) or not skill[k]
            for k in ("occupation_id", "skill_id", "label", "source_id")
        ):
            raise ValueError(
                "market skill rows need occupation_id, skill_id, label and source_id strings"
            )
        value = skill.get("importance")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 1 <= value <= 5
        ):
            raise ValueError("market skill importance must use the IM 1–5 scale")
        key = (skill["occupation_id"], skill["skill_id"])
        if key in seen_skills or skill["source_id"] not in source_ids:
            raise ValueError("duplicate market skill or unknown source")
        seen_skills.add(key)


def market_context(
    occupation_id: str,
    geography: str = "US",
    snapshot: dict | None = None,
    as_of: str | None = None,
) -> dict:
    snapshot = public_snapshot() if snapshot is None else snapshot
    validate_snapshot(snapshot)
    today = date.fromisoformat(as_of) if as_of else date.today()
    rows = [r for r in snapshot["occupations"] if r["occupation_id"] == occupation_id]
    if len({(r["taxonomy"], r["taxonomy_vintage"]) for r in rows}) > 1:
        raise ValueError(
            "Ambiguous occupation taxonomy/vintage; supply a snapshot with one explicit mapping"
        )
    exact = [r for r in rows if r["geography"].casefold() == geography.casefold()]
    national = [r for r in rows if r["geography"] == "US"]
    row = (
        exact[0]
        if exact
        else national[0]
        if national
        and (geography.upper() == "US" or geography.upper().startswith("US-"))
        else None
    )
    base = {
        "schema_version": "portfolio.v1",
        "requested_occupation": occupation_id,
        "requested_geography": geography,
        "as_of": today.isoformat(),
        "coverage": {
            "occupations_in_snapshot": len(snapshot["occupations"]),
            "requested_occupation_found": bool(row),
        },
        "interpretation": "Occupation context is descriptive. Wages are population estimates, and openings are official projections; neither measures a training return or a job offer probability.",
    }
    if row is None:
        return {
            **base,
            "status": "missing",
            "geography_status": "uncovered",
            "occupation": None,
            "sources": [],
            "skills": [],
        }
    source = next(s for s in snapshot["sources"] if s["source_id"] == row["source_id"])
    age = (
        today
        - datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00")).date()
    ).days
    skills = [
        s
        for s in snapshot.get("skills", [])
        if s["occupation_id"] == occupation_id + ".00"
        and s.get("recommend_suppress") != "Y"
        and s.get("not_relevant") != "Y"
    ]
    relevant_ids = {row["source_id"]} | {s["source_id"] for s in skills}
    sources = []
    for s in snapshot["sources"]:
        if s["source_id"] in relevant_ids:
            days = (
                today
                - datetime.fromisoformat(
                    s["retrieved_at"].replace("Z", "+00:00")
                ).date()
            ).days
            sources.append(
                {
                    **s,
                    "retrieval_age_days": days,
                    "freshness_status": "future_dated"
                    if days < 0
                    else "stale"
                    if days > 180
                    else "available",
                }
            )
    statuses = {s["freshness_status"] for s in sources}
    status = (
        "future_dated"
        if "future_dated" in statuses
        else "stale"
        if "stale" in statuses
        else "available"
    )
    return {
        **base,
        "status": status,
        "retrieval_age_days": age,
        "geography_status": "exact" if exact else "national_only",
        "occupation": row,
        "sources": sources,
        "skills": sorted(skills, key=lambda s: (-s["importance"], s["skill_id"])),
        "crosswalk": snapshot.get("crosswalk"),
        "missing_metrics": [
            k
            for k in (
                "employment",
                "annual_openings",
                "median_annual_wage",
                "projected_change_pct",
            )
            if row.get(k) is None
        ],
    }
