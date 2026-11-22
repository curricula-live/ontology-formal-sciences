"""Independently check the byte and RDF content of a standalone v1 release."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from pyoxigraph import BlankNode, DefaultGraph, NamedNode, RdfFormat, parse
from rdflib import Dataset, Graph, RDF, RDFS, SKOS
from rdflib.namespace import XSD

from pipeline.common import C, G, checksum
from pipeline.contract import ARTIFACTS, GRAPH_NAMES, read_json, validate_manifest


def records(path, fmt, bit, name=None):
    for quad in parse(path=path, format=fmt):
        graph = quad.graph_name
        if fmt == RdfFormat.TURTLE:
            graph = NamedNode(str(G.asserted))
        if isinstance(graph, (DefaultGraph, BlankNode)) or isinstance(quad.subject, BlankNode) or isinstance(quad.object, BlankNode):
            raise ValueError("Release profile requires named graphs and named resources")
        if name is not None and graph.value != str(G[name]):
            raise ValueError(f"Unexpected graph in {path.name}")
        yield graph.value, str(quad.subject), str(quad.predicate), str(quad.object), bit


def rdflib_records(path, fmt):
    if fmt == "turtle":
        graph = Graph().parse(path, format=fmt)
        rows = ((s, p, o, G.asserted) for s, p, o in graph)
    else:
        dataset = Dataset()
        dataset.parse(path, format=fmt)
        rows = dataset.quads()
    for s, p, o, graph in rows:
        # Both plain RDF 1.1 strings and explicit xsd:string have the same datatype.
        value = o.n3()
        if getattr(o, "datatype", None) == XSD.string:
            value = value.removesuffix("^^" + XSD.string.n3())
        yield str(graph), s.n3(), p.n3(), value


def verify(directory, expected_digest=None):
    directory = Path(directory)
    files = list(directory.iterdir())
    if {p.name for p in files} != ARTIFACTS | {"manifest.json"} or any(
        not p.is_file() or p.is_symlink() for p in files
    ):
        raise ValueError("Unexpected v1 artifact inventory")
    if expected_digest is not None and checksum(directory / "manifest.json") != expected_digest:
        raise ValueError("Pinned manifest checksum mismatch")
    manifest = validate_manifest(read_json(directory / "manifest.json"))
    for artifact, digest in manifest["artifacts"].items():
        if checksum(directory / artifact) != digest:
            raise ValueError(f"Artifact checksum mismatch: {artifact}")
    report = read_json(directory / "validation-report.json")
    if (not isinstance(report, dict) or report.get("conforms") is not True or report.get("findings") != []
            or not isinstance(report.get("profile"), str) or not report["profile"].strip()):
        raise ValueError("Release validation failed")

    # A temporary SQLite database bounds the comparison's working memory. Each bit records
    # set membership in an artifact. Repeated statements and serialization order are immaterial.
    with closing(sqlite3.connect("")) as db:
        db.execute("""CREATE TABLE quads (
            g TEXT, s TEXT, p TEXT, o TEXT, files INTEGER, PRIMARY KEY(g,s,p,o)
        ) WITHOUT ROWID""")
        for filename, fmt, bit, name in [
            ("formal-sciences.trig", RdfFormat.TRIG, 1, None),
            ("formal-sciences.nq", RdfFormat.N_QUADS, 2, None),
            ("formal-sciences.ttl", RdfFormat.TURTLE, 4, "asserted"),
            ("source-alignments.trig", RdfFormat.TRIG, 4, "alignments"),
        ]:
            db.executemany("""INSERT INTO quads VALUES(?,?,?,?,?) ON CONFLICT(g,s,p,o)
                              DO UPDATE SET files = files | excluded.files""",
                           records(directory / filename, fmt, bit, name))
        if db.execute("SELECT 1 FROM quads WHERE files & 3 != 3 LIMIT 1").fetchone():
            raise ValueError("Release serializations describe different RDF datasets")
        if db.execute("SELECT 1 FROM quads WHERE g IN (?,?) AND files != 7 LIMIT 1",
                      (str(G.asserted), str(G.alignments))).fetchone():
            raise ValueError("Standalone graph artifact differs from released dataset")
        counts_by_iri = dict(db.execute("SELECT g, COUNT(*) FROM quads GROUP BY g"))
        counts = {name: counts_by_iri.pop(str(G[name]), 0) for name in GRAPH_NAMES}
        if counts_by_iri or counts != manifest["counts"]:
            raise ValueError("Unexpected named graphs or graph counts")
        if db.execute("""SELECT 1 FROM quads a JOIN quads b USING(s,p,o)
                         WHERE a.g=? AND b.g=? LIMIT 1""", (str(G.asserted), str(G.inferred))).fetchone():
            raise ValueError("Inferred graph contains an asserted triple")
        concepts, = db.execute("SELECT COUNT(*) FROM quads WHERE g=? AND p=? AND o=?",
                               (str(G.asserted), RDF.type.n3(), SKOS.Concept.n3())).fetchone()
        predicates, = db.execute("SELECT COUNT(DISTINCT p) FROM quads WHERE g=?",
                                 (str(G.asserted),)).fetchone()
        if (concepts, predicates) != (manifest["concepts"], manifest["predicates"]):
            raise ValueError("Manifest concept or predicate count differs from RDF")

        # Independently parse each file, then compare exact RDF term membership.
        for filename, fmt, name in [
            ("formal-sciences.trig", "trig", None),
            ("formal-sciences.nq", "nquads", None),
            ("formal-sciences.ttl", "turtle", "asserted"),
            ("source-alignments.trig", "trig", "alignments"),
        ]:
            rows = set(rdflib_records(directory / filename, fmt))
            expected = set(db.execute(
                "SELECT g,s,p,o FROM quads" + (" WHERE g=?" if name else ""),
                (str(G[name]),) if name else (),
            ))
            if rows != expected:
                raise ValueError(f"RDF parser disagreement in {filename}")

        canonical = {row[0] for row in db.execute(
            "SELECT s FROM quads WHERE g=? AND p=? AND o=?",
            (str(G.asserted), RDF.type.n3(), SKOS.Concept.n3()),
        )}
        mapping_predicates = {p.n3() for p in (SKOS.exactMatch, SKOS.closeMatch, RDFS.seeAlso)}
        for predicate in mapping_predicates:
            if db.execute("SELECT 1 FROM quads WHERE g=? AND p=? LIMIT 1",
                          (str(G.asserted), predicate)).fetchone():
                raise ValueError("Source mapping appears in the asserted graph")
        if db.execute("SELECT 1 FROM quads WHERE g=? AND p=? AND o=? LIMIT 1",
                      (str(G.provenance), RDF.type.n3(), SKOS.Concept.n3())).fetchone():
            raise ValueError("Canonical concept declaration appears in the provenance graph")
        for s, p, o in db.execute("SELECT s,p,o FROM quads WHERE g=?", (str(G.alignments),)):
            if s not in canonical or p not in mapping_predicates or not o.startswith("<") or o.startswith("<" + str(C)):
                raise ValueError("Invalid alignment graph boundary")
        inferred = set(db.execute("SELECT s,p,o FROM quads WHERE g=?", (str(G.inferred),)))
        asserted_skos = set(db.execute("SELECT s,p,o FROM quads WHERE g=? AND p IN (?,?)",
                                       (str(G.asserted), SKOS.broader.n3(), SKOS.related.n3())))
        permitted = {(o, SKOS.narrower.n3() if p == SKOS.broader.n3() else p, s)
                     for s, p, o in asserted_skos} - asserted_skos
        if inferred != permitted:
            raise ValueError("Inferred graph differs from the release inference profile")
    if manifest.get("release"):
        from pipeline.curate.identities import lifecycle_errors
        from pipeline.validate import identity_errors

        dataset = Dataset()
        dataset.parse(directory / "formal-sciences.nq", format="nquads")
        asserted, provenance = dataset.graph(G.asserted), dataset.graph(G.provenance)
        errors = identity_errors(asserted) + lifecycle_errors(asserted, provenance)
        if errors:
            raise ValueError("; ".join(errors))
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("dist"))
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    print(verify(args.directory, args.manifest_sha256))
