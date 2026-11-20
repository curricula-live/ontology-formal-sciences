import json
import shutil

import pytest
from rdflib import Graph, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, D, ROOT, V, checksum, read
from pipeline.package_check import verify
from pipeline.quality import comparison, graph_metrics
from pipeline.reason import reason


def test_connectivity_counts_only_asserted_concept_edges():
    graph, prov = Graph(), Graph()
    for term, domain in [(C.graph, "mathematics"), (C.algorithm, "computer-science"), (C.isolate, "mathematics")]:
        graph.add((term, RDF.type, SKOS.Concept))
        graph.add((term, SKOS.inScheme, D[domain]))
        prov.add((term, PROV.wasDerivedFrom, URIRef(BASE + "module/" + domain + "/modules/test.ttl")))
    # Shared scheme membership cannot connect the isolated concept.
    graph.add((C.algorithm, SKOS.related, C.graph))
    result = graph_metrics(graph, prov)
    assert result["connected_components"] == 2
    assert result["isolated_concepts"] == 1
    assert result["largest_component"] == 2
    assert result["cross_domain_relation_counts"] == {str(SKOS.related): 1}
    assert result["concepts_by_scheme"] == {"mathematics": 2, "computer-science": 1}
    assert result["scientific_connectivity"]["participating_concepts"] == 0

    graph.add((C.isolate, V.uses, C.graph))
    statement = URIRef("urn:test:evidenced-edge")
    for predicate, obj in (
        (RDF.subject, C.isolate), (RDF.predicate, V.uses), (RDF.object, C.graph),
        (DCTERMS.source, URIRef("urn:test:reference")),
    ):
        prov.add((statement, predicate, obj))
    result = graph_metrics(graph, prov)
    assert result["connected_components"] == 1
    science = result["scientific_connectivity"]
    assert science["participating_concepts"] == 2
    assert science["concepts_without_specific_relations"] == 1
    assert science["largest_component"] == 2
    assert science["cited_relations"] == 1
    assert science["cross_domain_relations"] == 0
    assert science["evidence_backed"]["component_size_histogram"] == {"2": 1}
    assert result["taxonomic_connectivity"]["component_size_histogram"] == {"1": 3}
    assert science["citation_coverage"] == 1

    graph.add((C.algorithm, V.uses, C.graph))
    result = graph_metrics(graph, prov)
    assert result["scientific_connectivity"]["largest_component"] == 3
    assert result["scientific_connectivity"]["evidence_backed"]["largest_component"] == 2
    assert result["scientific_connectivity"]["citation_coverage"] == 0.5



def test_comparison_excludes_unmeasured_indicators():
    before = {"concepts": 7, "counts": {"asserted": 26}, "sources": {}}
    after = dict(before, concepts=10, quality={"cross_domain_relations": 3})
    assert comparison(before, after) == {"concepts": 3, "asserted": 0, "staged_graphs": 0, "staged_triples": 0}


def test_reasoning_has_no_unjustified_closure():
    graph = Graph()
    graph.add((C.a, SKOS.broader, C.b))
    graph.add((C.b, SKOS.broader, C.c))
    graph.add((C.a, SKOS.related, C.c))
    graph.add((C.a, SKOS.exactMatch, C.c))
    graph.add((C.b, SKOS.narrower, C.a))
    assert set(reason(graph)) == {
        (C.c, SKOS.narrower, C.b),
        (C.c, SKOS.related, C.a),
    }


def test_package_rejects_valid_but_wrong_dataset(tmp_path):
    # A matching new checksum alone cannot establish TriG/N-Quads equivalence.
    path = tmp_path / "package"
    shutil.copytree(ROOT / "dist", path)
    nq = path / "formal-sciences.nq"
    with nq.open("a") as stream:
        stream.write("<urn:unapproved> <urn:predicate> <urn:target> <urn:candidate> .\n")
    manifest = read(path / "manifest.json")
    manifest["artifacts"][nq.name] = checksum(nq)
    (path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="different RDF datasets"):
        verify(path)
