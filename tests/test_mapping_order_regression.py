"""Regression: SKOS closeMatch must not reserve a source identity as exactMatch."""
import json

import pytest
from rdflib import Graph, RDF, SKOS, URIRef

from pipeline.common import C
from pipeline import curate


SOURCE = "https://example.org/native/topic"
EVIDENCE = f"<{SOURCE}> <{RDF.type}> <{SKOS.Concept}> .\n"


def _run_review(tmp_path, monkeypatch, first, second):
    alignments = tmp_path / "domains/_shared/alignments"
    alignments.mkdir(parents=True)
    (alignments / "toy.ttl").write_text(
        f"<{C.a}> <{first}> <{SOURCE}> .\n"
        f"<{C.b}> <{second}> <{SOURCE}> .\n"
    )
    rows = [
        {
            "id": f"toy-{idx}",
            "source": "toy",
            "external": SOURCE,
            "canonical": str(C["a"] if idx == 0 else C["b"]),
            "predicate": str(pred),
            "sha256": "pinned-toy-sha",
            "evidence": EVIDENCE,
            "rationale": "Source identity has been independently reviewed.",
        }
        for idx, pred in enumerate((first, second))
    ]
    path = tmp_path / "reviews/approved/mappings.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(rows))
    other = tmp_path / "reviews/rejected/mappings.json"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("[]")
    graph = Graph()
    for concept in (C.a, C.b):
        graph.add((concept, RDF.type, SKOS.Concept))
    monkeypatch.setattr(curate, "ROOT", tmp_path)
    catalog = {
        "toy": {
            "allow_mapping": True, "license": "CC-BY-4.0",
            "sha256": "pinned-toy-sha", "url": "https://example.org/native.nt"
        }
    }
    return curate.reviewed(catalog, graph, Graph())


@pytest.mark.parametrize("first,second", [
    (SKOS.closeMatch, SKOS.exactMatch),
    (SKOS.exactMatch, SKOS.closeMatch),
])
def test_exact_and_close_match_are_order_independent(tmp_path, monkeypatch, first, second):
    mappings = _run_review(tmp_path, monkeypatch, first, second)
    assert (C.a, first, URIRef(SOURCE)) in mappings
    assert (C.b, second, URIRef(SOURCE)) in mappings
    assert len(mappings) == 2


def test_two_distinct_exact_targets_for_one_source_are_rejected(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="Conflicting identity"):
        _run_review(tmp_path, monkeypatch, SKOS.exactMatch, SKOS.exactMatch)
