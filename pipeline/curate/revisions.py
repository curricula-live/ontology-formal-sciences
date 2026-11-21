"""Keep superseded scientific interpretations queryable in the provenance graph."""
from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, ROOT, V, checksum, read
from pipeline.curate.relations import statement_for

LEDGER = ROOT / "reviews/quality/relation-revisions.json"


def apply_revisions(graph, provenance):
    rows = read(LEDGER)
    seen = set()
    for row in rows:
        s, p, o = row["former"]
        old = C[s], V[p], C[o]
        s, p, o = row["replacement"]
        new = C[s], SKOS.broader if p == "skos:broader" else V[p], C[o]
        if old in seen or old in graph or new not in graph or not row["rationale"].strip():
            raise ValueError(f"Unresolved superseded assertion: {old}")
        seen.add(old)
        old_stmt, new_stmt = statement_for(old), statement_for(new)
        provenance.add((old_stmt, RDF.type, RDF.Statement))
        provenance.add((old_stmt, DCTERMS.type, Literal("superseded interpretation")))
        provenance.add((new_stmt, PROV.wasRevisionOf, old_stmt))
        provenance.add((new_stmt, DCTERMS.description, Literal(row["rationale"], lang="en")))
        for field, value in zip((RDF.subject, RDF.predicate, RDF.object), old):
            provenance.add((old_stmt, field, value))
        provenance.add((new_stmt, RDF.type, RDF.Statement))
        for field, value in zip((RDF.subject, RDF.predicate, RDF.object), new):
            provenance.add((new_stmt, field, value))
        for ref in row["sources"]:
            provenance.add((old_stmt, DCTERMS.source, URIRef(ref)))
        for witness in row.get("pinned_witnesses", []):
            entity = URIRef(witness)
            if not provenance.value(entity, DCTERMS.isPartOf):
                raise ValueError(f"Missing historical source witness: {entity}")
            provenance.add((old_stmt, PROV.wasDerivedFrom, entity))
    return {"retired_assertions": len(seen), "ledger_sha256": checksum(LEDGER)}
