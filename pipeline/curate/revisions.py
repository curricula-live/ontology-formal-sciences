"""Keep superseded scientific interpretations queryable in the provenance graph."""
from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read
from pipeline.contract import DIGEST
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
        for ref in row.get("replacement_sources", []):
            provenance.add((new_stmt, DCTERMS.source, URIRef(ref)))
        for path, digest in row.get("former_modules", {}).items():
            module = URIRef(BASE + "module/" + path)
            if (module, RDF.type, PROV.Entity) not in provenance or not DIGEST.fullmatch(digest):
                raise ValueError(f"Invalid historical module witness: {module}")
            snapshot = URIRef(str(module) + "?sha256=" + digest)
            provenance.add((old_stmt, PROV.wasDerivedFrom, module))
            provenance.add((old_stmt, PROV.wasDerivedFrom, snapshot))
            provenance.add((snapshot, RDF.type, PROV.Entity))
            provenance.add((snapshot, PROV.specializationOf, module))
            provenance.add((snapshot, DCTERMS.identifier, Literal(digest)))
        for witness in row.get("pinned_witnesses", []):
            entity = URIRef(witness)
            if not provenance.value(entity, DCTERMS.isPartOf):
                raise ValueError(f"Missing historical source witness: {entity}")
            provenance.add((old_stmt, PROV.wasDerivedFrom, entity))
    return {"retired_assertions": len(seen), "ledger_sha256": checksum(LEDGER)}
