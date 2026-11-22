import sqlite3

import pytest
from rdflib import Dataset, Literal, OWL, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline import consumer
from pipeline.common import BASE, C, D, G, V, checksum, write
from pipeline.contract import ARTIFACTS, CONTRACT, GRAPH_NAMES, metadata
from pipeline.curate import identities
from pipeline.package_check import verify


def fixture_package(directory, successor=False, *, retired=False):
    directory.mkdir()
    data = Dataset()
    graph, prov = data.graph(G.asserted), data.graph(G.provenance)
    for subject, label in [(C.example, "Original"), (C.target, "Target")]:
        graph.add((subject, RDF.type, SKOS.Concept))
        graph.add((subject, SKOS.inScheme, D.mathematics))
        graph.add((subject, SKOS.prefLabel, Literal(label, lang="en")))
    if retired:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(identities, "reviewed_migrations", lambda: [{
                "former": "example", "decision": "replace", "targets": ["target"],
                "rationale": "Isolated test identity", "scientific_reference": "https://example.org/review",
                "review_id": "test-1",
            }])
            identities.apply_migrations(graph, prov)
    elif not successor:
        # The successor removes this old assertion and discloses a scoped revision.
        graph.add((C.example, V.uses, C.target))
    if successor and not retired:
        triple = C.example, V.represents, C.target
        graph.add(triple)
        former, revised = (consumer.statement_for(item) for item in
                           [(C.example, V.uses, C.target), triple])
        prov.add((revised, PROV.wasRevisionOf, former))
        prov.add((revised, DCTERMS.description, Literal("Test revision preserves the old interpretation.")))
        for predicate, obj in zip((RDF.subject, RDF.predicate, RDF.object), (C.example, V.uses, C.target)):
            prov.add((former, predicate, obj))
        for predicate, obj in zip((RDF.subject, RDF.predicate, RDF.object), triple):
            prov.add((revised, predicate, obj))

    for fmt, name in [("nquads", "formal-sciences.nq"), ("trig", "formal-sciences.trig")]:
        data.serialize(destination=directory / name, format=fmt)
    graph.serialize(destination=directory / "formal-sciences.ttl", format="turtle")
    (directory / "source-alignments.trig").write_text(f"<{G.alignments}> {{ }}\n")
    write(directory / "validation-report.json", {"conforms": True, "findings": [], "profile": "test fixture"})
    write(directory / "manifest.json", {
        "version": "1.0.1" if successor else "1.0.0", "contract": CONTRACT, "namespace": BASE,
        "counts": {name: len(data.graph(G[name])) for name in GRAPH_NAMES},
        "artifacts": {name: checksum(directory / name) for name in ARTIFACTS},
        "predicates": len(set(graph.predicates())), "concepts": 2, "conforms": True, "sources": {},
        "release": metadata("candidate", "Foundation"),
        "rights": {"project": {"software": "MIT", "authored_rdf_and_editorial_mappings": "CC-BY-4.0",
                               "credit": "Curricula contributors", "notice": "LICENSE"}, "sources": {}},
    })
    return directory, checksum(directory / "manifest.json")


def query(store, predicate):
    return bool(store.query(f"ASK {{ GRAPH <{G.asserted}> {{ <{C.example}> <{predicate}> <{C.target}> }} }}"))


def test_atomic_activation_replacement_repeat_and_rollback(tmp_path, monkeypatch):
    intake = consumer.Consumer(tmp_path / "db")
    a, h_a = fixture_package(tmp_path / "a")
    b, h_b = fixture_package(tmp_path / "b", successor=True)
    first_id, next_id = "a" * 40, "b" * 40
    first, _ = intake.install(a, first_id, h_a)
    assert intake.install(a, first_id, h_a) == (first, None)
    receipt, old = intake.snapshot()
    assert receipt == first and query(old, V.uses)

    activate = consumer._activate

    def fail_after_pointer_update(db, commit):
        activate(db, commit)
        other_receipt, other_snapshot = intake.snapshot()
        assert other_receipt == first and query(other_snapshot, V.uses)
        raise sqlite3.OperationalError("injected activation failure")

    monkeypatch.setattr(consumer, "_activate", fail_after_pointer_update)
    with pytest.raises(sqlite3.OperationalError, match="activation failure"):
        intake.install(b, next_id, h_b)
    with pytest.raises(ValueError, match="never activated"):
        intake.rollback(next_id)
    assert intake.snapshot()[0] == first

    monkeypatch.setattr(consumer, "_activate", activate)
    second, changes = intake.install(b, next_id, h_b)
    receipt, new = intake.snapshot()
    assert receipt == second and changes["asserted"] == {"added": 1, "removed": 1}
    assert query(old, V.uses) and not query(new, V.uses) and query(new, V.represents)
    with pytest.raises(ValueError, match="explicit rollback"):
        intake.install(a, first_id, h_a)
    with pytest.raises(ValueError, match="already has a different manifest"):
        intake.install(a, next_id, h_a)

    (a / "formal-sciences.nq").write_text("corrupt")
    with pytest.raises(ValueError, match="Artifact checksum mismatch"):
        intake.install(a, "c" * 40, h_a)
    assert intake.snapshot()[0] == second
    assert intake.rollback(first_id) == first
    assert query(intake.snapshot()[1], V.uses)


def test_resolve_deprecation_and_unknown(tmp_path):
    a, digest = fixture_package(tmp_path / "a", successor=True, retired=True)
    intake = consumer.Consumer(tmp_path / "db")
    assert verify(a, digest)
    intake.install(a, "d" * 40, digest)
    _, graphs = intake.snapshot()
    assert consumer.resolve(graphs, str(C.example)) == {"status": "deprecated", "targets": [str(C.target)]}
    assert consumer.resolve(graphs, str(C.target)) == {"status": "active", "targets": []}
    assert consumer.resolve(graphs, str(C.missing)) == {"status": "unknown", "targets": []}


@pytest.mark.parametrize("change,reason", [
    ("delete", "Canonical IRI deleted"), ("reuse", "Canonical scope changed"),
    ("reactivate", "Retired canonical IRI reused"),
])
def test_invalid_successors(tmp_path, change, reason):
    a, _ = fixture_package(tmp_path / "a", successor=True, retired=True)
    baseline = (a / "formal-sciences.nq").read_bytes()
    before, after = consumer.dataset(baseline), consumer.dataset(baseline)
    graph = after.graph(G.asserted)
    if change == "delete":
        graph.remove((C.example, None, None))
    elif change == "reuse":
        graph.set((C.example, SKOS.prefLabel, Literal("Another concept", lang="en")))
    else:
        graph.remove((C.example, OWL.deprecated, None))
        graph.remove((C.example, DCTERMS.isReplacedBy, None))
    with pytest.raises(ValueError, match=reason):
        consumer.successor_changes(before, after)
