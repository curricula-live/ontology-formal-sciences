"""Deterministic release metrics. Counts come from distinct graph terms or retained decisions."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from rdflib import RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, ROOT, V, read, registry


def components(concepts, neighbors):
    remaining = concepts.copy()
    component_sizes = []
    while remaining:
        queue = [remaining.pop()]
        size = 0
        while queue:
            current = queue.pop()
            size += 1
            new = neighbors[current].intersection(remaining)
            queue.extend(new)
            remaining.difference_update(new)
        component_sizes.append(size)
    return component_sizes


def relation_connectivity(edges, owners, population=None):
    neighbors = defaultdict(set)
    cross = Counter()
    for subject, _, obj in edges:
        neighbors[subject].add(obj)
        neighbors[obj].add(subject)
        if owners[subject] != owners[obj]:
            cross[f"{owners[subject]} -> {owners[obj]}"] += 1
    participating = set(neighbors)
    sizes = components(participating if population is None else population, neighbors)
    return {
        "relations": len(edges),
        "participating_concepts": len(participating),
        "participating_by_scheme": dict(Counter(owners[term] for term in participating)),
        "cross_domain_relations": sum(cross.values()),
        "cross_domain_by_direction": dict(cross),
        "components_with_edges": sum(size > 1 for size in sizes),
        "component_size_histogram": dict(Counter(map(str, sizes))),
        "largest_component": max(sizes, default=0),
    }


def graph_metrics(graph, prov):
    """Measure asserted taxonomy, scientific edges and replayable evidence separately."""
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    owners, modules = {}, Counter()
    module_prefix = BASE + "module/"
    for concept in concepts:
        owner, = (str(term).removeprefix(module_prefix) for term in prov.objects(concept, PROV.wasDerivedFrom)
                  if str(term).startswith(module_prefix))
        owners[concept] = owner.split("/", 1)[0]
        modules[owner] += 1

    relations, cross_domain = Counter(), Counter()
    asserted = {(s, p, o) for s, p, o in graph if s in concepts and o in concepts}
    for subject, predicate, obj in asserted:
        relations[str(predicate)] += 1
        if owners[subject] != owners[obj]:
            cross_domain[str(predicate)] += 1

    full = relation_connectivity(asserted, owners, concepts)
    hierarchy = {triple for triple in asserted if triple[1] == SKOS.broader}
    specific = {triple for triple in asserted if str(triple[1]).startswith(str(V))}
    cited, source_edges = set(), defaultdict(set)
    for statement in prov.subjects(DCTERMS.source):
        triple = tuple(prov.value(statement, prop) for prop in (RDF.subject, RDF.predicate, RDF.object))
        if triple not in specific:
            continue
        cited.add(triple)
        for witness in prov.objects(statement, PROV.wasDerivedFrom):
            source = prov.value(witness, DCTERMS.isPartOf)
            if source is not None:
                source_edges[str(source).removeprefix(BASE + "source/")].add(triple)

    science = relation_connectivity(specific, owners)
    science.update({
        "relations_by_predicate": dict(Counter(str(triple[1]) for triple in specific)),
        "cited_relations": len(cited),
        "citation_coverage": round(len(cited) / len(specific), 6) if specific else None,
        "concepts_without_specific_relations": len(concepts) - science["participating_concepts"],
        "evidence_backed": relation_connectivity(cited, owners),
        "pinned_source_contributions": {
            name: relation_connectivity(triples, owners) for name, triples in source_edges.items()
        },
    })
    return {
        "concepts_by_scheme": dict(Counter(owners.values())),
        "concepts_by_owning_module": dict(modules),
        "relation_counts": dict(relations),
        "cross_domain_relation_counts": dict(cross_domain),
        "cross_domain_relations": sum(cross_domain.values()),
        "connected_components": sum(full["component_size_histogram"].values()),
        "largest_component": full["largest_component"],
        "isolated_concepts": full["component_size_histogram"].get("1", 0),
        "taxonomic_connectivity": relation_connectivity(hierarchy, owners, concepts),
        "scientific_connectivity": science,
    }

def mapping_counts(graph, maps, catalog):
    """Track still-open retained candidate pairs separately from batch admission queues."""
    decided = set()
    result = {source: Counter() for source in catalog}
    for state in ("approved", "rejected"):
        for row in read(ROOT / "reviews" / state / "mappings.json"):
            decided.add((row["source"], row["external"], row["canonical"]))
            result[row["source"]][state] += 1
    pending = set()
    for path in sorted((ROOT / "reviews/pending").glob("*.json")):
        for row in read(path):
            source = row.get("source", path.stem)
            if row["state"] != "pending" or row["sha256"] != catalog[source]["sha256"]:
                continue
            key = source, row["external"], row["canonical"]
            if key in decided or key in pending:
                continue
            pending.add(key)
            if (URIRef(row["canonical"]), RDF.type, SKOS.Concept) in graph:
                result[source]["pending"] += 1
            else:
                result[source]["nonconcept_candidates"] += 1
    if sum(counts["approved"] for counts in result.values()) != len(maps):
        raise ValueError("Published mappings differ in number from approved review decisions")
    return result


def quality(graph, maps, prov, inferred, inventory, report):
    catalog = registry()
    decisions = mapping_counts(graph, maps, catalog)
    result = graph_metrics(graph, prov)
    result.update({
        "staged_graphs": sum(row["stage_validation"] == "passed" for row in inventory.values()),
        "staged_triples": sum(row["staged_triples"] for row in inventory.values()),
        "approved_mappings": len(maps),
        "pending_mapping_pairs": sum(row["pending"] for row in decisions.values()),
        "pending_nonconcept_pairs": sum(row["nonconcept_candidates"] for row in decisions.values()),
        "rejected_mappings": sum(row["rejected"] for row in decisions.values()),
        "inferred_triples": len(inferred),
        "validation_findings": len(report["findings"]),
        "sources_with_mapping_disabled": sorted(key for key in catalog if not catalog[key]["allow_mapping"]),
        "batch_eligible_entities": sum(row.get("admission", {}).get("eligible", 0) for row in inventory.values()),
        "batch_pending_entities": sum(row.get("admission", {}).get("pending", 0) for row in inventory.values()),
        "contributions": {},
    })
    for source, entry in inventory.items():
        admission = entry.get("admission", {})
        row = {state: decisions[source][state] for state in ("approved", "rejected", "pending")}
        eligible, identities = admission.get("eligible"), admission.get("identities")
        row.update(eligible=eligible, identities=identities, new_concepts=admission.get("new_concepts"),
                   admitted_fraction=round(identities / eligible, 6) if eligible and identities is not None else None)
        result["contributions"][source] = row
    return result


def comparison(before, after):
    """Signed changes in common numeric indicators, including pre-quality manifests."""
    def indicators(manifest):
        result = dict(manifest["counts"], concepts=manifest["concepts"])
        result["staged_triples"] = sum(row["staged_triples"] for row in manifest["sources"].values())
        result["staged_graphs"] = sum(row["stage_validation"] == "passed" for row in manifest["sources"].values())
        result.update({k: v for k, v in manifest.get("quality", {}).items() if type(v) is int})
        return result
    a, b = indicators(before), indicators(after)
    return {key: b[key] - a[key] for key in sorted(a.keys() & b.keys())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two immutable release manifests")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    print(json.dumps(comparison(read(args.before), read(args.after)), indent=2))
