"""Replay endpoint evidence and classify the resolution work for relation candidates."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import re

from pyoxigraph import Literal as SourceLiteral, NamedNode
from rdflib import RDF, RDFS, SKOS, URIRef

from pipeline.common import C, D, ROOT, read
from pipeline.normalize import label_key

DIRECTORY = ROOT / "reviews/endpoints"
MARDI = "https://portal.mardi4nfdi.de/entity/"
PROFILE_TYPES = {
    "Q6534268": "research-field", "Q6534269": "application-problem",
    "Q6534270": "model", "Q6534271": "quantity",
    "Q6534272": "modeling-task", "Q5981696": "formulation",
}
NON_TOPICS = {"quantity", "application-problem", "research-field"}
MARDI_APPLIED_FIELDS = {
    "Q6684695": "enzyme kinetics", "Q6821435": "agronomy",
}
ROLE_HEADS = {
    "model": {"control-systems-theory", "differential-equations", "statistical-model"},
    "modeling-task": {"algorithms", "numerical-analysis", "statistical-estimation"},
    "formulation": {"numerical-analysis", "linear-algebra", "differential-equations", "statistical-estimation"},
}
# Descriptions stay in the source store. Hashing tokens lets offline review
# compare definitions without republishing upstream text.
STOP = set("the a an of is are in for with from and by to be or as at on that this which".split())


def definition_terms(text):
    return {sha256(word.encode()).hexdigest()[:16]
            for word in re.findall(r"[^\W\d_]+", label_key(text)) if len(word) >= 3 and word not in STOP}


def applied_contexts(store, graph):
    """Find model and task records whose source context is confined to named applied fields."""
    for local, label in MARDI_APPLIED_FIELDS.items():
        if not any(isinstance(q.object, SourceLiteral) and q.object.language == "en" and q.object.value == label
                   for q in store.quads_for_pattern(NamedNode(MARDI + local),
                                                    NamedNode(str(RDFS.label)), None, graph)):
            raise ValueError(f"Unverified MathModDB field anchor {local}")
    incoming = {}
    for predicate in ("P1560", "P1513", "P147"):
        origins = defaultdict(set)
        for q in store.quads_for_pattern(None, NamedNode(MARDI + predicate), None, graph):
            if isinstance(q.subject, NamedNode) and isinstance(q.object, NamedNode):
                origins[q.object.value.removeprefix(MARDI)].add(q.subject.value.removeprefix(MARDI))
        incoming[predicate] = origins

    problem_fields = {problem: fields for problem, fields in incoming["P1560"].items()
                      if fields and fields <= MARDI_APPLIED_FIELDS.keys()}
    model_problems = {model: problems for model, problems in incoming["P1513"].items()
                      if problems and problems <= problem_fields.keys()}
    task_models = {task: models for task, models in incoming["P147"].items()
                   if models and models <= model_problems.keys()}
    return {local: sorted(origins) for local, origins in
            (model_problems | task_models).items()}


def collect(store, graph_name, source_id, namespace, edges):
    graph = NamedNode(graph_name)
    definition_properties = {
        "mathmoddb": ("https://schema.org/description",),
        "ml-schema": ("http://purl.org/dc/terms/description",),
        "stato": ("http://purl.obolibrary.org/obo/IAO_0000115",),
        "ontomath-pro": (str(SKOS.definition),),
    }[source_id]
    scope = applied_contexts(store, graph) if source_id == "mathmoddb" else {}
    evidence = {}
    for local in sorted({endpoint for left, _, right in edges for endpoint in (left, right)}):
        node = NamedNode(namespace + local)
        labels, english, signature, types, parents = set(), set(), set(), set(), set()
        for quad in store.quads_for_pattern(node, None, None, graph):
            predicate = quad.predicate.value
            value = quad.object
            if isinstance(value, SourceLiteral) and value.language in {"en", None}:
                if predicate in {str(RDFS.label), str(SKOS.prefLabel)} and value.value.strip():
                    (english if value.language == "en" else labels).add(value.value.strip())
                if predicate in definition_properties:
                    signature.update(definition_terms(value.value))
            if isinstance(value, NamedNode):
                if predicate in {str(RDF.type), MARDI + "P1460"}:
                    types.add(value.value)
                if predicate in {str(RDFS.subClassOf), str(SKOS.broader)} and value.value.startswith(namespace):
                    parents.add(value.value.removeprefix(namespace))
        role = "untyped"
        if source_id == "mathmoddb":
            roles = {PROFILE_TYPES[t.removeprefix(MARDI)] for t in types if t.removeprefix(MARDI) in PROFILE_TYPES}
            if len(roles) == 1:
                role, = roles
        elif "http://www.w3.org/2002/07/owl#Class" in types:
            role = "class"
        # Field evidence applies only to an actual model or modeling task.
        evidence[local] = {
            "labels": sorted(english or labels),
            "definition_terms": sorted(signature),
            "types": sorted(types),
            "parents": sorted(parents),
            "role": role,
        }
        if role in {"model", "modeling-task"} and local in scope:
            evidence[local]["applied_contexts"] = scope[local]
    return evidence


def digest(record):
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode()).hexdigest()


def evidence_for(source_id, record):
    path = DIRECTORY / f"{source_id}.json"
    if not path.is_file():
        raise ValueError(f"Missing endpoint evidence for {source_id}")
    evidence = read(path)
    if (evidence["sha256"] != record["sha256"]
            or evidence["edges_sha256"] != digest(record["edges"])):
        raise ValueError(f"Endpoint evidence drifted for {source_id}")
    expected = {t for left, _, right in record["edges"] for t in (left, right)}
    if expected != evidence["entities"].keys():
        raise ValueError(f"Incomplete endpoint evidence for {source_id}")
    return evidence["entities"]


def reviewed_projections(source_id, namespace, record, evidence, canonical):
    path = DIRECTORY / f"{source_id}-projections.json"
    if not path.is_file():
        return {}
    document = read(path)
    if document["sha256"] != record["sha256"]:
        raise ValueError(f"Endpoint projections need review for {source_id}")
    rejected = {(row["external"], row["canonical"])
                for row in read(ROOT / "reviews/rejected/mappings.json") if row["source"] == source_id}
    targets = {}
    for local, row in document["projections"].items():
        target = C[row["canonical"]]
        if (local not in evidence or digest(evidence[local]) != row["evidence_sha256"]
                or (namespace + local, str(target)) in rejected
                or (target, RDF.type, SKOS.Concept) not in canonical or not row["rationale"].strip()
                or not row["reference"].startswith(("https://", "http://"))):
            raise ValueError(f"Invalid scoped endpoint projection: {source_id} {local}")
        targets[local] = target, row
    return targets


def canonical_names(graph):
    labels = defaultdict(set)
    for predicate in (SKOS.prefLabel, SKOS.altLabel):
        for subject, label in graph.subject_objects(predicate):
            if (subject, RDF.type, SKOS.Concept) in graph:
                labels[label_key(str(label))].add(subject)
    return labels


def compatibility(source, role, graph, candidate):
    domains = {"mathmoddb": ("mathematics",), "stato": ("statistics",),
               "ontomath-pro": ("mathematics",), "ml-schema": ("computer-science", "statistics")}[source]
    scope = any((candidate, SKOS.inScheme, D[domain]) in graph for domain in domains)
    ancestors = {str(parent).removeprefix(str(C))
                 for parent in graph.transitive_objects(candidate, SKOS.broader)}
    role_hint = bool(ancestors.intersection(ROLE_HEADS[role])) if role in ROLE_HEADS else None
    return scope, role_hint


def triage(source, namespace, record, evidence, target_index, graph, mappings):
    """Rank review suggestions with recorded signals. No score grants resolution."""
    names = canonical_names(graph)
    neighbors = defaultdict(set)
    for left, _, right in record["edges"]:
        neighbors[left].add(right)
        neighbors[right].add(left)
    hints = {
        target: set(graph.objects(target, SKOS.broader)) for target in graph.subjects(RDF.type, SKOS.Concept)
    }
    results = {}
    for local, info in evidence.items():
        external = URIRef(namespace + local)
        resolved = target_index.get(external, set())
        labels = info["labels"]
        direct = set(mappings.subjects(None, external))
        lexical = set().union(*(names[label_key(label)] for label in labels))
        adjacent = set().union(*(target_index.get(URIRef(namespace + key), set())
                                 for key in neighbors[local] | set(info["parents"])))
        suggestions = []
        if len(resolved) != 1 and info["role"] not in NON_TOPICS:
            for target in direct | lexical:
                terms = set().union(*(definition_terms(str(value)) for value in graph.objects(target, SKOS.definition)))
                scope, role_hint = compatibility(source, info["role"], graph, target)
                suggestions.append({
                    "canonical": str(target), "reviewed_reference": target in direct,
                    "label_match": target in lexical, "scope_compatible": scope, "role_compatible": role_hint,
                    "definition_overlap": len(terms.intersection(info["definition_terms"])),
                    "neighbor_support": len(hints[target].intersection(adjacent)),
                })
        if len(resolved) == 1:
            state = "resolved"
        elif len(resolved) > 1:
            state = "ambiguous_identity"
        elif info.get("applied_contexts"):
            state = "outside_reviewed_domain"
        elif info["role"] in NON_TOPICS:
            state = "outside_profile_role"
        elif suggestions:
            state = "review_mapping"
        elif len(labels) != 1 or info["role"] == "untyped":
            state = "need_endpoint_evidence"
        elif source == "mathmoddb":
            state = "review_domain_scope"
        else:
            state = "candidate_missing_subject"
        results[local] = {
            "state": state, "role": info["role"], "applied_contexts": info.get("applied_contexts", []),
            "canonical": sorted(map(str, resolved)),
            "suggestions": sorted(suggestions, key=lambda s: (
                not s["reviewed_reference"], not s["scope_compatible"], s["role_compatible"] is False,
                -s["definition_overlap"], -s["neighbor_support"], s["canonical"],
            )),
        }
    return results


def summary(rows, edges):
    counts = Counter(row["state"] for row in rows.values())
    combinations = Counter(" + ".join(sorted({rows[left]["state"], rows[right]["state"]}))
                           for left, _, right in edges)
    return {"endpoints": len(rows), "by_state": dict(counts), "relation_endpoint_states": dict(combinations)}
