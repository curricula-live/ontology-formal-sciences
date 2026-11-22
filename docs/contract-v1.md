# Curricula RDF release contract v1

A package consists of manifest.json and exactly five hashed artifacts. Pin the Git commit and manifest SHA-256 together. The ontology version describes the semantic release line. A commit identifies the exact build. Contract-major changes require a new contract string.

| File | Meaning |
|---|---|
| formal-sciences.ttl | All approved canonical assertions, including vocabulary declarations. Sorted N-Triples form is a valid Turtle serialization. |
| formal-sciences.trig | Named graphs for asserted knowledge, alignments, inference and provenance. Default graph is empty. |
| formal-sciences.nq | The same quads as TriG. |
| source-alignments.trig | Only the reviewed alignments graph. |
| validation-report.json | Conformance and closed-world findings. |
| manifest.json | Contract ID, ontology version, source roster, evidence revisions and authors, named graph sizes and SHA-256 hashes of the five other files. |

## Logical graphs and package identity

The four logical graph IRIs are the namespace followed by
`graph/asserted`, `graph/inferred`, `graph/alignments` and
`graph/provenance`. They do not encode the release version.
A consumer chooses its physical storage, staging, activation, and rollback
strategy. The default graph is empty.

The supported intake pins an immutable Git commit and the SHA-256 of its
exact manifest bytes. That pair is the receipt. The manifest has no embedded
copy of the commit or of its own digest. `ontology.yaml` supplies the sole
producer ontology version, while `contract` defines the wire format.
For v1 candidates, the required `release` metadata includes status,
scientific maturity, and the fixed graph map. The required `rights` inventory
gives channel-specific terms and attribution. Existing pre-v1 packages using
this same contract remain readable without these additive fields. Source and
quality diagnostics can grow without changing the artifact inventory.

Verify the pinned manifest, its schema, all artifact hashes, graph roles and
counts, dataset and standalone graph equivalence, and valid inference.
RDFLib and Oxigraph parse and compare every RDF artifact independently.
The consumer also checks that replacement arcs resolve to live subjects in
the same canonical scheme and that candidate retirement has recorded
provenance. The reference consumer copies the package into an isolated
staging directory and changes the pointer in one SQLite transaction. A
failed validation, load, or update leaves the prior package active. Reads
hold their selected snapshot across later transactions. Rollback selects a
previously accepted receipt.

```sh
python -m pipeline.package_check dist --manifest-sha256 "$manifest_digest"
python -m pipeline.consumer "$scratch_dir" install dist "$release_commit" "$manifest_digest"
python -m pipeline.consumer "$scratch_dir" resolve https://curricula.live/id/formal-sciences/concept/opencs-c3339
python -m pipeline.consumer "$scratch_dir" rollback "$previous_commit"
```

Consumers get the commit and digest through a trusted producer handoff.
The checkout-based consumer verifies package integrity against that pin.
It does not authenticate Git objects or implement a production database.
The producer builds and verifies packages entirely within this repository.

## Version and maturity

An additive compatible release can publish new concepts, evidence, optional
roles and metadata under the existing namespace and graph contract.
An editorial correction refines wording or a scientific statement while
preserving denotation. Record the reason and preserve scope and statement
history. The reference compatibility gate conservatively flags changes to a
previous preferred label, definition or scheme for review. An identity
migration preserves the old IRI as a resolvable record and discloses the
replacement or split. Reinterpretation of an established IRI, changing the
meaning of a graph, mandatory consumption changes, and removing permanent
identities are incompatible. Version increments reflect actual semantics
and wire changes.

Foundation, Expanded and Mature describe scientific maturity. Candidate and
stable describe publication status. A package can be technically valid and
still require independent scientific and rights approval. The immutable Git
commit and manifest digest identify exact contents within either stage.
The tag workflow requires an accepted commit on main and stable status for
the v1 publication path. See the [readiness report](release-candidate-v1.md).

The source inventory includes admission summaries for registered batches.
The provenance graph connects each generated module to its reviewed batch,
source revision, digest and attribution. A topic's `dct:source` identifies
the source entity that supports the topic. Approved SKOS mapping triples
retain their own review provenance. The manifest's quality object reports
coverage and distinguishes pending mapping pairs from pending admission
entities.

The manifest reports `quality.scientific_connectivity` over asserted
concept-to-concept edges with project scientific predicates. It counts
the endpoints, weak components, cross-scheme edges and edges backed by
statement citations. SKOS hierarchy and generic associations contribute
to the full graph metrics separately. Consumers can compare both views
to track the depth and reach of scientific assertions.

Source-derived scientific statements carry a provenance witness with
the original endpoint IRIs, source predicate, axiom shape, snapshot
digest and review rationale. The witness is linked from the canonical
statement using `prov:wasDerivedFrom`. Its RDF reification terms identify
the source expression under the recorded axiom shape. The manifest
includes extracted, approved, rejected, pending, unresolved and
ambiguous source counts. The scientific connectivity report includes
an evidence-backed subgraph and per-source distinct edge counts.

The manifest's per-source `endpoint_resolution` summarizes the states
of distinct native endpoints and their combinations across extracted
relations. `candidate_actions` assigns each candidate one primary review
action. Exclusion actions describe publication scope for this profile.
A witness may also link to a scoped endpoint-projection entity with
the native endpoint, canonical subject, evidence fingerprint and reviewed
reason. It provides source-aware resolution for the statement.
