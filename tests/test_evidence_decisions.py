from copy import deepcopy
import importlib.util
import json

import pytest

from skillbundle.benchmark import benchmark_skillspan, bio_spans, score
from skillbundle.career import analyze_fit
from skillbundle.investment import plan_investment
from skillbundle.learning import progress_to_review, review_progress
from skillbundle.ner import PerceptronNER
from skillbundle.research import build_research
from skillbundle.resources import read_resource_text
from skillbundle.workforce import allocate_workforce


def resource(name):
    return json.loads(read_resource_text(name + ".json"))


def test_overlap_is_maximum_one_to_one():
    assert score({(0, 3), (3, 6)}, {(0, 6)}, True)["true_positive"] == 1
    # First broad prediction must be reassigned to let the second match.
    result = score({(0, 10), (1, 4)}, {(2, 3), (7, 8)}, True)
    assert result["true_positive"] == 2
    assert result["recall"] == result["precision"] == 1
    assert bio_spans(["SQL", "skills"], ["I", "I"]) == [(0, 2, "SQL skills")]


def test_micro_negative_rows_and_limit(tmp_path):
    path = tmp_path / "sample.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {"tokens": ["Python"], "tags_skill": ["B"], "tags_knowledge": ["O"]},
                {"tokens": ["SQL"], "tags_skill": ["O"], "tags_knowledge": ["B"]},
            ]
        ),
        encoding="utf-8",
    )
    result = benchmark_skillspan(path)
    assert result["micro_strict"]["precision"] == 0.5
    assert result["micro_strict"]["recall"] == 1
    assert result["strict"]["recall"] == 0.5
    assert result["errors"]["false_positive_sentences"] == 1
    assert benchmark_skillspan(path, target="combined")["micro_strict"]["f1"] == 1
    assert benchmark_skillspan(path, limit=0)["rows"] == 0
    with pytest.raises(ValueError):
        benchmark_skillspan(path, limit=-1)
    path.write_text('{"tokens":["SQL"],"tags_skill":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="equal-length"):
        benchmark_skillspan(path)
    model_path = tmp_path / "legacy.json"
    PerceptronNER().save(model_path)
    with pytest.raises(ValueError, match="variant"):
        benchmark_skillspan(path, engine="averaged", model_path=model_path)


def passed(data):
    course = data["courses"][0]
    data["progress"] = [
        {
            "course_id": course["id"],
            "status": "completed",
            "assessment": "passed",
            "actual_hours": 11,
            "artifact": "local-work/pivot.csv",
            "review_note": "Self-assessed: reconciled totals and explained denominator; reproduce using documented steps",
            "rubric": dict.fromkeys(
                ["correctness", "reproducibility", "interpretation", "independence"], 2
            ),
        }
    ]
    return data


def test_task_assessment_requires_artifact_and_all_dimensions():
    data = passed(resource("analyst_learning_demo"))
    assert plan_investment(data)["progress"]["passed_records"] == 1
    original = plan_investment(resource("analyst_learning_demo"))
    assert plan_investment(data)["reviewed_summary"] == original["reviewed_summary"]
    for field, value in [
        ("status", "in_progress"),
        ("artifact", ""),
        ("review_note", ""),
        ("rubric", {"correctness": 3}),
    ]:
        invalid = deepcopy(data)
        invalid["progress"][0][field] = value
        with pytest.raises(ValueError, match="Passed"):
            review_progress(invalid, invalid["courses"])


def test_transfer_preserves_evidence_and_requires_fresh_role_review():
    data = passed(resource("analyst_learning_demo"))
    with pytest.raises(ValueError, match="Confirm"):
        progress_to_review(data)
    data["confirm_evidence_transfer"] = True
    transferred = progress_to_review(data)
    incoming = transferred["analysis_input"]
    assert incoming["review"]["applied"] is False
    assert incoming["evidence"] == data["analysis_input"]["evidence"]
    assert len(incoming["review"]["added_evidence"]) == transferred["added_items"]
    result = analyze_fit(
        incoming["job_text"],
        incoming["candidate_text"],
        incoming["evidence"],
        review=incoming["review"],
    )
    assert result["summary"]["score_visibility"] != "visible"
    incoming["review"]["applied"] = True
    result = analyze_fit(
        incoming["job_text"],
        incoming["candidate_text"],
        incoming["evidence"],
        review=incoming["review"],
    )
    assert result["summary"]["score_visibility"] == "visible"


def test_transfer_never_reinterprets_negative_existing_evidence():
    data = passed(resource("analyst_learning_demo"))
    data["analysis_input"]["evidence"].append(
        {
            "skill_id": "software.sql",
            "canonical_skill": "SQL",
            "evidence_type": "work",
            "source_text": "No SQL experience",
            "negated": True,
        }
    )
    data["confirm_evidence_transfer"] = True
    incoming = progress_to_review(data)["analysis_input"]
    incoming["review"]["applied"] = True
    result = analyze_fit(
        incoming["job_text"],
        incoming["candidate_text"],
        incoming["evidence"],
        incoming["review"],
    )
    assert (
        next(r for r in result["requirements"] if r["skill_id"] == "software.sql")[
            "status"
        ]
        != "direct"
    )
    assert incoming["evidence"][-1]["negated"] is True


def test_repeated_transfer_updates_notes_without_duplicate_strength():
    data = passed(resource("analyst_learning_demo"))
    data["confirm_evidence_transfer"] = True
    first = progress_to_review(data)
    data["analysis_input"] = first["analysis_input"]
    data["analysis_input"]["review"]["applied"] = True
    data["progress"][0]["review_note"] = "Updated assessment of the same work"
    second = progress_to_review(data)
    assert second["added_items"] == 0
    assert (
        len(second["analysis_input"]["review"]["added_evidence"])
        == first["added_items"]
    )
    assert all(
        e["result"] == "Updated assessment of the same work"
        for e in second["analysis_input"]["review"]["added_evidence"]
    )


def test_research_is_normalized_and_missing_duration_is_not_zero(tmp_path):
    result = build_research(str(tmp_path / "research.sqlite"))
    assert result["sample_size"] == 8
    assert (
        next(r for r in result["results"]["skill_mentions"] if r["skill"] == "sql")[
            "descriptions"
        ]
        == 6
    )
    complete = result["results"]["resource_completeness"][0]
    assert complete["duration_needs_assumption"] == 2
    assert all(r["provider_fee"] == 0 for r in result["learning_resources"])


def test_consent_backfill_leadtime_and_learning_uncertainty():
    data = resource("workforce_demo")
    data["require_consent"] = True
    for employee in data["employees"]:
        employee.pop("consent", None)
    assert allocate_workforce(data)["scenarios"]["internal_only"]["filled"] == 0
    for employee in data["employees"]:
        employee.update(consent="met", backfill_cost=50)
    result = allocate_workforce(data)["scenarios"]["hybrid"]
    assert result["cash_cost"] == 1600
    assert sum(a["cost_components"]["backfill"] for a in result["assignments"]) == 200
    data["horizon_days"] = 10
    for role in data["roles"]:
        role.update(internal_lead_days=11, external_lead_days=11, vacancy_daily_cost=2)
    result = allocate_workforce(data)["scenarios"]["hybrid"]
    assert result["filled"] == 0 and result["economic_cost"] == 80
    data = resource("workforce_demo")
    data["training_effect_multiplier"] = 0
    assert allocate_workforce(data)["scenarios"]["internal_only"]["filled"] == 2


@pytest.mark.skipif(
    importlib.util.find_spec("scipy") is None, reason="optional optimization extra"
)
def test_milp_matches_exact_and_medium_costs_reconcile():
    data = resource("workforce_demo")
    data["roles"][0].update(
        priority=3, vacancy_daily_cost=10, internal_lead_days=1, external_lead_days=5
    )
    exact = allocate_workforce(data)
    data["solver"] = "milp"
    mixed = allocate_workforce(data)
    for name, expected in exact["scenarios"].items():
        actual = mixed["scenarios"][name]
        assert (
            actual["filled_priority"],
            actual["economic_cost"],
            actual["internal_moves"],
        ) == (
            expected["filled_priority"],
            expected["economic_cost"],
            expected["internal_moves"],
        )
    business = allocate_workforce(resource("workforce_business_demo"))["scenarios"][
        "hybrid"
    ]
    assert (business["filled"], business["economic_cost"]) == (12, 81040)
    assert (
        sum(sum(a["cost_components"].values()) for a in business["assignments"])
        == business["economic_cost"]
    )
    assert (
        len({a["employee_id"] for a in business["assignments"] if a["employee_id"]})
        == business["internal_moves"]
    )
