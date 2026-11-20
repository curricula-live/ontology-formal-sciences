"""Bind editorial audit findings to current identities and pinned review records."""
from collections import Counter

from rdflib import RDF, SKOS

from pipeline.common import BASE, C, ROOT, checksum, read, registry
from pipeline.parse import ingest, staged

AUDITS = ROOT / "reviews/quality"


def release_audit(version, graph, sources):
    path = AUDITS / f"{version}.json"
    if not path.is_file():
        return None
    audit = read(path)
    if audit["version"] != version:
        raise ValueError("Semantic audit version mismatch")

    mappings = {}
    for state in ("approved", "rejected"):
        for row in read(ROOT / f"reviews/{state}/mappings.json"):
            mappings[(row["source"], row["id"])] = state
    formal_properties = read(ROOT / "reviews/formal-properties/openmath-decisions.json")["decisions"]
    declarations = {row["name"]: row["claims"] for row in
                    read(ROOT / "reviews/formal-properties/mathlib4-declarations.json")["declarations"]}
    ledgers = {}
    counts, methods, batch_domains, domains, predicates = (
        Counter(), Counter(), Counter(), Counter(), Counter()
    )
    unique = set()
    for row in audit["cases"]:
        source, method = row["source"], row["method"]
        key = tuple(row["key"]) if isinstance(row["key"], list) else row["key"]
        identity = source, method, key
        verdict = row["verdict"]
        if (source not in sources or identity in unique or not row["rationale"].strip() or
                verdict not in {"retained", "corrected", "withheld"}):
            raise ValueError(f"Invalid semantic audit case: {identity}")
        unique.add(identity)
        expected = "rejected" if verdict == "withheld" else "approved"
        if method == "batch_admission":
            if source not in ledgers:
                ledgers[source] = read(ROOT / f"reviews/approved/batches/{source}.json")
            slug = row["canonical"]
            term = C[slug]
            if (ledgers[source]["sha256"] != sources[source]["sha256"] or
                    ledgers[source]["identities"].get(key) != slug or
                    (term, RDF.type, SKOS.Concept) not in graph or not row["label_witness"]):
                raise ValueError(f"Batch audit identity no longer resolves: {identity}")
            if "broader" in row and (term, SKOS.broader, C[row["broader"]]) not in graph:
                raise ValueError(f"Audited parent correction is absent: {identity}")
            if row.get("requires_definition") and graph.value(term, SKOS.definition) is None:
                raise ValueError(f"Audited scope correction is absent: {identity}")
            domain = str(graph.value(term, SKOS.inScheme)).removeprefix(BASE + "scheme/")
            batch_domains[domain] += 1
        elif method == "mapping":
            if mappings.get((source, key)) != expected:
                raise ValueError(f"Audited mapping decision changed: {identity}")
        elif method == "relation_projection":
            relation_decisions = read(ROOT / f"reviews/relations/{source}-decisions.json")
            known = {tuple(entry[:3]) for entry in relation_decisions["decisions"][expected]}
            if key not in known:
                raise ValueError(f"Audited relation decision changed: {identity}")
        elif method == "formal_property":
            if formal_properties[key]["state"] != expected:
                raise ValueError(f"Audited OpenMath decision changed: {identity}")
        elif method == "formal_declaration":
            name, *triple = key
            if not any(claim["triple"] == triple and claim["state"] == expected
                       for claim in declarations.get(name, ())):
                raise ValueError(f"Audited Mathlib claim decision changed: {identity}")
        else:
            raise ValueError(f"Unknown audit method: {method}")
        counts[verdict] += 1
        methods[method] += 1
        domains[domain if method == "batch_admission" else row["scheme"]] += 1
        if "predicate" in row:
            predicates[row["predicate"]] += 1
    for source, assessment in audit["source_assessments"].items():
        if sources[source]["sha256"] != assessment["sha256"]:
            raise ValueError(f"Source assessment requires review: {source}")
    return dict(
        record=str(path.relative_to(ROOT)), sha256=checksum(path), cases=len(unique),
        verdicts=dict(counts), by_method=dict(methods), batch_sample_by_scheme=dict(batch_domains),
        by_scheme=dict(domains),
        by_predicate=dict(predicates), sources=sorted({source for source, _, _ in unique}),
        selection_limit=audit["selection_limit"], source_assessments=audit["source_assessments"],
        corrected_subjects=[str(C[row["canonical"]]) for row in audit["cases"] if row["verdict"] == "corrected"],
    )


def replay(version, offline=False):
    """Verify sampled labels against the same original named graphs as batch admission."""
    audit = read(AUDITS / f"{version}.json")
    sources = registry()
    by_source = {}
    for row in audit["cases"]:
        if row["method"] == "batch_admission":
            by_source.setdefault(row["source"], []).append(row)
    verified = 0
    for source, rows in sorted(by_source.items()):
        entry = sources[source]
        graph = ingest(entry, offline)["graph"]
        store = staged(entry)
        for row in rows:
            witness = " ".join(row["label_witness"])
            if not bool(store.query(f"ASK {{ GRAPH <{graph}> {{ {witness} }} }}")):
                raise ValueError(f"Semantic audit label witness changed: {row['key']}")
            verified += 1
    return {"audit": version, "source_families": len(by_source), "verified_batch_witnesses": verified}
