# Formal sciences ontology

A curated RDF ontology spanning mathematics, computer science, logic and statistics. The independently buildable release uses stable Curricula IRIs, accepts reviewed evidence from external vocabularies and records its inference separately.

## Reproduce the release

Use Python 3.12 in a checkout. The code locates sources and domains relative to that checkout.

    python -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.lock
    python -m pytest -q
    python -m pipeline.cli build
    git diff --exit-code -- dist

The build and core tests run offline after installation. Use dist/formal-sciences.ttl for the asserted graph and dist/formal-sciences.trig or .nq when provenance, mapping and inference boundaries matter. A SPARQL example is available in docs/cross-domain.rq.

## Contribute and update

    python -m pipeline.cli sources status
    python -m pipeline.cli fetch --source cso
    python -m pipeline.cli ingest --source cso --offline
    python -m pipeline.cli align --source cso --offline
    python -m pipeline.cli audit --source cso --offline

Source documents land under sources/<id>/original and are verified on each access. Store large private snapshots outside Git. PyOxigraph streams a document into a private per-source named graph keyed by its SHA-256. A temporary store is promoted only after a complete parse. Non-RDF adapters extract a declared subset. Candidates are written to .cache/candidates. Move decisions into the review ledger with an evidence statement and rationale, update the canonical Turtle module or alignment and rebuild. Only the build and validation jobs can certify the resulting release. Maintainers must review the proposed changes before merging.

The scheduled network audit verifies pinned documents and flags newer repository revisions or changed downloads. To adopt a revision, retain the old byte snapshot, fetch the new document separately, verify its license and checksum, change its source manifest in a branch, ingest it and refresh ingestion.json from the successful run. Rerun alignment and audit, then review affected decisions before updating the exports. Source updates never overwrite accepted decisions automatically.

- [Processing scope, licensing and actual ingestion counts](docs/sources.md)
- [RDF package contract](docs/contract-v1.md)
- [Editorial policy, provenance, predicates and inference](docs/model.md)
- [Continuation and remaining source work](docs/continuation.md)

The daily revision-proposal workflow rotates through fifteen ontology sources and accepts a source ID via manual dispatch. For a local proposal, use a disposable checkout and run `python -m pipeline.refresh SOURCE`. It verifies that the new snapshot parses, generates candidates and opens a draft PR on GitHub when the source bytes change. Sources with reviewed mapping decisions require explicit revision of the affected evidence before rebuilding. GitHub's workflow permission to create pull requests is required for automatic proposals. The read-only weekly audit covers all available sources.
