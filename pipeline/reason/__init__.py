from rdflib import Graph, SKOS


def reason(graph):
    inferred = Graph()
    for subject, parent in graph.subject_objects(SKOS.broader):
        if (parent, SKOS.narrower, subject) not in graph:
            inferred.add((parent, SKOS.narrower, subject))
    for subject, target in graph.subject_objects(SKOS.related):
        if (target,SKOS.related,subject) not in graph:
            inferred.add((target,SKOS.related,subject))
    return inferred
