"""Run the published-dataset competency queries against a release's N-Quads file."""
import argparse
import json
from pathlib import Path

from pyoxigraph import RdfFormat, Store

from pipeline.common import ROOT


def answers(dataset):
    store = Store()
    store.bulk_load(path=dataset, format=RdfFormat.N_QUADS)
    answers_by_query = {}
    for path in sorted((ROOT / "docs/queries").glob("*.rq")):
        result = store.query(path.read_text())
        columns = [var.value for var in result.variables]
        answers_by_query[path.stem] = [
            {name: term.value if term is not None else None for name, term in zip(columns, row)}
            for row in result
        ]
    return answers_by_query


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", type=Path, default=ROOT / "dist/formal-sciences.nq")
    print(json.dumps(answers(parser.parse_args().dataset), ensure_ascii=False, indent=2))
