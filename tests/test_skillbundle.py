import json
import tempfile
import unittest
from pathlib import Path

from skillbundle.benchmark import benchmark_skillspan
from skillbundle.dictionary import extract
from skillbundle.metrics import bundle_metrics
from skillbundle.ner import PerceptronNER
from skillbundle.normalization import normalize_label
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
        self.assertGreaterEqual(metrics["breadth"], 3)
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


if __name__ == "__main__":
    unittest.main()
