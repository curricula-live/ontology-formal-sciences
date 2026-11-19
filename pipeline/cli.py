import argparse
import json
import sys
from rdflib import Graph
from pipeline.common import ROOT, registry, read
from pipeline.curate import authored
from pipeline.fetch import fetch
from pipeline.parse import ingest, staged
from pipeline.align import candidates
from pipeline.publish import build


def audit(source, offline=False):
    stats = ingest(source,offline)
    store = staged(source)
    checked = 0
    for state in ("approved","rejected"):
        for row in read(ROOT / "reviews" / state / "mappings.json"):
            if row["source"] != source["id"]:
                continue
            if row["sha256"] != source["sha256"] or not bool(store.query("ASK { GRAPH <"+stats["graph"]+"> { "+row["evidence"]+" } }")):
                raise ValueError("Decision evidence no longer present: "+row["id"])
            checked += 1
    return dict(source=source["id"],verified_decisions=checked,**{"triples":stats["triples"]})


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd",required=True)
    listing = subs.add_parser("sources")
    listing.add_argument("view",choices=["list","status"])
    for cmd in ("fetch","ingest","align","audit"):
        p = subs.add_parser(cmd)
        p.add_argument("--source",required=True,choices=sorted(registry()))
        p.add_argument("--offline",action="store_true")
    for cmd in ("build","validate","stats","reason"):
        subs.add_parser(cmd)
    args = parser.parse_args()
    try:
        catalog = registry()
        if args.cmd == "sources":
            result = list(catalog) if args.view=="list" else {k:s["status"] for k,s in catalog.items()}
        elif hasattr(args,"source"):
            s = catalog[args.source]
            if args.cmd=="fetch":
                result = {"path":str(fetch(s,args.offline))}
            elif args.cmd=="ingest":
                result = ingest(s,args.offline)
            elif args.cmd=="audit":
                result = audit(s,args.offline)
            else:
                result = {"candidates":len(candidates(s,authored()[0],args.offline))}
        else:
            manifest = build()
            result = {k:manifest[k] for k in ("contract","counts","concepts","predicates","conforms")}
        print(json.dumps(result,indent=2))
    except Exception as exc:
        print(json.dumps({"error":str(exc)}),file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
