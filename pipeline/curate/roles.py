"""Reviewed role assertions and conservative endpoint checks."""
from collections import Counter, defaultdict
from hashlib import sha256
import json

from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, ROOT, V, checksum, read
from pipeline.curate.relations import statement_for

ROLES = ROOT / "reviews/approved/scientific-roles.json"
POLICY = ROOT / "reviews/quality/predicate-roles.json"


def basis_for(graph, subject, row, provenance):
    if "statement" in row:
        left, predicate, right = row["statement"]
        triple = C[left], V[predicate], C[right]
        if subject not in (triple[0], triple[2]) or triple not in graph:
            raise ValueError(f"Missing reviewed role evidence: {subject}")
        statement = statement_for(triple)
        if not (provenance.value(statement, DCTERMS.source) or
                provenance.value(statement, PROV.wasDerivedFrom)):
            raise ValueError(f"Role statement lacks source provenance: {subject}")
        return [statement]
    definition = graph.value(subject, SKOS.definition)
    if not definition or str(definition) != row.get("definition"):
        raise ValueError(f"Role definition changed or is missing: {subject}")
    return list(provenance.objects(subject, PROV.wasDerivedFrom))


def apply_roles(graph, provenance):
    found = set()
    for row in read(ROLES):
        subject = C[row["subject"]]
        if (subject, RDF.type, SKOS.Concept) not in graph or not row["rationale"].strip():
            raise ValueError(f"Invalid role subject or rationale: {subject}")
        basis = basis_for(graph, subject, row, provenance)
        if not basis:
            raise ValueError(f"Role lacks a stable evidence basis: {subject}")
        row_digest = sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        for name in row["roles"]:
            role = V[name]
            triple = subject, V.hasScientificRole, role
            if triple in found or (role, RDF.type, V.ScientificRole) not in graph:
                raise ValueError(f"Duplicate or undefined reviewed role: {triple}")
            found.add(triple)
            graph.add(triple)
            statement = statement_for(triple)
            for predicate, obj in [
                (RDF.type, RDF.Statement), (RDF.subject, subject), (RDF.predicate, V.hasScientificRole),
                (RDF.object, role), (DCTERMS.description, Literal(row["rationale"], lang="en")),
                (DCTERMS.identifier, Literal(row_digest)),
            ]:
                provenance.add((statement, predicate, obj))
            for source in basis:
                provenance.add((statement, PROV.wasDerivedFrom, source))
    if set(graph.triples((None, V.hasScientificRole, None))) != found:
        raise ValueError("Unreviewed scientific role in the asserted graph")


def role_profile(graph, provenance=None):
    policy = read(POLICY)
    report = defaultdict(Counter)
    roles = defaultdict(set)
    for subject, role in graph.subject_objects(V.hasScientificRole):
        roles[subject].add(role)
        if provenance is not None and not provenance.value(
            statement_for((subject, V.hasScientificRole, role)), PROV.wasDerivedFrom
        ):
            raise ValueError(f"Missing scientific role provenance: {subject}")
    errors = []
    review_queue = []
    exceptions = {}
    for row in policy["exceptions"]:
        s, p, o = row["statement"]
        triple = C[s], V[p], C[o]
        if triple in exceptions or triple not in graph or p not in policy["constraints"] or not row["rationale"].strip():
            raise ValueError(f"Invalid reviewed role exception: {triple}")
        exceptions[triple] = row["rationale"]
    for predicate, rule in policy["constraints"].items():
        for subject, obj in graph.subject_objects(V[predicate]):
            scoped = (subject, V[predicate], obj)
            if scoped in exceptions:
                report[predicate]["reviewed_exception"] += 1
                continue
            states = []
            for endpoint, side in ((subject, "subject"), (obj, "object")):
                expected = {V[name] for name in rule[side].get("expected", [])}
                forbidden = {V[name] for name in rule[side].get("incompatible", [])}
                if roles[endpoint] & forbidden:
                    states.append("incompatible")
                elif expected and not roles[endpoint] & expected:
                    states.append("unresolved")
            state = "incompatible" if "incompatible" in states else "unresolved" if states else "scope_supported"
            report[predicate][state] += 1
            if state != "scope_supported":
                review_queue.append({"subject": str(subject), "predicate": predicate, "object": str(obj), "state": state})
            if state == "incompatible":
                errors.append(f"Reviewed roles contradict {predicate}: {subject} -> {obj}")
    reviewed = {subject for subject, _ in graph.subject_objects(V.hasScientificRole)}
    return {"reviewed_subjects": len(reviewed),
            "unclassified_subjects": sum(s not in reviewed for s in graph.subjects(RDF.type, SKOS.Concept)),
            "role_counts": dict(Counter(str(role).removeprefix(str(V)) for _, role in
                                       graph.subject_objects(V.hasScientificRole))),
            "review_queue": sorted(review_queue, key=lambda row: (row["predicate"], row["subject"], row["object"])),
            "predicate_review": {p: dict(states) for p, states in report.items()},
            "unconstrained_predicates": sorted(str(p).removeprefix(str(V)) for p in set(graph.predicates())
                if str(p).startswith(str(V)) and p != V.hasScientificRole
                and str(p).removeprefix(str(V)) not in policy["constraints"]),
            "ledger_sha256": checksum(ROLES), "policy_sha256": checksum(POLICY)}, errors
