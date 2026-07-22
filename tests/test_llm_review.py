import unittest

from skillbundle.llm_review import (
    LLMConfig,
    LLMNotConfiguredError,
    LLMReviewClient,
    _json_object,
)


class FakeReviewClient(LLMReviewClient):
    def __init__(self, response):
        super().__init__(LLMConfig("test-key", "https://example.test/v1", "test-model"))
        self.response = response

    def complete_json(self, system_prompt, user_prompt):
        return self.response


class LLMReviewTests(unittest.TestCase):
    def test_json_object_accepts_code_fence(self):
        self.assertEqual(
            _json_object('```json\n{"decision":"uncertain"}\n```'),
            {"decision": "uncertain"},
        )

    def test_disabled_client_fails_closed(self):
        client = LLMReviewClient(LLMConfig("", "https://example.test/v1", ""))
        with self.assertRaises(LLMNotConfiguredError):
            client.complete_json("system", "user")

    def test_fit_review_sanitizes_decision_and_limits_confidence(self):
        client = FakeReviewClient(
            {
                "overall_note": "Use the result as a verification aid.",
                "requirements": [
                    {
                        "requirement": "Python",
                        "decision": "certainly_met",
                        "confidence": 2,
                        "evidence_quote": "Built Python pipelines.",
                        "rationale": "Direct evidence.",
                        "next_step": "Show one project outcome.",
                    }
                ],
            }
        )
        result = client.review_fit(
            "Must have Python.",
            "Built Python pipelines.",
            [{"canonical_skill": "Python"}],
        )
        item = result["requirements"][0]
        self.assertEqual(item["decision"], "uncertain")
        self.assertEqual(item["confidence"], 1.0)
        self.assertEqual(item["requirement"], "Python")


if __name__ == "__main__":
    unittest.main()
