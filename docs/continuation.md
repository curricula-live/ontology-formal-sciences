# Release review and next work

1. Review the initial canonical modules, especially the broad domain placement and the mapping ledger. Approvals in this release are editorial decisions prepared for this PR. Qualified maintainers can revise or reject them with explicit reasons.
2. ACM CCS needs an authorized downloadable classification and confirmed redistribution rights. The DMOP origin returned HTTP 504. Acquire a provenance-verifiable v5.4 snapshot from the authors or an authorized archive. Avoid substituting an ontology that merely imports its IRIs.
3. Review sampled sources individually before broadening coverage. OpenAlex research topics are bibliographic clusters. Mathlib extraction inventories source modules; formal theorem signatures and proof dependency extraction require Lean elaboration. OEIS contains one sequence. TPTP contains one problem's clause headers. zbMATH and DLMF each cover one resource. RDF/RDFS currently covers the RDFS schema document.
4. Larger source staging remains local/private by default. Mutable upstream URLs may cease to reproduce previously acquired bytes. Retain a lawful private mirror and restore exact bytes under original/snapshot before offline ingest. Generated archive headers and API timestamps can change even if the underlying facts remain equivalent. An integrity mismatch requires explicit review.
5. Canonical release graphs currently fit in RDFLib memory. Staging is disk-backed; benchmark memory before expanding the canonical release to millions of triples. A streaming publisher will be needed before admitting that volume.

The Phase 0 byte snapshots are preserved by digest in the project owner's private archive on tower. Fetch checks FORMAL_SCIENCES_SNAPSHOT_DIR or the default ~/.local/share/curricula/formal-sciences/snapshots location before using the network. Three endpoints produced different bytes immediately on refetch (DBpedia, TPTP and zbMATH). Restore the archived bytes to reproduce those exact historical documents. A public CI runner without that archive reports their drift in the weekly network audit.

For automatically opened GitHub PRs to trigger a separate pull_request run, configure ONTOLOGY_REVIEW_TOKEN as a repository-scoped GitHub App token or equivalent automation credential. GitHub suppresses recursive workflow events initiated with the default GITHUB_TOKEN. With the default token, a maintainer can push the reviewed revision to trigger the PR checks before merge.


## 0.2.0 development scope

Three checksum-pinned batches add 2,091 new canonical headings. OpenCS
contributes 908, OntoMathPro 867 and STATO 316. STATO also reuses 17
existing canonical IRIs. The modules record editorial subject hierarchies
and leave source-specific OWL modeling in staging. The release connects all
2,450 concepts in one weakly connected component, with 55 explicit
cross-domain edges. See the manifest for the complete measured distribution
and the competency queries for concrete relationship evidence.

The context-sensitive OpenCS admission policy covers selected computing
families. OntoMathPro covers a reviewed English subset. STATO covers
selected native statistical classes. Expansion remains uneven across domains,
particularly logic. The logic extension adds modal systems, Kripke semantics and branching-time verification. Pending candidates require source scope and sense review.
ACM CCS publication rights, DMOP acquisition and the unrecovered historical
snapshots remain open. Formal theorem extraction from Lean still requires
elaboration, and the Mathlib adapter currently indexes module dependencies.

The three batch snapshots and the historical OntoMathEdu bytes were
verified in the development environment. The cloud proxy returned HTTP 403
for the historical CSO download during this replay. Existing CSO review
evidence and hashes remain in the release, and replay requires access to the
registered upstream or the digest-indexed archive.

The release build uses in-memory RDFLib and performs serialization round
trips. Staging and the independent package verifier use disk-backed stores.
Use `python -m pipeline.benchmark build` and
`python -m pipeline.benchmark parse --source opencs` on Linux to measure
local build and parse costs. The latter requires a local verified snapshot.

## 0.3.0 development scope

This stage adds 63 authored subjects across logic, mathematics, computer
science and statistics. Logic grows from 78 to 115 concepts. The new
modules cover SMT, equality reasoning, rewrite systems, proof theory,
type safety, dependent types and model theory. Mathematical coverage
includes polynomial factorization, elementary number theory,
generating functions and algebraic topology. The RDF reuses the OpenCS
Cantor–Zassenhaus subject and the OntoMathPro fundamental-group subject.

Across the full release, specific scientific predicates connect 200
concepts through 159 assertions, with 56 crossing a scheme boundary.
The baseline is 117 concepts, 95 assertions and 37 cross-scheme assertions
under the same definition. The largest scientific component has 21
concepts in both versions. The full SKOS graph remains connected.
See the manifest for predicate counts, citation coverage and the number
of concepts outside the scientific subgraph.

The audit of v0.2.0 records 30 judgments from the pinned source batches.
It led to three scope corrections with stable IRIs and flagged three
topics for further review. The reconciliation pass approves 20 OpenCS
topic matches and 13 OntoMathPro class references. It rejects four
candidate pairs involving mismatched scope or bilingual ambiguity.
The CSO reconciliations reuse previously approved decisions and the
matching OntoMathPro references. The historical CSO snapshot remains
unavailable through the local cloud proxy.

- [Batch audit and sampling procedure](semantic-audit-v0.2.md)
- [SPARQL queries and observed results](queries/README.md)

## 0.4.0 development scope

Source relationship profiles retain 2,819 candidate triples or named
restriction witnesses. The canonical graph uses 51 MathModDB and 21
STATO assertions after review. Eleven explicit rejections preserve
source IDs and decision rationales. MathModDB contributes 43 new
canonical subjects covering mathematical models and numerical methods.
The science extensions add 23 logic subjects, including theory
combination, proof terms, normalization and type-theoretic proof
checking. The mathematical extensions cover lattice fixed points,
linear arithmetic and linear-system model reduction.

The release contains 2,590 canonical concepts. The specific-relation
subgraph has 274 edges touching 308 concepts, with a largest component
of 36. The evidence-backed view has 254 edges touching 286 concepts,
with a largest component of 33. Applying the same metric to v0.3.0
gives 139 edges touching 178 concepts and a largest component of 12.
The evidence view includes pinned source witnesses and published
statement citations. The three new competency queries verify these
joins across the asserted, alignments and provenance graphs.

Only a subset of extracted source endpoints has reviewed canonical
identity. MathModDB contributes most of the unresolved candidates,
including applied topics and notation beyond this formal-sciences slice.
Ontology expressions beyond the registered shapes require a separate
semantic review. OntoMathPro's universal restrictions remain source
evidence for review. See the [relationship enrichment guide](relation-enrichment.md)
for the profiles, review procedure and 20-item sampled audit.

## 0.5.0 development scope

The release inventories 2,875 source candidates and records 173 approved
source projections and 18 explicit rejections. Of the 2,653 candidates
with unresolved endpoints in v0.4.0, 81 now have approved canonical
relations. The reviewed MathModDB cohort adds 49 subjects. Seven scoped
endpoint projections reuse existing or newly authored subjects across
MathModDB and STATO, including the OntoMathPro finite element method,
state-space matrix roles, the Poisson log-likelihood and two statistical
estimation procedures. The added logic coverage includes System F,
parametricity, structural induction, proof assistants and abstract
interpretation.

The endpoint report identifies 745 candidates outside the current
MathModDB profile by source role and 545 in the two reviewed applied
contexts. Another 1,168 MathModDB candidates still require domain scope
review. The decisions also expose pending subject admissions and
mapping reviews in STATO, plus 71 review-only OntoMathPro universal
restriction candidates. Prior rejection records and the IDs of all
2,590 v0.4.0 concepts remain in the release history.

The published graph contains 2,667 concepts, 399 specific scientific
relations and 389 participating concepts. With only cited or pinned
scientific edges, 367 concepts participate in 62 components, with 55
concepts in the largest. The corresponding v0.4.0 sizes were 286, 54
and 33. See the [semantic audit](semantic-audit-v0.5.md) and the
[endpoint replay guide](relation-enrichment.md).

## 0.6.0 completed scope

OpenMath, ML-Schema and selected Mathlib declarations joined the MathModDB
and STATO evidence profiles. The release contained 2,751 canonical
subjects and 534 scientific statements, including 514 with evidence.
Scientific statements touched 480 subjects. The largest evidence-backed
component contained 85 subjects, and 67 evidenced edges crossed schemes.
The audit reviewed 40 cases, clarified four subjects and recorded 12
withheld interpretations. [v0.6.0 semantic audit](semantic-audit-v0.6.md)

## 0.7.0 completed scope

The release contains 2,849 subjects and 702 specific scientific edges.
There are 682 evidence-backed edges, touching 556 subjects in 70
components. The largest evidence-backed component has 199 subjects.
Evidenced cross-scheme edges increased from 67 to 82. OpenMath now
reviews 190 formal properties from 23 content dictionaries. STATO
distinguishes test statistics, reference laws and computed diagnostics.
Reviewed OpenCS subjects extend logic, proof theory and computability.
Full native-neighborhood counts identify OpenCS and OntoMathPro endpoint
limitations. Shared DBpedia anchors join OpenCS evidence with approved
CSO witnesses for review. The Mathlib index records visible declaration
headers in 8,728 source files and preserves selected proof occurrences
with exact source anchors.

The manifest reports participation and evidence by scheme, predicate, type
and source. Individual competency queries demonstrate the statistical use
of multiset multiplicity, the use of derivative rules in automatic
differentiation, and the separate roles of a proof, a result and a named
ingredient. Common operation subjects connect many of the new expressions.
The local manifest also records source-specific gaps.
[v0.7.0 semantic audit](semantic-audit-v0.7.md)

## Remaining milestones

- Ground scientific claims for the 2,272 subjects outside the scientific
  subgraph. Prioritize existing concept neighborhoods in probability,
  program semantics, proof theory and discrete mathematics, with scoped
  independent witnesses where native predicates express topical association.
- Reproduce the full CSO neighborhood against the pinned bytes. The cloud
  workspace cannot fetch the registered CSO host. Existing mapping
  evidence can replay in GitHub CI.
- Review unresolved OpenMath dictionary scope and symbol identities,
  including references to absent symbols. Preserve the corrected scope of
  formula statements across subsequent snapshots.
- Establish a pinned Lean toolchain and object environment to export
  elaborated types and actual proof dependencies. Report those separately
  from the textual declaration and import indexes.
- Finish source acquisitions and rights verification for OntoMathEdu,
  ACM CCS and DMOP. Retain quantified OWL meaning and native identifiers
  in source review. Continue benchmark work before million-triple releases.
