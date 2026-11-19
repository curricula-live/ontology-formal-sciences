from pyoxigraph import NamedNode, Literal as OxLiteral
from rdflib import RDF, RDFS, SKOS
from pipeline.common import ROOT, read, write
from pipeline.normalize import label_key
from pipeline.parse import ingest, staged


def candidates(source, canonical, offline=False):
    ingest(source, offline)
    store = staged(source)
    index = {}
    for predicate in [SKOS.prefLabel, SKOS.altLabel]:
        for term, label in canonical.subject_objects(predicate):
            index.setdefault((label_key(str(label)), label.language or ""), set()).add(str(term))
    decisions = {}
    for state in ("approved", "rejected"):
        for row in read(ROOT / "reviews" / state / "mappings.json"):
            decisions[row["external"], row["canonical"]] = state
    matches = set()
    for pred in (SKOS.prefLabel, SKOS.altLabel, RDFS.label):
        for quad in store.quads_for_pattern(None, NamedNode(str(pred)), None, None):
            if not isinstance(quad.subject, NamedNode) or not isinstance(quad.object, OxLiteral):
                continue
            label = quad.object
            for target in index.get((label_key(label.value), label.language or "en"), ()):
                matches.add((quad.subject.value, target, label.value))
    result = [dict(external=e, canonical=c, label=l, state=decisions.get((e,c),"pending"),
                   rule="normalized-label", sha256=source["sha256"]) for e,c,l in sorted(matches)]
    write(ROOT / ".cache" / "candidates" / (source["id"] + ".json"), result)
    return result
