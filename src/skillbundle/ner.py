from __future__ import annotations

import json
import re
from pathlib import Path


LABELS = ("O", "B-SKILL", "I-SKILL")
TOKEN_RE = re.compile(r"\S+")


def normalize_tag(tag: str) -> str:
    if tag == "B":
        return "B-SKILL"
    if tag == "I":
        return "I-SKILL"
    return tag if tag in LABELS else "O"


def token_features(tokens: list[str], index: int) -> list[str]:
    token = tokens[index]
    lower = token.casefold()
    shape = re.sub(r"[A-Z]", "A", re.sub(r"[a-z]", "a", re.sub(r"\d", "0", token)))
    features = [
        "bias",
        f"lower={lower}",
        f"shape={shape}",
        f"prefix={lower[:3]}",
        f"suffix={lower[-3:]}",
        f"prev={tokens[index - 1].casefold() if index else '<BOS>'}",
        f"next={tokens[index + 1].casefold() if index + 1 < len(tokens) else '<EOS>'}",
        f"has_digit={any(char.isdigit() for char in token)}",
        f"is_upper={token.isupper()}",
    ]
    return features


def tags_to_char_spans(
    text: str, tags: list[str], offsets: list[tuple[int, int]]
) -> list[dict[str, object]]:
    spans = []
    start = None
    for index, tag in enumerate(tags + ["O"]):
        prefix = tag.split("-", 1)[0]
        if prefix in {"B", "O"} or (prefix == "I" and start is None):
            if start is not None:
                spans.append(
                    {
                        "text": text[start : offsets[index - 1][1]],
                        "start": start,
                        "end": offsets[index - 1][1],
                        "label": "SKILL",
                    }
                )
                start = None
        if prefix == "B":
            start = offsets[index][0]
    return spans


class PerceptronNER:
    """A small, dependency-free supervised BIO tagger for reproducible baselines."""

    def __init__(self, weights: dict[str, dict[str, float]] | None = None):
        self.weights = weights or {label: {} for label in LABELS}

    def predict_tags(self, tokens: list[str]) -> list[str]:
        predictions = []
        for index in range(len(tokens)):
            features = token_features(tokens, index)
            scores = {
                label: sum(
                    self.weights.get(label, {}).get(feature, 0.0)
                    for feature in features
                )
                for label in LABELS
            }
            best = max(LABELS, key=lambda label: (scores[label], -LABELS.index(label)))
            if best == "I-SKILL" and (not predictions or predictions[-1] == "O"):
                best = "B-SKILL"
            predictions.append(best)
        return predictions

    def train(self, rows: list[dict[str, object]], epochs: int = 5) -> dict[str, int]:
        updates = 0
        for _ in range(epochs):
            for row in rows:
                tokens = row["tokens"]
                gold = [normalize_tag(tag) for tag in row["tags_skill"]]
                predicted = self.predict_tags(tokens)
                for index, (actual, guess) in enumerate(zip(gold, predicted)):
                    if actual == guess:
                        continue
                    features = token_features(tokens, index)
                    for feature in features:
                        self.weights[actual][feature] = (
                            self.weights[actual].get(feature, 0.0) + 1.0
                        )
                        self.weights[guess][feature] = (
                            self.weights[guess].get(feature, 0.0) - 1.0
                        )
                    updates += 1
        return {"epochs": epochs, "updates": updates, "rows": len(rows)}

    def extract(self, text: str) -> list[dict[str, object]]:
        matches = list(TOKEN_RE.finditer(text))
        tokens = [match.group(0) for match in matches]
        tags = self.predict_tags(tokens)
        offsets = [(match.start(), match.end()) for match in matches]
        return tags_to_char_spans(text, tags, offsets)

    def save(self, path: Path, metadata: dict[str, object] | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"labels": LABELS, "weights": self.weights, "metadata": metadata or {}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "PerceptronNER":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(payload["weights"])


def load_skillspan_rows(
    path: Path, limit: int | None = None
) -> list[dict[str, object]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
        if limit and len(rows) >= limit:
            break
    return rows
