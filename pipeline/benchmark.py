"""Measure fresh disk-backed source parsing or a publication build. Run once per process."""
import argparse
import json
import resource
import sys
import tempfile
import time
from pathlib import Path

from pyoxigraph import NamedNode, Store

from pipeline.common import BASE, registry
from pipeline.fetch import fetch
from pipeline.parse import load_graph
from pipeline.publish import build


def measure(operation, source_id=None):
    if not sys.platform.startswith("linux"):
        raise RuntimeError("This benchmark reports Linux ru_maxrss in KiB")
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        if operation == "parse":
            source = registry()[source_id]
            snapshot = fetch(source, offline=True)
            store = Store(str(Path(tmp) / "stage"))
            graph = NamedNode(BASE + "stage/" + source_id + "/" + source["sha256"])
            load_graph(store, snapshot, source, graph)
            if not bool(store.query(source["validation_query"])):
                raise ValueError("Source competency check failed")
            result = dict(source=source_id, sha256=source["sha256"], input_bytes=snapshot.stat().st_size,
                          staged_triples=len(store))
        else:
            dest = Path(tmp) / "dist"
            manifest = build(dest)
            result = dict(concepts=manifest["concepts"], counts=manifest["counts"],
                          output_bytes=sum(p.stat().st_size for p in dest.iterdir()))
        result.update(operation=operation, elapsed_seconds=round(time.perf_counter() - start, 3),
                      process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("build")
    commands.add_parser("parse").add_argument("--source", required=True, choices=registry())
    args = parser.parse_args()
    print(json.dumps(measure(args.operation, getattr(args, "source", None)), indent=2))
