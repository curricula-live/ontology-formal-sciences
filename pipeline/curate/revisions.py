"""Keep superseded scientific interpretations queryable in the provenance graph."""
from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read
from pipeline.contract import DIGEST
from pipeline.curate.relations import statement_for

LEDGER = ROOT / "reviews/quality/relation-revisions.json"


def archive(provenance, triple, disposition=None):
    statement = statement_for(triple)
    provenance.add((statement, RDF.type, RDF.Statement))
    for field, value in zip((RDF.subject, RDF.predicate, RDF.object), triple):
        provenance.add((statement, field, value))
    if disposition:
        provenance.add((statement, DCTERMS.type, Literal(disposition)))
    return statement


def retain_module(provenance, path, digest, statement=None):
    module = URIRef(BASE + "module/" + path)
    if (module, RDF.type, PROV.Entity) not in provenance or not DIGEST.fullmatch(digest):
        raise ValueError(f"Invalid historical module witness: {module}")
    snapshot = URIRef(str(module) + "?sha256=" + digest)
    provenance.add((snapshot, RDF.type, PROV.Entity))
    provenance.add((snapshot, PROV.specializationOf, module))
    provenance.add((snapshot, DCTERMS.identifier, Literal(digest)))
    if statement:
        provenance.add((statement, PROV.wasDerivedFrom, snapshot))


def apply_revisions(graph, provenance):
    rows = read(LEDGER)
    seen = set()
    for row in rows:
        s, p, o = row["former"]
        old = C[s], V[p], C[o]
        new = None
        if row["replacement"]:
            s, p, o = row["replacement"]
            new = C[s], SKOS.broader if p == "skos:broader" else V[p], C[o]
        if old in seen or new == old or (new is not None and new not in graph) or not row["rationale"].strip():
            raise ValueError(f"Unresolved superseded assertion: {old}")
        # A passage can preserve its original approval and witness in provenance.
        # Only the explicitly reviewed withdrawal removes its asserted projection.
        if old in graph:
            if not row.get("withdraw_passage") or new is not None:
                raise ValueError(f"Superseded assertion remains active: {old}")
            graph.remove(old)
        seen.add(old)
        old_stmt = statement_for(old)
        new_stmt = statement_for(new) if new is not None else None
        archive(provenance, old, "superseded interpretation" if new_stmt else "withdrawn interpretation")
        if new_stmt:
            archive(provenance, new)
            provenance.add((new_stmt, PROV.wasRevisionOf, old_stmt))
            provenance.add((new_stmt, DCTERMS.description, Literal(row["rationale"], lang="en")))
        else:
            provenance.add((old_stmt, DCTERMS.description, Literal(row["rationale"], lang="en")))
        for ref in row["sources"]:
            provenance.add((old_stmt, DCTERMS.source, URIRef(ref)))
        for ref in row.get("replacement_sources", []):
            provenance.add((new_stmt, DCTERMS.source, URIRef(ref)))
        for path, digest in row.get("former_modules", {}).items():
            module = URIRef(BASE + "module/" + path)
            provenance.add((old_stmt, PROV.wasDerivedFrom, module))
            retain_module(provenance, path, digest, old_stmt)
        for witness in row.get("pinned_witnesses", []):
            entity = URIRef(witness)
            if not provenance.value(entity, DCTERMS.isPartOf):
                raise ValueError(f"Missing historical source witness: {entity}")
            provenance.add((old_stmt, PROV.wasDerivedFrom, entity))
    return {"retired_assertions": len(seen), "ledger_sha256": checksum(LEDGER)}
