"""Project reviewed scientific topic families from the pinned OpenCS SKOS graph.

Run with python -m pipeline.curate.opencs [--offline] [--write].
The default compares a fresh projection with every committed output.
"""
import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote

from pyoxigraph import Literal as OxLiteral, NamedNode
from rdflib import Graph, Literal, RDF, SKOS

from pipeline.common import BASE, C, D, ROOT, read, registry
from pipeline.curate import DOMAINS
from pipeline.parse import ingest, staged

SOURCE = "opencs"
UPSTREAM = "https://w3id.org/ocs/ont/"
DBPEDIA = "http://dbpedia.org/resource/"
DIGEST = "a59ef7c77364d1a067e84bbec1c88dbaf5ae3a6df2184832887d9a106b3c08e5"
LEDGER = Path("reviews/approved/batches/opencs.json")
QUEUE = Path("reviews/pending/batches/opencs.json")
EVIDENCE = Path("sources/opencs/admission-witnesses.tsv")
POLICY = Path("sources/opencs/admission-policy.json")
HEADER = f"""@prefix c: <{C}> .
@prefix scheme: <{BASE}scheme/> .
@prefix skos: <{SKOS}> .

"""


@dataclass
class Topic:
    labels: set = field(default_factory=set)
    parents: set = field(default_factory=set)
    references: set = field(default_factory=set)


def source_index(store, graph_name):
    """Scan four predicate indexes. The original 538k statements stay on disk."""
    graph = NamedNode(graph_name)
    terms = {}
    prefix = re.compile(re.escape(UPSTREAM) + r"(C[1-9][0-9]*)$")
    concept = NamedNode(str(SKOS.Concept))
    for quad in store.quads_for_pattern(None, NamedNode(str(RDF.type)), concept, graph):
        match = prefix.fullmatch(quad.subject.value)
        if match:
            terms[match[1]] = Topic()
    for predicate in (SKOS.prefLabel, SKOS.broader, SKOS.closeMatch):
        for quad in store.quads_for_pattern(None, NamedNode(str(predicate)), None, graph):
            subject = terms.get(quad.subject.value.removeprefix(UPSTREAM))
            if subject is None:
                continue
            target = quad.object
            if predicate == SKOS.prefLabel and isinstance(target, OxLiteral) and target.language == "en":
                subject.labels.add(target.value)
            elif predicate == SKOS.broader and isinstance(target, NamedNode) and prefix.fullmatch(target.value):
                subject.parents.add(target.value.removeprefix(UPSTREAM))
            elif predicate == SKOS.closeMatch and isinstance(target, NamedNode) and target.value.startswith(DBPEDIA):
                subject.references.add(target.value)
    return terms


def words(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    return re.findall(r"[^\W_]+", "".join(ch for ch in text if not unicodedata.combining(ch)))


def reference_key(label):
    return " ".join(words(unquote(label).replace("_", " ")))


def collision_keys(label):
    """Loose keys open review cases only. They can never authorize a merge."""
    keys = set()
    for variant in (label, re.sub(r"\s*\([^()]+\)$", "", label)):
        terms = words(variant.replace("'s", "").replace("’s", ""))
        if terms:
            if terms[-1].endswith("s") and not terms[-1].endswith(("ss", "is", "us")):
                terms[-1] = terms[-1][:-1]
            keys.add(" ".join(terms))
    return keys


def editorial_index():
    existing = defaultdict(set)
    for path in sorted((ROOT / "domains").glob("*/modules/**/*.ttl")):
        if "batches" in path.parts:
            continue
        graph = Graph().parse(path)
        for node in graph.subjects(RDF.type, SKOS.Concept):
            for predicate in (SKOS.prefLabel, SKOS.altLabel):
                for label in graph.objects(node, predicate):
                    for key in collision_keys(str(label)):
                        existing[key].add(str(node))
    return existing


def ancestor_paths(terms, source_id, depth=4):
    """One shortest stable witness for each ancestor, with cycle protection."""
    paths = {source_id: (source_id,)}
    frontier = [source_id]
    for _ in range(depth):
        next_frontier = []
        for node in frontier:
            for parent in sorted(terms[node].parents):
                if parent in terms and parent not in paths:
                    paths[parent] = paths[node] + (parent,)
                    next_frontier.append(parent)
        frontier = next_frontier
    return paths


def classify(terms, source_id, families):
    topic = terms[source_id]
    if len(topic.labels) != 1 or len(topic.references) != 1:
        return None
    label = next(iter(topic.labels))
    ref = next(iter(topic.references)).removeprefix(DBPEDIA)
    if reference_key(ref) != reference_key(label):
        return None
    paths = ancestor_paths(terms, source_id)
    for family, pattern, roots in families:
        if pattern.search(label):
            witnesses = [paths[root] for root in roots if root in paths and root != source_id]
            if witnesses:
                path = min(witnesses, key=lambda item: (len(item), item))
                return family, label, path
    return None


def project(terms, policy, existing, decisions):
    families = [
        (name, re.compile(rule["labels"], re.I), rule["scope"])
        for name, rule in policy["families"].items()
    ]
    candidates = {}
    for source_id in sorted(terms):
        match = classify(terms, source_id, families)
        if match:
            candidates[source_id] = match
    for source_id, entry in policy.get("reviewed_topics", {}).items():
        topic = terms.get(source_id)
        if (topic is None or topic.labels != {entry["label"]}
                or topic.references != {entry["anchor"]}
                or entry["native_parent"] not in topic.parents or not entry["scope"].strip()):
            raise ValueError(f"Reviewed OpenCS topic witness changed: {source_id}")
        candidates[source_id] = (entry["family"], entry["label"], (source_id, entry["native_parent"]))

    by_key = defaultdict(set)
    for source_id, (_, label, _) in candidates.items():
        for key in collision_keys(label):
            by_key[key].add(source_id)

    minted, pending, withheld = {}, {}, {}
    for source_id, (family, label, path) in candidates.items():
        if source_id in policy["exclude"]:
            withheld[source_id] = policy["exclude"][source_id]
            continue
        external = UPSTREAM + source_id
        if external in decisions:
            withheld[source_id] = "existing individual review"
            continue
        keys = collision_keys(label)
        hits = set().union(*(existing.get(key, set()) for key in keys))
        if source_id in policy["review_candidates"]:
            hits.add(str(C[policy["review_candidates"][source_id]]))
        near = set().union(*(by_key[key] for key in keys)) - {source_id}
        if hits or near:
            pending[external] = {
                "label": label, "canonical_candidates": sorted(hits),
                "upstream_candidates": sorted(UPSTREAM+i for i in near),
            }
            continue
        minted[source_id] = (family, label, path)
    return minted, pending, withheld, len(candidates)


def json_text(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def outputs(source, terms, policy, existing, decisions):
    from collections import Counter
    minted, pending, withheld, eligible = project(terms, policy, existing, decisions)
    groups = defaultdict(list)
    reviewed_parents = defaultdict(set)
    for parent, children in policy["direct_broader"].items():
        for child in children:
            if child not in terms or parent not in terms[child].parents:
                raise ValueError(f"Unwitnessed OpenCS direct hierarchy: {child} -> {parent}")
            if child in minted and parent in minted:
                reviewed_parents[child].add(parent)
    overrides = policy.get("editorial_broader", {})
    if missing := overrides.keys() - minted.keys():
        raise ValueError(f"OpenCS broader overrides must target admitted topics: {sorted(missing)}")
    witnesses = ["id\tcanonical\tmodule\tscope_path\tclose_match\tpublished_direct_parents"]
    identities = {}
    reviewed = policy.get("reviewed_topics", {})
    owners = {}
    if reviewed:
        for path in sorted(ROOT.glob("domains/*/modules/**/*.ttl")):
            if "batches" not in path.parts:
                owners.update(Graph().parse(path).subject_objects(SKOS.inScheme))
    for source_id, (family, label, path) in sorted(minted.items()):
        slug = "opencs-" + source_id.lower()
        identities[UPSTREAM + source_id] = slug
        if source_id in reviewed:
            broader = reviewed[source_id]["broader"]
            domain = str(owners.get(C[broader])).removeprefix(str(D))
            if domain not in DOMAINS:
                raise ValueError(f"Unknown OpenCS reviewed parent: {broader}")
        else:
            broader = overrides.get(source_id, policy["families"][family]["broader"])
            domain = "computer-science"
        parents = [f"c:{broader}"] + ["c:opencs-" + p.lower() for p in sorted(reviewed_parents[source_id])]
        scope = f" ;\n    skos:definition {Literal(reviewed[source_id]['scope'], lang='en').n3()}" if source_id in reviewed else ""
        groups[domain, family].append(
            f"c:{slug} a skos:Concept ; skos:prefLabel {Literal(label, lang='en').n3()} ;\n"
            f"    skos:inScheme scheme:{domain} ; skos:broader {', '.join(parents)}{scope} .\n"
        )
        witnesses.append("\t".join((source_id, slug, family, ">".join(path), next(iter(terms[source_id].references)), ",".join(sorted(reviewed_parents[source_id])) or "-")))
    files = {Path(f"domains/{domain}/modules/batches/opencs-{family}.ttl"): HEADER+"\n".join(rows)
             for (domain, family), rows in groups.items()}
    ledger = {
        "source": SOURCE, "sha256": DIGEST, "revision": source["revision"], "license": source["license"],
        "policy": "OpenCS subject-family admission v1. Reviewed naming families, taxonomic scope and concordant topic referents. See sources/opencs/admission-policy.json and admission-witnesses.tsv.",
        "eligible": eligible, "pending": len(pending), "identities": identities,
        "exclusions": dict(Counter(withheld.values())),
        "modules": {str(path): sha256(content.encode()).hexdigest() for path, content in files.items()},
    }
    files[LEDGER] = json_text(ledger)
    files[QUEUE] = json_text(pending)
    files[EVIDENCE] = "\n".join(witnesses) + "\n"
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--write", action="store_true", help="materialize the policy proposal for review")
    args = parser.parse_args()
    print(json.dumps(replay(offline=args.offline, write=args.write), sort_keys=True))


def replay(offline=False, write=False):
    source = registry()[SOURCE]
    if (not source["allow_mapping"] or source["license"] != "CC-BY-4.0" or
            source["sha256"] != DIGEST or source["revision"] != "0.4.0"):
        raise ValueError("OpenCS license or snapshot changed. Review policy and identities before refreshing.")
    report = ingest(source, offline)
    terms = source_index(staged(source), report["graph"])
    decisions = {
        row["external"] for state in ("approved", "rejected")
        for row in read(ROOT / "reviews" / state / "mappings.json") if row["source"] == SOURCE
    }
    files = outputs(source, terms, read(ROOT / POLICY), editorial_index(), decisions)
    extra = set(ROOT.glob("domains/*/modules/batches/opencs-*.ttl")) - {ROOT / p for p in files}
    if extra:
        raise ValueError(f"Stale generated modules require explicit review: {extra}")
    for path, content in files.items():
        absolute = ROOT / path
        if write:
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.write_text(content, encoding="utf-8")
        elif not absolute.is_file() or absolute.read_bytes() != content.encode():
            raise ValueError(f"OpenCS admission differs at {path}")
    batch = json.loads(files[LEDGER])
    return {"source": SOURCE, "typed": len(terms), "eligible": batch["eligible"],
            "admitted": len(batch["identities"]), "pending": batch["pending"]}


if __name__ == "__main__":
    main()
