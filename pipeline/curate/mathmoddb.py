"""Replay the reviewed mathematical model and numerical method subjects."""
import argparse
import csv
import json
from hashlib import sha256
import re

from pyoxigraph import Literal as OxLiteral, NamedNode
from rdflib import Graph, Literal, RDFS, SKOS

from pipeline.common import C, D, ROOT, registry
from pipeline.normalize import label_key
from pipeline.parse import ingest, staged

SOURCE = "mathmoddb"
NATIVE = "https://portal.mardi4nfdi.de/entity/"
DIGEST = "acf15d06ae49aea4d81977b7bee30d159eb3931efa922dddb2af538d917ae63d"
MODULE = "domains/mathematics/modules/batches/mathmoddb-mathematical-models.ttl"
LEDGER = "reviews/approved/batches/mathmoddb.json"
SCOPE = "sources/mathmoddb/subject-scope.tsv"


def outputs(source, store, graph_name):
    baseline = Graph()
    for path in sorted(ROOT.glob("domains/*/modules/**/*.ttl")):
        if path != ROOT / MODULE:
            baseline.parse(path)
    labels = {label_key(str(label)) for p in (SKOS.prefLabel, SKOS.altLabel)
              for label in baseline.objects(None, p)}
    lines = [f"@prefix c: <{C}> .", f"@prefix scheme: <{D}> .", f"@prefix skos: <{SKOS}> .", ""]
    identities = {}
    with (ROOT / SCOPE).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        native, parent, label = row["id"], row["broader"], row["source_label"]
        external = NATIVE + native
        if not re.fullmatch(r"Q[0-9]+", native) or external in identities:
            raise ValueError(f"Invalid or duplicate MathModDB subject: {native}")
        name = NamedNode(external)
        witnessed_labels = {
            quad.object.value for quad in store.quads_for_pattern(
                name, NamedNode(str(RDFS.label)), None, NamedNode(graph_name)
            ) if isinstance(quad.object, OxLiteral) and quad.object.language == "en"
        }
        if witnessed_labels != {label}:
            raise ValueError(f"MathModDB English label changed for {native}")
        if label_key(label) in labels or (C[parent], SKOS.inScheme, D.mathematics) not in baseline:
            raise ValueError(f"Ambiguous label or unresolved mathematics heading: {native}")
        labels.add(label_key(label))
        slug = "mathmoddb-" + native.lower()
        identities[external] = slug
        lines.extend([
            f"c:{slug} a skos:Concept ; skos:prefLabel {Literal(label, lang='en').n3()} ;",
            f"    skos:inScheme scheme:mathematics ; skos:broader c:{parent} .", "",
        ])
    text = "\n".join(lines)
    ledger = dict(source=SOURCE, sha256=source["sha256"], revision=source["revision"], license=source["license"],
                  policy="Reviewed MathModDB subject slice for numerical mathematics and model reduction.",
                  eligible=len(rows), pending=0, exclusions={}, identities=identities,
                  modules={MODULE: sha256(text.encode()).hexdigest()})
    return {MODULE: text, LEDGER: json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n"}


def replay(offline=False, write=False):
    source = registry()[SOURCE]
    if source["sha256"] != DIGEST or source["license"] != "CC-BY-4.0":
        raise ValueError("Review MathModDB source rights and scope for this revision")
    stats = ingest(source, offline)
    artifacts = outputs(source, staged(source), stats["graph"])
    for name, text in artifacts.items():
        path = ROOT / name
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())
        elif not path.is_file() or path.read_bytes() != text.encode():
            raise ValueError(f"MathModDB subject admission differs at {name}")
    return {"source": SOURCE, "admitted": len(json.loads(artifacts[LEDGER])["identities"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(replay(offline=args.offline, write=args.write)))
