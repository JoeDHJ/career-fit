# Privacy and fairness

Career Fit is built to help a person prepare for a job application. It should not be used as an automated hiring or rejection system.

## Data handling

- The demo runs on `127.0.0.1` and sends text to the local Python process.
- The repository contains no personal resume, employment record, or hosted profile.
- Users should avoid placing names, contact details, identification numbers, or sensitive personal data into examples committed to a public repository.
- Optional structured evidence is user-controlled and remains local in the demo.
- Any future hosted deployment needs a separate consent, retention, deletion, access-control, and security design.

## Known limitations

- The English seed dictionary is small and does not cover every occupation, language, or synonym.
- Exact matching can miss informal experience, spelling variants, and employer-specific language.
- A negative-statement rule can be conservative and should be reviewed by the user.
- A missing mention is not proof that a person lacks the underlying ability.
- Transferable evidence is a preparation hypothesis, not proof of equivalence.
- Job descriptions may encode occupational, institutional, or demographic bias.
- Evidence types, transfer rules, and score weights are heuristics and have not been calibrated to hiring outcomes.

## Safe use

Use the report to ask:

- What can I demonstrate with a concrete example?
- Is this a foundation gap, a proof gap, or a translation problem?
- Which requirement should I practice or verify next?
- Which hard gate needs confirmation before I invest more time?
- What should I add to a resume bullet, portfolio page, or interview story?

Do not use Career Fit to infer protected characteristics, rank candidates for an employer, make an adverse decision, or claim that a preparation action has a known causal effect on hiring.

## Fairness guardrails

1. Do not collect or score protected traits.
2. Keep hard gates visible and challengeable instead of hiding them inside a single score.
3. Treat missing evidence as uncertainty, not as proof of inability.
4. Let users correct extracted requirements and evidence before relying on the report.
5. Preserve the original text and matching method so a coach or researcher can audit the result.
