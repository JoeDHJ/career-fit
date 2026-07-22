# Career Fit v0.3 requirements

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
8. Expose the matching method, including direct skill ID, reviewable transfer crosswalk, and same-category baseline.
9. Calculate Evidence Fit, Capability Signal, Proof Signal, Application Readiness, and Information Confidence.
10. Keep hard-gate status separate from soft evidence overlap and expose met, not_met, and unknown states.
11. Generate ranked gaps classified as proof, translation, bridge, foundation, or verification gaps.
12. Give each priority gap a time horizon, effort estimate, action type, expected artifact, and evidence prompt.
13. Expose the complete assessment as JSON and render it in a local interactive page.
14. Keep all user-facing project content in English, including the page, CLI labels, documentation, examples, and screenshots.
15. Preserve the legacy SkillBundle extraction and benchmark commands during the rename.
16. Compare two to three target roles for one candidate using the same deterministic analysis and expose the preparation-priority basis.

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
- The JSON output contains enough fields to reproduce the score calculation and the next-action rationale.
- A user can compare two or three roles, see the ranking basis, and load a selected role into the detailed view.
- The visual page explains the economic meaning and limitations of every metric in plain English.
