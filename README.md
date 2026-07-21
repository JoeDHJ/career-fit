# SkillBundle

SkillBundle is an explainable toolkit for extracting skills from English text, normalizing them to public concepts, mapping them to a versioned ten-category research layer, and measuring skill bundles.

The first release keeps the baseline deliberately transparent. Exact/normalized matching is a reproducible baseline; it is not presented as a finished semantic NER or occupational skills ontology. Optional ML dependencies are reserved for later candidate generation and benchmarked model releases.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m skillbundle.cli extract "Build Python and SQL pipelines and manage customer projects"
python -m skillbundle.cli taxonomy
python -m skillbundle.cli benchmark --input path\to\skillspan_test.json
python -m skillbundle.cli train --input path\to\skillspan_train.json --output data\processed\ner.json
python -m skillbundle.cli benchmark --input path\to\skillspan_test.json --engine ner --model data\processed\ner.json
python -m skillbundle.cli normalize "unknown skill phrase"
python -m skillbundle.cli serve
```

## Taxonomy architecture

SkillBundle preserves the source taxonomy and a separate research layer. ESCO v1.2.1 is the primary public canonical source; O*NET provides U.S. enrichment. The research layer has ten categories and 45 two-category combinations:

1. cognitive skill / 认知技能
2. social skill / 社交技能
3. character skill / 品格技能
4. writing skill / 写作技能
5. customer and project management / 客户与项目管理技能
6. people management / 人员管理技能
7. financial skill / 财务技能
8. general computer skill / 通用计算机技能
9. specific software skill / 特定软件技能
10. AI skill / AI技能

The public seed dictionary in `config/seed_dictionary_en.json` is intentionally small and generic. It is not the unpublished internal Chinese dictionary.

## Data sources

- ESCO v1.2.1: public canonical skill concepts and relationships; use the official download/API flow.
- O*NET 30.3: U.S. software skills, knowledge, skills, and occupation enrichment.
- SkillSpan: public benchmark with de-identified text and skill/knowledge BIO tags.

Raw ESCO files are not vendored by default. The source registry records the official landing pages and redistribution status.

## Metrics and caveats

The toolkit reports strict and overlap span F1, breadth, category diversity, HHI concentration, rarity, pair support, and NPMI. NPMI is a co-occurrence association statistic, not causal complementarity. Every extraction result carries its method, dictionary version, confidence, and review status.
