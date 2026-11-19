from rdflib import Graph, RDF, SKOS, URIRef, Literal
from rdflib.namespace import PROV, DCTERMS
from pipeline.common import ROOT, BASE, D, read, checksum

DOMAINS = ("mathematics", "computer-science", "logic", "statistics")


def authored():
    graph, prov, seen = Graph(), Graph(), set()
    for path in sorted((ROOT / "domains").rglob("*.ttl")):
        rel = path.relative_to(ROOT / "domains")
        if rel.parts[:2] in [("_shared","shapes"), ("_shared","alignments")]:
            continue
        module = Graph().parse(path)
        node = URIRef(BASE + "module/" + str(rel))
        prov.add((node, DCTERMS.identifier, Literal(checksum(path))))
        prov.add((node, RDF.type, PROV.Entity))
        for term in module.subjects(RDF.type, SKOS.Concept):
            if rel.parts[0] not in DOMAINS or (term,SKOS.inScheme,D[rel.parts[0]]) not in module:
                raise ValueError(f"Owning module and scheme disagree: {term} in {rel}")
            if term in seen:
                raise ValueError(f"Multiple owning modules for {term}")
            seen.add(term)
            prov.add((term, PROV.wasDerivedFrom, node))
        for triple in module:
            if triple in graph:
                raise ValueError(f"Duplicate authored assertion in {rel}: {triple}")
            graph.add(triple)
    return graph, prov


def reviewed(registry, graph, prov):
    mappings = Graph()
    for path in (ROOT / "domains/_shared/alignments").glob("*.ttl"):
        mappings.parse(path)
    expected = Graph()
    taken, exact, veto = set(), {}, set()
    for state in ("rejected","approved"):
        for r in read(ROOT / "reviews" / state / "mappings.json"):
            s = registry[r["source"]]
            ext, can = URIRef(r["external"]), URIRef(r["canonical"])
            key = (ext,can)
            if key in taken or not r["rationale"].strip():
                raise ValueError(f"Duplicate/conflicting/unsupported decision: {key}")
            taken.add(key)
            if state == "rejected":
                veto.add(key)
                continue
            if not s["allow_mapping"] or s["license"] not in {"CC0-1.0","CC-BY-4.0","Apache-2.0"} or r["sha256"] != s["sha256"]:
                raise ValueError(f"Rights or evidence revision changed: {ext}")
            if (can, RDF.type, SKOS.Concept) not in graph:
                raise ValueError(f"Unowned target {can}")
            pred = URIRef(r["predicate"])
            if pred not in {SKOS.exactMatch, SKOS.closeMatch}:
                raise ValueError(f"Unsupported mapping {pred}")
            if pred == SKOS.exactMatch and ext in exact:
                raise ValueError(f"Conflicting identity for {ext}")
            exact[ext] = can if pred == SKOS.exactMatch else exact.get(ext)
            evidence = Graph().parse(data=r["evidence"],format="nt")
            if not any(p not in {SKOS.prefLabel, SKOS.altLabel, URIRef("http://www.w3.org/2000/01/rdf-schema#label")} for _,p,_ in evidence.triples((ext,None,None))):
                raise ValueError(f"Missing structural evidence: {ext}")
            expected.add((can,pred,ext))
            record = URIRef(BASE + "review/" + r["id"])
            prov.add((record, RDF.type, PROV.Entity))
            prov.add((record, PROV.wasDerivedFrom, ext))
            prov.add((record, PROV.hadPrimarySource, URIRef(s["url"])))
            prov.add((record, DCTERMS.identifier, Literal(s["sha256"])))
            prov.add((record, DCTERMS.description, Literal(r["rationale"],lang="en")))
            for p,o in [(RDF.subject,can),(RDF.predicate,pred),(RDF.object,ext)]:
                prov.add((record,p,o))
    if set(mappings) != set(expected):
        raise ValueError("Authored alignments and approved decisions disagree")
    return mappings
