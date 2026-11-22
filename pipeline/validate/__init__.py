from collections import deque

from rdflib import Graph, OWL, RDF, SKOS, RDFS, URIRef, Literal
from rdflib.namespace import DCTERMS
from pyshacl import validate
from pipeline.common import ROOT, C, V
from pipeline.normalize import label_key

RELATIONS = {
    SKOS.broader, SKOS.related, V.uses, V.solves, V.represents, V.hasProperty, V.proves,
    V.containsSymbol, V.invokesAlgorithm, V.requiresPremise, V.analyzes, V.supportsOperation, V.hasInputStructure,
    V.requiresAssumption, V.recognizesExactly, V.computes, V.guarantees,
    V.hasDiscretization, V.hasWeakFormulation, V.hasApproximation, V.hasModelingAssumption,
    V.appliesToModel, V.usesReferenceDistribution, V.estimates, V.hasFormulationComponent,
    V.isSolutionOf, V.producesEstimate,
    V.implementsAlgorithm, V.hasEvaluationComponent, V.reportsEvaluationMeasure,
    V.executesImplementation, V.documentsEvaluationOutput,
}


def hierarchy_cycle_issue(graph):
    """Reject directed cycles in the editorial SKOS broader hierarchy.

    SKOS itself does not impose general acyclicity. This is an explicit
    constraint of Curricula's canonical navigation hierarchy; source-native
    SKOS graphs are not subject to this additional editorial rule.
    """
    links = {}
    indegree = {}
    for child, parent in graph.subject_objects(SKOS.broader):
        links.setdefault(child, set()).add(parent)
        indegree.setdefault(child, 0)
        indegree[parent] = indegree.get(parent, 0) + 1
    queue = deque(node for node, degree in indegree.items() if degree == 0)
    removed = 0
    while queue:
        child = queue.popleft()
        removed += 1
        for parent in links.get(child, ()):
            indegree[parent] -= 1
            if indegree[parent] == 0:
                queue.append(parent)
    if removed == len(indegree):
        return None
    remaining = sorted(str(node) for node, degree in indegree.items() if degree > 0)
    return (f"Canonical SKOS broader hierarchy cycle detected "
            f"({len(remaining)} affected nodes; examples: {remaining[:3]})")


def identity_errors(graph):
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    retired = set(graph.subjects(OWL.deprecated, Literal(True)))
    errors = []
    for concept in retired:
        replacements = set(graph.objects(concept, DCTERMS.isReplacedBy))
        if concept not in concepts or any(
            target not in concepts or target in retired
            or graph.value(target, SKOS.inScheme) != graph.value(concept, SKOS.inScheme)
            for target in replacements
        ):
            errors.append(f"Invalid canonical replacement: {concept}")
    for s, o in graph.subject_objects(DCTERMS.isReplacedBy):
        if s not in retired:
            errors.append(f"Replacement requires a deprecated subject: {s}")
    for s, o in graph.subject_objects(OWL.deprecated):
        if s not in concepts or o != Literal(True):
            errors.append(f"Invalid canonical deprecation marker: {s} {o}")
    for s, p, o in graph:
        if p in RELATIONS - {SKOS.broader, SKOS.related} and (s in retired or o in retired):
            errors.append(f"Scientific assertion uses a retired duplicate or other retired subject: {s} {p} {o}")
    return errors


def check(graph, provenance=None):
    shapes = Graph()
    for path in (ROOT / "domains/_shared/shapes").glob("*.ttl"):
        shapes.parse(path)
    conforms, _, message = validate(graph, shacl_graph=shapes, inference="none")
    errors = identity_errors(graph)
    if cycle_issue := hierarchy_cycle_issue(graph):
        errors.append(cycle_issue)
    if provenance is not None:
        from pipeline.curate.identities import lifecycle_errors

        errors.extend(lifecycle_errors(graph, provenance))
    if not conforms:
        errors.append(message)
    concepts = set(graph.subjects(RDF.type,SKOS.Concept))
    administrative = {OWL.deprecated, DCTERMS.isReplacedBy}
    labels = {}
    for c in concepts:
        if not str(c).startswith(str(C)):
            errors.append(f"Foreign canonical identifier: {c}")
        for label in graph.objects(c,SKOS.prefLabel):
            key = (label_key(str(label)),label.language,graph.value(c,SKOS.inScheme))
            if key in labels and labels[key] != c:
                errors.append(f"Ambiguous preferred label in scheme: {label}")
            labels[key] = c
    for s,p,o in graph:
        if p in RELATIONS and (s not in concepts or o not in concepts or s == o):
            errors.append(f"Invalid relation endpoints: {s} {p} {o}")
        if p not in RELATIONS | administrative | {V.hasScientificRole,RDF.type,SKOS.prefLabel,SKOS.altLabel,SKOS.definition,SKOS.inScheme,RDFS.label,RDFS.domain,RDFS.range,RDFS.comment}:
            errors.append(f"Predicate outside asserted profile: {p}")
    return {"conforms":not errors,"findings":sorted(errors),"profile":"SHACL and closed-world editorial constraints"}
