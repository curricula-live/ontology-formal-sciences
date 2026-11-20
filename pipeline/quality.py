"""Deterministic release metrics. Counts come from distinct graph terms or retained decisions."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from rdflib import RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, D, ROOT, V, read, registry


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


def graph_metrics(graph, prov):
    """Measure weak connectivity over asserted edges between concept individuals."""
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    owners, domains, modules = {}, Counter(), Counter()
    module_prefix = BASE + "module/"
    for concept in concepts:
        # Authors attach exactly one owning module. Other provenance may identify upstream sources.
        owner, = (str(term).removeprefix(module_prefix) for term in prov.objects(concept, PROV.wasDerivedFrom)
                  if str(term).startswith(module_prefix))
        owners[concept] = owner.split("/", 1)[0]
        modules[owner] += 1
        for scheme in graph.objects(concept, SKOS.inScheme):
            domains[str(scheme).removeprefix(str(D))] += 1

    relations, cross_domain, neighbors = Counter(), Counter(), defaultdict(set)
    for subject, predicate, obj in graph:
        if subject in concepts and obj in concepts:
            relations[str(predicate)] += 1
            if owners[subject] != owners[obj]:
                cross_domain[str(predicate)] += 1
            neighbors[subject].add(obj)
            neighbors[obj].add(subject)
    component_sizes = components(concepts, neighbors)
    scientific = defaultdict(set)
    scientific_counts = Counter()
    cross_science = 0
    cited = {
        (prov.value(statement, RDF.subject), prov.value(statement, RDF.predicate),
         prov.value(statement, RDF.object))
        for statement in prov.subjects(DCTERMS.source)
    }
    cited_edges = 0
    for subject, predicate, obj in graph:
        if subject in concepts and obj in concepts and str(predicate).startswith(str(V)):
            scientific_counts[str(predicate)] += 1
            scientific[subject].add(obj)
            scientific[obj].add(subject)
            cross_science += owners[subject] != owners[obj]
            cited_edges += (subject, predicate, obj) in cited
    participating = set(scientific)
    science_components = components(participating, scientific)

    return {
        "concepts_by_scheme": dict(domains),
        "concepts_by_owning_module": dict(modules),
        "relation_counts": dict(relations),
        "cross_domain_relation_counts": dict(cross_domain),
        "cross_domain_relations": sum(cross_domain.values()),
        "connected_components": len(component_sizes),
        "largest_component": max(component_sizes, default=0),
        "isolated_concepts": sum(not neighbors[term] for term in concepts),
        "scientific_connectivity": {
            "relations": sum(scientific_counts.values()),
            "relations_by_predicate": dict(scientific_counts),
            "cited_relations": cited_edges,
            "cross_domain_relations": cross_science,
            "participating_concepts": len(participating),
            "participating_by_scheme": dict(Counter(owners[term] for term in participating)),
            "concepts_without_specific_relations": len(concepts - participating),
            "components_with_edges": len(science_components),
            "largest_component": max(science_components, default=0),
        },
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
