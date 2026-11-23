"""Rehearse package replacement and rollback on a disposable local Fuseki/TDB2."""
import argparse
import json
import socket
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pyoxigraph import Literal, NamedNode, RdfFormat, parse

from pipeline.common import C, G, checksum
from pipeline.contract import GRAPH_NAMES
from pipeline.package_check import verify


def resources(package):
    rows = defaultdict(set)
    for q in parse(path=package / "formal-sciences.nq", format=RdfFormat.N_QUADS):
        rows[q.graph_name.value].add((q.subject, q.predicate, q.object))
    return rows


def replace_update(rows):
    parts = []
    for graph, triples in sorted(rows.items()):
        data = "\n".join(f"{s} {p} {o} ." for s, p, o in sorted(triples, key=lambda triple: tuple(map(str, triple))))
        parts.append(f"GRAPH <{graph}> {{\n{data}\n}}")
    return "CLEAR ALL;\nINSERT DATA {\n" + "\n".join(parts) + "\n}"


def term(value):
    if value["type"] == "uri":
        return NamedNode(value["value"])
    if value["type"] not in {"literal", "typed-literal"}:
        raise ValueError(f"Unexpected rehearsal RDF term: {value['type']}")
    if "xml:lang" in value:
        return Literal(value["value"], language=value["xml:lang"])
    if "datatype" in value:
        return Literal(value["value"], datatype=NamedNode(value["datatype"]))
    return Literal(value["value"])


def query(server, sparql):
    url = server + "/release/query?" + urlencode({"query": sparql})
    request = Request(url, headers={"Accept": "application/sparql-results+json"})
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def update(server, sparql):
    data = sparql.encode()
    request = Request(server + "/release/update", data=data, method="POST",
                      headers={"Content-Type": "application/sparql-update; charset=utf-8"})
    with urlopen(request, timeout=90) as response:
        response.read()


def check_dataset(server, expected):
    found = defaultdict(set)
    result = query(server, "SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?s ?p ?o } }")
    for row in result["results"]["bindings"]:
        found[row["g"]["value"]].add(tuple(term(row[v]) for v in ("s", "p", "o")))
    if found != expected:
        raise ValueError("Fuseki dataset differs from the verified package")
    if query(server, "ASK { ?s ?p ?o }")["boolean"]:
        raise ValueError("Unexpected data in Fuseki default graph")


def start(port, jar, directory, log):
    process = subprocess.Popen(["java", "-jar", str(jar), "--localhost", "--tdb2", f"--port={port}",
                                f"--loc={directory / 'tdb2'}", "--update", "/release"],
                               cwd=directory, stdout=log, stderr=subprocess.STDOUT)
    server = f"http://127.0.0.1:{port}"
    start_time = time.monotonic()
    while process.poll() is None and time.monotonic() - start_time < 45:
        try:
            query(server, "ASK { ?s ?p ?o }")
            return process, server
        except (URLError, TimeoutError):
            time.sleep(0.25)
    stop(process)
    raise RuntimeError("Fuseki failed to start")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def rehearse(jar, predecessor, candidate, baseline_digest, candidate_digest):
    jar = jar.resolve()
    verify(predecessor, baseline_digest)
    verify(candidate, candidate_digest)
    before, after = resources(predecessor), resources(candidate)
    if before == after:
        raise ValueError("Rehearsal requires two distinct packages")
    stages = []
    with TemporaryDirectory(prefix="formal-fuseki-rehearsal-") as temp:
        directory = Path(temp)
        (directory / "tdb2").mkdir()
        log_path = directory / "fuseki.log"
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        process = None
        try:
            with log_path.open("wb") as log:
                process, server = start(port, jar, directory, log)
                update(server, replace_update(before))
                check_dataset(server, before)
                update(server, replace_update(before))
                check_dataset(server, before)
                stages.extend(["baseline-import", "repeat-import"])
                try:
                    missing = (directory / "missing.rdf").as_uri()
                    update(server, replace_update(after) + f"; LOAD <{missing}>")
                except HTTPError as exc:
                    if exc.code < 400 or exc.code >= 600:
                        raise
                else:
                    raise ValueError("Fuseki accepted the deliberately failing update")
                check_dataset(server, before)
                stages.append("failure-rollback")
                update(server, replace_update(after))
                check_dataset(server, after)
                if not query(server, f"""ASK {{ GRAPH <{G.asserted}> {{
                    <{C['opencs-c3339']}> <http://purl.org/dc/terms/isReplacedBy> <{C['a-star-search']}> }} }}""")["boolean"]:
                    raise ValueError("The A* replacement cannot be resolved in Fuseki")
                stages.append("successor-replacement-and-identity")
                stop(process)
                process, server = start(port, jar, directory, log)
                check_dataset(server, after)
                stages.append("tdb2-reopen")
                update(server, replace_update(before))
                check_dataset(server, before)
                stages.append("explicit-rollback")
        except Exception as exc:
            tail = "\n".join(log_path.read_text(errors="replace").splitlines()[-18:])
            raise RuntimeError(f"Rehearsal stopped after {stages}: {exc}\n{tail}") from exc
        finally:
            if process is not None:
                stop(process)
    return {"engine_jar_sha256": checksum(jar),
            "predecessor_manifest_sha256": checksum(predecessor / "manifest.json"),
            "candidate_manifest_sha256": checksum(candidate / "manifest.json"),
            "candidate_graph_counts": {name: len(after[str(G[name])]) for name in GRAPH_NAMES},
            "passed": stages}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--predecessor-digest", required=True)
    parser.add_argument("--candidate-digest", required=True)
    args = parser.parse_args()
    print(json.dumps(rehearse(args.jar, args.predecessor, args.candidate,
                              args.predecessor_digest, args.candidate_digest), indent=2))
