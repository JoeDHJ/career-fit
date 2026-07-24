from __future__ import annotations

import json
import unittest
from pathlib import Path

from skillbundle.career import analyze_fit, compare_roles
from skillbundle.resources import read_resource_text


ROOT = Path(__file__).resolve().parents[1]


class ReleaseExampleTests(unittest.TestCase):
    def test_packaged_resources_match_source_config(self):
        for name in (
            "seed_dictionary_en.json",
            "onet_enrichment_en.json",
            "taxonomy_10_ai.json",
        ):
            self.assertEqual(
                read_resource_text(name),
                (ROOT / "config" / name).read_text(encoding="utf-8"),
            )

    def test_documented_single_job_example_is_runnable(self):
        example = ROOT / "examples" / "single_job"
        result = analyze_fit(
            (example / "people_analytics_job.txt").read_text(encoding="utf-8"),
            (example / "candidate_profile.txt").read_text(encoding="utf-8"),
            json.loads((example / "evidence.json").read_text(encoding="utf-8")),
            json.loads((example / "role_review.json").read_text(encoding="utf-8")),
        )

        self.assertEqual(result["schema_version"], "career_fit.v0.5")
        self.assertEqual(result["review"]["status"], "user_confirmed")
        self.assertEqual(result["summary"]["analysis_status"], "scored")
        self.assertIsNotNone(result["summary"]["evidence_fit_score"])

    def test_documented_role_comparison_is_runnable(self):
        example = ROOT / "examples" / "single_job"
        roles = json.loads(
            (ROOT / "examples" / "role_portfolio.json").read_text(encoding="utf-8")
        )
        result = compare_roles(
            roles,
            (example / "candidate_profile.txt").read_text(encoding="utf-8"),
            json.loads((example / "evidence.json").read_text(encoding="utf-8")),
            json.loads(
                (example / "candidate_evidence_review.json").read_text(encoding="utf-8")
            ),
        )

        self.assertEqual(result["schema_version"], "career_fit.compare.v0.3")
        self.assertIn(len(result["roles"]), {2, 3})


if __name__ == "__main__":
    unittest.main()
