"""Bind editorial audit findings to current identities and pinned review records."""
from collections import Counter

from rdflib import Dataset, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, D, G, ROOT, V, checksum, read, registry
from pipeline.curate.relations import statement_for
from pipeline.parse import ingest, staged

AUDITS = ROOT / "reviews/quality"


def canonical_triple(keys):
    subject, predicate, obj = keys
    return C[subject], SKOS.broader if predicate == "skos:broader" else V[predicate], C[obj]


def summarize_sample(sample, version, graph, provenance, mappings):
    from pipeline.curate.cs_evidence import DECISIONS
    from pipeline.semantic_sampling import design

    if (sample["baseline"], sample["seed"]) != design(version):
        raise ValueError("Semantic audit sampling design changed")
    observations, predicates, schemes = Counter(), Counter(), Counter()
    for row in sample["relations"]:
        old = canonical_triple(row["triple"])
        current = canonical_triple(row.get("replacement", row["triple"]))
        if (current not in graph or graph.value(old[0], SKOS.inScheme) != D[row["scheme"]]
                or not row["judgment"].strip()):
            raise ValueError(f"Sampled relationship cannot be verified: {row['triple']}")
        if old != current and (old in graph or (statement_for(current), PROV.wasRevisionOf,
                                               statement_for(old)) not in provenance):
            raise ValueError(f"Sampled correction lacks its retired interpretation: {row['triple']}")
        if row["outcome"] == "evidence_added" and not provenance.value(statement_for(current), DCTERMS.source):
            raise ValueError(f"Sampled new evidence is absent: {row['triple']}")
        schemes[row["scheme"]] += 1
        predicates[row["triple"][1]] += 1
        observations[row["outcome"]] += 1
    for row in sample["topics"]:
        subject = C[row["canonical"]]
        if ((subject, RDF.type, SKOS.Concept) not in graph or graph.value(subject, SKOS.inScheme) != D[row["scheme"]]
                or not row["judgment"].strip()):
            raise ValueError(f"Sampled canonical topic cannot be verified: {row['canonical']}")
        if row.get("definition_added") and not graph.value(subject, SKOS.definition):
            raise ValueError(f"Sampled scope correction is absent: {row['canonical']}")
        observations[row["outcome"]] += 1
    reviewed_passages = {
        (r["corpus"], r["path"], r["first"], r["last"], tuple(j["triple"]))
        for r in read(DECISIONS) for j in r["judgments"] if j["state"] == "approved"
    }
    for row in sample["passages"]:
        key = (row["corpus"], row["path"], row["first"], row["last"], tuple(row["triple"]))
        if key not in reviewed_passages or canonical_triple(row["triple"]) not in graph or not row["judgment"].strip():
            raise ValueError(f"Sampled passage cannot be verified: {key}")
        observations[row["outcome"]] += 1
    for row in sample.get("mappings", ()):
        if mappings.get((row["source"], row["id"])) != row["state"] or not row["judgment"].strip():
            raise ValueError(f"Sampled mapping cannot be verified: {row['id']}")
        observations[row["outcome"]] += 1
    return {
        "baseline": sample["baseline"], "seed": sample["seed"],
        "baseline_relation_sample": len(sample["relations"]),
        "baseline_topic_sample": len(sample["topics"]),
        "new_passage_sample": len(sample["passages"]),
        "mapping_sample": len(sample.get("mappings", ())),
        "outcomes": dict(observations), "baseline_relations_by_scheme": dict(schemes),
        "baseline_relations_by_predicate": dict(predicates),
    }


def release_audit(version, graph, sources, provenance=None):
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
    result = dict(
        record=str(path.relative_to(ROOT)), sha256=checksum(path), cases=len(unique),
        verdicts=dict(counts), by_method=dict(methods), batch_sample_by_scheme=dict(batch_domains),
        by_scheme=dict(domains),
        by_predicate=dict(predicates), sources=sorted({source for source, _, _ in unique}),
        selection_limit=audit["selection_limit"], source_assessments=audit["source_assessments"],
        corrected_subjects=[str(C[row["canonical"]]) for row in audit["cases"] if row["verdict"] == "corrected"],
    )
    if "stratified_sample" in audit:
        result["stratified_sample"] = summarize_sample(audit["stratified_sample"], version, graph, provenance, mappings)
    if "unresolved_identities" in audit:
        result["unresolved_identities"] = len(audit["unresolved_identities"])
    if "targeted_passages" in audit:
        from pipeline.curate.cs_evidence import DECISIONS

        rejected = {
            (row["corpus"], row["path"], row["first"], row["last"], tuple(decision["triple"]))
            for row in read(DECISIONS) for decision in row["judgments"] if decision["state"] == "rejected"
        }
        for row in audit["targeted_passages"]:
            key = row["corpus"], row["path"], row["first"], row["last"], tuple(row["triple"])
            if key not in rejected or canonical_triple(row["triple"]) in graph or not row["judgment"].strip():
                raise ValueError(f"Targeted passage exclusion cannot be verified: {key}")
        result["targeted_passage_exclusions"] = len(audit["targeted_passages"])
    if "legacy_citation_gaps" in audit:
        closed = audit["legacy_citation_gaps"]
        for keys in closed:
            triple = canonical_triple(keys)
            if triple not in graph or not provenance.value(statement_for(triple), DCTERMS.source):
                raise ValueError(f"Legacy citation gap is still open: {keys}")
        result["closed_legacy_citation_gaps"] = len(closed)
    if "baseline_comparison" in audit:
        result["baseline_comparison"] = audit["baseline_comparison"]
    return result


def replay(version, offline=False, baseline=None):
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
    report = {"audit": version, "source_families": len(by_source), "verified_batch_witnesses": verified}
    if baseline is not None:
        from pipeline.semantic_sampling import compare_participation, select

        sample = audit["stratified_sample"]
        if checksum(baseline) != audit["baseline_comparison"]["dataset_sha256"]:
            raise ValueError("Stratified audit baseline checksum differs")
        for kind, selected in select(baseline, version).items():
            stored = sample[kind]
            if isinstance(selected, list):
                if len(stored) != len(selected) or any(
                    any(expected.get(key) != value for key, value in row.items())
                    for row, expected in zip(selected, stored)
                ):
                    raise ValueError(f"Stratified audit selection differs: {kind}")
                report[f"verified_sampled_{kind}"] = len(selected)
            elif selected != stored:
                raise ValueError(f"Stratified audit selection differs: {kind}")
        if expected := audit["baseline_comparison"].get("participation"):
            previous, current = Dataset(), Dataset()
            previous.parse(baseline, format="nquads")
            current.parse(ROOT / "dist/formal-sciences.nq", format="nquads")
            if compare_participation(previous.graph(G.asserted), current.graph(G.asserted)) != expected:
                raise ValueError("Baseline-cohort participation comparison differs")
            report["verified_participation_comparison"] = True
    return report
