"""Independently check the byte and RDF content of a standalone v1 release."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from pyoxigraph import BlankNode, DefaultGraph, NamedNode, RdfFormat, parse
from rdflib import RDF, SKOS

from pipeline.common import BASE, G, checksum, read

ARTIFACTS = {"formal-sciences.ttl", "formal-sciences.trig", "formal-sciences.nq",
             "source-alignments.trig", "validation-report.json"}
GRAPH_NAMES = ("asserted", "alignments", "inferred", "provenance")


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


def verify(directory):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    if manifest["contract"] != "curricula.rdf-release/v1" or manifest["namespace"] != BASE:
        raise ValueError("Unexpected release contract or namespace")
    if set(manifest["artifacts"]) != ARTIFACTS or {p.name for p in directory.iterdir()} != ARTIFACTS | {"manifest.json"}:
        raise ValueError("Unexpected v1 artifact inventory")
    for artifact, digest in manifest["artifacts"].items():
        if checksum(directory / artifact) != digest:
            raise ValueError(f"Artifact checksum mismatch: {artifact}")
    report = read(directory / "validation-report.json")
    if manifest["conforms"] is not True or report["conforms"] is not True or report["findings"]:
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
        if concepts != manifest["concepts"]:
            raise ValueError("Manifest concept count differs from RDF")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("dist"))
    print(verify(parser.parse_args().directory))
