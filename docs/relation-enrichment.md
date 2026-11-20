# Source relationship enrichment

The pipeline extracts named source endpoints from pinned, named staging
graphs. Each profile defines the accepted source predicate IRIs and an RDF
axiom shape. MathModDB uses asserted triples. STATO uses immediate
`rdfs:subClassOf` restrictions with `owl:someValuesFrom`. OntoMathPro uses
`owl:equivalentClass` restrictions with `owl:allValuesFrom` as a review-only
profile. `skos:broader` and `skos:related` stay in the topical layer.

## Reproduce a source review

    python -m pipeline.cli replay-relations --source mathmoddb --offline
    python -m pipeline.cli replay-relations --source stato --offline
    ROBOT_JAR=/path/to/robot.jar python -m pipeline.cli replay-relations --source ontomath-pro --offline

`--write-evidence` recomputes the candidate file for review. The candidate
keys retain the source subject, source predicate key and source object.
The complete profile in `pipeline/curate/relations.py` resolves the key to
its predicate and declares the permitted direction. Decisions under
`reviews/relations/` bind both the source checksum and the profile checksum.
The build validates decisions against those keys, the source rights and
endpoint identity before it mutates the canonical graph. CI re-extracts
the source evidence and compares it with the committed record.

Canonical resolution uses admitted source identities and reviewed
`skos:exactMatch` decisions. A missing or ambiguous identity remains in
review. Label collisions, `rdfs:seeAlso`, class similarity and `skos:closeMatch`
supply no automatic endpoint identity. Projection needs a reviewed pair with
an explicit reason and a supported profile. For example, MathModDB
`used by` reverses into `appliesToModel` for reviewed mathematical tasks.
The definition preserves the specific application context.

Every approved edge carries a statement identifier and a provenance
witness with the original endpoints, source predicate, axiom shape and
snapshot digest. The witness records the editorial rationale. The
projection keeps OWL quantification in evidence metadata, and the
canonical graph remains a graph of SKOS subjects. Rejected pairs and
unresolved candidates retain their native identities in the review ledger.

The manifest counts the all-edge graph, the `skos:broader` subgraph, the
specific scientific subgraph, and its cited subset. Each subgraph has a
component-size histogram and scheme participation counts. Source
contribution metrics count distinct edges and participating canonical
concepts with replayable pinned evidence. An editorial citation also counts
toward the evidence-backed subgraph. Multiple witnesses for an edge can
contribute to multiple source totals.

## Representative audit

This editorial audit used a fixed sample of eight automatically generated
MathModDB subjects, six approved MathModDB source assertions and six
approved STATO projections. To reproduce it, independently order each
population by SHA-256 of `"0.4.0-source-audit\0" + key` and take the first
eight or six. Here `\0` is a NUL. A subject key is its complete native IRI.
An assertion key joins the three ledger fields with `|` in source order.
The audit checked the original pinned labels, descriptions, properties
and, for STATO, restriction shapes alongside each published interpretation.

| MathModDB subject | Judgment |
|---|---|
| Q6674306 | The finite-volume Darcy formulation has explicit spatial scope in the description. Keep it as a discretization topic. |
| Q6684570 | The H2 approximation topic is scoped to linear models. Keep it distinct from the bilinear variant. |
| Q6675409 | The Stokes model is an aggregate model record. It is distinct from the governing equation and its discretization. |
| Q6674142 | The bilinear input equation and its model context are explicit. |
| Q6775585 | The elastostatic no-body-force limit is narrower than the generic momentum balance. Keep the scoped topic and withhold the candidate link to a generic weak form. |
| Q6674143 | The description identifies the reduced bilinear input equation. Preserve the distinction from the starting equation. |
| Q6775737 | The record identifies the discretized weak momentum equation. Preserve both qualifiers. |
| Q6775296 | The elasticity record is scoped to a plate with a hole. The subject therefore retains the geometry qualification. |

| Evidence key | Judgment |
|---|---|
| Q6684552 / P1560 / Q6674144 | The model-reduction task explicitly records the reduced linear output equation as a component. |
| Q6675332 / P147 / Q6684561 | The documented time-evolution task applies to the bilinear model. The canonical direction starts at the task. |
| Q6674148 / P1655 / Q6674149 | Source descriptions distinguish the starting and reduced linear input equations. |
| Q6675333 / P147 / Q6684551 | Linear balanced truncation is documented on the LTI model. |
| Q6684551 / P1560 / Q6674148 | The LTI truncation task includes its unreduced input equation. |
| Q6675332 / P147 / Q6684558 | The bilinear H2 case is confined to the documented model. |
| 0000653 / input / 0000229 | Hosmer–Lemeshow uses an approximate chi-square reference. Preserve the distinction from an exact null law. |
| 0000285 / input / 0000060 | The hypergeometric test uses the matching conditional count distribution. |
| 0000309 / input / 0000229 | The Pearson goodness-of-fit statistic uses a chi-square approximation under its regularity conditions. |
| 0000426 / target / 0000421 | The Hunter–Schmidt record identifies the between-study variance estimand in context. |
| 0000095 / input / 0000059 | The paired t-test uses Student t for a statistic of paired differences under the null. |
| 0000425 / target / 0000421 | The Sidik–Jonkman estimator targets the between-study variance. |

Negative review cases include a mis-scoped Darcy time discretization,
the distinction between normality as a sampling assumption and the
Shapiro–Wilk reference distribution, and the distinction between a
universal OWL restriction and a witnessed defining relationship. See the
committed decisions for the rationale on each of the 11 rejected pairs.
These observations describe the reviewed sample and the stated
projections. Candidate coverage varies by source and by predicate.
