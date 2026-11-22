import json
import shutil
from hashlib import sha256

import pytest

from pipeline.common import ROOT, checksum, require_checkout
from pipeline.contract import metadata, read_json, validate_manifest
from pipeline.package_check import verify


def test_manifest_schema_and_identity(tmp_path):
    original = ROOT / "dist"
    package = tmp_path / "package"
    shutil.copytree(original, package)
    original_digest = checksum(package / "manifest.json")
    assert verify(package, original_digest)
    with pytest.raises(ValueError, match="Pinned manifest"):
        verify(package, "0" * 64)

    manifest = read_json(package / "manifest.json")
    manifest["version"] = "1.0.0"
    manifest.pop("release", None)
    with pytest.raises(ValueError, match="release status"):
        validate_manifest(manifest)
    manifest["release"] = metadata("candidate", "Foundation")
    manifest.setdefault("rights", read_json(original / "manifest.json").get("rights", {}))
    validate_manifest(manifest)
    manifest["counts"]["alignments"] = True
    with pytest.raises(ValueError, match="graph counts"):
        validate_manifest(manifest)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"version":"1.0.0","version":"0.9.0"}')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        read_json(duplicate)


def test_corrupt_serialization_rejected_even_with_updated_hash(tmp_path):
    source = ROOT / "dist"
    shutil.copytree(source, tmp_path, dirs_exist_ok=True)
    manifest_path = tmp_path / "manifest.json"
    manifest = read_json(manifest_path)
    tri = tmp_path / "formal-sciences.trig"
    tri.write_bytes(tri.read_bytes() + b"\n<urn:s> <urn:p> <urn:o> .\n")
    manifest["artifacts"][tri.name] = sha256(tri.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="named graphs"):
        verify(tmp_path)


def test_checkout_runtime(tmp_path):
    require_checkout()
    with pytest.raises(ValueError, match="complete ontology checkout"):
        require_checkout(tmp_path)
    assert "[project.scripts]" not in (ROOT / "pyproject.toml").read_text()
