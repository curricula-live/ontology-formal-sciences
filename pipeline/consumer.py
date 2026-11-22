"""Reference intake and atomic activation for a disposable local package store."""
import argparse
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from pyoxigraph import NamedNode, RdfFormat, Store
from rdflib import Dataset, Literal, OWL, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, G
from pipeline.contract import COMMIT, DIGEST, read_json, version_tuple
from pipeline.curate.relations import statement_for
from pipeline.package_check import verify


def dataset(data):
    result = Dataset()
    result.parse(data=data, format="nquads")
    return result


def successor_changes(before, after):
    """Check published lineage and return inspectable graph-level changes."""
    old, new = before.graph(G.asserted), after.graph(G.asserted)
    old_concepts = set(old.subjects(RDF.type, SKOS.Concept))
    new_concepts = set(new.subjects(RDF.type, SKOS.Concept))
    missing = old_concepts - new_concepts
    if missing:
        raise ValueError(f"Canonical IRI deleted: {min(missing)}")
    scope_fields = (SKOS.prefLabel, SKOS.definition, SKOS.inScheme)
    old_prov, new_prov = before.graph(G.provenance), after.graph(G.provenance)
    for concept in sorted(old_concepts):
        # A tombstone remains the same identity. A repurposed concept needs a fresh IRI.
        if (any(set(old.objects(concept, field)) != set(new.objects(concept, field)) for field in scope_fields)
                or not set(old.objects(concept, SKOS.altLabel)) <= set(new.objects(concept, SKOS.altLabel))):
            raise ValueError(f"Canonical scope changed without an approved compatibility policy: {concept}")
        if old.value(concept, OWL.deprecated) == Literal(True) and (
            new.value(concept, OWL.deprecated) != Literal(True)
            or set(old.objects(concept, DCTERMS.isReplacedBy)) != set(new.objects(concept, DCTERMS.isReplacedBy))
        ):
            raise ValueError(f"Retired canonical IRI reused or redirected: {concept}")
        if not set(old_prov.objects(concept, DCTERMS.source)) <= set(new_prov.objects(concept, DCTERMS.source)):
            raise ValueError(f"Canonical source origin lost: {concept}")
    if set(before.graph(G.alignments)) - set(after.graph(G.alignments)):
        raise ValueError("Reviewed mapping removed from successor")
    for triple in set(old) - set(new):
        retired = statement_for(triple)
        revisions = new_prov.subjects(PROV.wasRevisionOf, retired)
        fields = (RDF.subject, RDF.predicate, RDF.object)
        if (any((retired, field, value) not in new_prov for field, value in zip(fields, triple))
                or not any(tuple(new_prov.value(revision, term) for term in fields) in new
                           and new_prov.value(revision, DCTERMS.description)
                           for revision in revisions)):
            raise ValueError(f"Asserted statement removed without an archived revision: {retired}")
    for triple in old_prov:
        subject, predicate, _ = triple
        # A module resource describes the current source file. Statement and source witnesses
        # are retained independently of a changed module file checksum.
        if triple not in new_prov and not (
            predicate == DCTERMS.identifier and str(subject).startswith(BASE + "module/")
        ):
            raise ValueError(f"Historical provenance removed: {subject}")
    return {name: {"added": len(set(after.graph(G[name])) - set(before.graph(G[name]))),
                   "removed": len(set(before.graph(G[name])) - set(after.graph(G[name])))}
            for name in ("asserted", "alignments", "inferred", "provenance")}


@dataclass(frozen=True)
class Receipt:
    commit: str
    digest: str
    version: str


def _activate(db, commit):
    db.execute("INSERT INTO active VALUES(1, ?) ON CONFLICT(slot) DO UPDATE SET revision=excluded.revision",
               (commit,))


class Consumer:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS packages (
                       revision TEXT PRIMARY KEY, digest TEXT NOT NULL, version TEXT NOT NULL,
                       data BLOB NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS active (
                       slot INTEGER PRIMARY KEY CHECK(slot=1), revision TEXT NOT NULL
                       REFERENCES packages(revision))""")

    def _connect(self):
        db = sqlite3.connect(self.root / "intake.sqlite")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def install(self, directory, commit, digest):
        if not COMMIT.fullmatch(commit) or not DIGEST.fullmatch(digest):
            raise ValueError("A full release commit and manifest SHA-256 are required")
        with TemporaryDirectory(dir=self.root) as tmp:
            snapshot = Path(tmp) / "package"
            shutil.copytree(directory, snapshot, symlinks=True)
            verify(snapshot, digest)
            version = read_json(snapshot / "manifest.json")["version"]
            data = (snapshot / "formal-sciences.nq").read_bytes()
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            known = db.execute("SELECT digest FROM packages WHERE revision=?", (commit,)).fetchone()
            if known and known[0] != digest:
                raise ValueError("A release commit already has a different manifest")
            current = db.execute("""SELECT revision, version, data FROM active
                                    JOIN packages USING(revision)""").fetchone()
            if current and current[0] == commit:
                return Receipt(commit, digest, version), None
            changes = None
            if current:
                if version_tuple(version) < version_tuple(current[1]):
                    raise ValueError("Older releases require explicit rollback")
                changes = successor_changes(dataset(current[2]), dataset(data))
            if not known:
                db.execute("INSERT INTO packages VALUES(?,?,?,?)", (commit, digest, version, data))
            _activate(db, commit)
            return Receipt(commit, digest, version), changes

    def rollback(self, commit):
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT digest,version FROM packages WHERE revision=?", (commit,)).fetchone()
            if row is None:
                raise ValueError("Rollback target was never activated")
            _activate(db, commit)
            return Receipt(commit, *row)

    def snapshot(self):
        with closing(self._connect()) as db:
            row = db.execute("SELECT revision,digest,version,data FROM active JOIN packages USING(revision)").fetchone()
        if row is None:
            raise ValueError("No release is active")
        # Readers hold an isolated point-in-time view across later activations.
        graph = Store()
        graph.load(input=row[3], format=RdfFormat.N_QUADS)
        return Receipt(*row[:3]), graph


def resolve(store, iri):
    subject = NamedNode(iri)
    asserted = NamedNode(str(G.asserted))
    if not list(store.quads_for_pattern(subject, NamedNode(str(RDF.type)), NamedNode(str(SKOS.Concept)), asserted)):
        return {"status": "unknown", "targets": []}
    retired = any(store.quads_for_pattern(subject, NamedNode(str(OWL.deprecated)), None, asserted))
    targets = sorted(quad.object.value for quad in
                     store.quads_for_pattern(subject, NamedNode(str(DCTERMS.isReplacedBy)), None, asserted))
    return {"status": "deprecated" if retired else "active", "targets": targets}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storage", type=Path)
    commands = parser.add_subparsers(dest="action", required=True)
    load = commands.add_parser("install")
    load.add_argument("package", type=Path)
    load.add_argument("commit")
    load.add_argument("manifest_sha256")
    rollback = commands.add_parser("rollback")
    rollback.add_argument("commit")
    lookup = commands.add_parser("resolve")
    lookup.add_argument("iri")
    args = parser.parse_args()
    consumer = Consumer(args.storage)
    if args.action == "install":
        print(consumer.install(args.package, args.commit, args.manifest_sha256))
    elif args.action == "rollback":
        print(consumer.rollback(args.commit))
    else:
        print(resolve(consumer.snapshot()[1], args.iri))
