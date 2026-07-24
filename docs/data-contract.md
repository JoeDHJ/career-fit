# Career Fit data contract

The v0.5 JSON response uses `schema_version: career_fit.v0.5`. Field names are explicit so the output can be audited or used by a downstream notebook. The response separates extraction from user confirmation, keeps claim-only evidence distinct from proof, and exposes explicit coverage semantics.

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
  "importance_weight": null,
  "hard_constraint": false,
  "extraction_method": "dictionary_exact",
  "extraction_confidence": null,
  "source_taxonomy": "career_fit_seed_en",
  "source_skill_id": "software.python",
  "review_status": "baseline_unreviewed",
  "match_mode": "exact",
  "dictionary_version": "v0.2.3+onet-30.3-derived-v2",
  "status": "direct_weak",
  "status_label": "Mentioned, proof is thin",
  "match_score": null,
  "matching_method": "direct_skill_id",
  "evidence_strength": null,
  "evidence_ids": ["evidence-001"],
  "reviewable_evidence_ids": ["evidence-001"],
  "claimed_evidence_ids": [],
  "primary_evidence_id": "evidence-001",
  "evidence_aggregation": "primary_plus_top_two_supporting"
}
```

Hard gates use requirement types such as `professional_license`, `background_check`, `work_authorization`, `education`, and `experience_floor`. They carry `hard_constraint: true`, `status` values `met`, `not_met`, or `unknown`, and are not included in the soft-fit denominator. Free-text extraction is conservative: education uses ordered levels, experience floors require matching area terms, background checks remain `unknown` unless the candidate explicitly states a status, and ambiguous gates remain `unknown` until the user confirms them. Future, modal, and conditional claims such as `will`, `would`, `could`, `can`, `may`, `plan`, `by 2027`, or `if approved` do not establish a currently met gate; they remain `unknown`. An explicit current negative remains `not_met` even when the candidate also describes a future resolution. Explicitly negated experience, historical authorization or licensure, and expired, revoked, inactive, or otherwise no-longer-valid gates never count as current `met`; they are `not_met` when the current failure is explicit and `unknown` when the text only establishes a past state. Current/active/valid license wording is treated as equivalent current evidence when the required license terms are present.

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
  "evidence_status": "user_declared_structured_evidence",
  "verification_status": "user_declared",
  "negated": false,
  "source_taxonomy": "career_fit_seed_en",
  "source_skill_id": "software.python",
  "review_status": "baseline_unreviewed",
  "match_mode": "exact",
  "dictionary_version": "v0.2.3+onet-30.3-derived-v2"
}
```

Supported evidence types are `work`, `research_project`, `portfolio`, `github_project`, `course`, `certificate`, `self_reported`, and `unknown`. `self_reported` and `unknown` are claim-only types: they remain visible, but receive lower coverage, depth, recency, and proof weight. Mentions detected inside a conservative negative statement remain in the evidence list with `negated: true` and `evidence_status: negated_statement`, but are excluded from matching.

The review panel may add structured evidence. Review-added non-claim items use `evidence_status: user_declared_structured_evidence`; claim-only items use `user_confirmed_self_report`. Both carry `verification_status: user_declared` and are never silently upgraded to externally verified proof. The guided intake is a user-interface route over the same `added_evidence` contract: it requires a selected soft requirement, a task, and a context, and optionally carries a result, evidence type, duration, and recency. It does not create a score or verification claim by itself; the role-requirements review must still be applied.

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
- `analysis_status`: `scored`, `review_required`, or `insufficient_information`;
- `score_visibility`: `visible` only after a role-requirements review, otherwise `hidden`;
- `requirements_identified`: count of extracted requirements; it is not completeness or confidence;
- `input_completeness_score`: always `null` compatibility field, retained to prevent the old misleading interpretation;
- `evidence_coverage_score`: reviewable direct/transferable evidence coverage;
- `claimed_evidence_coverage_score`: claim-only coverage reported separately;
- `eligibility_verification_score`: known hard-gate status, or `null` when no hard gate was detected;

Before a `role_requirements` review is confirmed, all derived numeric score, coverage, weight, and extraction-confidence fields are returned as `null` in the API contract. Requirement counts and textual statuses remain available so the user can correct the extraction without being shown a provisional score. A `candidate_evidence` review unlocks neither role scores nor role-level comparison scores.
- `eligibility_status`: `no_gate_detected`, `unresolved`, or `verified`;
- `candidate_language`: the requested/detected language route and whether the English-first dictionary needs language review; this is a coverage caveat, not a language or employability judgment;
- `review_status`: `provisional`, `candidate_evidence_confirmed`, or `user_confirmed`;
- `review_required`: whether the extraction should be checked before relying on the plan;
- `readiness_status` and `decision`: human-readable routing labels;
- requirement, evidence, and hard-gate counts.

None of these fields is a confidence probability or calibrated hiring probability. When `analysis_status` is `insufficient_information`, fit and readiness scores are `null` and `analysis_reasons` explains what to add.

The response also includes `review_queue` and a `review` object. A review becomes score-bearing only when the request carries the explicit `applied: true` confirmation flag; a scope string alone cannot unlock scores or role comparison. A `role_requirements` review can remove extracted requirement IDs, change soft-requirement importance, add dictionary-backed or user-supplied requirements, add a missed hard eligibility gate, confirm hard-gate statuses, and add structured evidence. User-supplied soft labels receive a `user.custom.*` skill ID and require explicit evidence; they are not silently mapped to an analytical category. User-added eligibility text is kept as a hard constraint and remains `unknown` until candidate evidence or an explicit confirmation resolves it. When all extracted gaps are resolved, `next_actions` still contains an `application_plan` positioning action so the workflow ends with an application artifact rather than an empty result. A `candidate_evidence` review marks candidate evidence as reusable for comparison without confirming any role checklist, and comparison accepts only evidence explicitly labeled as user-declared. The server recomputes all derived scores from the reviewed structure; clients cannot directly submit a replacement score.

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

The comparison endpoint and CLI command use `schema_version: career_fit.compare.v0.4`. A response contains `role_count` and a `roles` array. Each role includes a deterministic `role_id`, a user-facing `role_label`, `priority_rank`, `priority_basis`, the single-role `summary`, the highest-priority `top_action`, a `top_mismatch`, a `top_bundle`, and the full single-role `analysis` for auditability. The request must carry evidence from a reviewed candidate state. `role_reviews` is keyed by `role_id`; the product leaves every card unranked until every role has an applied `role_requirements` review and a visible score. Only then does `comparison_status` become `ranked_after_role_review`, with a stable order by reviewed application readiness, then reviewed evidence fit, then role id. This is preparation priority, never a hiring-probability ranking.

## Optional occupation context

When `CAREER_FIT_ATLAS_URL` is configured, the local server proxies `GET /api/occupation-context?query=<title>` to AI Labor Atlas. The response always requires user confirmation. Exact title evidence uses `mapping_status: title_evidence`; a curated nonstandard-title crosswalk uses `mapping_status: editorial_candidate_crosswalk` and returns candidates with `mapping_status: candidate_family`, `mapping_note`, and `match_score: null`. These candidates are possible occupation families, not official equivalences, probabilities, or automatic classifications. Confirmed occupation context is separate from all Career Fit scores and eligibility decisions. A confirmed response includes `market_context.v0.2` with descriptive wages, employment, openings, projected change, AI exposure, representative tasks, adjacent occupations, data-vintage provenance, and an explicit SOC-mapping aggregation status when needed.

## Local narrow-screen browser regression

With AI Labor Atlas serving a demo release on port 8765 and Career Fit configured to use it on port 8766, run `powershell -ExecutionPolicy Bypass -File tools/verify_mobile_layout.ps1` from this repository. The script uses the Playwright CLI through `npx`, checks both pages at a 390px viewport for horizontal overflow, verifies the `Data Analyst` alias-empty release message, and then verifies that the `ML Engineer` alias candidate card exposes its mapping note and confirmation control. It stores no screenshots or browser artifacts in the repository and removes its temporary session directory. GitHub Actions runs the Python unit and compile checks in both repositories. The Career Fit workflow also installs Chromium, starts the Career Fit service with an Atlas demo release from `main`, runs this browser check, and cleans both services; the Atlas workflow does not claim browser coverage.

The comparison accepts exactly two or three non-empty role descriptions. A request with fewer than two or more than three roles is rejected with a user-facing validation error.

Roles are ordered by application readiness, then Evidence Fit and reviewable evidence coverage. This ordering describes where the supplied evidence supports preparation first; it is not a hiring-probability ranking. A lower-ranked role may reflect missing proof or an unresolved eligibility gate rather than lower underlying ability.
