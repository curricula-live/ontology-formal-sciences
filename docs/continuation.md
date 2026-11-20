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
