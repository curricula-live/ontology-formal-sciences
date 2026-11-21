from hashlib import sha256

import pytest
from rdflib import RDF
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, V, write
from pipeline.curate import authored, cs_evidence
from pipeline.curate.relations import statement_for


def test_reviewed_claim_separates_algorithm_and_executable():
    graph, prov = authored()
    report = cs_evidence.apply_reviewed_claims(graph, prov)
    claim = C["princeton-dijkstra-implementation"], V.implementsAlgorithm, C["dijkstra-s-algorithm"]
    statement = statement_for(claim)
    assert claim in graph
    assert (C["postgres-hash-index"], V.supportsOperation, C["database-range-lookup"]) not in graph
    evidence, = prov.objects(statement, PROV.wasDerivedFrom)
    assert prov.value(evidence, RDF.type) == PROV.Entity
    assert str(prov.value(evidence, DCTERMS.type)) == "reviewed primary-source passage"
    assert report["decisions"]["rejected"] > 0


def test_replay_checks_passage_bytes_and_line_range(monkeypatch, tmp_path):
    files = {"Notes.md": b"first\nchecked line\nlast\n", "LICENSE": b"Example license"}
    corpus = {
        "repository": "example/source", "revision": "1" * 40, "rights": "scope",
        "attribution": "source authors", "license_path": "LICENSE",
        "files": {name: sha256(data).hexdigest() for name, data in files.items()},
    }
    corpora, decisions, cache = tmp_path / "corpora.json", tmp_path / "decisions.json", tmp_path / "cache"
    monkeypatch.setattr(cs_evidence, "CORPORA", corpora)
    monkeypatch.setattr(cs_evidence, "DECISIONS", decisions)
    monkeypatch.setattr(cs_evidence, "CACHE", cache)
    write(corpora, {"source": corpus})
    for name, digest in corpus["files"].items():
        folder = cache / digest[:2]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / digest).write_bytes(files[name])
    row = {
        "corpus": "source", "path": "Notes.md", "first": 2, "last": 2,
        "sha256": sha256(b"checked line").hexdigest(),
        "judgments": [{"state": "approved", "triple": ["a", "solves", "b"], "scope": "checked scope"}],
    }
    write(decisions, [row])
    assert cs_evidence.replay(offline=True)["reviewed_passages"] == 1
    row["last"] = 3
    write(decisions, [row])
    with pytest.raises(ValueError, match="Reviewed passage differs"):
        cs_evidence.replay(offline=True)
