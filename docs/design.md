# Career Fit design

## Product boundary

Career Fit is a decision-support tool for job seekers. The v0.1 unit of analysis is one job description and one candidate profile. The output is an auditable preparation report, not an employment forecast.

The product has three audiences:

- job seekers need plain-language gaps and next actions;
- career coaches need a requirement–evidence trail they can challenge;
- labor economists and researchers need explicit definitions, versioned inputs, and separable descriptive measures.

## Architecture

~~~text
job text
  -> skill and hard-constraint extraction
  -> requirement records

candidate text + optional structured evidence
  -> evidence records
  -> direct / transferable / missing matching

requirements + evidence
  -> soft fit score + assessment confidence
  -> hard-constraint status
  -> prioritized gap-to-action plan
  -> JSON API + local visual explorer
~~~

The old skillbundle package remains the implementation compatibility namespace. career_fit is the public product namespace and delegates to the same transparent engine.

## Design principles

1. Evidence before keywords. A keyword mention is a weak self-report unless the user supplies a project, work sample, result, duration, or other context.
2. Constraints are not skills. Licenses, work authorization, degrees, and experience floors are checked separately.
3. Transfer is visible. Evidence in the same analytical category may be transferable, but it is never silently promoted to direct equivalence.
4. Uncertainty is part of the result. Every extraction and assessment carries method, confidence, or a reason for verification.
5. Actions are preparation advice. The engine does not claim that an action has a known causal effect on hiring.
6. Local by default. Candidate inputs stay in the local process in the demo.

## Extension points

- replace or extend the seed dictionary while retaining canonical IDs;
- add reviewed crosswalks from ESCO/O*NET concepts to the analytical layer;
- add candidate-confirmed evidence importers;
- plug in a benchmarked semantic candidate generator without changing the dictionary baseline;
- add outcome calibration only after defining a consented sample, target population, and validation protocol.
