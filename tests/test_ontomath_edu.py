"""Test the supported Manchester extension offline, and with the pinned OWLAPI tooling if available."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from pyoxigraph import NamedNode, RdfFormat, Store
import pytest
from rdflib import Graph, Namespace, OWL, RDF

from pipeline.common import ROOT, checksum, registry
from pipeline.fetch import fetch
from pipeline.parse import load_graph
from pipeline.parse.adapters import edu_frames

PART = Namespace("https://example.org/partition#")
HEADER = f"""Prefix: : <{PART}>
Ontology: <https://example.org/partition>
Class: :Left
Class: :Right
Class: :Whole
"""


def test_partition_list_and_unchanged_frames(tmp_path):
    path = tmp_path / "source.omn"
    other_frame = "    SubClassOf: :Whole\n"
    path.write_text(HEADER + "    DisjointUnionOf:\n        :Left,\n        :Right\n" + other_frame)
    normalized, graph = edu_frames(path, tmp_path)
    assert normalized.read_text() == HEADER + other_frame
    head = graph.value(PART.Whole, OWL.disjointUnionOf, any=False)
    assert list(graph.items(head)) == [PART.Left, PART.Right]
    assert graph.value(graph.value(head, RDF.rest), RDF.rest, any=False) == RDF.nil
    assert len(graph) == 5


@pytest.mark.parametrize("frame, error", [
    ("DisjointUnionOf: :Left, :Right", "outside a named class"),
    ("    DisjointUnionOf: :Left, :Missing", "locally declared"),
    ("    DisjointUnionOf: :Left, missing:Right", "Unknown OntoMathEdu prefix"),
    ("    DisjointUnionOf: :Left, :Left", "Repeated"),
    ("    DisjointUnionOf: :Left", "Unsupported"),
    ("    DisjointUnionOf: :Left, (:Right or :Whole)", "Unsupported"),
    ("    DisjointUnionOf: :Left,", "Incomplete"),
    ("    DisjointUnionOf:", "Incomplete"),
])
def test_partition_rejects_unsupported_frames(tmp_path, frame, error):
    path = tmp_path / "source.omn"
    path.write_text(HEADER + frame + "\n")
    with pytest.raises(ValueError, match=error):
        edu_frames(path, tmp_path)


@pytest.fixture
def robot():
    jar = Path(os.environ.get("ROBOT_JAR", ROOT / "tools/robot.jar"))
    if not jar.is_file():
        pytest.skip("Set ROBOT_JAR to run OWLAPI integration checks")
    assert checksum(jar) == (ROOT / "pipeline/parse/robot.sha256").read_text().strip()
    return ["java", "-jar", str(jar.resolve())]


def test_reasoner_confirms_partition_semantics(tmp_path, robot):
    """Coverage and pairwise disjointness each exclude a different witness class."""
    source = tmp_path / "source.omn"
    probes = """Class: :Overlap
    EquivalentTo: :Left and :Right
Class: :Uncovered
    EquivalentTo: :Whole and (not :Left) and (not :Right)
"""
    clean = tmp_path / "control.omn"
    clean.write_text(HEADER + probes)
    source.write_text(HEADER + "    DisjointUnionOf: :Left, :Right\n" + probes)
    args = [*robot, "reason", "--reasoner", "HermiT", "--input"]
    subprocess.run([*args, str(clean), "--output", str(tmp_path / "control.owl")], check=True, timeout=120)

    store, name = Store(), NamedNode("urn:partition-probe")
    load_graph(store, source, {"format": "manchester", "id": "ontomath-edu"}, name)
    ttl = tmp_path / "partition.ttl"
    store.dump(output=ttl, format=RdfFormat.TURTLE, from_graph=name)
    reasoned = subprocess.run([*args, str(ttl)], capture_output=True, text=True, timeout=120)
    diagnostic = reasoned.stdout + reasoned.stderr
    assert reasoned.returncode != 0
    assert str(PART.Overlap) in diagnostic and str(PART.Uncovered) in diagnostic
    assert "unsatisfiable" in diagnostic.lower()


def test_pinned_partition_axioms_against_owlapi(tmp_path, robot):
    source = registry()["ontomath-edu"]
    try:
        path = fetch(source, offline=True)
    except ValueError as exc:
        if "Missing or corrupt cache" in str(exc):
            pytest.skip("Fetch the OntoMathEdu snapshot for the full-source fidelity check")
        raise
    # Independent reference for this revision. Remove only the 16 specific two-line sections
    # from the original text. ROBOT directly parses all other axioms in that Manchester input.
    original = path.read_text()
    base, removed = re.subn(r"(?m)^    DisjointUnionOf:[ \t]*\n        [^\n]+\n", "", original)
    assert removed == 16
    baseline = tmp_path / "baseline.omn"
    baseline.write_text(base)
    name, store = NamedNode("urn:edu-snapshot"), Store()
    load_graph(store, path, source, name)
    assert len(store) == 7867
    result = tmp_path / "converted.nt"
    store.dump(output=result, format=RdfFormat.N_TRIPLES, from_graph=name)
    report = tmp_path / "owlapi.diff"
    subprocess.run([*robot, "diff", "--left", str(baseline), "--right", str(result),
                    "--output", str(report)], check=True, timeout=120)
    diff = report.read_text()
    assert "0 axioms in left ontology but not in right ontology:" in diff
    assert "16 axioms in right ontology but not in left ontology:" in diff

    axioms = []
    for line in diff.splitlines():
        if line.startswith("+ "):
            match = re.fullmatch(r"\+ DisjointUnion\((<[^>]+>(?: <[^>]+>)+)\)", line)
            assert match, line
            owner, *operands = re.findall(r"<([^>]+)>", match[1])
            axioms.append((owner, sorted(operands)))
    assert len(axioms) == 16 and sum(len(members) for _, members in axioms) == 40
    # Digest of the original named owners and operands after expanding the Manchester prefixes,
    # sorting operands within each frame, sorting frames, and using compact UTF-8 JSON.
    signature = json.dumps(sorted(axioms), separators=(",", ":")).encode()
    assert hashlib.sha256(signature).hexdigest() == "551980bbb5af7cc94ffce0096d0c3640f944bd82c89c44ea23ea9f8a1ddab95a"
    graph = Graph().parse(result, format="nt")
    classes = set(map(str, graph.subjects(RDF.type, OWL.Class)))
    assert all({owner, *operands} <= classes for owner, operands in axioms)
