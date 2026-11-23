from hashlib import sha256
from importlib import import_module
from io import BytesIO

import pytest


def test_mirror_has_to_supply_exact_pinned_bytes(tmp_path, monkeypatch):
    fetch = import_module("pipeline.fetch")
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    monkeypatch.setenv("FORMAL_SCIENCES_SNAPSHOT_DIR", str(tmp_path / "empty-vault"))
    snapshot = b"checksum-pinned original"
    source = dict(id="fixture", url="https://example.org/primary", mirrors=["https://example.org/mirror"],
                  sha256=sha256(snapshot).hexdigest())
    (tmp_path / "sources/fixture").mkdir(parents=True)
    attempts = []

    def download(url, timeout):
        attempts.append(url)
        return BytesIO(snapshot if url == source["mirrors"][0] else b"changed revision")

    monkeypatch.setattr(fetch, "urlopen", download)
    with pytest.raises(ValueError, match="Missing or corrupt cache"):
        fetch.fetch(source, offline=True)
    assert attempts == []
    result = fetch.fetch(source)
    assert result.read_bytes() == snapshot
    assert attempts == [source["url"], *source["mirrors"]]
