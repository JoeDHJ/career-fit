# Career Fit data contract

The v0.3 JSON response uses `schema_version: career_fit.v0.3`. Field names are explicit so the output can be audited or used by a downstream notebook. The v0.3 release adds a descriptive Role Fingerprint without changing the meaning of the existing scores.

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

## Role Fingerprint

`role_fingerprint` contains:

- `taxonomy_id` and `taxonomy_version`, which identify the ten-category analytical layer;
- `categories`, with role requirement counts, evidence counts, direct and transferable counts, evidence coverage, and a gap signal;
- `mismatch_dimensions`, the largest category-level gaps among categories required by this posting;
- `skill_bundles`, pairs of named requirements that appear together in the supplied posting, their evidence statuses, joint signal, and a suggested proof action;
- `caveat`, which keeps the interpretation boundary in the machine-readable result.

Categories are organizing dimensions, not substitutes for named skills. Skill bundles describe co-occurrence in the supplied job text. They are not estimates of wage value, employer preference beyond the posting, or worker ability.

## Reproducibility

The dictionary, taxonomy, negation rule, transfer map, extraction method, and importance weights are versioned in the repository. A future release must increment the schema or dictionary version when changing field meaning or score semantics.

## Role comparison response

The comparison endpoint and CLI command use `schema_version: career_fit.compare.v0.2`. A response contains `role_count` and a `roles` array. Each role includes a deterministic `role_id`, a user-facing `role_label`, `priority_rank`, `priority_basis`, the single-role `summary`, the highest-priority `top_action`, a `top_mismatch`, a `top_bundle`, and the full single-role `analysis` for auditability.

## Optional occupation context

When `CAREER_FIT_ATLAS_URL` is configured, the local server proxies `GET /api/occupation-context?query=<title>` to AI Labor Atlas. The response always requires user confirmation. Exact title evidence uses `mapping_status: title_evidence`; a curated nonstandard-title crosswalk uses `mapping_status: editorial_candidate_crosswalk` and returns candidates with `mapping_status: candidate_family`, `mapping_note`, and `match_score: null`. These candidates are possible occupation families, not official equivalences, probabilities, or automatic classifications. Confirmed occupation context is separate from all Career Fit scores and eligibility decisions.

## Local narrow-screen browser regression

With AI Labor Atlas serving a demo release on port 8765 and Career Fit configured to use it on port 8766, run `powershell -ExecutionPolicy Bypass -File tools/verify_mobile_layout.ps1` from this repository. The script uses the Playwright CLI through `npx`, checks both pages at a 390px viewport for horizontal overflow, verifies the alias-empty release message, and verifies that an alias candidate card exposes its mapping note and confirmation control. It stores no screenshots or browser artifacts in the repository and removes its temporary session directory. GitHub Actions runs the Python unit and compile checks; it does not run this browser check.

The comparison accepts exactly two or three non-empty role descriptions. A request with fewer than two or more than three roles is rejected with a user-facing validation error.

Roles are ordered by application readiness, then Evidence Fit and Information Confidence. This ordering describes where the supplied evidence supports preparation first; it is not a hiring-probability ranking. A lower-ranked role may reflect missing proof or an unresolved eligibility gate rather than lower underlying ability.
