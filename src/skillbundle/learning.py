"""Local work-sample progress, task rubrics and explicit evidence transfer."""

from __future__ import annotations

from copy import deepcopy

from .investment import number

RUBRIC = {
    "correctness": "0: not checked; 1: material errors; 2: core checks pass; 3: handles edge cases and reconciles totals",
    "reproducibility": "0: no artifact; 1: partial instructions; 2: another person can run/review it; 3: fresh run and malformed-input checks documented",
    "interpretation": "0: no explanation; 1: unsupported interpretation; 2: population, units and assumptions clear; 3: explains decision tradeoffs and remaining uncertainty",
    "independence": "0: contribution unclear; 1: copied with little explanation; 2: can explain and adapt the work; 3: independently diagnoses a new task variation",
}


def review_progress(payload, courses):
    progress = payload.get("progress", [])
    if not isinstance(progress, list) or len(progress) > 12:
        raise ValueError("progress must contain at most 12 work-sample records")
    by_id = {c["id"]: c for c in courses}
    seen = set()
    records = []
    for raw in progress:
        if not isinstance(raw, dict) or raw.get("course_id") not in by_id:
            raise ValueError(
                "progress must reference a current training/work-sample ID"
            )
        cid = raw["course_id"]
        if cid in seen:
            raise ValueError("duplicate progress record")
        seen.add(cid)
        status = raw.get("status", "planned")
        assessment = raw.get("assessment", "not_reviewed")
        if status not in {
            "planned",
            "in_progress",
            "completed",
            "paused",
        } or assessment not in {"not_reviewed", "revise", "passed"}:
            raise ValueError("invalid progress or assessment status")
        actual = raw.get("actual_hours")
        if actual is not None:
            actual = number(actual, "actual_hours", 0, 5000)
        artifact = raw.get("artifact", "")
        note = raw.get("review_note", "")
        if (
            not isinstance(artifact, str)
            or not isinstance(note, str)
            or len(artifact) > 4000
            or len(note) > 4000
        ):
            raise ValueError(
                "artifact and review note must be text of at most 4000 characters"
            )
        rubric = raw.get("rubric", {})
        if not isinstance(rubric, dict) or set(rubric) - set(RUBRIC):
            raise ValueError("unknown task-rubric dimension")
        levels = {}
        for key, value in rubric.items():
            level = number(value, "rubric level", 0, 3)
            if level != int(level):
                raise ValueError("rubric levels must be integers")
            levels[key] = int(level)
        if assessment == "passed" and (
            status != "completed"
            or not artifact.strip()
            or not note.strip()
            or set(levels) != set(RUBRIC)
            or min(levels.values()) < 2
        ):
            raise ValueError(
                "Passed assessment needs completed work, an artifact, review note and all four rubric dimensions at level 2 or 3"
            )
        records.append(
            {
                "course_id": cid,
                "title": by_id[cid]["title"],
                "status": status,
                "assessment": assessment,
                "actual_hours": actual,
                "planned_hours": by_id[cid]["hours"],
                "artifact": artifact.strip(),
                "review_note": note.strip(),
                "rubric": levels,
                "evidence_status": "user_declared_task_assessment; not independent verification",
            }
        )
    return {
        "records": records,
        "rubric": RUBRIC,
        "reported_actual_hours": round(
            sum(r["actual_hours"] for r in records if r["actual_hours"] is not None), 2
        ),
        "records_missing_actual_hours": sum(r["actual_hours"] is None for r in records),
        "passed_records": sum(r["assessment"] == "passed" for r in records),
        "interpretation": "Completion records do not automatically change fit, proficiency or eligibility. Explicitly transfer assessed work to the evidence-review workspace and review it there.",
    }


def progress_to_review(payload):
    from .investment import courses_checked, plan_investment

    if (
        not isinstance(payload, dict)
        or payload.get("confirm_evidence_transfer") is not True
    ):
        raise ValueError("Confirm the assessed artifacts before transferring evidence")
    result = plan_investment(payload)
    progress = review_progress(payload, courses_checked(payload.get("courses", [])))
    requirements = {
        r["skill_id"]: r["skill"] for r in result["evidence_map"] if r["skill_id"]
    }
    by_id = {c["id"]: c for c in payload["courses"]}
    additions = []
    for record in progress["records"]:
        if record["assessment"] != "passed":
            continue
        for skill in by_id[record["course_id"]]["skills"]:
            if skill in requirements:
                additions.append(
                    {
                        "skill_id": skill,
                        "canonical_skill": requirements[skill],
                        "evidence_type": "portfolio",
                        "source_text": record["artifact"],
                        "result": record["review_note"],
                        "source_name": "work-sample:" + record["course_id"],
                    }
                )
    if not additions:
        raise ValueError(
            "No assessed current-role work sample is available for transfer"
        )
    analysis_input = deepcopy(payload["analysis_input"])
    review = analysis_input.setdefault("review", {})
    # Preserve normalized evidence, including negation and verification metadata.
    # The added-evidence UI schema must never reinterpret existing records.
    existing = review.setdefault("added_evidence", [])
    added_count = 0
    for addition in additions:
        previous = next(
            (
                item
                for item in existing + analysis_input.get("evidence", [])
                if not item.get("negated")
                and item.get("skill_id") == addition["skill_id"]
                and item.get("source_text") == addition["source_text"]
            ),
            None,
        )
        if previous is None:
            existing.append(addition)
            added_count += 1
        else:
            previous["result"] = addition["result"]
    if len(review["added_evidence"]) > 30:
        raise ValueError(
            "Too many evidence items; consolidate the reviewed work samples"
        )
    review.update(applied=False, scope="role_requirements")
    review.pop("base_signature", None)
    return {
        "analysis_input": analysis_input,
        "added_items": added_count,
        "review_required": True,
    }
