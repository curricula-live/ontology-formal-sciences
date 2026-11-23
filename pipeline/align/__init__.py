"""Generate private review candidates. A lexical or structural hit never approves a pair."""
from collections import defaultdict

from pyoxigraph import Literal as OxLiteral, NamedNode, Store
from rdflib import Graph, OWL, RDF, SKOS, URIRef

from pipeline.common import C, ROOT, read, write
from pipeline.normalize import label_key
from pipeline.normalize.index import KEY, index_path, normalize
from pipeline.parse import staged

REFERENCES = (SKOS.exactMatch, SKOS.closeMatch, OWL.sameAs)


def candidates(source, canonical, offline=False):
    normalize(source, offline)
    store = Store.read_only(str(index_path(source) / "store"))
    raw = staged(source)
    topics = set(canonical.subjects(RDF.type, SKOS.Concept))
    decisions = {}
    anchors = defaultdict(set)
    for state in ("approved", "rejected"):
        for row in read(ROOT / "reviews" / state / "mappings.json"):
            topic = URIRef(row["canonical"])
            if topic not in topics:
                continue
            if row["source"] == source["id"]:
                current = row["sha256"] == source["sha256"]
                decisions[row["external"], row["canonical"]] = {
                    "state": state if current else "needs-revalidation",
                    "previous_decision": row["id"], "predicate": row["predicate"]}
            elif state == "approved" and URIRef(row["predicate"]) == SKOS.exactMatch:
                evidence = Graph().parse(data=row["evidence"], format="nt")
                for pred, ref in evidence.predicate_objects(URIRef(row["external"])):
                    if pred in REFERENCES and isinstance(ref, URIRef):
                        anchors[str(ref)].add((str(topic), row["id"]))

    origins = ROOT / "reviews/approved/batches" / (source["id"] + ".json")
    if origins.exists():
        batch = read(origins)
        for external, slug in batch["identities"].items():
            state = "admitted-origin" if batch["sha256"] == source["sha256"] else "needs-revalidation"
            decisions.setdefault((external, str(C[slug])), {"state": state})

    # Retain every candidate sense and the signals that led to it.
    matches = defaultdict(lambda: {"labels": set(), "references": set()})
    labels = defaultdict(set)
    for predicate in (SKOS.prefLabel, SKOS.altLabel):
        for topic, label in canonical.subject_objects(predicate):
            if topic in topics:
                labels[label_key(str(label)), label.language].add(str(topic))
    for (key, lang), targets in labels.items():
        for language in (("en", None) if lang == "en" else (lang,)):
            for quad in store.quads_for_pattern(None, KEY, OxLiteral(key, language=language), None):
                for target in targets:
                    matches[quad.subject.value, target]["labels"].add((key, language or ""))

    for ref, targets in anchors.items():
        for predicate in REFERENCES:
            for quad in raw.quads_for_pattern(None, NamedNode(str(predicate)), NamedNode(ref), None):
                if isinstance(quad.subject, NamedNode):
                    for target, review in targets:
                        matches[quad.subject.value, target]["references"].add((str(predicate), ref, review))

    result = []
    for (external, target), signals in sorted(matches.items()):
        words = sorted(signals["labels"])
        references = sorted(signals["references"])
        row = dict(external=external, canonical=target, sha256=source["sha256"], state="pending",
                   labels=[{"key": key, "language": lang} for key, lang in words],
                   references=[{"predicate": p, "reference": ref, "review": review}
                               for p, ref, review in references])
        if words:
            row["label"] = words[0][0]
        row["rule"] = ("lexical-and-reference" if words and references else
                       "shared-reference" if references else "normalized-label")
        row.update(decisions.get((external, target), {}))
        result.append(row)
    write(ROOT / ".cache" / "candidates" / (source["id"] + ".json"), result)
    return result
