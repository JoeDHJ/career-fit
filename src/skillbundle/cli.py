from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import benchmark_skillspan
from .dictionary import extract
from .metrics import bundle_metrics
from .ner import PerceptronNER, load_skillspan_rows
from .normalization import normalize_label
from .esco import load_esco_skills
from .server import serve
from .taxonomy import load_taxonomy, pair_codes


def parser():
    root = argparse.ArgumentParser(description="SkillBundle explainable skill toolkit")
    sub = root.add_subparsers(dest="command", required=True)
    item = sub.add_parser("extract", help="extract skills from text")
    item.add_argument("text")
    item.add_argument("--json", action="store_true")
    bench = sub.add_parser(
        "benchmark", help="evaluate the dictionary baseline on SkillSpan JSONL"
    )
    bench.add_argument("--input", required=True, type=Path)
    bench.add_argument("--limit", type=int)
    bench.add_argument("--engine", choices=["dictionary", "ner"], default="dictionary")
    bench.add_argument("--model", type=Path)
    train = sub.add_parser(
        "train", help="train the lightweight supervised SkillSpan NER baseline"
    )
    train.add_argument("--input", required=True, type=Path)
    train.add_argument("--output", required=True, type=Path)
    train.add_argument("--limit", type=int)
    train.add_argument("--epochs", type=int, default=5)
    normalize = sub.add_parser("normalize", help="normalize one label or return NIL")
    normalize.add_argument("label")
    esco = sub.add_parser(
        "ingest-esco", help="inspect an ESCO skills CSV exported from the official flow"
    )
    esco.add_argument("--input", required=True, type=Path)
    sub.add_parser("taxonomy", help="print the analytical taxonomy")
    sub.add_parser("serve", help="start the local live extractor")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "extract":
        items = extract(args.text)
        result = {
            "text": args.text,
            "extractions": items,
            "metrics": bundle_metrics(items),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "benchmark":
        print(
            json.dumps(
                benchmark_skillspan(args.input, args.limit, args.engine, args.model),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "train":
        rows = load_skillspan_rows(args.input, args.limit)
        model = PerceptronNER()
        metadata = model.train(rows, epochs=args.epochs)
        model.save(args.output, {"dataset": "SkillSpan", **metadata})
        print(
            json.dumps(
                {"output": str(args.output), **metadata}, ensure_ascii=False, indent=2
            )
        )
        return 0
    if args.command == "normalize":
        print(json.dumps(normalize_label(args.label), ensure_ascii=False, indent=2))
        return 0
    if args.command == "ingest-esco":
        rows = load_esco_skills(args.input)
        print(
            json.dumps(
                {"rows": len(rows), "sample": rows[:3]}, ensure_ascii=False, indent=2
            )
        )
        return 0
    if args.command == "taxonomy":
        payload = load_taxonomy()
        payload["pairs"] = pair_codes()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "serve":
        serve()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
