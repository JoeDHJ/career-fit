# Career Fit data contract

The v0.2 JSON response uses `schema_version: career_fit.v0.2`. Field names are explicit so the output can be audited or used by a downstream notebook.

## Requirement record

```json
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
  "extraction_confidence": 0.99,
  "source_taxonomy": "career_fit_seed_en",
  "source_skill_id": "software.python",
  "review_status": "baseline_unreviewed",
  "match_mode": "exact",
  "dictionary_version": "v0.2.0+onet-30.3-derived-v2",
  "status": "direct_weak",
  "status_label": "Mentioned, proof is thin",
  "match_score": 0.72,
  "matching_method": "direct_skill_id",
  "evidence_strength": 0.35,
  "evidence_ids": ["evidence-001"]
}
```

Hard gates use requirement types such as `professional_license`, `work_authorization`, `education`, and `experience_floor`. They carry `hard_constraint: true`, `status` values `met`, `not_met`, or `unknown`, and are not included in the soft-fit denominator.

Experience floors additionally expose `required_years` and, when available, `experience_area`.

## Evidence record

```json
{
  "evidence_id": "evidence-001",
  "skill_id": "software.python",
  "canonical_skill": "Python",
  "analysis_category_code": "specific_software_skill",
  "evidence_type": "research_project",
  "source_text": "Built a panel-data pipeline",
  "duration_months": 18,
  "recency_years": 1,
  "measurable_result": "1.3 million records",
  "evidence_status": "user_provided",
  "negated": false,
  "source_taxonomy": "career_fit_seed_en",
  "source_skill_id": "software.python",
  "review_status": "baseline_unreviewed",
  "match_mode": "exact",
  "dictionary_version": "v0.2.0+onet-30.3-derived-v2"
}
```

Supported evidence types are `work`, `research_project`, `portfolio`, `github_project`, `course`, `certificate`, `self_reported`, and `unknown`. Mentions detected inside a conservative negative statement remain in the evidence list with `negated: true` and `evidence_status: negated_statement`, but are excluded from matching.

## Gap and action record

```json
{
  "requirement_id": "req-001",
  "canonical_skill": "Python",
  "gap_type": "proof_gap",
  "action_type": "package_proof",
  "priority": "medium",
  "time_horizon": "before applying",
  "estimated_effort": "15–30 minutes",
  "action": "Turn your existing Python mention into one concrete proof point with a task, context, and measurable result.",
  "expected_artifact": "A quantified resume bullet, work sample, or interview story.",
  "evidence_prompt": "What did you do with Python, for whom, and what changed because of it?"
}
```

Gap types are `proof_gap`, `translation_gap`, `bridge_gap`, `foundation_gap`, and `verification_gap`. They are preparation categories, not ability judgments.

## Summary record

The summary includes:

- `evidence_fit_score`: importance-weighted requirement overlap;
- `role_fit_score`: compatibility alias for earlier clients;
- `capability_signal_score`: direct and transferable overlap;
- `proof_signal_score`: concreteness and reviewability of evidence;
- `application_readiness_score`: preparation triage under the supplied information;
- `assessment_confidence`: information completeness and extraction quality;
- `readiness_status` and `decision`: human-readable routing labels;
- requirement, evidence, and hard-gate counts.

None of these fields is a calibrated hiring probability.

## Reproducibility

The dictionary, taxonomy, negation rule, transfer map, extraction method, and importance weights are versioned in the repository. A future release must increment the schema or dictionary version when changing field meaning or score semantics.
