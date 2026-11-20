import gzip
import os
import shutil
import tempfile
from urllib.error import URLError
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
            stream = None
        if stream is not None:
            with stream as src, open(name, "wb") as out:
                shutil.copyfileobj(src, out)
        else:
            failures = []
            for url in (source["url"], *source.get("mirrors", ())):
                try:
                    with urlopen(url, timeout=180) as src, open(name, "wb") as out:
                        shutil.copyfileobj(src, out)
                except (URLError, TimeoutError) as exc:
                    failures.append(str(exc))
                    continue
                if checksum(Path(name)) == source["sha256"]:
                    break
                failures.append("checksum mismatch")
            else:
                raise ValueError(f"Could not retrieve pinned bytes for {source['id']}: {'; '.join(failures)}")
        if checksum(Path(name)) != source["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch for {source['id']}; review upstream revision")
        os.replace(name, dest)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return dest
