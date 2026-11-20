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

Resolve graph names as https://curricula.live/id/formal-sciences/graph/ followed by asserted, inferred, alignments or provenance. Consumer steps: verify the pinned manifest, its conformance and every file digest, parse the indicated RDF formats, check graph counts and equivalence, then atomically select the verified dataset. Every consumer owns its storage mapping. External IDs and permanent concept IRIs remain visible through its interface.

The reference intake in curricula-live/data is provisional. A pull-based job reads the reviewed producer main branch and proposes one immutable receipt in a pull request to dev. Updating main here requires producer review. Database changes are outside this contract.

GitHub Releases use v<ontology-version> tags for accepted main commits. Development builds are also reproducible from a branch or immutable commit. The provisional consumer compares manifest digests to avoid requesting another intake when an upstream code-only commit preserves the same release.

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
