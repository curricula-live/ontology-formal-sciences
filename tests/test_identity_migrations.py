from rdflib import Graph, Literal, OWL, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, D, V
from pipeline.curate.identities import apply_migrations, reviewed_migrations
from pipeline.curate.relations import statement_for
from pipeline.validate import check


def test_reviewed_duplicate_keeps_source_and_has_discoverable_replacement():
    row, = reviewed_migrations()
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

    assert apply_migrations(graph, provenance)["retired_duplicates"] == 1
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
