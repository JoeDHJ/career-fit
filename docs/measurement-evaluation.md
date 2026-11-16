# External extraction evaluation

External source annotations (tags_skill); no human annotations created by Career Fit

Two five-epoch CPU perceptrons trained on official train only: legacy independent-token model and averaged greedy sequence model (fixed seed 37). The sequence baseline was added after inspecting legacy dev errors. All methods/splits are reported; no claim of a prespecified experiment or independent confirmation. Test is not used for parameter selection. Dictionary remains the reviewed production reference.

| Split | Target | Method | Sentences | Exact precision | Exact recall | Exact F1 | Overlap F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| dev | skills | dictionary | 3174 | 0.023 | 0.019 | 0.021 | 0.176 |
| dev | skills | ner | 3174 | 0.041 | 0.220 | 0.069 | 0.269 |
| dev | skills | averaged | 3174 | 0.056 | 0.096 | 0.071 | 0.466 |
| dev | combined | dictionary | 3174 | 0.242 | 0.097 | 0.139 | 0.309 |
| test | skills | dictionary | 3569 | 0.037 | 0.028 | 0.032 | 0.191 |
| test | skills | ner | 3569 | 0.037 | 0.208 | 0.063 | 0.238 |
| test | skills | averaged | 3569 | 0.049 | 0.079 | 0.060 | 0.436 |
| test | combined | dictionary | 3569 | 0.301 | 0.111 | 0.162 | 0.338 |

Precision/recall/F1 are pooled span-level measures. Overlap uses maximum-cardinality one-to-one matching; sentence macro results and error counts are retained in the JSON. Empty-reference rows are included. No training sentence is drawn from dev/test.

- The dictionary includes knowledge/software labels that the benchmark may annotate under tags_knowledge instead of tags_skill. Reported scores concern the named tags_skill task and do not measure all occupational coverage.
- Extraction accuracy does not validate evidence strength, transfer weights, capability, hiring probability or training effects.
- Raw source sentences and model weights stay in local analysis directories. Bundled summary results reproduce offline; full re-estimation requires downloading the public source.

## Sources

- [skillspan-train](https://raw.githubusercontent.com/kris927b/SkillSpan/main/data/json/train.json): 4800 sentences, 2206792 bytes, domains {'tech': 3133, 'house': 1667}.
- [skillspan-dev](https://raw.githubusercontent.com/kris927b/SkillSpan/main/data/json/dev.json): 3174 sentences, 1036099 bytes, domains {'tech': 2156, 'house': 1018}.
- [skillspan-test](https://raw.githubusercontent.com/kris927b/SkillSpan/main/data/json/test.json): 3569 sentences, 1116219 bytes, domains {'tech': 2286, 'house': 1283}.
