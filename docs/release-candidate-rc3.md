# Formal Sciences v1.0.0-rc.3: review-driven delta

This isolated candidate is based on v1.0.0-rc.2
(`c7bb08f54dc2b8909e93e1f1763a551b17eeea2c`).
It adds no canonical concepts, source admissions, mappings, approved scientific
relationships, graph identifiers, or ontology contract changes.

## Changes

- Added explicit column-mean-centering qualifications to the **exact**
  statement-level provenance records for
  `svd-principal-component-analysis computes eigenvector` and
  `svd-principal-component-analysis uses singular-value-decomposition`.
  The existing PCA/SVD evidence is preserved.
- Expanded `NOTICE.md` to identify pinned OpenStax (CC BY-NC-SA 4.0)
  and Dive into Deep Learning (CC BY-SA 4.0) sources used **only**
  as independently interpreted evidence, citations and fingerprints.
- Both channels now have `unresolved` rights dispositions, rather than
  implying that owner/qualified review has already happened.
- Added the two channels to the notice's pinned `applies_to` inventory.
  The contract validator also continues to accept the pre-existing three
  source-family notice list from the pinned rc.2 predecessor.
- Clarified that a source reference used as a contrast must be explicitly
  distinguished by statement-level review scope (the Bayes/Mathlib case).
- Kept all previously published provenance. A proposed removal of the
  uncited DPDA prefix-free qualification was **not** applied because the
  successor-compatibility validator correctly forbids deleting historical
  provenance. This remains an S3 advisory, explicitly listed in
  `reviews/quality/rc3-delta.json`.

## Reproducible release

Expected candidate manifest SHA-256:

`a30bf1f5e2baaf01b06c8efbc8d74eaea73d7bfceede586b34c94fe2d8f8d477`

Distributable notice SHA-256:

`5d9b564fc88df41e2ff85590bb5245b60e9827e5182a475ddf698a5303bb7d88`

The six package files retain the `curricula.rdf-release/v1` contract.
The four graph counts are asserted 13,483, inferred 3,093, alignments 234,
provenance 19,781. The rc.2-to-rc.3 successor changes preserve all
published canonical and review decisions.

The review inputs are `reviews/quality/rc3-plan.json`,
`reviews/quality/rc3-delta.json` and
`reviews/quality/rc3/independent-review.json`.
The impact file compares against the rc.2 packet; newly added SVD
statement targets are included in the rc.3 targeted review rather than
retroactively changing earlier verdicts. Every assessment remains unassessed.

### Checks

The isolated Linux checkout on Python 3.14 returned
110 passed, 2 skipped; the two optional source-dependent checks have
not yet been replayed in this environment. Package verification and the
competency suite passed. A fresh disposable **Apache Jena Fuseki 5.6.0 / TDB2 rehearsal passed** all
six stages against the pinned rc.2 predecessor, including failure injection,
replacement, TDB2 reopening, and rollback. Its evidence is committed as
[rc.3 Fuseki rehearsal](../reviews/quality/rc3-fuseki.json). The authoritative
remote release gate is CI on the exact pushed commit, followed by scientific
and rights sign-off.

## Publication gates

**No stable release approval is implied by this patch.**

- A qualified reviewer/owner must confirm OpenMath derivative-work
  terms, native STATO/OBI scope, OpenDSA evidence-only use, and the new
  OpenStax/d2l evidence-only channels.
- An independent human scientific review is needed for the unresolved
  high-risk source cases; the previous AI review is not human approval.
- Confirm the final release notice is uploaded beside the six package
  files; the existing tag workflow attaches `NOTICE.md` separately.
- Require a clean candidate build, import and rollback verification before
  stable tag or merge.

This isolated branch is intended for careful review and integration into
`feat/formal-sciences`; it must not modify `main` or publish a tag.
