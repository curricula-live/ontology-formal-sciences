from rdflib import Graph, Literal, OWL, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, D, V
from pipeline.curate import identities
from pipeline.curate.relations import statement_for
from pipeline.validate import check


def test_reviewed_duplicate_keeps_source_and_has_discoverable_replacement(monkeypatch):
    row, = (item for item in identities.reviewed_migrations() if item["former"] == "opencs-c3339")
    monkeypatch.setattr(identities, "reviewed_migrations", lambda: [row])
    graph = Graph()
    provenance = Graph()
    preferred, former = C[row["preferred"]], C[row["former"]]
    native = next(Graph().parse(data=row["source_evidence"], format="nt").subjects(RDF.type))
    for concept in (former, preferred, C["computer-science"]):
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.inScheme, D["computer-science"]))
        graph.add((concept, SKOS.prefLabel, Literal(str(concept), lang="en")))
        if concept != C["computer-science"]:
            graph.add((concept, SKOS.broader, C["computer-science"]))
    graph.add((D["computer-science"], RDF.type, SKOS.ConceptScheme))
    original = (former, DCTERMS.source, native)
    provenance.add(original)

    assert identities.apply_migrations(graph, provenance)["retired_duplicates"] == 1
    replacement = (former, DCTERMS.isReplacedBy, preferred)
    assert replacement in graph and original in provenance
    assert (former, OWL.deprecated, Literal(True)) in graph
    assert (former, RDF.type, SKOS.Concept) in graph
    evidence = provenance.value(statement_for(replacement), PROV.wasDerivedFrom)
    assert provenance.value(evidence, DCTERMS.references) == native
    assert provenance.value(evidence, DCTERMS.identifier) == Literal(row["snapshot_sha256"])
    assert check(graph)["conforms"]

    graph.add((former, V.uses, preferred))
    assert any("retired duplicate" in issue for issue in check(graph)["findings"])
    graph.remove((former, V.uses, preferred))
    graph.add((preferred, OWL.deprecated, Literal(True)))
    graph.add((preferred, DCTERMS.isReplacedBy, former))
    assert any("Invalid canonical replacement" in issue for issue in check(graph)["findings"])


def test_split_requires_distinct_live_same_scheme_targets(monkeypatch):
    graph, provenance = Graph(), Graph()
    for concept in (C.former, C.a, C.b, C.other):
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.inScheme, D.logic if concept == C.other else D.mathematics))
    row = {"former": "former", "decision": "split", "targets": ["a", "b"],
           "rationale": "Test review", "review_id": "test-split",
           "scientific_reference": "https://example.org/review"}
    monkeypatch.setattr(identities, "reviewed_migrations", lambda: [row])
    identities.apply_migrations(graph, provenance)
    from pipeline.validate import identity_errors

    assert not identity_errors(graph) and not identities.lifecycle_errors(graph, provenance)
    graph.remove((C.former, DCTERMS.isReplacedBy, C.b))
    assert any("cardinality" in x for x in identities.lifecycle_errors(graph, provenance))
    graph.add((C.former, DCTERMS.isReplacedBy, C.other))
    assert any("Invalid canonical replacement" in x for x in identity_errors(graph))
    graph.remove((C.former, DCTERMS.isReplacedBy, C.other))
    graph.add((C.former, DCTERMS.isReplacedBy, C.missing))
    assert any("Invalid canonical replacement" in x for x in identity_errors(graph))
