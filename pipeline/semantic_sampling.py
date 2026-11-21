"""Select reproducible, independently ranked audit cases without replacement."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from rdflib import Dataset, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, G, V, read
from pipeline.curate.relations import statement_for
from pipeline.curate.cs_evidence import DECISIONS

BASELINE = "ed04aa8c2a39ddc89203c3905381a88d489733dc"
SEED = f"ontology-formal-sciences:v0.8.0:{BASELINE}"


def local(term):
    return str(term).rsplit("/", 1)[-1]


def ranked(key):
    return sha256((SEED + "\0" + key).encode()).digest()


def select(dataset):
    release = Dataset()
    release.parse(dataset, format="nquads")
    graph, prov = release.graph(G.asserted), release.graph(G.provenance)
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    owners = {term: local(graph.value(term, SKOS.inScheme)) for term in concepts}
    relations, topics, passages = defaultdict(list), defaultdict(list), defaultdict(list)
    for triple in graph:
        left, relation, right = triple
        if left not in concepts or right not in concepts or not str(relation).startswith(str(V)):
            continue
        statement = statement_for(triple)
        sources = {local(source) for entity in prov.objects(statement, PROV.wasDerivedFrom)
                   for source in prov.objects(entity, DCTERMS.isPartOf)}
        kind = (min(sources) if sources else
                "editorial-citation" if prov.value(statement, DCTERMS.source) else "unattributed")
        relations[owners[left], kind].append(triple)
    for subject in concepts:
        module, = (str(node) for node in prov.objects(subject, PROV.wasDerivedFrom)
                   if str(node).startswith(BASE + "module/"))
        if "/batches/" in module:
            batch = module.split("/batches/", 1)[1]
            kind = next(source for source in ("opencs", "ontomath-pro", "stato", "mathmoddb", "ml-schema")
                        if batch.startswith(source + "-"))
        else:
            kind = "authored"
        topics[owners[subject], kind].append(subject)
    for passage in read(DECISIONS):
        for judgment in passage["judgments"]:
            if judgment["state"] == "approved":
                passages[passage["corpus"]].append((passage, judgment["triple"]))
    return {
        "baseline": BASELINE, "seed": SEED,
        "relations": [
            {"scheme": scheme, "evidence_family": family, "population": len(pool),
             "triple": list(map(local, terms))}
            for (scheme, family), pool in sorted(relations.items())
            for terms in sorted(pool, key=lambda t: ranked("R:" + " ".join(term.n3() for term in t)))[:2]
        ],
        "topics": [
            {"scheme": scheme, "admission": source, "population": len(pool), "canonical": local(term)}
            for (scheme, source), pool in sorted(topics.items())
            for term in sorted(pool, key=lambda t: ranked("T:" + t.n3()))[:1]
        ],
        "passages": [
            {"corpus": source, "path": row["path"], "first": row["first"], "last": row["last"],
             "population": len(pool), "triple": triple}
            for source, pool in sorted(passages.items())
            for row, triple in sorted(pool, key=lambda pair: ranked(
                "P:" + pair[0]["path"] + ":" + str(pair[0]["first"]) + ":" + " ".join(pair[1])
            ))[:1]
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(select(args.baseline_dataset), ensure_ascii=False, indent=2))
