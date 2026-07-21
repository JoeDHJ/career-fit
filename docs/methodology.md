# Career Fit methodology

## 1. Requirement importance

The extractor assigns a requirement level from local language cues:

| Level | Examples | Weight |
| --- | --- | ---: |
| must | must have, required, mandatory | 1.0 |
| strongly preferred | strongly preferred, essential | 0.7 |
| preferred | preferred, bonus, plus | 0.4 |
| inferred | mentioned without a clear marker | 0.2 |

The v0.1 wording rules are intentionally conservative. They are not a claim that every employer uses these words consistently.

## 2. Requirement-level match

For soft requirement j:

~~~text
M_j = 0.35 C_j + 0.25 E_j + 0.20 P_j + 0.10 R_j + 0.10 D_j
~~~

Where:

- C is coverage: 1.0 for direct evidence, 0.55 for same-category transferable evidence, 0 for missing evidence;
- E is evidence strength, weighted by evidence type;
- P is a conservative proficiency signal;
- R is recency;
- D is evidence depth, using duration when supplied.

The Role Fit Score is:

~~~text
100 × Σ(weight_j × M_j) / Σ(weight_j)
~~~

This is a descriptive readiness index for the supplied text. It is not a probability and has no causal interpretation.

## 3. Evidence strength

The baseline evidence weights are:

| Evidence type | Base weight |
| --- | ---: |
| work | 0.95 |
| research project | 0.90 |
| portfolio / GitHub project | 0.80 |
| course | 0.60 |
| certificate | 0.55 |
| self-reported keyword | 0.35 |
| unknown | 0.25 |

Measurable results receive a small transparent bonus. This is a prioritization heuristic, not a psychometric scale.

## 4. Hard constraints

Licenses, work authorization, degrees, and explicit experience floors are checked separately. Their status is met, not_met, or unknown. An unknown hard constraint produces blocked_pending_verification; the UI asks the user to verify it rather than assuming absence.

## 5. Assessment Confidence

Assessment Confidence combines job-description clarity, average evidence strength, and the share of requirements with direct evidence. It describes the information available to the engine. It is not calibrated against interview or hiring outcomes.

## 6. Sensitivity and future validation

The most consequential modeling choices are the importance weights, transferability definition, evidence-type weights, and treatment of missing evidence. Future releases should publish sensitivity tables under alternative weights and validate only on a consented, well-defined sample. A high score should never be presented as evidence that a candidate is more productive or more likely to be hired.
