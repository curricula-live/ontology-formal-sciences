"""Replay explicitly reviewed Lean declarations without inferring claims from imports."""
from collections import Counter
from hashlib import sha256
from pathlib import PurePosixPath
import re
from tarfile import open as open_archive

from rdflib import DCTERMS, Literal, RDF, URIRef
from rdflib.namespace import PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read, registry
from pipeline.curate.relations import statement_for
from pipeline.fetch import fetch

SOURCE = "mathlib4"
LEDGER = ROOT / "reviews/formal-properties/mathlib4-declarations.json"
GITHUB = "https://github.com/leanprover-community/mathlib4"


def reviewed_declarations(source):
    ledger = read(LEDGER)
    if source["license"] != "Apache-2.0" or ledger["sha256"] != source["sha256"]:
        raise ValueError("Mathlib declaration evidence uses a different snapshot or license")
    rows = ledger["declarations"]
    identities = set()
    for row in rows:
        path = PurePosixPath(row["module"])
        if not path.parts or path.parts[0] != "Mathlib" or path.suffix != ".lean" or ".." in path.parts:
            raise ValueError(f"Invalid Mathlib module: {path}")
        if row["name"] in identities or not re.fullmatch(r"[\w.]+", row["name"]):
            raise ValueError(f"Invalid or duplicate declaration identity: {row['name']}")
        identities.add(row["name"])
        if row["first_line"] < 1 or row["last_line"] < row["first_line"]:
            raise ValueError(f"Invalid Mathlib source range: {row['name']}")
        if not re.fullmatch(r"[0-9a-f]{64}", row["witness_sha256"]):
            raise ValueError(f"Invalid Mathlib witness checksum: {row['name']}")
        if not row["rationale"].strip() or not row["claims"]:
            raise ValueError(f"Empty Mathlib declaration review: {row['name']}")
        for claim in row["claims"]:
            if claim["state"] not in {"approved", "rejected"} or not claim["rationale"].strip():
                raise ValueError(f"Invalid Mathlib claim decision: {row['name']}")
    return rows


def replay(offline=False):
    """Match line-ranged declarations and proofs to the reviewed excerpts in the original archive."""
    source = registry()[SOURCE]
    rows = reviewed_declarations(source)
    modules = {}
    with open_archive(fetch(source, offline)) as archive:
        for row in sorted(rows, key=lambda item: item["module"]):
            module = row["module"]
            if module not in modules:
                member = f"mathlib4-{source['revision']}/{module}"
                with archive.extractfile(member) as stream:
                    modules[module] = stream.read().decode("utf-8").splitlines()
            lines = modules[module][row["first_line"] - 1:row["last_line"]]
            if (not lines or len(lines) != row["last_line"] - row["first_line"] + 1 or
                    sha256("\n".join(lines).encode()).hexdigest() != row["witness_sha256"] or
                    not lines[0].startswith(("theorem " + row["token"] + " ", "def " + row["token"] + " "))):
                raise ValueError(f"Mathlib declaration or proof excerpt changed: {row['name']}")
    return {"source": SOURCE, "verified_declarations": len(rows), "modules": len(modules)}


def apply_declarations(source, graph, provenance):
    """Attach source evidence to independently reviewed and authored canonical assertions."""
    rows = reviewed_declarations(source)
    source_entity = URIRef(BASE + "source/mathlib4")
    provenance.add((source_entity, RDF.type, PROV.Entity))
    provenance.add((source_entity, DCTERMS.rights, URIRef("https://www.apache.org/licenses/LICENSE-2.0")))
    provenance.add((source_entity, DCTERMS.description, Literal(source["attribution"])))
    contributions, decisions = set(), Counter()
    for row in rows:
        name = row["name"]
        anchor = (f"{GITHUB}/blob/{source['revision']}/{row['module']}"
                  f"#L{row['first_line']}-L{row['last_line']}")
        declaration = URIRef(anchor)
        evidence = URIRef(BASE + "relation-evidence/mathlib4/" + name)
        for pred, obj in (
            (RDF.type, PROV.Entity), (DCTERMS.isPartOf, source_entity),
            (DCTERMS.identifier, Literal(source["sha256"])),
            (DCTERMS.type, Literal("Lean declaration")),
            (DCTERMS.title, Literal(name)), (PROV.hadPrimarySource, declaration),
            (DCTERMS.references, declaration),
            (V.evidenceContentDigest, Literal(row["witness_sha256"])),
            (DCTERMS.description, Literal(row["rationale"], lang="en")),
        ):
            provenance.add((evidence, pred, obj))
        for claim in row["claims"]:
            decisions[claim["state"]] += 1
            s, p, o = claim["triple"]
            triple = C[s], V[p], C[o]
            if claim["state"] == "rejected":
                if triple in graph:
                    raise ValueError(f"Rejected Mathlib assertion is present: {triple}")
                continue
            if triple not in graph:
                raise ValueError(f"Approved Mathlib assertion is missing: {triple}")
            statement = statement_for(triple)
            provenance.add((statement, DCTERMS.source, declaration))
            provenance.add((statement, PROV.wasDerivedFrom, evidence))
            provenance.add((statement, DCTERMS.description, Literal(claim["rationale"], lang="en")))
            contributions.add(triple)
    return {"reviewed_declarations": len(rows), "decisions": dict(decisions),
            "projected_relations": len(contributions), "review_sha256": checksum(LEDGER)}
