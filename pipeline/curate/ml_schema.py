"""Admit narrowly scoped subjects from the licensed ML-Schema core classes."""
from argparse import ArgumentParser
from collections import defaultdict
import csv
from hashlib import sha256
import json

from pyoxigraph import Literal as SourceLiteral, NamedNode
from rdflib import Graph, Literal, OWL, RDF, SKOS
from rdflib.namespace import DCTERMS

from pipeline.common import C, D, ROOT, registry
from pipeline.normalize import label_key
from pipeline.parse import ingest, staged

SOURCE = "ml-schema"
NAMESPACE = "http://www.w3.org/ns/mls#"
SCOPE = ROOT / "sources/ml-schema/subject-scope.tsv"
LEDGER = "reviews/approved/batches/ml-schema.json"
MODULE = "domains/{domain}/modules/batches/ml-schema-evaluation.ttl"
PREFIX = f"@prefix c: <{C}> .\n@prefix scheme: <{D}> .\n@prefix skos: <{SKOS}> .\n\n"


def description_digest(store, named_graph, iri):
    terms = {quad.object.value.strip() for quad in store.quads_for_pattern(
        NamedNode(iri), NamedNode(str(DCTERMS.description)), None, NamedNode(named_graph)
    ) if isinstance(quad.object, SourceLiteral) and quad.object.language in {"en", None}}
    if len(terms) != 1:
        raise ValueError(f"Expected one reviewed ML-Schema description for {iri}")
    return sha256(next(iter(terms)).encode()).hexdigest()


def outputs(source, store, named_graph):
    graph = Graph()
    for path in sorted(ROOT.glob("domains/*/modules/**/*.ttl")):
        if path.name != "ml-schema-evaluation.ttl":
            graph.parse(path)
    labels = {label_key(str(label)) for predicate in (SKOS.prefLabel, SKOS.altLabel)
              for label in graph.objects(None, predicate)}
    identities, by_domain = {}, defaultdict(list)
    with SCOPE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    for record in rows:
        native, slug, domain, parent = (record[k] for k in ("native", "slug", "domain", "parent"))
        label, definition = record["label"], record["definition"]
        external = NAMESPACE + native
        is_class = any(store.quads_for_pattern(NamedNode(external), NamedNode(str(RDF.type)),
                                               NamedNode(str(OWL.Class)), NamedNode(named_graph)))
        if (not is_class or description_digest(store, named_graph, external) != record["description_sha256"]
                or external in identities):
            raise ValueError(f"Missing or changed ML-Schema class: {native}")
        if label_key(label) in labels or (C[parent], SKOS.inScheme, D[domain]) not in graph:
            raise ValueError(f"Ambiguous label or unknown ML-Schema heading: {label}")
        labels.add(label_key(label))
        identities[external] = slug
        by_domain[domain].append(
            f"c:{slug} a skos:Concept ; skos:prefLabel {Literal(label, lang='en').n3()} ;\n"
            f"    skos:inScheme scheme:{domain} ; skos:broader c:{parent} ;\n"
            f"    skos:definition {Literal(definition, lang='en').n3()} ."
        )
    files = {MODULE.format(domain=domain): PREFIX + "\n\n".join(terms) + "\n"
             for domain, terms in by_domain.items()}
    ledger = dict(source=SOURCE, sha256=source["sha256"], revision=source["revision"], license=source["license"],
                  policy="Reviewed ML-Schema core subjects for implementation and evaluation. Each description is pinned to its class.",
                  eligible=len(rows), pending=0, exclusions={}, identities=identities,
                  modules={name: sha256(text.encode()).hexdigest() for name, text in files.items()})
    files[LEDGER] = json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    return files


def replay(offline=False, write=False):
    source = registry()[SOURCE]
    if source["license"] != "CC-BY-4.0" or not source["allow_mapping"]:
        raise ValueError("ML-Schema publication rights changed")
    stats = ingest(source, offline)
    files = outputs(source, staged(source), stats["graph"])
    for name, contents in files.items():
        path = ROOT / name
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents.encode())
        elif not path.is_file() or path.read_bytes() != contents.encode():
            raise ValueError(f"ML-Schema subject admission differs at {name}")
    return {"source": SOURCE, "admitted": len(json.loads(files[LEDGER])["identities"])}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(replay(offline=args.offline, write=args.write)))
