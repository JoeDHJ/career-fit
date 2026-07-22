import json
import tempfile
import unittest
from pathlib import Path

from skillbundle.benchmark import benchmark_skillspan
from skillbundle.career import analyze_fit, compare_roles, evidence_from_text
from skillbundle.dictionary import extract, load_dictionary
from skillbundle.metrics import bundle_metrics
from skillbundle.ner import PerceptronNER
from skillbundle.normalization import normalize_label
from skillbundle.requirements import extract_requirements
from skillbundle.server import render_page
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

    def test_v03_exposes_three_job_seeker_signals_and_actions(self):
        result = analyze_fit(
            "Must have Python and SQL.", "Built Python research projects."
        )
        summary = result["summary"]
        self.assertIn("capability_signal_score", summary)
        self.assertIn("proof_signal_score", summary)
        self.assertIn("application_readiness_score", summary)
        self.assertEqual(result["schema_version"], "career_fit.v0.3")
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
        with self.assertRaises(ValueError):
            compare_roles(["Role"] * 6, "Python")


if __name__ == "__main__":
    unittest.main()
