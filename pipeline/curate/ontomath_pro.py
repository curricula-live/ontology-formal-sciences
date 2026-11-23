"""Project a reviewed OntoMathPro subject index from the pinned OWL snapshot."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import re

from pyoxigraph import Literal as SourceLiteral, NamedNode
from rdflib import Graph, Literal, OWL, RDF, RDFS, SKOS

from pipeline.common import BASE, C, D, ROOT, read, registry
from pipeline.curate import DOMAINS
from pipeline.normalize import label_key
from pipeline.parse import ingest, staged

SOURCE = "ontomath-pro"
NAMESPACE = "http://cll.niimm.ksu.ru/ontologies/mathematics#"
DIGEST = "d8ceab757419a6ff07230342c47f4d49f8542ef998e0b052b31cde8fa5ab1c7f"
POLICY = Path("sources/ontomath-pro")
LEDGER = Path("reviews/approved/batches/ontomath-pro.json")
QUEUE = Path("reviews/pending/batches/ontomath-pro.json")
HEADER = f"@prefix c: <{C}> .\n@prefix scheme: <{D}> .\n@prefix skos: <{SKOS}> .\n\n"


def key(label):
    return "".join(c for c in label_key(label) if c.isalnum())


def editorial_index():
    graph = Graph()
    for path in sorted(ROOT.glob("domains/*/modules/**/*.ttl")):
        if not path.name.startswith("ontomath-pro-"):
            graph.parse(path)
    index = defaultdict(set)
    for topic in graph.subjects(RDF.type, SKOS.Concept):
        for predicate in (SKOS.prefLabel, SKOS.altLabel):
            for label in graph.objects(topic, predicate):
                index[key(str(label))].add(str(topic))
    return graph, index


def source_classes(store, graph_name):
    named = NamedNode(graph_name)
    qualified = re.compile(re.escape(NAMESPACE) + r"E[0-9]+")
    return {
        quad.subject.value for quad in store.quads_for_pattern(
            None, NamedNode(str(RDF.type)), NamedNode(str(OWL.Class)), named
        ) if isinstance(quad.subject, NamedNode) and qualified.fullmatch(quad.subject.value)
    }


def project(source, store, graph_name):
    classes = source_classes(store, graph_name)
    with (ROOT / POLICY / "scope.tsv").open(newline="", encoding="utf-8") as scope:
        rows = list(csv.DictReader(scope, delimiter="\t"))
    hints = read(ROOT / POLICY / "stato-candidates.json")
    authored, existing = editorial_index()
    decisions = {
        row["external"] for state in ("approved", "rejected")
        for row in read(ROOT / "reviews" / state / "mappings.json") if row["source"] == SOURCE
    }
    selected = defaultdict(set)
    identifiers = set()
    for row in rows:
        identifier = row["class"]
        if identifier in identifiers:
            raise ValueError(f"Duplicate OntoMathPro policy entry: {identifier}")
        identifiers.add(identifier)
        selected[key(row["reviewed_english_label"])].add(identifier)

    pending, identities, grouped = {}, {}, defaultdict(list)
    exclusions = Counter({"native classes outside reviewed scope": len(classes) - len(rows)})
    for row in rows:
        identifier, heading, label = (row[k] for k in ("class", "subject_collection", "reviewed_english_label"))
        external = NAMESPACE + identifier
        if external not in classes:
            raise ValueError(f"OntoMathPro policy subject is missing or foreign: {identifier}")
        labels = {quad.object.value.strip() for quad in store.quads_for_pattern(
            NamedNode(external), NamedNode(str(RDFS.label)), None, NamedNode(graph_name)
        ) if isinstance(quad.object, SourceLiteral) and quad.object.language == "en"}
        if not any(label_key(label) == label_key(original) for original in labels):
            raise ValueError(f"Reviewed English label differs from pinned source: {identifier}: {label}")
        owner = authored.value(C[heading], SKOS.inScheme)
        domain = str(owner).removeprefix(str(D))
        if domain not in DOMAINS:
            raise ValueError(f"Unresolved subject collection: {heading}")
        if external in decisions:
            exclusions["existing individual review"] += 1
            continue
        normalized = key(label)
        near = selected[normalized] - {identifier}
        targets = existing.get(normalized, set())
        if near or targets or identifier in hints:
            pending[external] = dict(label=label, canonical_candidates=sorted(targets),
                                     upstream_candidates=sorted({NAMESPACE + item for item in near}
                                                                | set(hints.get(identifier, ()))))
            continue
        slug = "ontomath-pro-" + identifier.lower()
        identities[external] = slug
        grouped[domain, heading].append(
            f"c:{slug} a skos:Concept ; skos:prefLabel {Literal(label, lang='en').n3()} ;\n"
            f"    skos:inScheme scheme:{domain} ; skos:broader c:{heading} .\n"
        )

    files = {Path(f"domains/{domain}/modules/batches/ontomath-pro-{heading}.ttl"): HEADER + "\n".join(items)
             for (domain, heading), items in grouped.items()}
    ledger = dict(source=SOURCE, sha256=source["sha256"], revision=source["revision"], license=source["license"],
                  policy="Project reviewed English OWL class names into editorial subject collections. See sources/ontomath-pro/scope.tsv.",
                  modules={str(path): sha256(content.encode()).hexdigest() for path, content in files.items()},
                  identities=identities, eligible=len(rows), pending=len(pending), exclusions=dict(exclusions))
    for path, record in ((LEDGER, ledger), (QUEUE, pending)):
        files[path] = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return files, ledger


def replay(offline=False, write=False):
    source = registry()[SOURCE]
    if source["sha256"] != DIGEST or source["license"] != "Apache-2.0":
        raise ValueError("Review OntoMathPro admission rights and scope for the new revision")
    report = ingest(source, offline)
    files, ledger = project(source, staged(source), report["graph"])
    existing = {path.relative_to(ROOT) for path in ROOT.glob("domains/*/modules/batches/ontomath-pro-*.ttl")}
    if existing - files.keys():
        raise ValueError(f"Stale OntoMathPro modules: {sorted(existing - files.keys())}")
    for path, content in files.items():
        destination = ROOT / path
        if write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content.encode())
        elif not destination.is_file() or destination.read_bytes() != content.encode():
            raise ValueError(f"OntoMathPro admission differs at {path}")
    return {k: ledger[k] for k in ("source", "eligible", "pending", "exclusions")} | {
        "admitted": len(ledger["identities"]), "modules": len(ledger["modules"])
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write a generated proposal for review")
    args = parser.parse_args()
    print(json.dumps(replay(offline=args.offline, write=args.write), indent=2))
