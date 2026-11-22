"""Independent, fixture-based attack tests for the published RDF package.

Unlike build-based tests, these use a tiny synthetic release and intentionally
re-sign mutated files to verify semantic equivalence, not only file digests.
"""
import json

import pytest
from rdflib import Dataset, Graph, Literal, RDF, SKOS, URIRef
from rdflib.namespace import PROV

from pipeline.common import BASE, C, G, checksum
from pipeline.package_check import verify


def _sign(directory, *, counts, concepts=2, conforms=True, findings=None):
    (directory / "validation-report.json").write_text(json.dumps({
        "conforms": conforms, "findings": [] if findings is None else findings
    }))
    artifacts = {
        name: checksum(directory / name)
        for name in (
            "formal-sciences.ttl",
            "formal-sciences.trig",
            "formal-sciences.nq",
            "source-alignments.trig",
            "validation-report.json",
        )
    }
    (directory / "manifest.json").write_text(json.dumps({
        "contract": "curricula.rdf-release/v1",
        "namespace": BASE,
        "version": "0.0.0-test",
        "concepts": concepts,
        "conforms": conforms,
        "counts": counts,
        "artifacts": artifacts,
    }, sort_keys=True))


@pytest.fixture
def mini_release(tmp_path):
    parts = {name: Graph() for name in ("asserted", "inferred", "alignments", "provenance")}
    for node, label in ((C["x"], "X"), (C["y"], "Y")):
        parts["asserted"].add((node, RDF.type, SKOS.Concept))
        parts["asserted"].add((node, SKOS.prefLabel, Literal(label, lang="en")))
    parts["asserted"].add((C["x"], SKOS.broader, C["y"]))
    parts["inferred"].add((C["y"], SKOS.narrower, C["x"]))
    parts["alignments"].add((C["x"], SKOS.closeMatch, URIRef("https://example.org/topic-x")))
    parts["provenance"].add((URIRef(BASE + "review/test"), RDF.type, PROV.Entity))
    _write_parts(tmp_path, parts)
    return tmp_path


def _write_parts(directory, parts):
    dataset = Dataset()
    for role, graph in parts.items():
        for s, p, o in graph:
            dataset.add((s, p, o, G[role]))
    (directory / "formal-sciences.ttl").write_text(parts["asserted"].serialize(format="turtle"))
    (directory / "formal-sciences.trig").write_text(dataset.serialize(format="trig"))
    (directory / "formal-sciences.nq").write_text(dataset.serialize(format="nquads"))
    alignments = Dataset()
    for s, p, o in parts["alignments"]:
        alignments.add((s, p, o, G.alignments))
    (directory / "source-alignments.trig").write_text(alignments.serialize(format="trig"))
    _sign(directory, counts={role: len(part) for role, part in parts.items()})


def test_minimal_release_is_valid(mini_release):
    assert verify(mini_release) == {
        "asserted": 5, "alignments": 1, "inferred": 1, "provenance": 1,
    }


def test_checksum_detects_an_unreviewed_byte_change(mini_release):
    with (mini_release / "formal-sciences.ttl").open("a") as handle:
        handle.write("\n# altered\n")
    with pytest.raises(ValueError, match="checksum"):
        verify(mini_release)


def test_rehashed_divergent_trig_is_rejected(mini_release):
    path = mini_release / "formal-sciences.trig"
    path.write_text(path.read_text().replace("https://example.org/topic-x", "https://example.org/topic-y"))
    manifest = json.loads((mini_release / "manifest.json").read_text())
    manifest["artifacts"][path.name] = checksum(path)
    (mini_release / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="different RDF datasets"):
        verify(mini_release)


def test_rehashed_standalone_alignment_mismatch_is_rejected(mini_release):
    path = mini_release / "source-alignments.trig"
    path.write_text(path.read_text().replace("https://example.org/topic-x", "https://example.org/topic-y"))
    manifest = json.loads((mini_release / "manifest.json").read_text())
    manifest["artifacts"][path.name] = checksum(path)
    (mini_release / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="different RDF datasets|Standalone graph"):
        verify(mini_release)


def test_rehashed_wrong_counts_are_rejected(mini_release):
    manifest = json.loads((mini_release / "manifest.json").read_text())
    manifest["counts"]["asserted"] += 1
    (mini_release / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="graph counts"):
        verify(mini_release)


def test_rehashed_false_validation_is_rejected(mini_release):
    manifest = json.loads((mini_release / "manifest.json").read_text())
    _sign(mini_release, counts=manifest["counts"], conforms=False)
    with pytest.raises(ValueError, match="validation failed"):
        verify(mini_release)


def test_extra_artifact_is_rejected(mini_release):
    (mini_release / "unapproved.txt").write_text("not part of the contract")
    with pytest.raises(ValueError, match="inventory"):
        verify(mini_release)


def test_rehashed_unrecognized_graph_is_rejected(mini_release):
    dataset = Dataset()
    dataset.parse(mini_release / "formal-sciences.nq", format="nquads")
    dataset.add((C["x"], RDF.type, SKOS.Concept, URIRef("urn:unexpected:graph")))
    for fmt, name in (("nquads", "formal-sciences.nq"), ("trig", "formal-sciences.trig")):
        (mini_release / name).write_text(dataset.serialize(format=fmt))
    manifest = json.loads((mini_release / "manifest.json").read_text())
    _sign(mini_release, counts=manifest["counts"])
    with pytest.raises(ValueError, match="Unexpected named graphs"):
        verify(mini_release)
