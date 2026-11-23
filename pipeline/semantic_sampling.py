"""Select reproducible, independently ranked audit cases without replacement."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

from rdflib import Dataset, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, G, ROOT, V, read
from pipeline.curate.relations import statement_for
from pipeline.curate.cs_evidence import DECISIONS

BASELINES = {
    "0.8.0": "ed04aa8c2a39ddc89203c3905381a88d489733dc",
    "0.9.0": "17c4c1db6901381b41bd377fb8c24c2f868c1f23",
}


def design(version):
    baseline = BASELINES[version]
    return baseline, f"ontology-formal-sciences:v{version}:{baseline}"


def local(term):
    return str(term).rsplit("/", 1)[-1]


def participation(graph):
    owners = {term: local(graph.value(term, SKOS.inScheme))
              for term in graph.subjects(RDF.type, SKOS.Concept)}
    linked = {
        term for s, p, o in graph
        if s in owners and o in owners and str(p).startswith(str(V)) and p != V.containsSymbol
        for term in (s, o)
    }
    return owners, linked


def compare_participation(baseline, current):
    """Count changes in the same canonical cohort under the same predicate profile."""
    earlier, linked_before = participation(baseline)
    latest, linked_now = participation(current)
    if any(latest.get(term) != scheme for term, scheme in earlier.items()):
        raise ValueError("The coverage comparison lost or reassigned an existing canonical subject")
    result = {}
    for scheme in sorted(set(earlier.values())):
        cohort = {term for term, owner in earlier.items() if owner == scheme}
        new = {term for term, owner in latest.items() if owner == scheme} - cohort
        result[scheme] = {
            "baseline_canonical": len(cohort),
            "baseline_participating": len(cohort & linked_before),
            "current_existing_participating": len(cohort & linked_now),
            "gained_existing": sorted(map(local, cohort & (linked_now - linked_before))),
            "lost_existing": sorted(map(local, cohort & (linked_before - linked_now))),
            "added_canonical": len(new),
            "added_participating": len(new & linked_now),
        }
    return result


def select(dataset, version="0.8.0"):
    baseline, seed = design(version)

    def ranked(key):
        return sha256((seed + "\0" + key).encode()).digest()

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
        if version == "0.9.0" and relation == V.containsSymbol:
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
        if (version == "0.8.0" and passage.get("introduced")
                or version == "0.9.0" and passage.get("introduced") != version):
            continue
        for judgment in passage["judgments"]:
            if judgment["state"] == "approved":
                passages[passage["corpus"]].append((passage, judgment["triple"]))
    sample = {
        "baseline": baseline, "seed": seed,
        "relations": [
            {"scheme": scheme, "evidence_family": family, "population": len(pool),
             "triple": list(map(local, terms))}
            for (scheme, family), pool in sorted(relations.items())
            for terms in sorted(pool, key=lambda t: ranked("R:" + " ".join(term.n3() for term in t)))
            [:(2 if version == "0.8.0" else 1)]
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

    if version == "0.9.0":
        mappings = defaultdict(list)
        for state in ("approved", "rejected"):
            for row in read(ROOT / f"reviews/{state}/mappings.json"):
                mappings[row["source"], state].append(row["id"])
        sample["mappings"] = [
            {"source": source, "state": state, "id": min(pool, key=lambda item: ranked("M:" + item)),
             "population": len(pool)}
            for (source, state), pool in sorted(mappings.items())
        ]
    return sample


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_dataset", type=Path)
    parser.add_argument("--release", default="0.8.0", choices=sorted(BASELINES))
    args = parser.parse_args()
    print(json.dumps(select(args.baseline_dataset, args.release), ensure_ascii=False, indent=2))
