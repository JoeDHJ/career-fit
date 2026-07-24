import json
import unittest
from pathlib import Path

from skillbundle.career import analyze_fit, compare_roles


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "jobseeker_scenarios.json"


class JobseekerScenarioTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fifty_profiles_complete_the_real_review_only_flow(self):
        self.assertEqual(len(self.cases), 50)
        for case in self.cases:
            baseline = analyze_fit(case["job_text"], case["candidate_text"])
            reviewed = analyze_fit(
                case["job_text"],
                case["candidate_text"],
                review={"scope": "role_requirements", "applied": True},
            )
            self.assertTrue(
                reviewed["next_actions"],
                msg=f"scenario {case['id']} returned no next action",
            )
            if case["id"] == "long_unemployed":
                self.assertEqual(
                    reviewed["summary"]["analysis_status"],
                    "insufficient_information",
                )
                self.assertIsNone(reviewed["summary"]["evidence_fit_score"])
            if case["id"] == "spanish_profile":
                self.assertTrue(
                    reviewed["summary"]["candidate_language"]["requires_language_review"]
                )
                self.assertIn(
                    "language",
                    " ".join(reviewed["summary"]["analysis_reasons"]).casefold(),
                )
            if case.get("compare_roles"):
                reviewed_evidence = [
                    {
                        "skill_id": item["skill_id"],
                        "canonical_skill": item["canonical_skill"],
                        "analysis_category_code": item.get("analysis_category_code", ""),
                        "evidence_type": "self_reported",
                        "source_text": item.get("source_text", case["candidate_text"]),
                        "evidence_status": "user_confirmed_self_report",
                        "verification_status": "user_declared",
                    }
                    for item in baseline["evidence"]
                    if not item.get("negated") and item.get("skill_id")
                ]
                comparison = compare_roles(
                    case["compare_roles"],
                    case["candidate_text"],
                    evidence=reviewed_evidence,
                    review={"scope": "candidate_evidence", "applied": True},
                )
                self.assertEqual(comparison["role_count"], 2)

    def test_structured_review_route_supports_language_limited_profile(self):
        case = next(item for item in self.cases if item["id"] == "spanish_profile")
        initial = analyze_fit(
            case["job_text"], case["candidate_text"], candidate_language="es"
        )
        evidence = [
            {
                "skill_id": item["skill_id"],
                "canonical_skill": item["canonical_skill"],
                "analysis_category_code": item.get("analysis_category_code", ""),
                "evidence_type": "self_reported",
                "source_text": case["candidate_text"],
                "evidence_status": "user_confirmed_self_report",
                "verification_status": "user_declared",
            }
            for item in initial["requirements"]
            if item.get("skill_id") and not item.get("hard_constraint")
        ]
        reviewed = analyze_fit(
            case["job_text"],
            case["candidate_text"],
            evidence=evidence,
            review={"scope": "role_requirements", "applied": True},
            candidate_language="es",
        )
        self.assertEqual(reviewed["summary"]["analysis_status"], "scored")
        self.assertEqual(reviewed["summary"]["candidate_language"]["requested"], "es")

    def test_background_check_is_a_separate_verification_gate(self):
        case = next(item for item in self.cases if item["id"] == "background_check_gate")
        result = analyze_fit(
            case["job_text"],
            case["candidate_text"],
            review={"scope": "role_requirements", "applied": True},
        )
        gate = next(
            item
            for item in result["hard_constraints"]
            if item["requirement_type"] == "background_check"
        )
        self.assertEqual(gate["status"], "unknown")
        self.assertTrue(
            any(item["action_type"] == "verify_constraint" for item in result["next_actions"])
        )

    def test_zero_gap_result_still_has_application_positioning_action(self):
        result = analyze_fit(
            "Must have Python and SQL.",
            "Built Python and SQL projects.",
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "analysis_category_code": "specific_software_skill",
                    "evidence_type": "work",
                    "source_text": "Built Python projects",
                    "result": "Delivered a working project",
                },
                {
                    "skill_id": "software.sql",
                    "canonical_skill": "SQL",
                    "analysis_category_code": "specific_software_skill",
                    "evidence_type": "work",
                    "source_text": "Built SQL projects",
                    "result": "Delivered a working project",
                },
            ],
            review={"scope": "role_requirements", "applied": True},
        )
        self.assertEqual(result["gaps"], [])
        self.assertEqual(result["next_actions"][0]["action_type"], "tailor_application")

    def test_user_can_add_an_unmapped_requirement_and_then_label_evidence(self):
        result = analyze_fit(
            "Operations role. Must have Python.",
            "Built a permit triage process.",
            review={
                "scope": "role_requirements",
                "applied": True,
                "added_requirements": [
                    {"text": "Permit triage", "importance_level": "must"}
                ],
                "added_evidence": [
                    {
                        "skill_id": "user.custom.002",
                        "canonical_skill": "Permit triage",
                        "evidence_type": "portfolio",
                        "source_text": "Built a permit triage process",
                        "result": "Created a working process",
                    }
                ],
            },
        )
        custom = next(
            item
            for item in result["requirements"]
            if item["canonical_skill"] == "Permit triage"
        )
        self.assertEqual(custom["skill_id"], "user.custom.002")
        self.assertEqual(custom["extraction_method"], "user_added")
        self.assertEqual(custom["status"], "direct")

    def test_user_can_add_a_missed_eligibility_gate(self):
        result = analyze_fit(
            "Operations role. Must have Python.",
            "Built a permit triage process. I am eligible to work in Canada.",
            review={
                "scope": "role_requirements",
                "applied": True,
                "added_requirements": [
                    {"text": "Must be eligible to work in Canada", "importance_level": "must"}
                ]
            },
        )
        gate = next(
            item
            for item in result["hard_constraints"]
            if item["requirement_type"] == "work_authorization"
        )
        self.assertTrue(gate["hard_constraint"])
        self.assertEqual(gate["extraction_method"], "user_added_constraint")
        self.assertEqual(gate["status"], "met")

    def test_external_evidence_requires_a_reviewable_source_text(self):
        with self.assertRaisesRegex(ValueError, "source_text"):
            analyze_fit(
                "Operations role. Must have Python.",
                "Built a project.",
                evidence=[
                    {
                        "skill_id": "software.python",
                        "canonical_skill": "Python",
                        "evidence_type": "work",
                    }
                ],
                review={"scope": "role_requirements", "applied": True},
            )

    def test_language_hint_is_validated(self):
        with self.assertRaisesRegex(ValueError, "candidate_language"):
            analyze_fit(
                "Operations role. Must have Python and SQL.",
                "Built a project with Python and SQL.",
                candidate_language="fr",
            )

    def test_ascii_only_non_english_profile_gets_a_language_warning(self):
        result = analyze_fit(
            "Operations role. Must have Python and SQL.",
            "Trabaje con clientes y prepare informes de datos.",
        )
        self.assertTrue(result["summary"]["candidate_language"]["requires_language_review"])


if __name__ == "__main__":
    unittest.main()
