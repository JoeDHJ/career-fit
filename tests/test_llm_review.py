import unittest

from skillbundle.llm_review import (
    LLMConfig,
    LLMNotConfiguredError,
    LLMReviewClient,
    _redact_text,
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

    def test_remote_endpoint_requires_https_and_exact_local_host(self):
        self.assertFalse(
            LLMConfig("key", "http://example.test/v1", "model").enabled
        )
        self.assertFalse(
            LLMConfig("key", "http://localhost.evil/v1", "model").enabled
        )
        self.assertTrue(
            LLMConfig("key", "https://example.test/v1", "model").enabled
        )
        self.assertTrue(
            LLMConfig("", "http://127.0.0.1:9000/v1", "model").enabled
        )

    def test_remote_review_redacts_common_direct_identifiers(self):
        redacted = _redact_text(
            "Contact worker@example.com or 415-555-0199; SSN 123-45-6789; "
            "portfolio https://example.com/u/name."
        )
        self.assertNotIn("worker@example.com", redacted)
        self.assertNotIn("415-555-0199", redacted)
        self.assertNotIn("123-45-6789", redacted)
        self.assertNotIn("https://example.com", redacted)

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
