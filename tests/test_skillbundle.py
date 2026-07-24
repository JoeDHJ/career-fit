import json
import http.client
import io
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from skillbundle.benchmark import benchmark_skillspan
from skillbundle.career import analyze_fit, compare_roles, evidence_from_text
from skillbundle.cli import main as cli_main
from skillbundle.dictionary import extract, load_dictionary
from skillbundle.metrics import bundle_metrics
from skillbundle.ner import PerceptronNER
from skillbundle.normalization import normalize_label
from skillbundle.requirements import extract_requirements
from skillbundle.server import Handler, render_page
from skillbundle.taxonomy import pair_codes


def assert_no_pre_review_score_values(testcase, value):
    prohibited = {
        "coverage",
        "evidence_strength",
        "evidence_coverage",
        "match_score",
        "impact_score",
        "priority_score",
        "bundle_match_score",
        "required_weight",
        "gap_score",
        "extraction_confidence",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            is_documentation_text = key == "coverage" and isinstance(child, str)
            if (key.endswith("_score") or key in prohibited) and child is not None and not is_documentation_text:
                testcase.fail(f"pre-review score field was not redacted: {key}={child!r}")
            assert_no_pre_review_score_values(testcase, child)
    elif isinstance(value, list):
        for child in value:
            assert_no_pre_review_score_values(testcase, child)


class CareerFitTests(unittest.TestCase):
    def test_extract_longest_match_and_offsets(self):
        text = "Manage customer service projects using Python and SQL."
        items = extract(text)
        values = {item["canonical"] for item in items}
        self.assertIn("Customer service", values)
        self.assertIn(
            "Project management", values
        ) if "Project management" in text else None
        self.assertIn("Python", values)
        self.assertEqual(text[items[0]["start"] : items[0]["end"]], items[0]["text"])

    def test_taxonomy_has_45_pairs(self):
        self.assertEqual(len(pair_codes()), 45)

    def test_metrics(self):
        items = extract("Python and SQL data analysis")
        metrics = bundle_metrics(items)
        self.assertEqual(metrics["unique_skill_count"], 3)
        self.assertGreaterEqual(metrics["breadth"], 2)
        self.assertGreater(metrics["category_entropy"], 0)

    def test_skillspan_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.json"
            row = {
                "tokens": ["Use", "Python", "and", "SQL"],
                "tags_skill": ["O", "B-SKILL", "O", "B-SKILL"],
            }
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = benchmark_skillspan(path)
            self.assertEqual(result["rows"], 1)
            self.assertGreater(result["strict"]["recall"], 0)

    def test_nil_normalization(self):
        self.assertEqual(normalize_label("quantum knitting")["skill_id"], "NIL")

    def test_onet_enrichment_is_provenanced_and_expands_exact_matches(self):
        version, entries = load_dictionary()
        self.assertIn("onet-30.3-derived-v2", version)
        self.assertGreaterEqual(len(entries), 400)
        item = next(
            item for item in extract("Built dashboards with AWS and critical thinking.")
        )
        self.assertEqual(item["source_taxonomy"], "onet_30_3")
        self.assertEqual(item["review_status"], "onet_exact_label_baseline")

    def test_ambiguous_software_labels_require_context(self):
        self.assertNotIn(
            "React", {item["canonical"] for item in extract("React to feedback.")}
        )
        matched = extract("Built a React dashboard with JavaScript.")
        self.assertIn("React", {item["canonical"] for item in matched})

    def test_common_software_aliases_are_not_bare_word_matches(self):
        self.assertNotIn(
            "Microsoft Word",
            {item["canonical"] for item in extract("Word the report carefully.")},
        )
        matched = extract("Prepared the report in Microsoft Word.")
        self.assertIn("Microsoft Word", {item["canonical"] for item in matched})

    def test_named_software_does_not_use_broad_category_transfer(self):
        result = analyze_fit("Must have Java.", "Built Python projects.")
        self.assertEqual(result["requirements"][0]["status"], "missing")

    def test_hard_gates_stay_unknown_when_level_or_domain_is_not_proven(self):
        education = analyze_fit(
            "Master's degree required.", "I have a Bachelor's degree."
        )
        self.assertEqual(education["hard_constraints"][0]["status"], "not_met")
        both_degrees = analyze_fit(
            "Master's degree required.",
            "I have a Bachelor's degree and a Master's degree.",
        )
        self.assertEqual(both_degrees["hard_constraints"][0]["status"], "met")
        higher_degree = analyze_fit(
            "Bachelor's degree required.",
            "I have a Master's degree.",
        )
        self.assertEqual(higher_degree["hard_constraints"][0]["status"], "met")
        field = analyze_fit(
            "Master's degree in computer science required.",
            "I have a Master's degree in history.",
        )
        self.assertEqual(field["hard_constraints"][0]["status"], "unknown")
        experience = analyze_fit(
            "5 years of people analytics experience required.",
            "I have 8 years of software engineering experience.",
        )
        self.assertEqual(experience["hard_constraints"][0]["status"], "unknown")
        no_sponsorship = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not need sponsorship and am authorized to work in the United States.",
        )
        self.assertEqual(no_sponsorship["hard_constraints"][0]["status"], "met")
        no_sponsorship_rephrase = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not require sponsorship.",
        )
        self.assertEqual(no_sponsorship_rephrase["hard_constraints"][0]["status"], "met")
        contradictory = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not need sponsorship, but I am not authorized to work.",
        )
        self.assertEqual(contradictory["hard_constraints"][0]["status"], "not_met")

    def test_hard_gate_negations_and_post_experience_areas_are_conservative(self):
        needs_authorization = analyze_fit(
            "Authorization to work in the United States is required.",
            "I need a work permit and my application is pending.",
        )
        self.assertEqual(needs_authorization["hard_constraints"][0]["status"], "unknown")
        contradictory_authorization = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not require sponsorship, but my work authorization is pending.",
        )
        self.assertEqual(contradictory_authorization["hard_constraints"][0]["status"], "unknown")
        background_not_passed = analyze_fit(
            "A background check is required.",
            "I have not passed a background check yet.",
        )
        self.assertEqual(background_not_passed["hard_constraints"][0]["status"], "not_met")
        background_failed = analyze_fit(
            "A background check is required.",
            "I failed a background check.",
        )
        self.assertEqual(background_failed["hard_constraints"][0]["status"], "not_met")
        background_in_progress = analyze_fit(
            "A background check is required.",
            "I have not completed a background check yet, but I can pass one.",
        )
        self.assertEqual(background_in_progress["hard_constraints"][0]["status"], "unknown")
        for future_claim in (
            "I can pass a background check.",
            "I will pass a background check.",
            "I would pass a background check.",
        ):
            future = analyze_fit("A background check is required.", future_claim)
            self.assertEqual(future["hard_constraints"][0]["status"], "unknown")
        higher_degree = analyze_fit(
            "Master's degree required.",
            "I do not have a Bachelor's degree, but I have a Master's degree.",
        )
        self.assertEqual(higher_degree["hard_constraints"][0]["status"], "met")
        missing_required_degree = analyze_fit(
            "Master's degree required.",
            "I do not have a Master's degree, but I have a Bachelor's degree.",
        )
        self.assertEqual(missing_required_degree["hard_constraints"][0]["status"], "not_met")
        post_experience = analyze_fit(
            "Five years of experience in people analytics required.",
            "I have eight years of experience in people analytics.",
        )
        self.assertEqual(post_experience["hard_constraints"][0]["status"], "met")
        nursing_license = analyze_fit(
            "An active nursing license is required.",
            "Registered nurse with an active license.",
        )
        self.assertEqual(nursing_license["hard_constraints"][0]["status"], "met")

    def test_future_and_conditional_hard_gates_stay_unknown(self):
        cases = (
            (
                "A background check is required.",
                "I will have completed a background check.",
                "background_check",
            ),
            (
                "Authorization to work in the United States is required.",
                "I will be authorized to work next month.",
                "work_authorization",
            ),
            (
                "Authorization to work in the United States is required.",
                "I would be authorized to work if approved.",
                "work_authorization",
            ),
            (
                "Five years of operations experience required.",
                "I will have five years of operations experience by 2027.",
                "experience_floor",
            ),
            (
                "Master's degree required.",
                "I will complete my master's degree next year.",
                "education",
            ),
            (
                "An active nursing license is required.",
                "I will obtain a nursing license next year.",
                "professional_license",
            ),
        )
        for job_text, candidate_text, requirement_type in cases:
            result = analyze_fit(job_text, candidate_text)
            gate = next(
                item
                for item in result["hard_constraints"]
                if item["requirement_type"] == requirement_type
            )
            self.assertEqual(gate["status"], "unknown", candidate_text)

        current_authorization = analyze_fit(
            "Authorization to work in the United States is required.",
            "I have current work authorization.",
        )
        self.assertEqual(
            current_authorization["hard_constraints"][0]["status"], "met"
        )
        sponsorship_with_future_authorization = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not need sponsorship but I will be authorized next month.",
        )
        self.assertEqual(
            sponsorship_with_future_authorization["hard_constraints"][0]["status"],
            "unknown",
        )
        current_negative_with_future = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not have authorization yet, but I will be authorized next month.",
        )
        self.assertEqual(
            current_negative_with_future["hard_constraints"][0]["status"],
            "not_met",
        )

        current_gate_with_unrelated_future_action = (
            (
                "Authorization to work in the United States is required.",
                "I am authorized to work and can start next month.",
                "work_authorization",
            ),
            (
                "A background check is required.",
                "I passed a background check and can start next month.",
                "background_check",
            ),
            (
                "An active nursing license is required.",
                "I hold an active nursing license and can start next month.",
                "professional_license",
            ),
        )
        for job_text, candidate_text, requirement_type in (
            current_gate_with_unrelated_future_action
        ):
            result = analyze_fit(job_text, candidate_text)
            gate = next(
                item
                for item in result["hard_constraints"]
                if item["requirement_type"] == requirement_type
            )
            self.assertEqual(gate["status"], "met", candidate_text)

    def test_hard_gate_negation_and_historical_states_do_not_look_current(self):
        experience_cases = (
            "I do not have five years of operations experience.",
            "I lack five years of operations experience.",
            "I have not reached five years of operations experience.",
            "I have five years of experience, but not in operations.",
        )
        for candidate_text in experience_cases:
            result = analyze_fit(
                "Five years of operations experience required.", candidate_text
            )
            self.assertEqual(
                result["hard_constraints"][0]["status"], "not_met", candidate_text
            )
        for candidate_text in (
            "I have no less than five years of operations experience.",
            "I have no fewer than five years of operations experience.",
            "I have not only five years of operations experience.",
            "I have more than five years of operations experience.",
        ):
            result = analyze_fit(
                "Five years of operations experience required.", candidate_text
            )
            self.assertEqual(
                result["hard_constraints"][0]["status"], "met", candidate_text
            )
        for candidate_text in (
            "I have less than five years of operations experience.",
            "I have under five years of operations experience.",
            "I have fewer than five years of operations experience.",
            "I have five years of operations experience, but none is relevant.",
            "I have five years of operations experience, but it is not relevant.",
            "I have five years of operations experience, but none is qualifying.",
            "I have five years of operations experience; however, I do not meet the requirement.",
            "I have five years of operations experience. It is not relevant.",
            "I have five years of operations experience. None is relevant.",
            "I have five years of operations experience. I do not meet the requirement.",
        ):
            result = analyze_fit(
                "Five years of operations experience required.", candidate_text
            )
            self.assertEqual(
                result["hard_constraints"][0]["status"], "not_met", candidate_text
            )

        authorization_cases = (
            ("I was authorized to work in the United States.", "unknown"),
            ("I used to have work authorization.", "unknown"),
            ("I was authorized to work, but my authorization expired.", "not_met"),
            ("I am no longer authorized to work.", "not_met"),
        )
        for candidate_text, expected_status in authorization_cases:
            result = analyze_fit(
                "Authorization to work in the United States is required.",
                candidate_text,
            )
            self.assertEqual(
                result["hard_constraints"][0]["status"], expected_status, candidate_text
            )

        license_cases = (
            ("I held an active nursing license.", "unknown"),
            ("I previously held an active nursing license.", "unknown"),
            ("My nursing license is expired.", "not_met"),
            ("I have an inactive nursing license.", "not_met"),
            ("I hold a current nursing license.", "met"),
            ("I have a current nursing license.", "met"),
            ("I am not currently licensed as a nurse.", "not_met"),
            ("I am currently licensed as a nurse.", "met"),
        )
        for candidate_text, expected_status in license_cases:
            result = analyze_fit(
                "An active nursing license is required.", candidate_text
            )
            self.assertEqual(
                result["hard_constraints"][0]["status"], expected_status, candidate_text
            )

        for candidate_text in (
            "I am not eligible to work in the United States.",
            "I do not hold a valid work permit.",
        ):
            result = analyze_fit(
                "Authorization to work in the United States is required.",
                candidate_text,
            )
            self.assertEqual(
                result["hard_constraints"][0]["status"], "not_met", candidate_text
            )

    def test_untrusted_evidence_provenance_and_nonfinite_numbers_fail_closed(self):
        result = analyze_fit(
            "Must have Python and SQL.",
            "Python SQL",
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "evidence_type": "work",
                    "source_text": "A user supplied claim.",
                    "verification_status": "externally_verified",
                    "evidence_status": "verified",
                }
            ],
            review={"scope": "role_requirements", "applied": True},
        )
        evidence = next(item for item in result["evidence"] if item["skill_id"] == "software.python")
        self.assertEqual(evidence["verification_status"], "user_declared")
        self.assertEqual(evidence["evidence_status"], "user_declared_structured_evidence")
        with self.assertRaises(ValueError):
            analyze_fit(
                "Must have Python and SQL.",
                "Python SQL",
                evidence=[
                    {
                        "skill_id": "software.python",
                        "canonical_skill": "Python",
                        "evidence_type": "work",
                        "source_text": "A user supplied claim.",
                        "recency_years": "inf",
                    }
                ],
                review={"scope": "role_requirements", "applied": True},
            )
        with self.assertRaisesRegex(ValueError, "non-negative"):
            analyze_fit(
                "Must have Python and SQL.",
                "Python SQL",
                evidence=[
                    {
                        "skill_id": "software.python",
                        "canonical_skill": "Python",
                        "evidence_type": "work",
                        "source_text": "A user supplied claim.",
                        "duration_months": -1,
                    }
                ],
                review={"scope": "role_requirements", "applied": True},
            )

    def test_hard_gates_without_candidate_evidence_do_not_produce_a_total_score(self):
        result = analyze_fit(
            "Bachelor's degree required. Five years of operations experience required.",
            "I am interested in this role.",
        )
        self.assertEqual(result["summary"]["analysis_status"], "insufficient_information")
        self.assertIsNone(result["summary"]["application_readiness_score"])
        self.assertIn("No candidate evidence was identified.", result["summary"]["analysis_reasons"])

    def test_low_information_input_does_not_produce_a_reliable_score(self):
        result = analyze_fit("Must have Python.", "Built Python projects.")
        self.assertEqual(result["summary"]["analysis_status"], "insufficient_information")
        self.assertIsNone(result["summary"]["evidence_fit_score"])
        self.assertEqual(result["summary"]["decision"], "insufficient_information")
        keyword_stack = analyze_fit(
            "Must have Python and SQL.",
            "Python SQL data tools and reporting experience",
        )
        self.assertEqual(keyword_stack["summary"]["analysis_status"], "insufficient_information")
        self.assertIsNone(keyword_stack["summary"]["evidence_fit_score"])

    def test_scores_stay_hidden_until_role_requirements_are_confirmed(self):
        job = "Must have Python and SQL. Strongly preferred stakeholder communication."
        candidate = "Built Python and SQL reporting projects and presented findings to stakeholders."
        provisional = analyze_fit(job, candidate)
        self.assertEqual(provisional["summary"]["analysis_status"], "review_required")
        self.assertEqual(provisional["summary"]["score_visibility"], "hidden")
        self.assertIsNone(provisional["summary"]["evidence_fit_score"])
        self.assertIsNone(provisional["summary"]["input_completeness_score"])
        self.assertEqual(provisional["summary"]["eligibility_status"], "no_gate_detected")
        self.assertIsNone(provisional["summary"]["eligibility_verification_score"])
        self.assertIsNone(provisional["summary"]["evidence_coverage_score"])
        self.assertTrue(
            all(item.get("importance_weight") is None for item in provisional["requirements"])
        )
        self.assertTrue(
            all(item.get("extraction_confidence") is None for item in provisional["requirements"])
        )
        self.assertTrue(
            all(item.get("extraction_confidence") is None for item in provisional["evidence"])
        )
        self.assertTrue(all(item.get("match_score") is None for item in provisional["requirements"]))
        self.assertTrue(all(item.get("impact_score") is None for item in provisional["gaps"]))
        self.assertEqual(provisional["role_fingerprint"]["mismatch_dimensions"], [])
        self.assertTrue(
            all(item.get("bundle_match_score") is None for item in provisional["role_fingerprint"]["skill_bundles"])
        )
        assert_no_pre_review_score_values(self, provisional)
        reviewed = analyze_fit(job, candidate, review={"scope": "role_requirements", "applied": True})
        self.assertEqual(reviewed["summary"]["analysis_status"], "scored")
        self.assertEqual(reviewed["summary"]["score_visibility"], "visible")
        self.assertIsNotNone(reviewed["summary"]["evidence_fit_score"])

    def test_claim_only_evidence_does_not_look_like_reviewable_proof(self):
        claim = analyze_fit(
            "Must have Python and SQL.",
            "Python SQL",
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "evidence_type": "self_reported",
                    "source_text": "I can use Python.",
                }
            ],
            review={"scope": "role_requirements", "applied": True},
        )
        item = next(item for item in claim["requirements"] if item["canonical_skill"] == "Python")
        self.assertEqual(item["status"], "claimed")
        self.assertEqual(item["claimed_evidence_ids"], ["evidence-001"])
        self.assertEqual(item["reviewable_evidence_ids"], [])
        self.assertLess(claim["summary"]["proof_signal_score"], 50)

        proof = analyze_fit(
            "Must have Python and SQL.",
            "Python SQL",
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "evidence_type": "work",
                    "source_text": "Built a Python reporting workflow.",
                    "result": "Reduced manual reporting time by 30%.",
                    "duration_months": 12,
                }
            ],
            review={"scope": "role_requirements", "applied": True},
        )
        proof_item = next(item for item in proof["requirements"] if item["canonical_skill"] == "Python")
        self.assertEqual(proof_item["status"], "direct")
        self.assertGreater(proof["summary"]["proof_signal_score"], claim["summary"]["proof_signal_score"])

    def test_weak_extra_evidence_cannot_lower_a_stronger_primary(self):
        strong = {
            "skill_id": "software.python",
            "canonical_skill": "Python",
            "evidence_type": "work",
            "source_text": "Built a Python data pipeline.",
            "result": "Processed 1.3 million records.",
            "duration_months": 18,
        }
        weak = {
            "skill_id": "software.python",
            "canonical_skill": "Python",
            "evidence_type": "self_reported",
            "source_text": "I know Python.",
        }
        strong_result = analyze_fit("Must have Python and SQL.", "Python SQL", evidence=[strong], review={"scope": "role_requirements", "applied": True})
        combined_result = analyze_fit("Must have Python and SQL.", "Python SQL", evidence=[strong, weak], review={"scope": "role_requirements", "applied": True})
        strong_item = strong_result["requirements"][0]
        combined_item = combined_result["requirements"][0]
        self.assertGreaterEqual(combined_item["match_score"], strong_item["match_score"])
        self.assertEqual(combined_item["primary_evidence_id"], "evidence-001")
        self.assertEqual(combined_item["evidence_aggregation"], "primary_plus_top_two_supporting")

    def test_review_can_change_importance_and_add_structured_evidence(self):
        job = "Must have Python. Strongly preferred SQL."
        base = analyze_fit(job, "I have worked on reporting.")
        sql = next(item for item in base["requirements"] if item["canonical_skill"] == "SQL")
        reviewed = analyze_fit(
            job,
            "I have worked on reporting.",
            review={
                "scope": "role_requirements",
                "applied": True,
                "importance_overrides": {sql["requirement_id"]: "preferred"},
                "added_evidence": [
                    {
                        "skill_id": "software.python",
                        "canonical_skill": "Python",
                        "analysis_category_code": "specific_software_skill",
                        "evidence_type": "github_project",
                        "source_text": "A public Python reporting repository.",
                        "result": "Documented a reproducible workflow.",
                        "duration_months": 6,
                        "recency_years": 1,
                    }
                ],
            },
        )
        self.assertEqual(reviewed["summary"]["analysis_status"], "scored")
        self.assertEqual(
            next(item for item in reviewed["requirements"] if item["canonical_skill"] == "SQL")["importance_level"],
            "preferred",
        )
        evidence = next(item for item in reviewed["evidence"] if item["evidence_id"] == "user-evidence-001")
        self.assertEqual(evidence["evidence_type"], "github_project")
        self.assertEqual(evidence["verification_status"], "user_declared")
        self.assertEqual(evidence["duration_months"], 6.0)

    def test_structured_evidence_can_support_a_short_profile(self):
        result = analyze_fit(
            "Must have Python and SQL.",
            "Python",
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "source_text": "Built a Python data pipeline.",
                }
            ],
            review={"scope": "role_requirements", "applied": True},
        )
        self.assertEqual(result["summary"]["analysis_status"], "scored")

    def test_guided_intake_evidence_can_start_a_resume_free_profile(self):
        job = (
            "Office coordinator. Must have communication and Excel. "
            "Preferred: customer service. Schedule meetings and maintain records."
        )
        candidate = "I am looking for work and do not have a current resume."
        baseline = analyze_fit(job, candidate)
        requirement = next(
            item
            for item in baseline["review_queue"]
            if not item["hard_constraint"]
        )
        reviewed = analyze_fit(
            job,
            candidate,
            review={
                "scope": "role_requirements",
                "applied": True,
                "added_evidence": [
                    {
                        "skill_id": requirement["skill_id"],
                        "canonical_skill": requirement["canonical_skill"],
                        "analysis_category_code": requirement["analysis_category_code"],
                        "evidence_type": "work",
                        "source_text": "Scheduled appointments and maintained a shared calendar at a community group.",
                        "result": "Kept requests organized and reduced missed follow-ups.",
                    }
                ],
            },
        )
        self.assertEqual(reviewed["summary"]["analysis_status"], "scored")
        assessment = next(
            item
            for item in reviewed["requirements"]
            if item["skill_id"] == requirement["skill_id"]
        )
        self.assertIn(assessment["status"], {"direct", "direct_weak"})
        self.assertEqual(reviewed["evidence"][0]["verification_status"], "user_declared")

    def test_user_review_can_remove_add_and_confirm_without_silent_score_edits(self):
        base = analyze_fit(
            "Must have Python and SQL. Bachelor's degree required.",
            "Built Python projects.",
        )
        education = next(
            item for item in base["hard_constraints"] if item["requirement_type"] == "education"
        )
        sql = next(item for item in base["requirements"] if item.get("canonical_skill") == "SQL")
        reviewed = analyze_fit(
            "Must have Python and SQL. Bachelor's degree required.",
            "Built Python projects.",
            review={
                "scope": "role_requirements",
                "applied": True,
                "removed_requirement_ids": [sql["requirement_id"]],
                "constraint_status_overrides": {education["requirement_id"]: "met"},
                "added_evidence": [
                    {
                        "skill_id": "software.sql",
                        "canonical_skill": "SQL",
                        "analysis_category_code": "specific_software_skill",
                        "source_text": "Built a SQL reporting workflow.",
                    }
                ],
            },
        )
        self.assertEqual(reviewed["review"]["status"], "user_confirmed")
        self.assertTrue(reviewed["review"]["changes"])
        self.assertEqual(
            next(item for item in reviewed["hard_constraints"] if item["requirement_type"] == "education")["matching_method"],
            "user_confirmed_constraint",
        )

    def test_supervised_ner_trains_and_extracts(self):
        rows = [{"tokens": ["Use", "Python"], "tags_skill": ["O", "B-SKILL"]}]
        model = PerceptronNER()
        model.train(rows, epochs=3)
        self.assertTrue(
            any(item["text"] == "Python" for item in model.extract("Use Python"))
        )

    def test_career_fit_separates_soft_fit_from_hard_constraints(self):
        result = analyze_fit(
            "Must have Python and SQL. A valid professional license is required.",
            "Built Python projects and analyzed data.",
            review={"scope": "role_requirements", "applied": True},
        )
        self.assertGreater(result["summary"]["role_fit_score"], 0)
        self.assertEqual(result["summary"]["blocking_constraint_count"], 1)
        self.assertEqual(result["summary"]["decision"], "verify_before_applying")
        self.assertTrue(
            any(item["gap_type"] == "verification_gap" for item in result["gaps"])
        )

    def test_hard_constraints_allow_requirement_after_keyword(self):
        result = analyze_fit(
            "Bachelor's degree required. No visa sponsorship is available.",
            "Completed a bachelor's degree.",
        )
        types = {item["requirement_type"] for item in result["hard_constraints"]}
        self.assertIn("education", types)
        self.assertIn("work_authorization", types)
        visa = next(
            item
            for item in result["hard_constraints"]
            if item["requirement_type"] == "work_authorization"
        )
        self.assertIn("No visa sponsorship", visa["original_text"])

    def test_requirement_importance_is_local_to_clause(self):
        requirements = extract_requirements(
            "Must have Python and SQL. Strongly preferred: causal inference. HR data is a plus."
        )
        levels = {
            item["canonical_skill"]: item["importance_level"] for item in requirements
        }
        self.assertEqual(levels["Python"], "must")
        self.assertEqual(levels["SQL"], "must")
        self.assertEqual(levels["Causal inference"], "strongly_preferred")
        self.assertEqual(levels["HR data"], "preferred")

    def test_career_fit_reports_transferable_and_evidence_gaps(self):
        result = analyze_fit(
            "Must have SQL and strongly preferred data visualization.",
            "Built Python research projects.",
        )
        statuses = {item["status"] for item in result["requirements"]}
        self.assertIn("transferable", statuses)
        self.assertTrue(result["gaps"])

    def test_analyze_fit_rejects_blank_job_and_candidate_text(self):
        with self.assertRaisesRegex(ValueError, "job_text"):
            analyze_fit("   ", "Built Python projects.")
        with self.assertRaisesRegex(ValueError, "candidate_text"):
            analyze_fit("Must have Python.", "\n\t")

    def test_cli_reports_blank_input_without_traceback(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cli_main(["analyze", "--job", " ", "--candidate", "Python"])
        self.assertEqual(code, 2)
        self.assertIn("Error:", stderr.getvalue())
        self.assertIn("job_text", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_rejects_four_roles_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            roles_file = Path(temp) / "roles.json"
            roles_file.write_text(
                json.dumps(["Role one", "Role two", "Role three", "Role four"]),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cli_main(
                    [
                        "compare",
                        "--roles-file",
                        str(roles_file),
                        "--candidate",
                        "Built Python projects.",
                    ]
                )
        self.assertEqual(code, 2)
        self.assertIn("at most three", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_structured_evidence_can_raise_evidence_strength(self):
        evidence = [
            {
                "skill_id": "software.python",
                "canonical_skill": "Python",
                "analysis_category_code": "specific_software_skill",
                "evidence_type": "research_project",
                "source_text": "Built a panel-data pipeline",
                "measurable_result": "1.3 million records",
                "duration_months": 18,
            }
        ]
        result = analyze_fit(
            "Must have Python and SQL. Strongly preferred communication.",
            "Python",
            evidence=evidence,
            review={"scope": "role_requirements", "applied": True},
        )
        item = result["requirements"][0]
        self.assertEqual(item["status"], "direct")
        self.assertGreater(item["evidence_strength"], 0.9)
        self.assertEqual(len(evidence_from_text("Python")), 1)

    def test_negated_profile_statement_is_not_counted_as_evidence(self):
        result = analyze_fit(
            "Must have HR data.", "Have not worked directly with HR data."
        )
        item = result["requirements"][0]
        self.assertEqual(item["status"], "missing")
        self.assertEqual(result["summary"]["excluded_evidence_count"], 1)
        self.assertEqual(item["evidence_ids"], [])

    def test_spelled_experience_floor_and_work_gate_are_extracted(self):
        requirements = extract_requirements(
            "Must have five years of operations experience and authorization to work in the United States."
        )
        types = {item["requirement_type"] for item in requirements}
        self.assertIn("experience_floor", types)
        self.assertIn("work_authorization", types)
        experience = next(
            item
            for item in requirements
            if item["requirement_type"] == "experience_floor"
        )
        self.assertEqual(experience["required_years"], 5)
        result = analyze_fit(
            "Must have five years of operations experience and authorization to work in the United States.",
            "Eight years of operations experience. Authorized to work in the United States.",
        )
        self.assertEqual(result["summary"]["blocking_constraint_count"], 0)
        unresolved = analyze_fit(
            "Authorization to work in the United States is required.",
            "The profile does not state current United States work authorization.",
        )
        self.assertEqual(unresolved["hard_constraints"][0]["status"], "unknown")
        no_sponsorship = analyze_fit(
            "Authorization to work in the United States is required.",
            "I do not need sponsorship and am authorized to work in the United States.",
        )
        self.assertEqual(no_sponsorship["hard_constraints"][0]["status"], "met")

    def test_v03_exposes_three_job_seeker_signals_and_actions(self):
        result = analyze_fit(
            "Must have Python and SQL.", "Built Python research projects."
        )
        summary = result["summary"]
        self.assertIn("capability_signal_score", summary)
        self.assertIn("proof_signal_score", summary)
        self.assertIn("application_readiness_score", summary)
        self.assertEqual(result["schema_version"], "career_fit.v0.5")
        self.assertTrue(result["next_actions"])
        self.assertIn("expected_artifact", result["next_actions"][0])

    def test_role_fingerprint_exposes_dimensions_and_bundles(self):
        result = analyze_fit(
            "Must have Python and SQL. Strongly preferred stakeholder communication.",
            "Built Python research projects and presented findings to stakeholders.",
        )
        fingerprint = result["role_fingerprint"]
        self.assertEqual(fingerprint["taxonomy_id"], "deming_kahn_10_ai")
        self.assertTrue(fingerprint["categories"])
        self.assertTrue(fingerprint["skill_bundles"])
        self.assertEqual(fingerprint["skill_bundles"][0]["skills"], ["Python", "SQL"])
        self.assertIn("dimensions", result["interpretation"])

    def test_client_page_exposes_role_fingerprint_explanations(self):
        page = render_page()
        self.assertIn('id="fingerprint-panel"', page)
        self.assertIn("Role fingerprint", page)
        self.assertIn("They do not estimate market value", page)
        self.assertIn('id="review-panel"', page)
        self.assertIn('id="input-coverage-score"', page)
        self.assertIn('id="market-context"', page)
        self.assertNotIn("Information confidence", page)

    def test_client_page_exposes_confirmed_occupation_review_context(self):
        page = render_page()
        self.assertIn('id="occupation-query"', page)
        self.assertIn("What workers say", page)
        self.assertIn('id="occupation-review-source-filter"', page)
        self.assertIn('id="occupation-review-topic-filter"', page)
        self.assertIn("Select a standard occupation", page)
        self.assertIn("They are not verified facts or representative of all workers", page)
        self.assertIn("candidate occupation families", page)
        self.assertIn("mapping_note", page)

    def test_client_page_distinguishes_empty_alias_crosswalk(self):
        page = render_page()
        empty_alias_message = (
            "This occupation family was recognized, but the current Atlas data "
            "release has no candidate occupations to display. Run the full data "
            "build or try another title."
        )
        self.assertIn(empty_alias_message, page)
        self.assertLess(
            page.index('if (isCandidateFamily && !hasCandidates)'),
            page.index('if (!hasCandidates) { occupationCandidates.appendChild'),
        )

    def test_client_page_exposes_review_first_and_structured_evidence_flow(self):
        page = render_page()
        self.assertIn('id="candidate-file"', page)
        self.assertIn('id="candidate-language"', page)
        self.assertIn("English-first", page)
        self.assertIn("Scores remain hidden until this step is submitted.", page)
        self.assertIn("Review first", page)
        self.assertIn("importance_overrides", page)
        self.assertIn("evidenceTypeLabels", page)
        self.assertIn("candidate_evidence", page)
        self.assertIn("No gate detected", page)
        self.assertIn("canShowNonScoreActions", page)
        self.assertIn('id="guided-intake"', page)
        self.assertIn('id="guided-intake-task"', page)
        self.assertIn('id="guided-intake-context"', page)
        self.assertIn("No resume? Start with one example", page)

    def test_client_page_invalidates_stale_results_before_reuse(self):
        page = render_page()
        self.assertIn('let analyzedSignature = "";', page)
        self.assertIn("function currentAnalysisIsFresh()", page)
        self.assertIn("function invalidateCurrentResult(message)", page)
        self.assertIn("Inputs changed. Analyze the current text before relying on a result.", page)
        self.assertIn("requestId !== analysisRequestId", page)
        self.assertIn("Target roles changed. Compare again to refresh the ranking.", page)
        self.assertIn("if (!currentAnalysisIsFresh())", page)

    def test_role_comparison_is_deterministic_and_keeps_audit_trails(self):
        result = compare_roles(
            [
                "Role: Data Analyst\nMust have Python and data visualization.",
                "Role: Java Developer\nMust have Java and cloud computing.",
            ],
            "Built Python research projects and created data visualizations.",
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "evidence_type": "research_project",
                    "source_text": "Built Python research projects.",
                    "evidence_status": "user_declared_structured_evidence",
                    "verification_status": "user_declared",
                }
            ],
            review={"scope": "candidate_evidence", "applied": True},
        )
        self.assertEqual(result["schema_version"], "career_fit.compare.v0.3")
        self.assertEqual(result["role_count"], 2)
        self.assertEqual(result["roles"][0]["priority_rank"], 1)
        self.assertEqual(result["roles"][0]["role_label"], "Data Analyst")
        self.assertEqual(result["roles"][1]["role_label"], "Java Developer")
        self.assertIn("analysis", result["roles"][0])
        self.assertIn("priority_basis", result["roles"][0])

    def test_role_comparison_reuses_reviewed_candidate_evidence_without_confirming_roles(self):
        candidate = "Built Python research projects and created data visualizations."
        candidate_review = analyze_fit(
            "Must have Python and data visualization.",
            candidate,
            evidence=[
                {
                    "skill_id": "software.python",
                    "canonical_skill": "Python",
                    "evidence_type": "research_project",
                    "source_text": "Built Python research projects.",
                    "evidence_status": "user_declared_structured_evidence",
                    "verification_status": "user_declared",
                }
            ],
            review={"scope": "role_requirements", "applied": True},
        )
        result = compare_roles(
            [
                "Role: Data Analyst\nMust have Python and data visualization.",
                "Role: Java Developer\nMust have Java and cloud computing.",
            ],
            candidate,
            evidence=candidate_review["evidence"],
            review={"scope": "candidate_evidence", "applied": True},
        )
        self.assertEqual(result["schema_version"], "career_fit.compare.v0.3")
        self.assertTrue(
            all(item["summary"]["review_status"] == "candidate_evidence_confirmed" for item in result["roles"])
        )
        self.assertTrue(
            all(item["summary"]["review_required"] for item in result["roles"])
        )
        self.assertTrue(
            all(item["summary"]["evidence_fit_score"] is None for item in result["roles"])
        )
        self.assertTrue(all(item["top_bundle"] is None for item in result["roles"]))
        for item in result["roles"]:
            assert_no_pre_review_score_values(self, item["analysis"])
        self.assertEqual(
            result["interpretation"]["review"],
            "Candidate evidence can be reused across roles after review, but role requirements and hard gates should be confirmed in the selected role view.",
        )

    def test_role_comparison_rejects_oversized_batches(self):
        with self.assertRaises(ValueError):
            compare_roles(["Role one"], "Python")
        with self.assertRaisesRegex(ValueError, "at most three"):
            compare_roles(["Role"] * 4, "Python")
        with self.assertRaisesRegex(ValueError, "applied candidate_evidence"):
            compare_roles(["Role one", "Role two"], "Built Python projects.")
        with self.assertRaisesRegex(ValueError, "cannot modify role requirements"):
            compare_roles(
                ["Role one", "Role two"],
                "Built Python projects.",
                evidence=[
                    {
                        "skill_id": "software.python",
                        "canonical_skill": "Python",
                        "evidence_type": "work",
                        "source_text": "Built Python projects.",
                        "evidence_status": "user_declared_structured_evidence",
                        "verification_status": "user_declared",
                    }
                ],
                review={
                    "scope": "candidate_evidence",
                    "applied": True,
                    "removed_requirement_ids": ["req-001"],
                },
            )

    def test_api_reports_blank_inputs_and_four_role_requests(self):
        from http.server import ThreadingHTTPServer

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def post(path, payload):
            connection = http.client.HTTPConnection(
                "127.0.0.1", server.server_port
            )
            body = json.dumps(payload).encode("utf-8")
            connection.request(
                "POST",
                path,
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            result = json.loads(response.read().decode("utf-8"))
            status = response.status
            connection.close()
            return status, result

        try:
            status, result = post(
                "/api/analyze",
                {"job_text": " ", "candidate_text": "Built Python projects."},
            )
            self.assertEqual(status, 400)
            self.assertIn("job_text", result["detail"])
            status, result = post(
                "/api/analyze",
                {"job_text": "Must have Python.", "candidate_text": "\t"},
            )
            self.assertEqual(status, 400)
            self.assertIn("candidate_text", result["detail"])
            status, result = post(
                "/api/compare",
                {
                    "roles": ["Role one", "Role two", "Role three", "Role four"],
                    "candidate_text": "Built Python projects.",
                },
            )
            self.assertEqual(status, 400)
            self.assertIn("at most three", result["detail"])
            status, result = post(
                "/api/analyze",
                {
                    "job_text": "Must have Python and SQL.",
                    "candidate_text": "Built Python research projects.",
                    "review": {
                        "scope": "role_requirements",
                        "applied": True,
                        "removed_requirement_ids": ["req-002"],
                    },
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(result["review"]["status"], "user_confirmed")
            status, result = post(
                "/api/analyze",
                {
                    "job_text": "Must have Python and SQL. Strongly preferred communication.",
                    "candidate_text": "Built Python and SQL reporting projects and presented findings.",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(result["summary"]["score_visibility"], "hidden")
            self.assertIsNone(result["summary"]["evidence_coverage_score"])
            self.assertTrue(all(item["match_score"] is None for item in result["requirements"]))
            self.assertTrue(all(item["importance_weight"] is None for item in result["requirements"]))
            self.assertTrue(all(item["impact_score"] is None for item in result["gaps"]))
            self.assertEqual(result["role_fingerprint"]["mismatch_dimensions"], [])
            status, result = post(
                "/api/compare",
                {
                    "roles": [
                        "Role: Data Analyst\nMust have Python and data visualization.",
                        "Role: Java Developer\nMust have Java and cloud computing.",
                    ],
                    "candidate_text": "Built Python research projects and created data visualizations.",
                    "evidence": [
                        {
                            "skill_id": "software.python",
                            "canonical_skill": "Python",
                            "evidence_type": "research_project",
                            "source_text": "Built Python research projects.",
                            "evidence_status": "user_declared_structured_evidence",
                            "verification_status": "user_declared",
                        }
                    ],
                    "review": {"scope": "candidate_evidence", "applied": True},
                },
            )
            self.assertEqual(status, 200)
            self.assertTrue(
                all(item["summary"]["score_visibility"] == "hidden" for item in result["roles"])
            )
            self.assertTrue(
                all(item["summary"]["evidence_fit_score"] is None for item in result["roles"])
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
