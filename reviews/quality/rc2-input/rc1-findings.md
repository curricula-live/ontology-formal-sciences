# CURRICULA.LIVE — v1.0.0-rc.2 SCIENTIFIC CORRECTION AND RIGHTS REMEDIATION

Continue `curricula-live/ontology-formal-sciences` from the exact reviewed v1.0.0-rc.1 candidate:

`083f22b2f25c5cb520838c6b3eec22fea0072b6c`

Work on `feat/formal-sciences`.

An independent AI reviewer examined 148 items from rc.1 and returned **ACCEPT WITH CORRECTIONS**.

The review identified no confirmed S1 identity or relation-direction defects, but several scientific scope errors, unsupported assertions and source-rights issues.

The objective is to produce **v1.0.0-rc.2**, resolving every actionable finding without reopening broad ontology development.

## Hard constraints

- Do not modify other repositories or `main`.
- Do not merge PR #1, create a stable tag or publish v1.0.0.
- Preserve all canonical IRIs and approved/rejected mapping decisions.
- Do not add new concept cohorts or optimize connectivity.
- Do not fabricate citations, licensing permissions or independent review verdicts.
- Preserve reviewable records of statements corrected or withheld.
- Do not silently remove assertions or rewrite provenance.
- Make focused commits and push progress checkpoints.
- Do not repeat broad repository research.

Use the independent review findings below as a **correction specification**, not as proof that all scientific assertions have been independently validated.

## 1. Source-rights remediation

### OpenMath

Inspect the actual selected dictionary ledger, pinned source notices and release distribution.

The reviewer found 23 selected dictionaries, while older documentation describes only ten official dictionaries plus `combinat1`.

Correct the documentation to match the verified ledger, distinguishing official and experimental dictionaries.

Add a distributable notice that:

- Credits the OpenMath Society and relevant dictionary authors.
- Identifies the derived material and its original dictionaries.
- Clearly states that Curricula's RDF projection is not the original OpenMath Content Dictionary.
- Preserves the applicable derivative-work notice conditions from the pinned sources.
- Links to the original sources and identifies the selected source revisions.

Ensure the notice is discoverable from the README, release metadata and future release assets.

**Preserve the exact existing six-artifact RDF package contract.** Do not add a seventh file to `dist/` if that would invalidate the release profile. A repository-level NOTICE, structured manifest rights fields and release-asset documentation are acceptable when consistent with the contract.

Do not independently declare OpenMath legally cleared. Maintain its unresolved owner-review status.

### STATO

Add an explicit, distributable STATO attribution and rights notice identifying:

- STATO's CC BY 3.0 licence.
- The pinned source revision.
- Original source attribution.
- The presence of separately attributed embedded OBI content.
- The specific native identifiers, labels and relation projections published by Curricula.
- Any transformations made by the project.

Add or strengthen tests ensuring that source-native projections do not silently expand into imported OBI-owned content.

Maintain the legal-review gate until the actual redistribution conditions are confirmed.

### OpenDSA

Keep OpenDSA in the evidence-only channel:

- Pinned references.
- File hashes.
- Independently authored scientific judgments.
- No copied source text or code.

Verify the documented MIT notice and flag any file-specific terms encountered.

Do not mark owner approval as completed.

## 2. Correct the six uncited scientific assertions

The reviewer identified six existing `uses` relations without citation entries, contradicting the documented evidence policy.

Investigate them individually:

1. `conflict-driven-clause-learning → clause-learning`
2. `huffman-coding → tree-graph-theory`
3. `bias-of-an-estimator → expected-value`
4. `probabilistic-graphical-model → graph-graph-theory`
5. `gradient-descent → derivative`
6. `graph-algorithm → graph-graph-theory`

For each:

- Verify scientific meaning and predicate applicability.
- Locate a credible, precise, primary or authoritative source.
- Record a replayable citation and the correct scope, if possible.
- Prefer a more accurate existing predicate or existing canonical endpoint when justified.
- Withhold the assertion if sufficient evidence is unavailable.

Specific cautions:

- Huffman coding produces a rooted binary prefix-code tree; avoid an unnecessarily broad mathematical implication.
- Estimator bias is a statistical property, not a method-to-ingredient relationship.
- Gradient descent uses gradients, not an arbitrary derivative concept.
- The generic graph-algorithm relationship may be better modeled as an input-structure relation or withheld.

Preserve the former published interpretation in review/provenance records when correcting or withholding a statement.

Make the asserted citation policy testable in CI, without requiring citations for predicates to which that policy does not apply.

## 3. Correct confirmed scientific issues

### Knaster–Tarski

Correct the definition of `knaster-tarski-fixed-point-theorem`.

The fixed-point set of a monotone self-map on a complete lattice forms a complete lattice under the induced order.

Do not imply that arbitrary fixed-point subset suprema and infima are necessarily calculated as the corresponding suprema and infima of the ambient lattice.

Maintain the canonical IRI and Result role.

Add a semantic regression test with a finite monotone-lattice counterexample if practical.

### Cantor–Zassenhaus

Inspect the existing assertion:

Cantor–Zassenhaus `computes` an irreducible polynomial over a field.

The algorithm performs randomized factorization over finite fields; the current object and scope are misleading.

Retarget only if an appropriate existing canonical concept and evidence support the correction. Otherwise withhold the assertion with an explicit review record.

Do not create a new concept merely to rescue the edge.

### Propositional-resolution soundness

Review the two `uses` edges connecting soundness of propositional resolution to logical disjunction and logical negation.

These are not clearly method-to-ingredient dependencies.

Withhold the two statements and record the semantic reason, unless an existing formally appropriate predicate and strong evidence clearly justify replacement.

### Bayes' theorem

The current Mathlib citation describes a totalized convention and does not directly establish the positivity premises for ordinary conditional-probability ratios.

Find a suitable authoritative source for the standard ratio form and its conditioning requirements.

Keep the Mathlib source as explicitly contrasting evidence when appropriate.

If the assertion cannot be supported at its published scope, withhold it.

### Welch's t-test

Clarify that the Student's t reference distribution is an approximation under the Welch–Satterthwaite degrees-of-freedom treatment.

Record the exact review scope.

Document that `usesReferenceDistribution` may describe exact or approximate reference laws, with the relevant qualification attached to assertions.

Do not equate a native source's generic specified-input relationship with a mathematically established reference-distribution assertion without editorial evidence.

### Deterministic pushdown automata

For `recognizesExactly` deterministic context-free languages, verify and document the acceptance convention.

Use authoritative evidence for final-state acceptance. Do not generalize the same claim to empty-stack acceptance.

Withhold or narrow the assertion if the evidence does not support the convention.

### PCA via SVD

Clarify that the covariance eigenvector correspondence requires mean-centered data.

Record the scope without changing canonical identity.

## 4. Address smaller semantic ambiguities

Perform only concise scope and documentation corrections:

- `inductive-recursion`: distinguish structural recursion over inductive types from the separate notion of induction-recursion.
- `transition-matrix`: clarify that this record concerns a stochastic-process transition matrix rather than all uses of the phrase.
- `behavioral-regression`: review whether the current role classification is sufficiently specific.
- `context-free-language`: clarify instance versus language-family semantics.
- MathModDB task/model records: document source granularity without reclassifying the entire cohort.
- Deprecated A*: ensure the active algorithm remains discoverable through appropriate navigation without introducing a hierarchy cycle.

Do not perform a broad identity or taxonomy migration.

## 5. Regression tests and scientific QA

Create focused regressions for every confirmed correction.

In particular, tests should reject:

- Unsupported method-to-ingredient relationships for theorem/result entities.
- Uncited scientific assertions under the defined citation policy.
- Incorrect finite-field factorization output scope.
- Unsupported generalization of reference-law assumptions.
- Incorrect graph changes resulting from identity migrations.

Preserve the distinction between technical evidence replay and scientific validity.

Archive the original rc.1 review findings.

Regenerate a new rc.2 review packet with all assessment fields **unassessed**. Do not copy the previous reviewer's verdicts into the new candidate as though the candidate itself had been reviewed.

Provide a deterministic change-impact report identifying which rc.1 review items are unchanged, corrected, withheld or require re-review.

## 6. Release candidate generation

After correcting the identified issues:

1. Run focused tests during development.
2. Rebuild the RDF release deterministically.
3. Run the complete suite once against the final candidate.
4. Verify all competency queries, SHACL constraints and identity migrations.
5. Replay applicable source evidence.
6. Independently check artifact hashes and dataset equivalence.
7. Run a clean-checkout reproduction.
8. Rerun the necessary Fuseki/TDB2 replacement and rollback rehearsal against the **new manifest digest**.
9. Update the rights inventory, coverage report and known limitations.
10. Prepare the v1.0.0-rc.2 readiness report.
11. Commit and push all changes to `feat/formal-sciences`.
12. Verify both GitHub Actions workflows on the resulting commit.

Do not declare the previous rc.1 Fuseki test sufficient if the candidate data or importer behavior have changed.

Preserve the existing release contract and logical graph IRIs.

The manifest should continue to state release status `candidate`, not stable.

## 7. Required final report

Report:

- Final commit SHA and clean working-tree status.
- Files changed and scientific assertions corrected, replaced or withheld.
- Source notices added and their exact publication locations.
- Remaining rights questions requiring owner approval.
- Exact test counts and GitHub CI results.
- Reproducible release manifest SHA-256.
- Fuseki/TDB2 rehearsal outcome for rc.2.
- Independent-review packet location.
- Unresolved scientific questions.
- Explicit PASS / FAIL / BLOCKED / NOT RUN release gates.

End with either:

**RELEASE CANDIDATE READY — PUBLICATION GATED**

or:

**RELEASE CANDIDATE NOT READY — CORRECTIONS REMAINING**

Do not merge PR #1, create v1.0.0 or mark the project independently verified.

## Resource discipline

This is a **bounded correction cycle**, not another broad stabilization programme.

Do not explore unrelated scientific sources, add new ontology cohorts, redesign the producer or repeatedly run every test after small changes.

Commit verified milestones frequently so progress survives an execution-limit interruption.

Prioritize correcting scientifically false statements and shipping required source notices over optional cosmetic documentation changes.