"""Replay a pinned Lean kernel probe over two local theorem fixtures."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from rdflib import Literal, RDF, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read, write
from pipeline.curate.relations import statement_for

FIXTURES = ROOT / "pipeline/lean"
REPORT = ROOT / "reviews/formal-properties/lean-kernel-probe.json"
RELEASE = "https://github.com/leanprover/lean4/releases/download/v4.36.0/lean-4.36.0-linux.tar.zst"
PIN = {
    "version": "4.36.0",
    "commit": "611c117bfaf7b7ae1cfcf246ce6fba31e8f509e9",
    "linux_x86_64_archive_sha256": "2b7ab1ed8b92d2e6abfaf41344823b510064dbc9c0260cac73eb496ab2dea6eb",
    "url": RELEASE,
}
DECLARATIONS = {"FormalSciences.booleanDeMorgan", "FormalSciences.wordAppendAssoc"}


def fixture_digests():
    return {path.name: checksum(path) for path in sorted(FIXTURES.glob("*.lean"))}


def validate_record(record):
    if record["toolchain"] != PIN or record["fixtures"] != fixture_digests():
        raise ValueError("Lean kernel probe report differs from the pinned inputs")
    proofs = record["proofs"]
    if (len(proofs) != len(DECLARATIONS) or {row["declaration"] for row in proofs} != DECLARATIONS
            or any(not row["elaborated_type"] or not row["direct_proof_constants"]
                   or "sorryAx" in row["transitive_axioms"] for row in proofs)):
        raise ValueError("Incomplete kernel-checked Lean fixture evidence")
    return record


def replay(lean, write_evidence=False):
    executable = Path(lean).resolve(strict=True)
    version = subprocess.check_output([executable, "--version"], text=True, timeout=30)
    if f"version {PIN['version']}," not in version or f"commit {PIN['commit']}," not in version:
        raise ValueError("Executable differs from the pinned Lean toolchain")
    with TemporaryDirectory() as destination:
        env = {**os.environ, "LEAN_PATH": destination}
        command = [executable, "-DwarningAsError=true"]
        subprocess.run([*command, "-o", str(Path(destination) / "Inspect.olean"), "Inspect.lean"],
                       cwd=FIXTURES, env=env, check=True, timeout=120)
        output = subprocess.check_output([*command, "Probe.lean"], cwd=FIXTURES, env=env,
                                         text=True, timeout=120)
    record = validate_record({"toolchain": PIN, "fixtures": fixture_digests(),
                              "scope": "locally compiled fixtures importing Lean core",
                              "proofs": [json.loads(line) for line in output.splitlines()]})
    if write_evidence:
        write(REPORT, record)
    elif record != read(REPORT):
        raise ValueError("Kernel probe output differs from the recorded evidence")
    return record


def apply_kernel_probe(graph, provenance):
    record = validate_record(read(REPORT))
    source = URIRef(BASE + "source/lean-kernel-fixture")
    provenance.add((source, RDF.type, PROV.Entity))
    provenance.add((source, DCTERMS.hasVersion, Literal(PIN["version"])))
    provenance.add((source, PROV.hadPrimarySource, URIRef(RELEASE)))
    proof = next(row for row in record["proofs"] if row["declaration"] == "FormalSciences.booleanDeMorgan")
    target = C["logical-negation"], V.hasProperty, C["de-morgan-conjunction-law"]
    if target not in graph:
        raise ValueError("The reviewed Boolean property is absent")
    statement = statement_for(target)
    witness = URIRef(BASE + "relation-evidence/lean-kernel-fixture/" + proof["declaration"])
    document = URIRef("https://github.com/curricula-live/ontology-formal-sciences/blob/feat/formal-sciences/pipeline/lean/Probe.lean")
    for predicate, obj in (
        (RDF.type, PROV.Entity), (DCTERMS.isPartOf, source),
        (DCTERMS.type, Literal("kernel-checked Lean fixture")),
        (DCTERMS.title, Literal(proof["declaration"])), (PROV.hadPrimarySource, document),
        (V.evidenceContentDigest, Literal(record["fixtures"]["Probe.lean"])),
        (V.evidenceExtraction, Literal("elaborated Lean type and checked proof term")),
    ):
        provenance.add((witness, predicate, obj))
    for name in proof["direct_type_constants"]:
        provenance.add((witness, V.sourceElaboratedTypeConstant, Literal(name)))
    for name in proof["direct_proof_constants"]:
        provenance.add((witness, V.sourceDirectProofConstant, Literal(name)))
    provenance.add((statement, PROV.wasDerivedFrom, witness))
    provenance.add((statement, DCTERMS.source, document))
    return {"toolchain": PIN, "checked_fixture_theorems": len(record["proofs"]),
            "mathlib_checked_declarations": 0, "report_sha256": checksum(REPORT)}
