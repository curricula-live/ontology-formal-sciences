# Semantic audit for v0.8.0

The baseline sample covers 37 scientific assertions and 14 canonical
subjects. It uses fixed hash ranking within subject-scheme and evidence-family
strata for assertions, and within scheme and admission-method strata for
subjects. An additional sample selects one approved judgment per new primary
source corpus, for eight cases. The separate targeted review checks 14
known ambiguity, scope and source-role risks. Sample outcomes describe
the reviewed cases, with no graph-wide error-rate estimate.
[Structured review ledger](../reviews/quality/0.8.0.json)

## Findings

| Finding | Disposition and evidence |
| --- | --- |
| OpenMath expression edges | The full inventory of 230 edges comprises 167 symbol occurrences and 63 scoped properties. The new projection preserves native identities, the source expression digest, and guard occurrences. Former interpretations remain in provenance. |
| Mathematical class membership | Adjacency matrices and matrix-scope graph Laplacians belong to the matrix class. Their former generic dependencies are now hierarchy. The independent adjacency-matrix representation claim survives. |
| Theorem hypotheses | Completeness and monotonicity in Knaster–Tarski, and termination and local confluence in Newman's lemma, are premises. The fixed-point result is recorded separately as a guarantee. |
| Algorithms and artifacts | DPLL and CDCL invoke unit propagation. The Princeton executable realizes Dijkstra's algorithm. Raft's TLA+ specification represents its protocol. The reviewed negative ledger preserves the rejected implementation interpretation. |
| Feature hashing placement | OpenCS C44766 stays on its existing IRI. Its canonical parent is now Feature extraction, based on the methodology and the reviewed sparse feature output. |
| Source scope | A small-angle damped and driven pendulum subject now explicitly denotes its mathematical model. The raw OpenCS and OntoMathPro association and restriction roles stay in their original evidence. |
| Identity ambiguity | The two published A* subjects require reconciliation. The OntoMathPro reduced-group class requires a more precise mathematical convention before stronger mapping. |
| Additional assumptions and remaining gaps | Elementary Bayes ratios require positive conditioning probabilities. Four sampled legacy relationships still lack scope-specific citations. The queue dependency of breadth-first search gained a source witness. |
| ML-Schema | The model keeps implementation, execution run, evaluation and measure roles separate. Output of a trained model and assignment of a hyperparameter remain withheld as evaluation projections. |
| Lean | The pinned toolchain checked two local fixtures. Actual direct type constants, direct proof constants and transitive axioms are recorded separately. Mathlib passages remain textual because its object cache returned HTTP 403. |

The two-part interval and distinctness premises remain attached to their
source statements. The first- and higher-moment density formulas retain their
finite-moment scope. The review withholds unsupported cardinality and symbol
projections, including a sample expression that collapses duplicate values
and a formula referencing an undeclared interval symbol.

## Reproduce the sample

Retrieve the exact v0.7.0 N-Quads artifact, then replay the selection and
sampled source labels.

```sh
git show ed04aa8:dist/formal-sciences.nq > /tmp/formal-sciences-v0.7.nq
python -m pipeline.cli replay-semantic-audit --release 0.8.0 --offline \
  --baseline /tmp/formal-sciences-v0.7.nq
```

The build checks current assertions and their archived predecessors against
the review ledger. Mathematical and computing evidence has separate replay
commands. [Source relationship guide](relation-enrichment.md)
