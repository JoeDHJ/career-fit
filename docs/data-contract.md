# Career Fit data contract

The v0.1 JSON response uses schema_version career_fit.v0.1. Field names are intentionally explicit so the output can be audited or used by a downstream notebook.

## Requirement record

~~~json
{
  "requirement_id": "req-001",
  "requirement_type": "skill",
  "canonical_skill": "Python",
  "skill_id": "software.python",
  "analysis_category_code": "specific_software_skill",
  "original_text": "Python",
  "source_context": "Must have Python and SQL.",
  "importance_level": "must",
  "importance_weight": 1.0,
  "hard_constraint": false,
  "extraction_method": "dictionary_exact",
  "extraction_confidence": 0.99
}
~~~

Hard constraints use requirement_type values such as professional_license, work_authorization, education, and experience_floor. They carry hard_constraint true and are not included in the soft-fit denominator.

## Evidence record

~~~json
{
  "evidence_id": "evidence-001",
  "skill_id": "software.python",
  "canonical_skill": "Python",
  "analysis_category_code": "specific_software_skill",
  "evidence_type": "research_project",
  "source_text": "Built a panel-data pipeline",
  "measurable_result": "1.3 million records",
  "duration_months": 18,
  "recency_years": 1
}
~~~

Supported evidence types are work, research_project, portfolio, github_project, course, certificate, self_reported, and unknown. Users may add fields; the engine ignores fields it does not use.

## Assessment record

Each soft requirement copies the requirement fields and adds:

~~~json
{
  "status": "direct",
  "status_label": "Direct evidence / 直接证据",
  "match_score": 0.92,
  "coverage": 1.0,
  "evidence_strength": 0.98,
  "evidence_ids": ["evidence-001"]
}
~~~

The full response also contains:

- requirements: all soft and hard requirement assessments;
- evidence: normalized evidence objects used in the match;
- hard_constraints: the hard-constraint subset and statuses;
- gaps: ranked preparation recommendations;
- summary: scores, counts, and a decision label;
- interpretation: non-causal caveats shown by the UI.

## Reproducibility

The dictionary, taxonomy, extraction method, and importance weights are versioned in the repository. A future release must increment the schema or dictionary version when changing field meaning or score semantics.
