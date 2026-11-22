"""Produce the Foundation candidate's coverage and independent review packet."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

from rdflib import Literal, OWL, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, G, ROOT, V, checksum, read, write
from pipeline.consumer import dataset, successor_changes
from pipeline.contract import read_json
from pipeline.curate.relations import statement_for
from pipeline.package_check import verify

PLAN = ROOT / "reviews/quality/rc-v1-plan.json"


def local(iri):
    return str(iri).rsplit("/", 1)[-1]


def stratify(rows, size, seed):
    """Proportional allocation with deterministic largest remainders and rank selection."""
    pools = defaultdict(list)
    for row in rows:
        pools[tuple(row["stratum"])].append(row)
    total = len(rows)
    size = min(size, total)
    if not total:
        return {"population": 0, "sample": [], "strata": []}
    counts = {key: size * len(pool) // total for key, pool in pools.items()}
    remainder_rank = sorted(pools, key=lambda key: (-(size * len(pools[key]) % total), key))
    for key in remainder_rank[:size - sum(counts.values())]:
        counts[key] += 1
    results, groups = [], []
    for key, pool in sorted(pools.items()):
        groups.append({"stratum": list(key), "population": len(pool), "selected": counts[key]})
        ranked = sorted(pool, key=lambda row: (sha256((seed + "\0" + row["id"]).encode()).digest(), row["id"]))
        results.extend(ranked[:counts[key]])
    return {"population": total, "sample": results, "strata": groups}


def assessment():
    return {"verdict": "unassessed", "reviewer": None, "evidence_checked": [], "reason": None,
            "correction_or_followup": None}


def packet(manifest, data, plan):
    asserted, alignments, provenance = (data.graph(G[name]) for name in ("asserted", "alignments", "provenance"))
    topics = {s: local(asserted.value(s, SKOS.inScheme)) for s in asserted.subjects(RDF.type, SKOS.Concept)}
    families = {relation: family for family, predicates in plan["relation_families"].items() for relation in predicates}

    def objects(graph, subject, predicate):
        return sorted(map(str, graph.objects(subject, predicate)))

    def concept_info(subject):
        return {"iri": str(subject), "scheme": topics[subject], "labels": objects(asserted, subject, SKOS.prefLabel),
                "definitions": objects(asserted, subject, SKOS.definition),
                "parents": objects(asserted, subject, SKOS.broader),
                "roles": objects(asserted, subject, V.hasScientificRole)}

    def relation_info(triple, graph_name):
        reference = statement_for(triple)
        s, p, o = triple
        result = {"id": str(reference), "graph": str(G[graph_name]), "triple": list(map(str, triple)),
                  "subject": concept_info(s),
                  "witnesses": objects(provenance, reference, PROV.wasDerivedFrom),
                  "citations": objects(provenance, reference, DCTERMS.source),
                  "review_scopes": objects(provenance, reference, DCTERMS.description),
                  "previous_interpretations": objects(provenance, reference, PROV.wasRevisionOf),
                  "assessment": assessment()}
        result["evidence"] = [{
            "id": str(witness),
            "source_resource": objects(provenance, witness, DCTERMS.isPartOf),
            "source_link": objects(provenance, witness, PROV.hadPrimarySource),
            "identifier_or_digest": objects(provenance, witness, DCTERMS.identifier),
            "native_terms": {local(term): objects(provenance, witness, term)
                             for term in (RDF.subject, RDF.predicate, RDF.object)},
            "evidence_type": objects(provenance, witness, DCTERMS.type),
            "extraction_level": objects(provenance, witness, V.evidenceExtraction),
        } for witness in sorted(provenance.objects(reference, PROV.wasDerivedFrom))]
        if o in topics:
            result["object"] = concept_info(o)
        return result

    def admission(subject):
        origin = next(node for node in provenance.objects(subject, PROV.wasDerivedFrom)
                      if str(node).startswith(BASE + "module/"))
        path = str(origin).removeprefix(BASE + "module/")
        if "/batches/" not in path:
            return "authored"
        batch = path.split("/batches/")[1]
        return next((key for key, row in manifest["sources"].items()
                     if row.get("admission") and batch.startswith(key + "-")), "unresolved-batch")

    concept_population = [{"id": str(subject), "stratum": [scheme, admission(subject)],
                           "concept": concept_info(subject),
                           "native_sources": objects(provenance, subject, DCTERMS.source),
                           "origins": objects(provenance, subject, PROV.wasDerivedFrom), "assessment": assessment()}
                          for subject, scheme in topics.items()]
    reviews = {}
    for entry in read(ROOT / "reviews/approved/mappings.json"):
        reviews[entry["canonical"], entry["predicate"], entry["external"]] = entry
    alignment_population = []
    for triple in alignments:
        review = reviews[tuple(map(str, triple))]
        alignment_population.append({"id": review["id"], "stratum": [topics[triple[0]], local(triple[1])],
                                     "triple": list(map(str, triple)), "source": review["source"],
                                     "snapshot_sha256": review["sha256"], "review_rationale": review["rationale"],
                                     "record": "reviews/approved/mappings.json", "assessment": assessment()})
    scientific_population = []
    for triple in asserted:
        s, p, o = triple
        if s in topics and o in topics and str(p).startswith(str(V)) and p != V.containsSymbol:
            family = families[local(p)]
            item = relation_info(triple, "asserted")
            item["stratum"] = [topics[s], family]
            scientific_population.append(item)

    role_census = [relation_info((s, V.hasScientificRole, o), "asserted")
                   for s, o in sorted(asserted.subject_objects(V.hasScientificRole))]
    migration_census = []
    for s in sorted(asserted.subjects(OWL.deprecated, Literal(True))):
        detail = relation_info((s, OWL.deprecated, Literal(True)), "asserted")
        detail["replacement_targets"] = objects(asserted, s, DCTERMS.isReplacedBy)
        detail["native_sources"] = objects(provenance, s, DCTERMS.source)
        migration_census.append(detail)
    gap_census = [row for row in sorted(scientific_population, key=lambda row: row["id"]) if not row["citations"]]

    targeted_relations = []
    for s, p, o, risk in plan["target_relations"]:
        triple = C[s], SKOS.broader if p == "skos:broader" else V[p], C[o]
        if triple not in asserted:
            raise ValueError(f"Targeted assertion is absent: {triple}")
        targeted_relations.append(relation_info(triple, "asserted") | {"risk": risk})
    vetoes = {row["id"]: row for row in read(ROOT / "reviews/rejected/mappings.json")}
    targeted_mappings = []
    for key in plan["rejected_mappings"]:
        record = vetoes[key]
        targeted_mappings.append({"source": record["source"], "id": key, "proposed_target": record["canonical"],
                                  "native": record["external"], "predicate": record["predicate"],
                                  "decision": "withheld", "rationale": record["rationale"],
                                  "record": "reviews/rejected/mappings.json", "assessment": assessment()})
    targeted_projections = []
    for source, triples in plan["rejected_projections"].items():
        path = ROOT / f"reviews/relations/{source}-decisions.json"
        ledger = read(path)
        for keys in triples:
            decision, = (r for r in ledger["decisions"]["rejected"] if r[:3] == keys)
            targeted_projections.append({"native_keys": keys, "source": source, "decision": "withheld",
                                         "snapshot_sha256": ledger["sha256"], "rationale": decision[3],
                                         "record": str(path.relative_to(ROOT)), "assessment": assessment()})
    return {
        "review_status": "prepared for independent review",
        "assessment_choices": ["supported_at_stated_scope", "unsupported", "incorrect_direction",
                               "role_confusion", "wrong_identity", "needs_assumption", "insufficient_evidence"],
        "seed": plan["seed"],
        "method": "Largest-remainder allocation proportional to stratum size, followed by hash ranking without replacement. Zero allocations are recorded. Census and targeted cases are separate and cannot estimate an overall error rate.",
        "representative": {name: stratify(rows, plan["sample_sizes"][name], plan["seed"] + ":" + name)
                           for name, rows in [("concepts", concept_population), ("alignments", alignment_population),
                                               ("scientific_relations", scientific_population)]},
        "critical_census": {"role_assignments": role_census, "identity_migrations": migration_census,
                            "scientific_statements_without_citation": gap_census},
        "targeted": {"relation_scopes": targeted_relations, "rejected_mappings": targeted_mappings,
                     "rejected_projections": targeted_projections},
        "evidence_note": "A stored rationale records the producer judgment. Compare RDF terms, source snapshot and actual scientific scope before completing an assessment.",
    }


def coverage(manifest, data):
    graph = data.graph(G.asserted)
    by_scheme = defaultdict(set)
    for subject in graph.subjects(RDF.type, SKOS.Concept):
        by_scheme[local(graph.value(subject, SKOS.inScheme))].add(subject)
    by_domain = {}
    for scheme, members in sorted(by_scheme.items()):
        buckets, agenda = {}, [C[scheme]]
        depth = {C[scheme]: 0}
        for parent in agenda:
            for subject in graph.subjects(SKOS.broader, parent):
                if subject in members and subject not in depth:
                    depth[subject] = depth[parent] + 1
                    agenda.append(subject)
        for branch in sorted(s for s in graph.subjects(SKOS.broader, C[scheme]) if s in members):
            descendants = set(graph.transitive_subjects(SKOS.broader, branch)) & members
            buckets[local(branch)] = {"label": str(graph.value(branch, SKOS.prefLabel)),
                                      "members_including_branch": len(descendants)}
        role_counts = Counter(local(role) for s in members for role in graph.objects(s, V.hasScientificRole))
        by_domain[scheme] = {
            "canonical_subjects": len(members), "direct_branches": buckets,
            "minimum_same_scheme_taxonomic_depth": dict(Counter(str(n) for n in depth.values())),
            "unreachable_from_owner_root": len(members - set(depth)),
            "reviewed_roles": dict(role_counts),
            "unclassified": sum(not any(graph.objects(s, V.hasScientificRole)) for s in members),
            "with_definition": sum(any(graph.objects(s, SKOS.definition)) for s in members),
        }
    frames = {
        "msc2020": "Mathematics classification reference only. Noncommercial share-alike scope excludes a default source-content import.",
        "acm-ccs": "Computing classification reference. Permission remains unresolved.",
        "cso": "Computing research topic reference. Reviewed mappings are narrower than its staged corpus.",
        "opencs": "Computing and selected formal topics. Reviewed admission families limit the published scope.",
        "ontomath-pro": "Mathematics class hierarchy. Class depth and canonical topic depth have different meanings.",
        "ontomath-edu": "Educational ontology and native axiom scope. A staged class is not a canonical concept.",
        "stato": "Statistics vocabulary. Native labels and axioms are reviewed separately from imports.",
        "tptp": "Logic/formal reasoning reference with a narrow staged example.",
        "mathlib4": "Formal declarations and module index provide a granularity reference. Textual declarations differ from checked proofs.",
    }
    quality = manifest["quality"]
    return {
        "domains": by_domain,
        "reference_frames": {key: {"interpretation": note, "snapshot_scope": manifest["sources"][key]["scope"],
                                    "staged_triples": manifest["sources"][key]["staged_triples"],
                                    "rights": manifest["sources"][key]["license"]} for key, note in frames.items()},
        "batch_admissions": {key: {field: value for field, value in row["admission"].items() if field != "modules"}
                             for key, row in manifest["sources"].items() if row.get("admission")},
        "mapping_dispositions": {key: quality[key] for key in
                                 ("approved_mappings", "rejected_mappings", "pending_mapping_pairs",
                                  "pending_nonconcept_pairs", "batch_pending_entities")},
        "scientific_connectivity_profile": {
            key: quality["scientific_connectivity"][key] for key in
            ("relations", "cited_relations", "coverage_by_scheme", "cross_domain_relations")
        },
        "limits": [
            "Direct taxonomic branches may overlap. Minimum path depth describes editorial organization, not formal granularity.",
            "Concepts range from subject areas to individual results, algorithms and representations. Counts do not establish breadth or correctness.",
            "Graphs of source axioms, indices or bibliography do not provide a denominator for canonical coverage.",
            "Connected components measure edge participation. They do not measure scientific importance, scope fidelity or overall completeness.",
            "Role counts apply only to the explicitly reviewed subset. Missing types are unresolved.",
        ],
    }


def generate(package, output):
    manifest = read_json(package / "manifest.json")
    data = dataset((package / "formal-sciences.nq").read_bytes())
    digest = checksum(package / "manifest.json")
    for name, payload in [("independent-review.json", packet(manifest, data, read(PLAN))),
                          ("coverage.json", coverage(manifest, data))]:
        write(output / name, payload | {"manifest_sha256": digest})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ROOT / "dist")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--predecessor", type=Path)
    args = parser.parse_args()
    verify(args.package)
    if args.predecessor:
        verify(args.predecessor, read(PLAN)["baseline"]["manifest_sha256"])
        print(successor_changes(*(dataset((path / "formal-sciences.nq").read_bytes())
                                 for path in (args.predecessor, args.package))))
    if args.output:
        generate(args.package, args.output)
