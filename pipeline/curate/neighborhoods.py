"""Inventory native topic neighborhoods without projecting scientific predicates."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pyoxigraph import NamedNode
from rdflib import Graph, OWL, RDFS, SKOS, URIRef

from pipeline.common import C, ROOT, checksum, read, registry, write
from pipeline.parse import ingest, staged

OCS = "https://w3id.org/ocs/ont/"
CSO = "https://cso.kmi.open.ac.uk/topics/"
CSO_SCHEMA = "https://cso.kmi.open.ac.uk/schema/cso#"
OMP = "http://cll.niimm.ksu.ru/ontologies/mathematics#"
DBPEDIA = "http://dbpedia.org/resource/"
PROFILES = {
    "opencs": (OCS, "CC-BY-4.0", {
        "broader_topic": str(SKOS.broader), "associated_topic": str(SKOS.related),
    }),
    "cso": (CSO, "CC-BY-4.0", {
        "super_topic": CSO_SCHEMA + "superTopicOf", "contributes_to_topic": CSO_SCHEMA + "contributesTo",
        "related_equivalent_topic": CSO_SCHEMA + "relatedEquivalent",
    }),
    "ontomath-pro": (OMP, "Apache-2.0", {
        "named_subclass": str(RDFS.subClassOf), "named_disjoint_classes": str(OWL.disjointWith),
    }),
}
REPORT = ROOT / "reviews/neighborhoods"


def mapping_rows():
    return {state: read(ROOT / f"reviews/{state}/mappings.json") for state in ("approved", "rejected")}


def context_digest(source, decisions):
    sources = {source, "cso"} if source == "opencs" else {source}
    mapping_context = {state: [row for row in rows if row["source"] in sources]
                       for state, rows in decisions.items()}
    batch = ROOT / f"reviews/approved/batches/{source}.json"
    configuration = [PROFILES[source], mapping_context, checksum(batch) if batch.is_file() else None]
    return sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()


def endpoint_index(source, decisions):
    exact, references, rejected = defaultdict(set), defaultdict(set), defaultdict(set)
    batch = ROOT / f"reviews/approved/batches/{source}.json"
    if batch.exists():
        for external, slug in read(batch)["identities"].items():
            exact[external].add(str(C[slug]))
    for row in decisions["approved"]:
        if row["source"] == source:
            targets = exact if row["predicate"] == str(SKOS.exactMatch) else references
            targets[row["external"]].add(row["canonical"])
    for row in decisions["rejected"]:
        if row["source"] == source:
            rejected[row["external"]].add(row["canonical"])
    return exact, references, rejected


def resolution(left, right, exact, references, rejected):
    if any(len(exact.get(term, ())) > 1 for term in (left, right)):
        return "ambiguous_admitted_identity"
    if left in exact and right in exact:
        return "same_canonical_subject" if exact[left] == exact[right] else "two_canonical_subjects"
    if any(term not in exact and term in references for term in (left, right)):
        return "needs_scoped_endpoint_review"
    if any(term not in exact and term in rejected for term in (left, right)):
        return "unresolved_with_negative_history"
    if left in exact or right in exact:
        return "one_canonical_subject"
    return "neither_endpoint_admitted"


def anchor_claims(decisions):
    """Use explicit native CSO witnesses already validated by mapping evidence replay."""
    anchors = defaultdict(set)
    for row in decisions["approved"]:
        if row["source"] != "cso" or row["predicate"] != str(SKOS.exactMatch):
            continue
        evidence = Graph().parse(data=row["evidence"], format="nt")
        for anchor in evidence.objects(URIRef(row["external"]), OWL.sameAs):
            if isinstance(anchor, URIRef) and str(anchor).startswith(DBPEDIA):
                anchors[str(anchor)].add((row["external"], row["canonical"]))
    return anchors


def anchor_candidates(store, graph, decisions, exact, rejected):
    anchors = anchor_claims(decisions)
    candidates = []
    for ref, targets in sorted(anchors.items()):
        subjects = sorted({quad.subject.value for quad in store.quads_for_pattern(
            None, NamedNode(str(SKOS.closeMatch)), NamedNode(ref), graph
        ) if isinstance(quad.subject, NamedNode) and quad.subject.value.startswith(OCS)})
        possible = {canonical for _, canonical in targets}
        for external in subjects:
            for cso, canonical in sorted(targets):
                if canonical in rejected.get(external, ()):
                    status = "rejected_pair"
                elif len(subjects) != 1 or len(possible) != 1:
                    status = "ambiguous_shared_anchor"
                elif external in exact:
                    status = "consistent_with_review" if exact[external] == {canonical} else "conflicting_admitted_subject"
                else:
                    status = "review_shared_anchor"
                candidates.append([external, ref, cso, canonical, status])
    return candidates


def inventory(source, store, graph_name, decisions):
    source_id = source["id"]
    prefix, license, predicates = PROFILES[source_id]
    if source["license"] != license:
        raise ValueError(f"Review the {source_id} neighborhood rights")
    graph = NamedNode(graph_name)
    exact, references, rejected = endpoint_index(source_id, decisions)
    by_predicate = {}
    for kind, predicate in sorted(predicates.items()):
        counts = Counter()
        for quad in store.quads_for_pattern(None, NamedNode(predicate), None, graph):
            if not all(isinstance(term, NamedNode) and term.value.startswith(prefix)
                       for term in (quad.subject, quad.object)):
                counts["outside_native_named_scope"] += 1
                continue
            left, right = quad.subject.value, quad.object.value
            state = resolution(left, right, exact, references, rejected)
            counts[state] += 1
        by_predicate[kind] = {"predicate": predicate, "candidate_causes": dict(counts)}
    anchors = anchor_candidates(store, graph, decisions, exact, rejected) if source_id == "opencs" else []
    result = {
        "source": source_id, "sha256": source["sha256"], "revision": source["revision"],
        "profile": "source-neighborhood-review-v1", "by_predicate": by_predicate,
        "context_sha256": context_digest(source_id, decisions),
        "shared_dbpedia_anchor_candidates": anchors,
        "anchor_dispositions": dict(Counter(row[-1] for row in anchors)),
    }
    if source_id == "ontomath-pro":
        result["owl_restriction_inventory"] = {
            name: sum(1 for _ in store.quads_for_pattern(None, NamedNode(str(predicate)), None, graph))
            for name, predicate in {
                "all_values_from": OWL.allValuesFrom, "some_values_from": OWL.someValuesFrom,
                "has_value": OWL.hasValue,
            }.items()
        }
    return result


def replay(source_id, offline=False, write_evidence=False):
    source = registry()[source_id]
    graph = ingest(source, offline)["graph"]
    record = inventory(source, staged(source), graph, mapping_rows())
    path = REPORT / f"{source_id}.json"
    if write_evidence:
        write(path, record)
    elif record != read(path):
        raise ValueError(f"Source neighborhood evidence changed: {source_id}")
    return {"source": source_id, "by_predicate": record["by_predicate"],
            "anchor_dispositions": record["anchor_dispositions"]}


def release_summaries(sources):
    decisions = mapping_rows()
    for path in sorted(REPORT.glob("*.json")):
        source = sources[path.stem]
        data = read(path)
        if (data["sha256"] != source["sha256"] or data["revision"] != source["revision"]
                or data["context_sha256"] != context_digest(path.stem, decisions)):
            raise ValueError(f"Stale neighborhood evidence: {path.stem}")
        yield path.stem, {key: data[key] for key in (
            "profile", "by_predicate", "anchor_dispositions", "owl_restriction_inventory"
        ) if key in data} | {
            "evidence_sha256": checksum(path),
        }
