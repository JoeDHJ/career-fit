# Career Fit v0.5 requirements

## User problem

Job seekers often receive a binary “qualified” or “not qualified” signal from keyword tools. That signal hides at least four different situations: an actual foundation gap, a proof gap, transferable experience that needs a bridge, and a hard application gate that still needs verification.

Career Fit must make those distinctions legible and actionable without claiming to predict employer decisions.

## Functional requirements

1. Accept one job description and one candidate profile as plain text.
2. Accept optional structured evidence with type, source text, result, duration, and recency fields.
3. Extract dictionary-backed skill requirements with offsets, canonical IDs, category codes, importance, method, and confidence.
4. Extract explicit professional-license, work-authorization, education, and experience-floor gates.
5. Support numeric and common spelled-out experience floors such as “five years of experience.”
6. Detect conservative local negation in candidate text and exclude negated skill mentions from matching while retaining them for auditability.
7. Match requirements as direct, thin direct, transferable, or missing evidence.
8. Expose the matching method, including direct skill ID and reviewable explicit transfer crosswalks.
9. Extract a reviewable checklist first; show Evidence Fit, Capability Signal, Proof Signal, and Application Readiness only after role requirements are confirmed.
10. Keep hard-gate status separate from soft evidence overlap and expose met, not_met, and unknown states.
11. Mark a result `insufficient_information` instead of presenting a fit score when fewer than two requirements, too-short job or candidate text, or no candidate evidence is supplied; mark otherwise-sufficient unreviewed input `review_required` and hide numeric scores.
12. Let users review extracted requirements, change importance, confirm hard gates, add known requirements, and add structured evidence before recalculating.
13. Provide a guided, resume-free intake route for low-information profiles: let a user choose a mapped soft requirement and describe one task, context, optional result, evidence type, duration, and recency before recalculating.
14. Keep future, modal, and conditional hard-gate claims unresolved until current evidence or explicit user confirmation establishes their status.
15. Generate ranked gaps classified as proof, translation, bridge, foundation, or verification gaps.
16. Give each priority gap a time horizon, effort estimate, action type, expected artifact, and evidence prompt.
17. Expose the complete assessment as JSON and render it in a local interactive page.
18. Keep all user-facing project content in English, including the page, CLI labels, documentation, examples, and screenshots.
19. Preserve the legacy SkillBundle extraction and benchmark commands during the rename.
20. Compare two to three target roles for one candidate using the same deterministic analysis and expose the preparation-priority basis.
21. Expose a Role Fingerprint that separates category-level mismatch from named-skill evidence.
22. Identify posting-specific skill bundles and turn them into integrated proof-artifact suggestions.
23. Keep bundle co-occurrence separate from claims about market value, productivity, wages, or hiring probability.
24. Distinguish claim-only evidence from reviewable proof, preserve verification status, and aggregate multiple evidence items monotonically.
25. Allow candidate-evidence review state to be reused for role comparison, while requiring each compared role's own checklist confirmation before showing role-specific scores.
26. Offer a local plain-text or Markdown resume import with a visible redaction reminder and no hosted upload requirement.

## Non-goals

- predicting hiring probability, salary, interview selection, or productivity;
- ranking people for employers or making automatic exclusion decisions;
- inferring protected traits or using them in a score;
- presenting transferable evidence as proof of equivalence;
- treating missing text as proof that a candidate lacks a capability;
- claiming the seed dictionary or transfer map is complete;
- silently uploading candidate data to a hosted service.

## Acceptance criteria

- A user can run the example with one command and inspect every requirement row.
- A negative candidate statement is visible in the evidence audit but does not raise a requirement match.
- A spelled-out experience floor and an authorization-to-work clause can be extracted and checked separately.
- A missing hard gate can produce `verify_before_applying` even when soft overlap is high.
- Same-category or crosswalk evidence is labeled transferable rather than direct.
- Structured project evidence scores stronger than a bare keyword mention.
- A claim-only evidence item is labeled as a claim and does not receive the same proof/readiness contribution as reviewable work or project evidence.
- A weak extra evidence item cannot lower the result supported by a stronger primary item, and the primary evidence ID remains auditable.
- A resume-free user can choose a mapped requirement, record a task and context, optionally add a result, and carry the resulting user-declared evidence through the review route without exposing a score before confirmation.
- Future or conditional hard-gate claims remain `unknown`, while an explicit current negative remains `not_met`; a current statement such as `I have current work authorization` can be recognized as `met`.
- Explicitly negated experience, historical authorization or licensure, and expired/revoked/inactive gates cannot be counted as current evidence; current/active/valid license wording is recognized when the required license terms are present.
- A first-pass response with enough text has `review_required`, null score fields, and `score_visibility: hidden`; a reviewed response has `score_visibility: visible`.
- A role with no detected hard gate reports `eligibility_status: no_gate_detected` and a null eligibility verification score rather than claiming verification.
- The JSON output contains enough fields to reproduce the score calculation and the next-action rationale.
- A user can compare two or three roles, see the ranking basis, and load a selected role into the detailed view.
- A single-role response contains category profiles, largest mismatch dimensions, and posting-specific skill bundles with auditable statuses.
- The visual page explains the economic meaning and limitations of every metric in plain English.
