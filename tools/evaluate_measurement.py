"""Reproduce external extraction evaluation without using the test split for tuning."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

from skillbundle.benchmark import benchmark_skillspan
from skillbundle.ner import PerceptronNER, load_skillspan_rows

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://raw.githubusercontent.com/kris927b/SkillSpan/main/data/json/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    raw = ROOT / "data/raw/skillspan"
    raw.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest_path = raw / "retrieval_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )
    sources = []
    for split in ("train", "dev", "test"):
        target = raw / (split + ".jsonl")
        url = SOURCE + split + ".json"
        if args.download:
            with urlopen(
                Request(
                    url, headers={"User-Agent": "CareerFit reproducible evaluation"}
                ),
                timeout=60,
            ) as response:
                target.write_bytes(response.read(15_000_000))
            manifest[split] = {
                "retrieved_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "retrieval_precision": "second",
                "source_url": url,
                "bytes": target.stat().st_size,
                "local_mtime": target.stat().st_mtime,
            }
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
        rows = load_skillspan_rows(target)
        acquisition = manifest.get(split, {})
        unchanged = (
            acquisition.get("bytes") == target.stat().st_size
            and acquisition.get("local_mtime") == target.stat().st_mtime
        )
        sources.append(
            {
                "source_id": "skillspan-" + split,
                "source_url": url,
                "source_vintage": "SkillSpan public repository; original official split",
                "retrieved_at": acquisition.get("retrieved_at") if unchanged else None,
                "retrieval_precision": acquisition.get("retrieval_precision")
                if unchanged
                else "unknown",
                "local_file_modified_at": datetime.fromtimestamp(
                    target.stat().st_mtime, timezone.utc
                ).isoformat(),
                "schema_version": "portfolio.v1",
                "geography": "English-language job postings; source-defined sampling",
                "unit_of_observation": "annotated sentence",
                "period": "source collection predates this release; not current labor demand",
                "status": "observed",
                "path": str(target.relative_to(ROOT)).replace("\\", "/"),
                "rows": len(rows),
                "bytes": target.stat().st_size,
                "domains": dict(Counter(r.get("source", "unknown") for r in rows)),
                "license": "MIT, Mike Zhang 2023; see source repository LICENSE",
                "paper": "https://aclanthology.org/2022.naacl-main.366/",
            }
        )
    model = PerceptronNER()
    training = model.train(load_skillspan_rows(raw / "train.jsonl"), epochs=5)
    model_path = ROOT / "data/processed/skillspan_ner.json"
    model.save(
        model_path,
        {
            "dataset": "SkillSpan",
            "training_split": "train",
            "epochs_fixed_before_evaluation": 5,
        },
    )
    averaged = PerceptronNER(sequence=True)
    averaged_training = averaged.train(
        load_skillspan_rows(raw / "train.jsonl"), epochs=5
    )
    averaged_path = ROOT / "data/processed/skillspan_averaged.json"
    averaged.save(
        averaged_path,
        {"dataset": "SkillSpan", "training_split": "train", "epochs": 5, "seed": 37},
    )
    results = []
    for split in ("dev", "test"):
        for engine in ("dictionary", "ner", "averaged"):
            result = benchmark_skillspan(
                raw / (split + ".jsonl"),
                engine=engine,
                model_path=model_path
                if engine == "ner"
                else averaged_path
                if engine == "averaged"
                else None,
            )
            results.append({"split": split, **result})
            print(split, engine, result["micro_strict"], flush=True)
        combined = benchmark_skillspan(
            raw / (split + ".jsonl"), engine="dictionary", target="combined"
        )
        results.append({"split": split, **combined})
        print(
            split,
            "dictionary combined skill/knowledge",
            combined["micro_strict"],
            flush=True,
        )
    payload = {
        "schema_version": "career_fit.measurement.v1",
        "reference": "External source annotations (tags_skill); no human annotations created by Career Fit",
        "protocol": "Two five-epoch CPU perceptrons trained on official train only: legacy independent-token model and averaged greedy sequence model (fixed seed 37). The sequence baseline was added after inspecting legacy dev errors. All methods/splits are reported; no claim of a prespecified experiment or independent confirmation. Test is not used for parameter selection. Dictionary remains the reviewed production reference.",
        "sources": sources,
        "training": {"legacy": training, "averaged": averaged_training},
        "results": results,
        "scope": [
            "The dictionary includes knowledge/software labels that the benchmark may annotate under tags_knowledge instead of tags_skill. Reported scores concern the named tags_skill task and do not measure all occupational coverage.",
            "Extraction accuracy does not validate evidence strength, transfer weights, capability, hiring probability or training effects.",
            "Raw source sentences and model weights stay in local analysis directories. Bundled summary results reproduce offline; full re-estimation requires downloading the public source.",
        ],
    }
    output = ROOT / "src/skillbundle/resources/measurement_results.json"
    payload["evaluated_at"] = stamp
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# External extraction evaluation",
        "",
        payload["reference"],
        "",
        payload["protocol"],
        "",
        "| Split | Target | Method | Sentences | Exact precision | Exact recall | Exact F1 | Overlap F1 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in results:
        m = r["micro_strict"]
        lines.append(
            f"| {r['split']} | {r['target']} | {r['engine']} | {r['rows']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {r['micro_overlap']['f1']:.3f} |"
        )
    lines += [
        "",
        "Precision/recall/F1 are pooled span-level measures. Overlap uses maximum-cardinality one-to-one matching; sentence macro results and error counts are retained in the JSON. Empty-reference rows are included. No training sentence is drawn from dev/test.",
        "",
    ] + ["- " + s for s in payload["scope"]]
    lines += ["", "## Sources", ""] + [
        f"- [{s['source_id']}]({s['source_url']}): {s['rows']} sentences, {s['bytes']} bytes, domains {s['domains']}."
        for s in sources
    ]
    (ROOT / "docs/measurement-evaluation.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
