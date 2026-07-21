# Data contract

Each extraction item contains:

```json
{
  "text": "Python",
  "start": 5,
  "end": 11,
  "skill_id": "software.python",
  "canonical": "Python",
  "source_taxonomy": "seed_dictionary_en",
  "source_skill_id": "software.python",
  "analysis_category_code": "specific_software_skill",
  "mapping_method": "dictionary_exact",
  "confidence": 0.99,
  "review_status": "baseline_unreviewed",
  "dictionary_version": "v0.1.0"
}
```

Unmatched candidate phrases must be represented as `NIL` or omitted only when the caller requests matched-only output.

