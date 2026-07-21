from __future__ import annotations

import json
from pathlib import Path

from .dictionary import extract
from .ner import PerceptronNER


def bio_spans(tokens: list[str], tags: list[str]) -> list[tuple[int, int, str]]:
    spans = []
    start = None
    for index, tag in enumerate(tags + ["O"]):
        prefix = tag.split("-", 1)[0] if tag else "O"
        if prefix == "B" or (prefix == "I" and start is None) or prefix == "O":
            if start is not None:
                spans.append((start, index, " ".join(tokens[start:index])))
                start = None
        if prefix == "B":
            start = index
    return spans


def token_offsets(tokens: list[str]) -> list[tuple[int, int]]:
    offsets, cursor = [], 0
    for token in tokens:
        start = cursor
        cursor += len(token)
        offsets.append((start, cursor))
        cursor += 1
    return offsets


def gold_char_spans(tokens: list[str], tags: list[str]) -> set[tuple[int, int]]:
    offsets = token_offsets(tokens)
    return {
        (offsets[start][0], offsets[end - 1][1])
        for start, end, _ in bio_spans(tokens, tags)
    }


def overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return min(a[1], b[1]) > max(a[0], b[0])


def score(
    predicted: set[tuple[int, int]], gold: set[tuple[int, int]], relaxed: bool = False
) -> dict[str, float]:
    if relaxed:
        true_positive = sum(
            any(overlap(item, target) for target in gold) for item in predicted
        )
    else:
        true_positive = len(predicted & gold)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "predicted": len(predicted),
        "gold": len(gold),
        "true_positive": true_positive,
    }


def benchmark_skillspan(
    path: Path,
    limit: int | None = None,
    engine: str = "dictionary",
    model_path: Path | None = None,
) -> dict[str, object]:
    model = PerceptronNER.load(model_path) if engine == "ner" and model_path else None
    strict, relaxed, rows = [], [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        tokens, tags = row["tokens"], row["tags_skill"]
        text = " ".join(tokens)
        if engine == "ner":
            if model is None:
                raise ValueError("engine=ner requires --model")
            predicted_items = model.extract(text)
        else:
            predicted_items = extract(text)
        predicted = {(int(item["start"]), int(item["end"])) for item in predicted_items}
        gold = gold_char_spans(tokens, tags)
        strict.append(score(predicted, gold, relaxed=False))
        relaxed.append(score(predicted, gold, relaxed=True))
        rows += 1
        if limit and rows >= limit:
            break

    def aggregate(items):
        return {
            key: sum(float(item[key]) for item in items) / len(items) if items else 0.0
            for key in ("precision", "recall", "f1")
        }

    return {
        "dataset": "SkillSpan",
        "engine": engine,
        "rows": rows,
        "strict": aggregate(strict),
        "overlap": aggregate(relaxed),
        "note": "NER is a lightweight supervised perceptron baseline; dictionary remains the transparent reference.",
    }
