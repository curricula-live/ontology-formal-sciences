from pyoxigraph import Store, NamedNode, Literal as OxLiteral
from rdflib import RDF, RDFS, SKOS
from pipeline.common import ROOT, read, write
from pipeline.normalize import label_key
from pipeline.normalize.index import normalize, index_path, KEY


def candidates(source, canonical, offline=False):
    normalize(source, offline)
    store = Store.read_only(str(index_path(source)/"store"))
    index = {}
    for predicate in [SKOS.prefLabel, SKOS.altLabel]:
        for term, label in canonical.subject_objects(predicate):
            index.setdefault((label_key(str(label)), label.language or ""), set()).add(str(term))
    decisions = {}
    for state in ("approved", "rejected"):
        for row in read(ROOT / "reviews" / state / "mappings.json"):
            decisions[row["external"], row["canonical"]] = state
    matches = set()
    for (normalized, language), targets in index.items():
        languages = (language,None) if language == "en" else (language or None,)
        for lang in languages:
            key = OxLiteral(normalized,language=lang)
            for quad in store.quads_for_pattern(None,KEY,key,None):
                for target in targets:
                    matches.add((quad.subject.value,target,normalized))
    result = [dict(external=e, canonical=c, label=l, state=decisions.get((e,c),"pending"),
                   rule="normalized-label", sha256=source["sha256"]) for e,c,l in sorted(matches)]
    write(ROOT / ".cache" / "candidates" / (source["id"] + ".json"), result)
    return result
