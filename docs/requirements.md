# Career Fit v0.1 requirements

## User problem

Job seekers often receive a binary feeling—“qualified” or “not qualified”—from keyword tools. That hides the difference between an actual skill gap, a lack of evidence, and a hard admission constraint. Career Fit must make those distinctions legible.

## Functional requirements

1. Accept one job description and one candidate profile as plain text.
2. Accept optional structured evidence with type, source text, result, duration, and recency fields.
3. Extract dictionary-backed skill requirements with offsets, canonical IDs, category codes, importance, method, and confidence.
4. Extract hard constraints for professional licenses, work authorization, education, and experience floors when the wording is explicit.
5. Match requirements to evidence as direct, direct-but-weak, transferable, or missing.
6. Calculate a transparent Role Fit Score and Assessment Confidence score.
7. Keep hard-constraint status separate from soft fit and expose unknown verification states.
8. Generate ranked gaps with a time horizon and a concrete next action.
9. Expose the complete assessment as JSON and render it in a local interactive page.
10. Preserve the legacy SkillBundle extraction and benchmark commands during the rename.

## Non-goals

- predicting hiring probability, salary, or interview selection;
- ranking people for employers or making automatic exclusion decisions;
- inferring protected traits or using them in a score;
- presenting transferable evidence as proof of equivalence;
- claiming the small seed dictionary is complete;
- silently uploading candidate data to a hosted service.

## Acceptance criteria

- A user can run the example with one command and inspect every requirement row.
- A missing hard constraint can block the readiness label even when soft fit is high.
- A same-category skill is labeled transferable rather than direct.
- Structured project evidence scores stronger than a bare keyword mention.
- The JSON output contains enough fields to reproduce the score calculation.
- The visual page explains the economic meaning and limitations of its metrics in plain language.
