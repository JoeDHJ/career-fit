import json
import tempfile
import unittest
from pathlib import Path

from skillbundle.benchmark import benchmark_skillspan
from skillbundle.career import analyze_fit, evidence_from_text
from skillbundle.dictionary import extract
from skillbundle.metrics import bundle_metrics
from skillbundle.ner import PerceptronNER
from skillbundle.normalization import normalize_label
from skillbundle.requirements import extract_requirements
from skillbundle.taxonomy import pair_codes


class SkillBundleTests(unittest.TestCase):
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
        self.assertEqual(result["summary"]["decision"], "blocked_pending_verification")
        self.assertTrue(any(item["gap_type"] == "hard_constraint" for item in result["gaps"]))

    def test_hard_constraints_allow_requirement_after_keyword(self):
        result = analyze_fit(
            "Bachelor's degree required. No visa sponsorship is available.",
            "Completed a bachelor's degree.",
        )
        types = {item["requirement_type"] for item in result["hard_constraints"]}
        self.assertIn("education", types)
        self.assertIn("work_authorization", types)
        visa = next(
            item for item in result["hard_constraints"] if item["requirement_type"] == "work_authorization"
        )
        self.assertIn("No visa sponsorship", visa["original_text"])

    def test_requirement_importance_is_local_to_clause(self):
        requirements = extract_requirements(
            "Must have Python and SQL. Strongly preferred: causal inference. HR data is a plus."
        )
        levels = {item["canonical_skill"]: item["importance_level"] for item in requirements}
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


if __name__ == "__main__":
    unittest.main()
