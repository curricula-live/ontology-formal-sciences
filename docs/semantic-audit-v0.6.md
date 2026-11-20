# Semantic audit for v0.6.0

The audit covers seven source families, with 16 samples of existing batch
admissions and 24 targeted reviews of mappings, relation projections, OpenMath
statements and Mathlib declarations. The batch sample spans computer science, mathematics and statistics. Targeted
reviews also cover logic. Targeted cases include distinct predicates and cases with plausible
category or identity errors. This small sample and the deliberate selection of
difficult cases preclude an error-rate estimate.

[The audit ledger](../reviews/quality/0.6.0.json) records the source identities,
selection rule, label witnesses and editorial outcomes. To reproduce the batch
selection, use the v0.5.0 admission ledgers, keep minted source-prefixed
identities, and sort each source's IRIs by SHA-256 of the UTF-8 string
`0.6.0-strata` followed by NUL and the upstream IRI. Take the first four from
each source. The release build checks the audited identities and corrections
against the canonical graph. With staged snapshots available, run
`python -m pipeline.cli replay-semantic-audit --release 0.6.0 --offline` to
recheck the sampled labels against the pinned originals. The other audit cases
point to review records with separate source replay commands.

## Corrected existing admissions

- **CN2 rule induction.** OpenCS C17053 was admitted under the general
  Algorithms topic. Its native parent is Rule induction. The admission policy
  now places the same canonical subject under inductive rule learning in
  machine learning.
- **Free fall with air drag.** The MathModDB subject Q6675406 now explicitly
  denotes the drag-inclusive mathematical formulation.
- **Small-angle pendulum period.** Q6821441 now explicitly denotes a
  calculation in the linearized model.
- **Small-angle pendulum solution.** Q6821398 now explicitly denotes the
  solution of that mathematical formulation.

The remaining 12 sampled admissions retained their subjects and scopes.
Examples include the geometry of projective spaces, the Erlang distribution,
Welch's unequal-variance test, and linear balanced truncation. The batch
decisions and upstream identities remain available.

## Withheld candidates and identity decisions

| Source | Finding | Disposition |
| --- | --- | --- |
| OpenCS | The label “Material implication” refers to a particular inference rule in its explicit external reference. | Reject exact alignment to the Boolean truth function. |
| OpenMath | Seven formal witnesses contain a scope gap, role reversal or inconsistent expression. Examples include the direction of the not-subset witness, the range statement, and a vector body expressed with Boolean conjunction. | Retain the source statement identities, digests and reasons in the decision ledger. |
| ML-Schema | The same native property has distinct meanings for an evaluation result and a hyperparameter setting. A trained model output has a different role from an evaluation result. | Retain two rejected projections and three further candidates needing endpoint evidence. |
| Mathlib | Product commutativity is expressed as a type equivalence. Kleene's fixed point asserts equality of partial evaluations. | Decline projections to definitional equality. Preserve the exact source ranges and fingerprints. |
| OntoMathPro | The empty-set class, the mathematical topic and the OpenMath empty-set symbol have different types and purposes. | Publish a class reference and a scoped symbol binding, each with its own provenance. |

Spot checks on retained relations included the approximate t reference law for
Welch's test and the solution of a scoped drag-inclusive model. The broader
OpenMath audit also checked the nonzero condition in self-division and the
integer range of the factorial formula for binomial coefficients.

## Source boundaries

OpenCS generic associations aid disambiguation. Its hierarchy and associations
remain in staging and retain their SKOS meaning. The staged OntoMathPro
universals constrain fillers, so the RDF release preserves their review
outcomes without existential projections. OntoMathEdu has explicitly staged
object/formula partitions and existential axioms. Its publication rights
remain unverified. Existing CSO mappings continue to replay in evidence CI;
the pinned archive returned HTTP 403 in the release workspace. Mathlib module
imports remain source dependencies in staging.

The manifest reports candidate causes by source. A missing canonical subject,
a conflicting identity, an unreviewed mapping, weak evidence, or an
unsupported relation form requires a different review action. The report
counts excluded endpoint roles separately from unsupported relation semantics.
The selected-source assessments record licensing and dictionary scope limits.
