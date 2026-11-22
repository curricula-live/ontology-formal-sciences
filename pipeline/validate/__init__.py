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


def check(graph):
    shapes = Graph()
    for path in (ROOT / "domains/_shared/shapes").glob("*.ttl"):
        shapes.parse(path)
    conforms, _, message = validate(graph, shacl_graph=shapes, inference="none")
    errors = [] if conforms else [message]
    concepts = set(graph.subjects(RDF.type,SKOS.Concept))
    retired = set(graph.subjects(OWL.deprecated, Literal(True)))
    administrative = {OWL.deprecated, DCTERMS.isReplacedBy}
    for concept in retired:
        replacements = set(graph.objects(concept, DCTERMS.isReplacedBy))
        if (concept not in concepts or len(replacements) != 1
                or any(target not in concepts or target in retired
                       or graph.value(target, SKOS.inScheme) != graph.value(concept, SKOS.inScheme)
                       for target in replacements)):
            errors.append(f"Invalid canonical replacement: {concept}")
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
        if p == DCTERMS.isReplacedBy and s not in retired:
            errors.append(f"Replacement requires a deprecated subject: {s}")
        if p == OWL.deprecated and (s not in concepts or o != Literal(True)):
            errors.append(f"Invalid canonical deprecation marker: {s} {o}")
        if p in RELATIONS - {SKOS.broader, SKOS.related} and (s in retired or o in retired):
            errors.append(f"Scientific assertion uses a retired duplicate: {s} {p} {o}")
        if p not in RELATIONS | administrative | {RDF.type,SKOS.prefLabel,SKOS.altLabel,SKOS.definition,SKOS.inScheme,RDFS.label,RDFS.domain,RDFS.range,RDFS.comment}:
            errors.append(f"Predicate outside asserted profile: {p}")
    return {"conforms":not errors,"findings":sorted(errors),"profile":"SHACL and closed-world editorial constraints"}
