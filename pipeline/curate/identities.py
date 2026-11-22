"""Publish reviewed canonical replacements while retaining historical subjects."""
from hashlib import sha256

from rdflib import Graph, Literal, OWL, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, checksum, read, registry
from pipeline.curate.relations import statement_for
from pipeline.parse import ingest, staged

LEDGER = ROOT / "reviews/approved/identity-migrations.json"


def reviewed_migrations():
    catalog = registry()
    rows = read(LEDGER)
    for row in rows:
        source = catalog[row["source"]]
        if row["snapshot_sha256"] != source["sha256"] or row["decision"] != "duplicate":
            raise ValueError(f"Invalid snapshot or identity decision: {row['former']}")
        if not row["rationale"].strip() or not row["scientific_reference"].startswith("https://"):
            raise ValueError(f"Missing identity rationale or reference: {row['former']}")
        batch = read(ROOT / f"reviews/approved/batches/{row['source']}.json")
        if batch["identities"].get(row["native"]) != row["former"]:
            raise ValueError(f"Identity change lost its original admission: {row['former']}")
        native = URIRef(row["native"])
        evidence = Graph().parse(data=row["source_evidence"], format="nt")
        if not (any(evidence.objects(native, SKOS.prefLabel))
                and any(evidence.objects(native, SKOS.closeMatch))):
            raise ValueError(f"Incomplete native identity witness: {row['former']}")
    return rows


def apply_migrations(graph, provenance):
    rows = reviewed_migrations()
    for row in rows:
        original, preferred = C[row["former"]], C[row["preferred"]]
        native = URIRef(row["native"])
        if (original, DCTERMS.source, native) not in provenance:
            raise ValueError(f"Missing source origin for retired concept: {original}")
        graph.add((original, OWL.deprecated, Literal(True)))
        triple = original, DCTERMS.isReplacedBy, preferred
        graph.add(triple)
        statement = statement_for(triple)
        witness = URIRef(BASE + "identity-review/" + sha256(str(original).encode()).hexdigest())
        provenance.add((statement, RDF.type, RDF.Statement))
        provenance.add((statement, PROV.wasDerivedFrom, witness))
        for field, value in zip((RDF.subject, RDF.predicate, RDF.object), triple):
            provenance.add((statement, field, value))
        for field, value in (
            (RDF.type, PROV.Entity),
            (DCTERMS.type, Literal("reviewed canonical duplicate")),
            (DCTERMS.identifier, Literal(row["snapshot_sha256"])),
            (DCTERMS.references, native),
            (DCTERMS.source, URIRef(row["scientific_reference"])),
            (DCTERMS.description, Literal(row["rationale"], lang="en")),
        ):
            provenance.add((witness, field, value))
    return {"retired_duplicates": len(rows), "ledger_sha256": checksum(LEDGER)}


def replay(offline=False):
    catalog = registry()
    stores = {}
    rows = reviewed_migrations()
    for row in rows:
        key = row["source"]
        if key not in stores:
            source = catalog[key]
            name = ingest(source, offline)["graph"]
            stores[key] = staged(source), name
        store, name = stores[key]
        answer = store.query(f"ASK {{ GRAPH <{name}> {{ {row['source_evidence']} }} }}")
        if not bool(answer):
            raise ValueError(f"Native identity witness differs: {row['native']}")
    return {"verified_migrations": len(rows)}
