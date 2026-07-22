from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMReviewError(RuntimeError):
    """Raised when a semantic review cannot be completed safely."""


class LLMNotConfiguredError(LLMReviewError):
    """Raised when no approved model endpoint has been configured."""


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        try:
            timeout_seconds = float(os.getenv("CAREER_FIT_LLM_TIMEOUT_SECONDS", "30"))
        except ValueError:
            timeout_seconds = 30.0
        return cls(
            api_key=os.getenv("CAREER_FIT_LLM_API_KEY", "").strip(),
            base_url=os.getenv("CAREER_FIT_LLM_BASE_URL", "https://api.openai.com/v1")
            .strip()
            .rstrip("/"),
            model=os.getenv("CAREER_FIT_LLM_MODEL", "").strip(),
            timeout_seconds=timeout_seconds,
        )

    @property
    def enabled(self) -> bool:
        local_endpoint = self.base_url.startswith(
            ("http://127.0.0.1", "http://localhost", "http://[::1]")
        )
        return bool(self.model and (self.api_key or local_endpoint))


def _json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise LLMReviewError("The model did not return a JSON object.")
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as error:
        raise LLMReviewError("The model returned invalid JSON.") from error
    if not isinstance(value, dict):
        raise LLMReviewError("The model returned JSON with the wrong shape.")
    return value


class LLMReviewClient:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.config.enabled:
            raise LLMNotConfiguredError(
                "Semantic review is not configured. Set the model endpoint and model name."
            )
        body = json.dumps(
            {
                "model": self.config.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:400]
            raise LLMReviewError(
                f"Semantic review request failed with HTTP {error.code}: {detail}"
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise LLMReviewError(f"Semantic review request failed: {error}") from error
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMReviewError(
                "The model response did not contain message content."
            ) from error
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        return _json_object(str(content))

    def review_fit(
        self,
        job_text: str,
        candidate_text: str,
        requirements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        system = (
            "You are a cautious career-evidence reviewer. Use only the supplied job "
            "and candidate text. Do not infer protected traits, hiring probability, "
            "or facts not present in the text. Return JSON only with keys: "
            "overall_note and requirements. Each requirements item must contain "
            "requirement, decision, confidence, evidence_quote, rationale, next_step. "
            "decision must be direct, transferable, missing, or uncertain."
        )
        user = json.dumps(
            {
                "job_text": job_text,
                "candidate_text": candidate_text,
                "deterministic_requirements": requirements,
            },
            ensure_ascii=False,
        )
        result = self.complete_json(system, user)
        items = result.get("requirements", [])
        if not isinstance(items, list):
            items = []
        allowed_requirements = {
            str(value).strip()
            for source in requirements
            if isinstance(source, dict)
            for value in (
                source.get("canonical_skill", ""),
                source.get("original_text", ""),
                source.get("requirement", ""),
            )
            if str(value).strip()
        }
        valid_decisions = {"direct", "transferable", "missing", "uncertain"}
        cleaned = []
        for item in items[:30]:
            if not isinstance(item, dict):
                continue
            requirement = str(item.get("requirement", "")).strip()
            if allowed_requirements and requirement not in allowed_requirements:
                continue
            decision = str(item.get("decision", "uncertain")).lower()
            if decision not in valid_decisions:
                decision = "uncertain"
            try:
                confidence = min(1.0, max(0.0, float(item.get("confidence", 0))))
            except (TypeError, ValueError):
                confidence = 0.0
            cleaned.append(
                {
                    "requirement": requirement[:240],
                    "decision": decision,
                    "confidence": confidence,
                    "evidence_quote": str(item.get("evidence_quote", ""))[:500],
                    "rationale": str(item.get("rationale", ""))[:800],
                    "next_step": str(item.get("next_step", ""))[:500],
                }
            )
        return {
            "overall_note": str(result.get("overall_note", ""))[:1200],
            "requirements": cleaned,
        }
