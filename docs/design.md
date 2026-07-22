# Career Fit design

## Product boundary

Career Fit is a decision-support tool for job seekers. The v0.3 product supports one detailed job description and a small comparison set of target roles for one candidate profile. The output is an auditable preparation report, not an employment forecast.

The product has three audiences:

- job seekers need plain-language distinctions and a concrete next move;
- career coaches need a requirement–evidence trail they can challenge;
- labor economists and researchers need explicit definitions, versioned inputs, and separable descriptive measures.

## User flow

```text
job description + candidate profile
  -> skill, negation, and hard-gate extraction
  -> requirement and evidence records
  -> direct / thin / transferable / missing matching
  -> capability, proof, readiness, and confidence signals
  -> multidimensional role fingerprint and posting-specific skill bundles
  -> ranked gap-to-action plan
  -> local JSON API + interactive explorer

optional role set + same candidate profile
  -> independent role analyses
  -> preparation-priority ranking
  -> inspect one role in the detailed evidence view
```

## Three-signal model

1. **Capability Signal** summarizes direct and explicitly transferable overlap.
2. **Proof Signal** summarizes evidence type, duration, recency, and measurable results.
3. **Application Readiness** combines must-have match, proof strength, and hard-gate status.

The signals are deliberately separable because a person can have capability without proof, proof without a resolved gate, or strong overlap with a role that is still not a priority.

## Design principles

1. Evidence before keywords. A keyword mention is weak unless context makes the evidence reviewable.
2. Negation is first-class. A statement such as “no direct HR-data experience” cannot increase the HR-data match.
3. Constraints are not skills. Licenses, work authorization, degrees, and experience floors are checked separately.
4. Transfer is visible. Explicit crosswalks and same-category baselines are labeled, never silently promoted to direct evidence.
5. Missing text is not missing ability. Every gap card explains this limitation.
6. Actions are preparation advice. The engine does not claim a known causal hiring effect.
7. Local by default. Candidate inputs stay in the local process in the demo.
8. English-only surface. User-facing page copy, documentation, CLI labels, examples, and screenshots use English for consistent public delivery.
9. Literature informs the workflow, not unsupported claims. The interface translates multidimensional mismatch and task transfer into evidence and practice actions while keeping their empirical boundaries visible.

## Extension points

- replace or extend the seed dictionary while retaining canonical IDs;
- add reviewed crosswalks from ESCO and O*NET concepts to the analytical layer;
- add candidate-confirmed evidence importers;
- plug in a benchmarked semantic candidate generator without changing the dictionary baseline;
- add outcome calibration only after defining a consented sample, target population, and validation protocol.
