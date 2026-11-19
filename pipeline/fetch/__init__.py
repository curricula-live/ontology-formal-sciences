import gzip
import os
import shutil
import tempfile
from urllib.request import urlopen
from pathlib import Path
from pipeline.common import ROOT, checksum


def fetch(source, offline=False):
    if not source.get("sha256"):
        raise ValueError(f"{source['id']} has no verified snapshot: {source.get('blocker')}")
    dest = ROOT / "sources" / source["id"] / "original" / "snapshot"
    if dest.exists() and checksum(dest) == source["sha256"]:
        return dest
    dest.parent.mkdir(exist_ok=True)
    packed = dest.with_suffix(".gz")
    vault = Path(os.environ.get("FORMAL_SCIENCES_SNAPSHOT_DIR", Path.home()/".local/share/curricula/formal-sciences/snapshots")) / source["sha256"]
    if offline and not packed.exists() and not vault.exists():
        raise ValueError(f"Missing or corrupt cache for {source['id']}; run fetch online")
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
        name = tmp.name
    try:
        if packed.exists():
            stream = gzip.open(packed,"rb")
        elif vault.exists():
            stream = vault.open("rb")
        else:
            stream = urlopen(source["url"],timeout=180)
        with stream as src, open(name,"wb") as out:
            shutil.copyfileobj(src, out)
        if checksum(Path(name)) != source["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch for {source['id']}; review upstream revision")
        os.replace(name, dest)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return dest
