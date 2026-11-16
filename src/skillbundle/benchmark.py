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
        if prefix == "B" or (prefix == "I" and start is None):
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
        # Maximum-cardinality bipartite matching: each span is counted once.
        targets = sorted(gold)
        matched: dict[int, int] = {}
        predictions = sorted(predicted)

        def augment(index: int, visited: set[int]) -> bool:
            for target, span in enumerate(targets):
                if target in visited or not overlap(predictions[index], span):
                    continue
                visited.add(target)
                if target not in matched or augment(matched[target], visited):
                    matched[target] = index
                    return True
            return False

        true_positive = sum(augment(index, set()) for index in range(len(predictions)))
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
    target: str = "skills",
) -> dict[str, object]:
    model = (
        PerceptronNER.load(model_path)
        if engine in {"ner", "averaged"} and model_path
        else None
    )
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit < 0
    ):
        raise ValueError("limit must be a nonnegative integer or None")
    if engine not in {"dictionary", "ner", "averaged"}:
        raise ValueError("engine must be dictionary, ner or averaged")
    if engine in {"ner", "averaged"} and model is None:
        raise ValueError("Supervised evaluation requires --model")
    if model is not None and model.sequence != (engine == "averaged"):
        raise ValueError("Engine label does not match the saved model variant")
    if target not in {"skills", "knowledge", "combined"}:
        raise ValueError("target must be skills, knowledge, or combined")
    strict, relaxed, rows = [], [], 0
    groups = {}
    errors = {
        "missed_gold": 0,
        "unmatched_predictions": 0,
        "boundary_overlap_only": 0,
        "gold_negative_sentences": 0,
        "false_positive_sentences": 0,
    }
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if limit is not None and rows >= limit:
            break
        row = json.loads(line)
        tokens, tags = row["tokens"], row["tags_skill"]
        if (
            not isinstance(tokens, list)
            or not isinstance(tags, list)
            or len(tokens) != len(tags)
            or any(not isinstance(t, str) for t in tokens + tags)
        ):
            raise ValueError(
                "each SkillSpan row requires equal-length token/tag string lists"
            )
        text = " ".join(tokens)
        if engine in {"ner", "averaged"}:
            if model is None:
                raise ValueError("engine=ner requires --model")
            predicted_items = model.extract(text)
        else:
            predicted_items = extract(text)
        predicted = {(int(item["start"]), int(item["end"])) for item in predicted_items}
        gold = gold_char_spans(tokens, tags)
        if target in {"knowledge", "combined"}:
            knowledge = row.get("tags_knowledge")
            if (
                not isinstance(knowledge, list)
                or len(knowledge) != len(tokens)
                or any(not isinstance(t, str) for t in knowledge)
            ):
                raise ValueError("knowledge evaluation requires aligned tags_knowledge")
            knowledge_gold = gold_char_spans(tokens, knowledge)
            gold = gold | knowledge_gold if target == "combined" else knowledge_gold
        exact = score(predicted, gold, relaxed=False)
        partial = score(predicted, gold, relaxed=True)
        strict.append(exact)
        relaxed.append(partial)
        group = groups.setdefault(
            str(row.get("source", "unknown")), {"strict": [], "overlap": []}
        )
        group["strict"].append(exact)
        group["overlap"].append(partial)
        errors["missed_gold"] += len(gold) - partial["true_positive"]
        errors["unmatched_predictions"] += len(predicted) - partial["true_positive"]
        errors["boundary_overlap_only"] += (
            partial["true_positive"] - exact["true_positive"]
        )
        errors["gold_negative_sentences"] += not bool(gold)
        errors["false_positive_sentences"] += not gold and bool(predicted)
        rows += 1

    def aggregate(items):
        return {
            key: sum(float(item[key]) for item in items) / len(items) if items else 0.0
            for key in ("precision", "recall", "f1")
        }

    def micro(items):
        tp = sum(item["true_positive"] for item in items)
        predicted = sum(item["predicted"] for item in items)
        gold = sum(item["gold"] for item in items)
        precision = tp / predicted if predicted else 0.0
        recall = tp / gold if gold else 0.0
        return {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0,
            "true_positive": tp,
            "predicted": predicted,
            "gold": gold,
        }

    return {
        "dataset": "SkillSpan",
        "engine": engine,
        "target": target,
        "rows": rows,
        "strict": aggregate(strict),
        "overlap": aggregate(relaxed),
        "schema_version": "career_fit.benchmark.v2",
        "micro_strict": micro(strict),
        "micro_overlap": micro(relaxed),
        "errors": errors,
        "by_source": {
            key: {
                "rows": len(values["strict"]),
                "micro_strict": micro(values["strict"]),
                "micro_overlap": micro(values["overlap"]),
            }
            for key, values in groups.items()
        },
        "aggregation": "strict/overlap are sentence macro means (empty-reference/prediction rows contribute zero); micro_* pool span counts; overlap uses one-to-one maximum-cardinality matching",
        "note": "NER is a lightweight supervised perceptron baseline; dictionary remains the transparent reference.",
    }
