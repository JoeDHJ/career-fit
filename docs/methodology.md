# Career Fit methodology

## 1. Requirement importance

The extractor assigns a requirement level from local language cues:

| Level | Examples | Weight |
| --- | --- | ---: |
| must | must have, required, mandatory | 1.0 |
| strongly preferred | strongly preferred, essential | 0.7 |
| preferred | preferred, bonus, plus | 0.4 |
| inferred | mentioned without a clear marker | 0.2 |

The wording rules are intentionally conservative. They are not a claim that every employer uses these words consistently.

## 2. Requirement-level match

For soft requirement `j`:

```text
M_j = 0.35 C_j + 0.25 E_j + 0.20 P_j + 0.10 R_j + 0.10 D_j
```

Where:

- `C` is coverage: 1.0 for direct evidence, 0.55 for explicit transfer evidence, 0.45 for the same-category baseline, and 0 for missing evidence;
- `E` is evidence strength, weighted by evidence type;
- `P` is a conservative proficiency signal;
- `R` is recency;
- `D` is evidence depth, using duration when supplied.

Evidence Fit is:

```text
100 × Σ(weight_j × M_j) / Σ(weight_j)
```

This is a descriptive preparation index for the supplied text. It is not a probability and has no causal interpretation.

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

Measurable results receive a small transparent bonus. Context heuristics used for free text are labeled in the evidence object and do not override explicit structured evidence.

## 4. Capability Signal

For descriptive triage, direct evidence contributes 1.0, thin direct evidence 0.82, transferable evidence 0.60, and missing evidence 0.0. The signal makes adjacent experience visible while preserving a clear distinction from direct proof.

## 5. Proof Signal

Proof Signal averages evidence strength over the role’s soft requirements. It rewards evidence types with a reviewable work product, duration, recency, or measurable result. A low Proof Signal can indicate an evidence-packaging problem rather than a capability problem.

## 6. Hard gates

Licenses, work authorization, degrees, and explicit experience floors are checked separately. Their status is `met`, `not_met`, or `unknown`.

- `not_met` produces `blocked_by_constraint`;
- `unknown` produces `verify_before_applying`;
- `met` contributes no penalty to the soft Evidence Fit score.

## 7. Application Readiness

Application Readiness is:

```text
100 × (0.50 must-have match
      + 0.30 proof signal
      + 0.20 hard-gate signal)
```

The hard-gate signal is 1.0 when there are no unresolved gates, 0.35 when a gate is unknown, and 0.0 when a gate is explicitly not met. The result is a preparation route, not a prediction of interview or hiring outcomes.

## 8. Negation and missing evidence

The candidate parser applies a conservative local negation rule to phrases such as “no,” “without,” “not,” and “not yet” before a matched skill. Negated mentions remain in the output with `negated: true` for auditability but are excluded from the evidence match.

A missing mention is not evidence that a person lacks the capability. The interface therefore calls missing cases foundation gaps only as a preparation hypothesis and asks the user to verify whether the issue is actually a translation or proof gap.

## 9. Dictionary expansion and mapping discipline

The English dictionary combines a small transparent seed layer with exact labels from O*NET 30.3. The enrichment includes Essential Skills, Transferable Skills, Knowledge elements, and Software Skills marked Hot Technology or In Demand. Each enrichment entry retains its O*NET element ID, source file, source taxonomy, mapping method, match mode, and baseline confidence.

O*NET labels are mapped into the ten-category analytical layer only when the mapping rule is explicit. Named software uses exact-label matching; common-word software names such as React, Go, and Zoom also require nearby software context. Generic aliases such as bare Word, Project, and Access are not matched on their own. The dictionary does not treat occupational importance ratings as proof that a candidate has a skill, and it does not infer synonyms beyond the small alias list for common software names. Unmatched language remains unmatched rather than being forced into a category.

## 10. Multidimensional role fingerprints and skill bundles

The Role Fingerprint operationalizes a multidimensional mismatch view. For each taxonomy category `c`, the engine reports the importance-weighted evidence coverage of the named requirements that fall in that category:

```text
Category coverage_c = sum(weight_j × Match_j) / sum(weight_j)
Gap signal_c = 1 - Category coverage_c
```

The category is an explanatory layer only. Direct evidence, transferable evidence, and missing evidence remain attached to each named requirement. The largest dimensions are ranked by the category gap multiplied by the role's requirement weight.

Skill bundles are pairs of distinct named requirements that occur in the same supplied posting. Each pair receives the lower of its two requirement weights and the lower of its two match scores. The resulting card suggests an integrated proof artifact. It does not estimate complementarity, productivity, wages, or a causal hiring effect.

This design draws on the task-based and multidimensional mismatch literature, including [Guvenen, Kuruscu, Tanaka, and Wiczer](https://www.aeaweb.org/articles?id=10.1257/mac.20160241), [Deming and Kahn](https://www.nber.org/papers/w23328), and [Postel-Vinay and Lise](https://doi.org/10.1257/aer.20162002). The papers motivate the dimensions and user workflow; they do not validate Career Fit's descriptive scores.

## 11. Sensitivity and future validation

The most consequential modeling choices are importance weights, transfer rules, evidence-type weights, and missing-evidence treatment. Future releases should publish sensitivity tables under alternative choices and validate only on a consented, well-defined sample. A high score should never be presented as evidence that a candidate is more productive or more likely to be hired.
