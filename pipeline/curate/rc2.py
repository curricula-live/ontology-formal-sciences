"""Scoped corrections from the rc.1 findings and the scientific citation gate."""
from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, ROOT, V, read
from pipeline.curate.relations import statement_for
from pipeline.curate.revisions import archive, retain_module
from pipeline.validate import RELATIONS

RECORD = ROOT / "reviews/quality/rc2-corrections.json"


def apply(graph, provenance):
    record = read(RECORD)
    edit = record["definition"]
    subject = C[edit["subject"]]
    old, new = [(subject, SKOS.definition, Literal(edit[key], lang="en"))
                for key in ("former", "replacement")]
    if old in graph or new not in graph:
        raise ValueError("The reviewed definition correction differs from the graph")
    prior = archive(provenance, old, "superseded definition")
    updated = archive(provenance, new)
    retain_module(provenance, edit["module"], edit["sha256"], prior)
    provenance.add((updated, PROV.wasRevisionOf, prior))
    provenance.add((updated, DCTERMS.type, Literal("same-identity definition correction")))
    provenance.add((updated, DCTERMS.description, Literal("Distinguish induced fixed-point bounds from ambient bounds.", lang="en")))
    provenance.add((updated, DCTERMS.source, URIRef(edit["source"])))
    for path, digest in record["navigation_modules"].items():
        retain_module(provenance, path, digest)
    for slug, scope in record["scopes"].items():
        term = C[slug]
        if (term, RDF.type, SKOS.Concept) not in graph:
            raise ValueError(f"Scope note has no canonical subject: {term}")
        graph.add((term, SKOS.scopeNote, Literal(scope, lang="en")))
    for s, p, o, scope, citation in record["claims"]:
        triple = C[s], V[p], C[o]
        if triple not in graph:
            raise ValueError(f"Reviewed scope has no active statement: {triple}")
        statement = archive(provenance, triple)
        provenance.add((statement, DCTERMS.description, Literal(scope, lang="en")))
        if citation:
            provenance.add((statement, DCTERMS.source, URIRef(citation)))


def findings(graph, provenance):
    errors = []
    for s, p, o in graph:
        if p in RELATIONS - {SKOS.broader, SKOS.related, V.containsSymbol}:
            if not provenance.value(statement_for((s, p, o)), DCTERMS.source):
                errors.append(f"Scientific assertion requires a citation: {s} {p} {o}")
        if p == V.uses and (s, V.hasScientificRole, V.Result) in graph and not any(
            (s, V.hasScientificRole, role) in graph for role in (V.Method, V.Algorithm)
        ):
            errors.append(f"Result-only subject has a method-to-ingredient assertion: {s}")
    return sorted(errors)
