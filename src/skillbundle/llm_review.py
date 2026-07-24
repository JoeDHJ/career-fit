from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


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
        try:
            parsed = urlparse(self.base_url)
            hostname = (parsed.hostname or "").casefold()
        except ValueError:
            return False
        local_endpoint = parsed.scheme == "http" and hostname in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
        secure_endpoint = parsed.scheme == "https" or local_endpoint
        return bool(
            self.model
            and secure_endpoint
            and (self.api_key or local_endpoint)
        )


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-])\d{3}[\s.-]\d{4}(?!\d)"
)
_US_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_URL = re.compile(r"\bhttps?://[^\s<>]+", re.I)
_SUPPORT_LEVELS = {"limited", "moderate", "strong"}


def _support_level(value: object) -> str:
    """Normalize optional model certainty without presenting a probability."""

    label = str(value or "").strip().lower()
    if label in _SUPPORT_LEVELS:
        return label
    try:
        numeric = min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return "limited"
    return "strong" if numeric >= 0.75 else "moderate" if numeric >= 0.4 else "limited"


def _redact_text(value: str) -> str:
    """Remove common direct identifiers before optional remote review."""

    value = _URL.sub("[redacted URL]", value)
    value = _EMAIL.sub("[redacted email]", value)
    value = _PHONE.sub("[redacted phone]", value)
    return _US_SSN.sub("[redacted government ID]", value)


def _redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_payload(item) for key, item in value.items()}
    return value


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
            "requirement, decision, support_level, evidence_quote, rationale, next_step. "
            "decision must be direct, transferable, missing, or uncertain."
        )
        user = json.dumps(
            _redact_payload(
                {
                    "job_text": job_text,
                    "candidate_text": candidate_text,
                    "deterministic_requirements": requirements,
                }
            ),
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
            cleaned.append(
                {
                    "requirement": requirement[:240],
                    "decision": decision,
                    "support_level": _support_level(
                        item.get("support_level", item.get("confidence"))
                    ),
                    "evidence_quote": str(item.get("evidence_quote", ""))[:500],
                    "rationale": str(item.get("rationale", ""))[:800],
                    "next_step": str(item.get("next_step", ""))[:500],
                }
            )
        return {
            "overall_note": str(result.get("overall_note", ""))[:1200],
            "requirements": cleaned,
        }
