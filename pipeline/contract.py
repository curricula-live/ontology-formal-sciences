"""Stable release metadata shared by the builder and offline consumers."""
import json
import re

from pipeline.common import BASE, G

CONTRACT = "curricula.rdf-release/v1"
GRAPH_NAMES = ("asserted", "alignments", "inferred", "provenance")
ARTIFACTS = {"formal-sciences.ttl", "formal-sciences.trig", "formal-sciences.nq",
             "source-alignments.trig", "validation-report.json"}
DIGEST = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {path.name}: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Nonstandard JSON number in {path.name}: {value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=reject_constant)


def version_tuple(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError(f"Invalid ontology version: {value}")
    return tuple(map(int, value.split(".")))


def metadata(status, maturity):
    return {"status": status, "scientific_maturity": maturity,
            "graph_iris": {name: str(G[name]) for name in GRAPH_NAMES}}


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("contract") != CONTRACT or manifest.get("namespace") != BASE:
        raise ValueError("Unexpected release contract or namespace")
    version = version_tuple(manifest.get("version"))
    counts, files = manifest.get("counts"), manifest.get("artifacts")
    if not isinstance(counts, dict) or set(counts) != set(GRAPH_NAMES) or any(
        type(n) is not int or n < 0 for n in counts.values()
    ):
        raise ValueError("Invalid graph counts")
    if not isinstance(files, dict) or set(files) != ARTIFACTS or any(
        not isinstance(d, str) or not DIGEST.fullmatch(d) for d in files.values()
    ):
        raise ValueError("Invalid artifact digest inventory")
    for field in ("concepts", "predicates"):
        n = manifest.get(field)
        if type(n) is not int or n < 1 or n > counts["asserted"]:
            raise ValueError(f"Invalid manifest {field}")
    if manifest.get("conforms") is not True or not isinstance(manifest.get("sources"), dict):
        raise ValueError("Invalid manifest conformance or source inventory")
    for source, row in manifest["sources"].items():
        if not isinstance(row, dict) or any(
            not isinstance(row.get(field), str) or not row[field].strip()
            for field in ("license", "attribution", "url", "scope")
        ):
            raise ValueError(f"Incomplete source attribution: {source}")
        if row.get("sha256") is not None and (
            not isinstance(row["sha256"], str) or not DIGEST.fullmatch(row["sha256"])
        ):
            raise ValueError(f"Invalid source digest: {source}")
    release = manifest.get("release")
    if release is not None or version >= (1, 0, 0):
        if (not isinstance(release, dict) or release.get("status") not in {"candidate", "stable"}
                or release.get("scientific_maturity") not in {"Foundation", "Expanded", "Mature"}
                or release.get("graph_iris") != metadata(None, None)["graph_iris"]):
            raise ValueError("Invalid release status, maturity or logical graph map")
    if "rights" in manifest:
        validate_rights(manifest["rights"], manifest["sources"])
    elif version >= (1, 0, 0):
        raise ValueError("Release requires a rights inventory")
    return manifest


def validate_rights(rights, native_sources):
    if not isinstance(rights, dict) or rights.get("project") != {
        "software": "MIT", "authored_rdf_and_editorial_mappings": "CC-BY-4.0",
        "credit": "Curricula contributors", "notice": "LICENSE",
    }:
        raise ValueError("Invalid project rights metadata")
    notice = rights.get("distribution_notice")
    if notice is not None and (
        not isinstance(notice, dict) or notice.get("path") != "NOTICE.md"
        or not isinstance(notice.get("sha256"), str) or not DIGEST.fullmatch(notice["sha256"])
        or notice.get("applies_to") not in (["native:openmath", "native:stato", "passage:opendsa"],
            ["native:openmath", "native:stato", "passage:opendsa", "passage:openstax-conditional", "passage:d2l-gradient"])
    ):
        raise ValueError("Invalid separate source notice metadata")
    families = rights.get("sources")
    if not isinstance(families, dict) or {"native:" + name for name in native_sources} - set(families):
        raise ValueError("Incomplete rights inventory")
    for family, row in families.items():
        if (not isinstance(row, dict) or row.get("disposition") not in {"verified", "unresolved", "incompatible"}
                or not isinstance(row.get("channels"), list) or not row["channels"]
                or any(not isinstance(ch, str) or not ch for ch in row["channels"])
                or any(not isinstance(row.get(key), str) or not row[key].strip()
                       for key in ("basis", "notice_or_source", "terms", "attribution"))
                or row["disposition"] == "incompatible" and row["channels"] != ["reference-or-staging-only"]):
            raise ValueError(f"Invalid rights entry: {family}")
