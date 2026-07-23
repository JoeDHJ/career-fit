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
        )
        self.assertEqual(result["summary"]["analysis_status"], "scored")

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
        result = analyze_fit("Must have Python.", "Python", evidence=evidence)
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
        self.assertEqual(result["schema_version"], "career_fit.v0.4")
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

    def test_role_comparison_is_deterministic_and_keeps_audit_trails(self):
        result = compare_roles(
            [
                "Role: Data Analyst\nMust have Python and data visualization.",
                "Role: Java Developer\nMust have Java and cloud computing.",
            ],
            "Built Python research projects and created data visualizations.",
        )
        self.assertEqual(result["schema_version"], "career_fit.compare.v0.2")
        self.assertEqual(result["role_count"], 2)
        self.assertEqual(result["roles"][0]["priority_rank"], 1)
        self.assertEqual(result["roles"][0]["role_label"], "Data Analyst")
        self.assertEqual(result["roles"][1]["role_label"], "Java Developer")
        self.assertIn("analysis", result["roles"][0])
        self.assertIn("priority_basis", result["roles"][0])

    def test_role_comparison_rejects_oversized_batches(self):
        with self.assertRaises(ValueError):
            compare_roles(["Role one"], "Python")
        with self.assertRaisesRegex(ValueError, "at most three"):
            compare_roles(["Role"] * 4, "Python")

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
                    "review": {"removed_requirement_ids": ["req-002"]},
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(result["review"]["status"], "user_confirmed")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
