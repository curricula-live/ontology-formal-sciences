"""Paths and identities shared by authoring, staging and release tools."""
import hashlib
import json
from pathlib import Path
from rdflib import Namespace

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://curricula.live/id/formal-sciences/"
C = Namespace(BASE + "concept/")
V = Namespace(BASE + "vocab/")
G = Namespace(BASE + "graph/")
D = Namespace(BASE + "scheme/")


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def registry():
    return {p.parent.name: read(p) for p in sorted((ROOT / "sources").glob("*/source.yaml"))}

def require_checkout(root=ROOT):
    if not (root / "ontology.yaml").is_file() or any(
        not (root / name).is_dir() for name in ("domains", "sources", "reviews")
    ):
        raise ValueError("Run python -m pipeline.cli from a complete ontology checkout")
