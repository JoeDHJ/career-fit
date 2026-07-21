from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmark import benchmark_skillspan
from .career import analyze_fit
from .dictionary import extract
from .metrics import bundle_metrics
from .ner import PerceptronNER, load_skillspan_rows
from .normalization import normalize_label
from .esco import load_esco_skills
from .server import serve
from .taxonomy import load_taxonomy, pair_codes


def parser():
    root = argparse.ArgumentParser(
        description="Career Fit explainable job-fit and career-pathway toolkit"
    )
    sub = root.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser(
        "analyze", help="compare one job description with one candidate profile"
    )
    job = analyze.add_mutually_exclusive_group(required=True)
    job.add_argument("--job", help="job description text")
    job.add_argument("--job-file", type=Path, help="path to a job description")
    candidate = analyze.add_mutually_exclusive_group(required=True)
    candidate.add_argument("--candidate", help="candidate profile text")
    candidate.add_argument("--candidate-file", type=Path, help="path to a candidate profile")
    analyze.add_argument(
        "--evidence-file",
        type=Path,
        help="optional JSON list of structured evidence objects",
    )
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
    sub.add_parser("serve", help="start the local Career Fit explorer")
    return root


def _input_text(value: str | None, path: Path | None, label: str) -> str:
    if value is not None:
        return value
    if path is not None:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"one of --{label} or --{label}-file is required")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    if args.command == "analyze":
        job_text = _input_text(args.job, args.job_file, "job")
        candidate_text = _input_text(args.candidate, args.candidate_file, "candidate")
        evidence = None
        if args.evidence_file:
            evidence = json.loads(args.evidence_file.read_text(encoding="utf-8"))
        print(
            json.dumps(
                analyze_fit(job_text, candidate_text, evidence),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
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
