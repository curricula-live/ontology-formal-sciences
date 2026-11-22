"""Replay reviewed computer-science claims from immutable primary-source passages."""
from collections import Counter
from hashlib import sha256
from pathlib import PurePosixPath
import os
import re
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from urllib.request import urlopen

from rdflib import Graph, Literal, OWL, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, D, ROOT, V, checksum, read
from pipeline.curate.relations import statement_for
from pipeline.normalize import label_key

CORPORA = ROOT / "reviews/cs-evidence/corpora.json"
DECISIONS = ROOT / "reviews/cs-evidence/decisions.json"
CACHE = ROOT / ".cache/cs-evidence"
DIGEST = re.compile("[0-9a-f]{64}")
EVIDENCE_MODES = {"source statement", "implementation observation", "formal source statement", "editorial interpretation"}
PERMITTED = {
    "analyzes", "appliesToModel", "computes", "estimates", "guarantees", "hasInputStructure", "hasModelingAssumption",
    "hasProperty", "implementsAlgorithm", "invokesAlgorithm", "recognizesExactly", "represents",
    "requiresAssumption", "requiresPremise", "solves", "supportsOperation", "uses",
}


def file_url(corpus, path, raw=False):
    base = "https://raw.githubusercontent.com" if raw else "https://github.com"
    revision = corpus["revision"] if raw else "blob/" + corpus["revision"]
    return f"{base}/{corpus['repository']}/{revision}/{quote(path)}"


def review_inputs():
    corpora, reviews = read(CORPORA), read(DECISIONS)
    for key, corpus in corpora.items():
        if (not re.fullmatch(r"[a-z][a-z0-9-]*", key)
                or not re.fullmatch(r"[\w.-]+/[\w.-]+", corpus["repository"])
                or not re.fullmatch("[0-9a-f]{40}", corpus["revision"])
                or not corpus["rights"].strip() or not corpus["attribution"].strip()
                or corpus["license_path"] not in corpus["files"]):
            raise ValueError(f"Invalid computer-science evidence corpus: {key}")
        for name, digest in corpus["files"].items():
            path = PurePosixPath(name)
            if (not path.parts or path.is_absolute() or ".." in path.parts
                    or path.as_posix() != name or not DIGEST.fullmatch(digest)):
                raise ValueError(f"Invalid computer-science evidence file: {key}/{name}")
    seen = set()
    for row in reviews:
        key = row["corpus"], row["path"], row["first"], row["last"]
        if (key in seen or row["path"] not in corpora[row["corpus"]]["files"]
                or row["first"] < 1 or row["last"] < row["first"]
                or not DIGEST.fullmatch(row["sha256"]) or not row["judgments"]):
            raise ValueError(f"Invalid or duplicate passage: {key}")
        seen.add(key)
        for decision in row["judgments"]:
            triple = decision["triple"]
            if (len(triple) != 3 or triple[1] not in PERMITTED
                    or decision["state"] not in {"approved", "rejected"} or not decision["scope"].strip()):
                raise ValueError(f"Invalid passage judgment: {key} {decision}")
            if (row.get("introduced") and decision.get("evidence_mode") not in EVIDENCE_MODES
                    or "evidence_mode" in decision and decision["evidence_mode"] not in EVIDENCE_MODES):
                raise ValueError(f"Missing or invalid passage evidence mode: {key} {decision}")
    return corpora, reviews


def cache_file(corpus, name, digest, offline):
    directory = CACHE / digest[:2]
    path = directory / digest
    if path.is_file() and checksum(path) == digest:
        return path
    if offline:
        raise ValueError(f"Missing or corrupt source passage cache: {name}")
    directory.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=directory, delete=False) as temporary:
        draft = directory / os.path.basename(temporary.name)
    try:
        with urlopen(file_url(corpus, name, raw=True), timeout=45) as stream:
            draft.write_bytes(stream.read())
        if checksum(draft) != digest:
            raise ValueError(f"Source file checksum changed: {name}")
        draft.replace(path)
    finally:
        draft.unlink(missing_ok=True)
    return path


def replay(offline=False):
    corpora, rows = review_inputs()
    documents = {}
    required = {(row["corpus"], row["path"]) for row in rows}
    for key, corpus in corpora.items():
        for name, digest in corpus["files"].items():
            path = cache_file(corpus, name, digest, offline)
            if (key, name) in required:
                documents[key, name] = path.read_text(encoding="utf-8").splitlines()
    for row in rows:
        key, first, last = (row["corpus"], row["path"]), row["first"], row["last"]
        lines = documents[key]
        if last > len(lines) or sha256("\n".join(lines[first - 1:last]).encode()).hexdigest() != row["sha256"]:
            raise ValueError(f"Reviewed passage differs from pinned file: {key}:{first}-{last}")
    return {"corpora": len(corpora), "reviewed_passages": len(rows),
            "verified_files": sum(len(corpus["files"]) for corpus in corpora.values())}


def suggest_passages(corpus_key, baseline, offline=False, limit=50):
    """Locate exact topic labels in pinned passages and return review candidates."""
    corpora, _ = review_inputs()
    corpus = corpora[corpus_key]
    graph = Graph().parse(baseline, format="turtle")
    linked = {term for s, p, o in graph if str(p).startswith(str(V)) and p != V.containsSymbol
              for term in (s, o)}
    labels = {label_key(str(label)): str(term) for term, label in graph.subject_objects(SKOS.prefLabel)
              if term not in linked and graph.value(term, OWL.deprecated) != Literal(True)
              and (term, SKOS.inScheme, D["computer-science"]) in graph and len(str(label).split()) > 1}
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(text) for text in sorted(labels, key=lambda x: (-len(x), x)))
                         + r")(?!\w)") if labels else None
    results, seen = [], set()
    for name, digest in sorted(corpus["files"].items()):
        if name == corpus["license_path"] or pattern is None:
            continue
        lines = cache_file(corpus, name, digest, offline).read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            for match in pattern.finditer(label_key(line)):
                subject = labels[match.group()]
                if (name, subject) in seen:
                    continue
                seen.add((name, subject))
                first, last = max(0, index - 2), min(len(lines), index + 5)
                results.append({"canonical": subject, "label_match": match.group(), "file": name,
                                "first": first + 1, "last": last,
                                "sha256": sha256("\n".join(lines[first:last]).encode()).hexdigest()})
                if len(results) == limit:
                    return results
    return results


def apply_reviewed_claims(graph, provenance):
    corpora, rows = review_inputs()
    sources = {}
    for key, corpus in corpora.items():
        source = sources[key] = URIRef(BASE + "source/" + key)
        provenance.add((source, RDF.type, PROV.Entity))
        provenance.add((source, DCTERMS.bibliographicCitation, Literal(corpus["attribution"])))
        provenance.add((source, DCTERMS.rights, URIRef(file_url(corpus, corpus["license_path"]))))
        provenance.add((source, DCTERMS.hasVersion, Literal(corpus["revision"])))

    facts, rejected = set(), set()
    counts, modes = Counter(), Counter()
    for row in rows:
        key, path = row["corpus"], row["path"]
        corpus = corpora[key]
        anchor = URIRef(file_url(corpus, path) + f"#L{row['first']}-L{row['last']}")
        evidence = URIRef(BASE + "relation-evidence/primary-passage/" + sha256(str(anchor).encode()).hexdigest())
        provenance.add((evidence, RDF.type, PROV.Entity))
        provenance.add((evidence, DCTERMS.isPartOf, sources[key]))
        provenance.add((evidence, DCTERMS.type, Literal("reviewed primary-source passage")))
        provenance.add((evidence, DCTERMS.identifier, Literal(corpus["files"][path])))
        provenance.add((evidence, V.evidenceContentDigest, Literal(row["sha256"])))
        provenance.add((evidence, PROV.hadPrimarySource, anchor))
        for decision in row["judgments"]:
            left, relation, right = decision["triple"]
            triple = C[left], V[relation], C[right]
            counts[decision["state"]] += 1
            if decision["state"] == "rejected":
                rejected.add(triple)
                continue
            concepts = (triple[0], triple[2])
            if concepts[0] == concepts[1] or any((term, RDF.type, SKOS.Concept) not in graph for term in concepts):
                raise ValueError(f"Unresolved computer-science claim endpoints: {triple}")
            graph.add(triple)
            facts.add(triple)
            statement = statement_for(triple)
            provenance.add((statement, RDF.type, RDF.Statement))
            provenance.add((statement, PROV.wasDerivedFrom, evidence))
            provenance.add((statement, DCTERMS.source, anchor))
            provenance.add((statement, DCTERMS.description, Literal(decision["scope"], lang="en")))
            for field, term in zip((RDF.subject, RDF.predicate, RDF.object), triple):
                provenance.add((statement, field, term))
            mode = decision.get("evidence_mode", "legacy passage review")
            modes[mode] += 1
            judgment_key = f"{statement}|{evidence}|{mode}|{decision['scope']}"
            judgment = URIRef(BASE + "relation-review/" + sha256(judgment_key.encode()).hexdigest())
            provenance.add((judgment, RDF.type, PROV.Entity))
            provenance.add((judgment, DCTERMS.subject, statement))
            provenance.add((judgment, PROV.wasDerivedFrom, evidence))
            provenance.add((judgment, DCTERMS.type, Literal(mode)))
            provenance.add((judgment, DCTERMS.description, Literal(decision["scope"], lang="en")))
    if any(triple in graph for triple in rejected):
        raise ValueError("A rejected source-passage interpretation is asserted")
    topics = {term for subject, _, obj in facts for term in (subject, obj)}
    native_opencs = {C[slug] for slug in read(ROOT / "reviews/approved/batches/opencs.json")["identities"].values()}
    return {
        "corpora": {key: {"revision": corpus["revision"], "rights": corpus["rights"],
                          "passages": sum(row["corpus"] == key for row in rows)}
                    for key, corpus in corpora.items()},
        "reviewed_passages": len(rows), "decisions": dict(counts), "distinct_relations": len(facts),
        "opencs_admitted_endpoints": len(topics & native_opencs),
        "approved_judgments_by_evidence_mode": dict(modes),
        "review_sha256": checksum(DECISIONS), "corpora_sha256": checksum(CORPORA),
    }
