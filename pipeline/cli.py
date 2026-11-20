import argparse
from importlib import import_module
import json
from pathlib import Path
import sys
from rdflib import Graph
from pipeline.common import ROOT, registry, read
from pipeline.curate import authored
from pipeline.normalize.index import normalize
from pipeline.fetch import fetch
from pipeline.parse import ingest, staged
from pipeline.align import candidates
from pipeline.publish import build
from pipeline.curate.relations import PROFILES, replay as replay_relations
from pipeline.curate.openmath import replay as replay_openmath
from pipeline.curate.mathlib_evidence import replay as replay_mathlib
from pipeline.parse import lean_index
from pipeline.curate import neighborhoods
from pipeline.semantic_audit import AUDITS, replay as replay_semantic_audit


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
    for cmd in ("fetch","ingest","normalize","align","audit"):
        p = subs.add_parser(cmd)
        p.add_argument("--source",required=True,choices=sorted(registry()))
        p.add_argument("--offline",action="store_true")
    batch = subs.add_parser("replay-batch")
    batch.add_argument("--source", required=True, choices=sorted(
        p.stem for p in (ROOT / "reviews/approved/batches").glob("*.json")
    ))
    batch.add_argument("--offline", action="store_true")
    relations = subs.add_parser("replay-relations")
    relations.add_argument("--source", required=True, choices=sorted(PROFILES))
    relations.add_argument("--offline", action="store_true")
    relations.add_argument("--write-evidence", action="store_true")
    formal = subs.add_parser("replay-openmath")
    formal.add_argument("--offline", action="store_true")
    formal.add_argument("--write-evidence", action="store_true")
    mathlib = subs.add_parser("replay-mathlib")
    mathlib.add_argument("--offline", action="store_true")
    mathlib_index = subs.add_parser("replay-mathlib-index")
    mathlib_index.add_argument("--offline", action="store_true")
    mathlib_index.add_argument("--write-evidence", action="store_true")
    mathlib_index.add_argument("--export", type=Path)
    native = subs.add_parser("replay-neighborhood")
    native.add_argument("--source", required=True, choices=sorted(neighborhoods.PROFILES))
    native.add_argument("--offline", action="store_true")
    native.add_argument("--write-evidence", action="store_true")
    semantic = subs.add_parser("replay-semantic-audit")
    semantic.add_argument("--release", required=True, choices=sorted(p.stem for p in AUDITS.glob("*.json")))
    semantic.add_argument("--offline", action="store_true")
    for cmd in ("build","validate","stats","reason"):
        subs.add_parser(cmd)
    args = parser.parse_args()
    try:
        catalog = registry()
        if args.cmd == "sources":
            result = list(catalog) if args.view=="list" else {k:s["status"] for k,s in catalog.items()}
        elif args.cmd == "replay-openmath":
            result = replay_openmath(args.offline, args.write_evidence)
        elif args.cmd == "replay-mathlib":
            result = replay_mathlib(args.offline)
        elif args.cmd == "replay-mathlib-index":
            if args.export is not None and args.write_evidence:
                parser.error("--export requires an existing verified inventory")
            result = (lean_index.export(args.export, args.offline) if args.export is not None
                      else lean_index.replay(args.offline, args.write_evidence))
        elif args.cmd == "replay-semantic-audit":
            result = replay_semantic_audit(args.release, args.offline)
        elif hasattr(args,"source"):
            s = catalog[args.source]
            if args.cmd=="fetch":
                result = {"path":str(fetch(s,args.offline))}
            elif args.cmd=="ingest":
                result = ingest(s,args.offline)
            elif args.cmd=="normalize":
                result = normalize(s,args.offline)
            elif args.cmd=="audit":
                result = audit(s,args.offline)
            elif args.cmd == "replay-relations":
                result = replay_relations(args.source, args.offline, args.write_evidence)
            elif args.cmd == "replay-neighborhood":
                result = neighborhoods.replay(args.source, args.offline, args.write_evidence)
            elif args.cmd == "replay-batch":
                from pipeline.curate.batches import SOURCE_POLICIES

                if args.source not in SOURCE_POLICIES:
                    raise ValueError(f"No registered admission policy for {args.source}")
                module = import_module("pipeline.curate." + args.source.replace("-", "_"))
                result = module.replay(offline=args.offline)
            else:
                result = {"candidates":len(candidates(s,authored()[0],args.offline))}
        else:
            manifest = build()
            result = {k:manifest[k] for k in ("contract","counts","concepts","predicates","conforms")}
            if args.cmd == "stats":
                result["quality"] = manifest["quality"]
        print(json.dumps(result,indent=2))
    except Exception as exc:
        print(json.dumps({"error":str(exc)}),file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
