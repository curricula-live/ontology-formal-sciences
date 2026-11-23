# Semantic audit for v0.7.0

The review covers 40 cases across six source families. It retains 29 scoped
interpretations and withholds 11 candidates. Five cases are a reproducible
sample of the new OpenCS cohort. The remaining cases target specific
formal-expression, OWL role, identity and proof risks.
[Review ledger](../reviews/quality/0.7.0.json)

| Area | Result |
| --- | --- |
| OpenMath guards | The ties-to-even rule retains the half-integer guard. The proper-subset property explicitly records its occurrence in the premise. |
| OpenMath source defects | The closed-interval expression uses an undeclared comparison symbol. One sample-statistic expression discards repeated observations, and a distribution standard-deviation expression lacks its square root. These statements stay withheld. |
| OpenCS and OntoMathPro identity | A source topic and its explicit referent support the Curry–Howard mapping. The complex-plane class supports a scoped reference from the canonical coordinate representation, which has its own Mathlib witness. |
| ML-Schema role boundaries | The source model distinguishes the run, executable implementation, abstract algorithm, measure, and recorded evaluation. The hyperparameter property use and trained-model output remain withheld for evaluation projections. |
| Mathlib proof and formula levels | The empirical measure counts multiplicity and needs a nonempty sample for the probability claim. The derivative theorem has individual differentiability premises. The fixed-point proof involves extensional program behavior and has a separate subject from the theorem it proves. |
| STATO input and output | Welch's test has distinct statistic and reference-law roles. PLS uses diagnostic outputs in the reviewed scope. Normality and continuity describe assumptions in two withheld test-input candidates. |

The audit samples risk cases by design, so the counts describe this
review rather than an estimated error rate. Source replay verifies the
sampled labels, declaration ranges and original relation witnesses.
Competency queries verify the published roles and their evidence paths.
[Mathlib source scope](../sources/mathlib4/README.md) · [Query catalog](queries/README.md)
