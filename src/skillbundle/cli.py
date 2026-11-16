from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmark import benchmark_skillspan
from .career import analyze_fit, compare_roles
from .dictionary import extract
from .metrics import bundle_metrics
from .ner import PerceptronNER, load_skillspan_rows
from .normalization import normalize_label
from .esco import load_esco_skills
from .server import serve
from .taxonomy import load_taxonomy, pair_codes
from .investment import plan_investment
from .workforce import allocate_workforce
from .market import market_context
from .resources import read_resource_text
from .capital_reports import capital_markdown
from .research import build_research


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be one or greater")
    return parsed


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
    candidate.add_argument(
        "--candidate-file", type=Path, help="path to a candidate profile"
    )
    analyze.add_argument(
        "--evidence-file",
        type=Path,
        help="optional JSON list of structured evidence objects",
    )
    analyze.add_argument(
        "--review-file",
        type=Path,
        help="optional JSON review object; scores are visible only after review",
    )
    analyze.add_argument(
        "--candidate-language",
        choices=["auto", "en", "es", "zh", "other"],
        default="auto",
        help="candidate profile language hint for conservative mapping",
    )
    compare = sub.add_parser(
        "compare", help="prioritize two to three target roles for one candidate"
    )
    compare.add_argument(
        "--roles-file", type=Path, required=True, help="JSON list of job descriptions"
    )
    compare_candidate = compare.add_mutually_exclusive_group(required=True)
    compare_candidate.add_argument("--candidate", help="candidate profile text")
    compare_candidate.add_argument(
        "--candidate-file", type=Path, help="path to a candidate profile"
    )
    compare.add_argument(
        "--evidence-file",
        type=Path,
        help="optional JSON list of structured evidence objects",
    )
    compare.add_argument(
        "--review-file",
        type=Path,
        help="optional JSON candidate-evidence review object",
    )
    compare.add_argument(
        "--candidate-language",
        choices=["auto", "en", "es", "zh", "other"],
        default="auto",
        help="candidate profile language hint for conservative mapping",
    )
    item = sub.add_parser("extract", help="extract skills from text")
    item.add_argument("text")
    item.add_argument("--json", action="store_true")
    bench = sub.add_parser(
        "benchmark", help="evaluate the dictionary baseline on SkillSpan JSONL"
    )
    bench.add_argument("--input", required=True, type=Path)
    bench.add_argument("--limit", type=_non_negative_int)
    bench.add_argument(
        "--engine", choices=["dictionary", "ner", "averaged"], default="dictionary"
    )
    bench.add_argument(
        "--target", choices=["skills", "knowledge", "combined"], default="skills"
    )
    bench.add_argument("--model", type=Path)
    train = sub.add_parser(
        "train", help="train the lightweight supervised SkillSpan NER baseline"
    )
    train.add_argument("--input", required=True, type=Path)
    train.add_argument("--output", required=True, type=Path)
    train.add_argument("--limit", type=_non_negative_int)
    train.add_argument("--epochs", type=_positive_int, default=5)
    train.add_argument(
        "--averaged",
        action="store_true",
        help="train an averaged greedy sequence baseline",
    )
    normalize = sub.add_parser("normalize", help="normalize one label or return NIL")
    normalize.add_argument("label")
    esco = sub.add_parser(
        "ingest-esco", help="inspect an ESCO skills CSV exported from the official flow"
    )
    esco.add_argument("--input", required=True, type=Path)
    sub.add_parser("taxonomy", help="print the analytical taxonomy")
    sub.add_parser("serve", help="start the local Career Fit explorer")
    for name, help_text in (
        ("invest", "choose a feasible 90-day training portfolio"),
        ("workforce", "compare reviewed mobility, training and hiring scenarios"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument(
            "--input",
            type=Path,
            help="reviewed JSON input; omit for the attributed fictional demo",
        )
        command.add_argument("--format", choices=["json", "markdown"], default="json")
        command.add_argument(
            "--case", choices=["legacy", "analyst", "business"], default="legacy"
        )
    sub.add_parser(
        "research", help="run SQL over the attributed employer/resource sample"
    )
    sub.add_parser(
        "measurement", help="show the bundled external extraction evaluation"
    )
    market = sub.add_parser(
        "market", help="inspect an offline portfolio.v1 occupation snapshot"
    )
    market.add_argument("--occupation-id", required=True)
    market.add_argument("--geography", default="US")
    market.add_argument("--snapshot-file", type=Path)
    market.add_argument("--as-of")
    return root


def _input_text(value: str | None, path: Path | None, label: str) -> str:
    if value is not None:
        return value
    if path is not None:
        return path.read_text(encoding="utf-8")
    raise ValueError(f"one of --{label} or --{label}-file is required")


def _main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    if args.command == "research":
        print(json.dumps(build_research(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "measurement":
        print(read_resource_text("measurement_results.json"))
        return 0
    if args.command in {"invest", "workforce"}:
        filename = (
            "investment_demo.json"
            if args.command == "invest"
            else "workforce_demo.json"
        )
        if args.case != "legacy":
            if (args.command, args.case) not in {
                ("invest", "analyst"),
                ("workforce", "business"),
            }:
                raise ValueError(
                    "Use invest --case analyst or workforce --case business"
                )
            filename = (
                "analyst_learning_demo.json"
                if args.case == "analyst"
                else "workforce_business_demo.json"
            )
        payload = json.loads(
            args.input.read_text(encoding="utf-8")
            if args.input
            else read_resource_text(filename)
        )
        result = (
            plan_investment(payload)
            if args.command == "invest"
            else allocate_workforce(payload)
        )
        print(
            capital_markdown(result)
            if args.format == "markdown"
            else json.dumps(result, ensure_ascii=False, indent=2)
        )
        return 0
    if args.command == "market":
        snapshot = (
            json.loads(args.snapshot_file.read_text(encoding="utf-8"))
            if args.snapshot_file
            else None
        )
        print(
            json.dumps(
                market_context(
                    args.occupation_id, args.geography, snapshot, args.as_of
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "analyze":
        try:
            job_text = _input_text(args.job, args.job_file, "job")
            candidate_text = _input_text(
                args.candidate, args.candidate_file, "candidate"
            )
            evidence = None
            if args.evidence_file:
                evidence = json.loads(args.evidence_file.read_text(encoding="utf-8"))
            review = None
            if args.review_file:
                review = json.loads(args.review_file.read_text(encoding="utf-8"))
            result = analyze_fit(
                job_text,
                candidate_text,
                evidence,
                review,
                args.candidate_language,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "compare":
        try:
            roles_payload = json.loads(args.roles_file.read_text(encoding="utf-8"))
            roles = (
                roles_payload.get("roles")
                if isinstance(roles_payload, dict)
                else roles_payload
            )
            if not isinstance(roles, list):
                raise ValueError(
                    "--roles-file must contain a JSON list or an object with a roles list"
                )
            candidate_text = _input_text(
                args.candidate, args.candidate_file, "candidate"
            )
            evidence = None
            if args.evidence_file:
                evidence = json.loads(args.evidence_file.read_text(encoding="utf-8"))
            review = None
            if args.review_file:
                review = json.loads(args.review_file.read_text(encoding="utf-8"))
            result = compare_roles(
                roles,
                candidate_text,
                evidence,
                review,
                args.candidate_language,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
                benchmark_skillspan(
                    args.input, args.limit, args.engine, args.model, args.target
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "train":
        rows = load_skillspan_rows(args.input, args.limit)
        model = PerceptronNER(sequence=args.averaged)
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


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (OSError, TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
