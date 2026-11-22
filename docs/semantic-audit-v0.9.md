# Semantic audit for v0.9.0

The review sampled 29 v0.8.0 scientific statements, 14 canonical subjects,
nine mapping decisions, and 13 new passage judgments. Selection uses a fixed
hash rank within subject scheme and evidence family, subject scheme and
admission method, source and mapping disposition, and new passage corpus.
The separate risk review covers source-level projections, batch identities,
and rejected passage interpretations. These strata and targeted cases support
specific findings. They do not estimate an ontology-wide error rate.
[Structured audit ledger](../reviews/quality/0.9.0.json)

| Finding | Disposition |
| --- | --- |
| A* identity | OpenCS C3339 and the authored A-star subject both refer to ordinary A* search. One IRI is deprecated with a reviewable replacement. The original source identity, concept record, and taxonomy remain available. |
| Topological sorting | The previous generic dependency on a directed acyclic graph is now an input assumption. The revised statement cites NetworkX and links to the previous interpretation in provenance. |
| Suffix automaton | The subject now distinguishes terminal-state acceptance of suffixes from arbitrary initial-state paths spelling substrings. The graph dependency uses the partial transition graph convention. |
| Independent random variable | The scope annotation identifies independence as a property of a family or joint law. The native class and admission record remain intact. |
| Legacy citation gaps | The reviewed passages cover fixed-point semantics in Lean's while-loop definition, NLTK's empty-clause resolution refutation, SciPy's conjugate-gradient inner products, and pgmpy's discrete MAP calculation. The MAP subject distinguishes posterior mass from a specified continuous posterior density. |
| Bayes ratios | The elementary statement requires positive probabilities of both conditioning events. The cited Mathlib statement uses a totalized conditional measure, so the elementary premise is recorded as an editorial interpretation together with its scope. |
| Unsafe source projections | The source-guided review withheld application of the comparison lower bound to radix sorting, an exact-Hessian premise for BFGS, recognition of all context-free languages by deterministic PDAs, and identifying SciPy's Jonker–Volgenant assignment routine as Hungarian. |
| Remaining ambiguity and evidence gap | The OntoMathPro reduced-group class still needs an independent scope witness for any stronger mapping. The sampled relationship from estimator bias to expected value needs a scope-specific source. CSO sample review uses stored witnesses. |

OpenMath operator occurrences still use \`containsSymbol\` and contribute only
to expression metrics. Its scoped mathematical properties still contribute to
scientific metrics. The code distinguishes source passage replay, editorial
review, and the separate Lean kernel probe. Textual source extraction from
Lean and Mathlib remains textual evidence.

## Reproduce the review

\`\`\`sh
git show 17c4c1d:dist/formal-sciences.nq > /tmp/formal-sciences-v0.8.nq
python -m pipeline.cli replay-semantic-audit --release 0.9.0 \
  --baseline /tmp/formal-sciences-v0.8.nq
python -m pipeline.cli replay-cs-evidence
python -m pipeline.cli replay-identity-migrations
\`\`\`

The audit reselects the sampled items and independently recalculates
participation for the v0.8.0 cohort. Use the reviewed pinned source cache with
\`--offline\` for network-independent replay. The release build and package
checks verify SHACL conformance, graph partitions, and artifact equivalence.
They provide a separate check from scientific review.
