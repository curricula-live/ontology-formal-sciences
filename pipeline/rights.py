"""Generate the publication inventory from declared and observable release channels."""
from collections import defaultdict


from rdflib.namespace import DCTERMS

from pipeline.common import BASE, ROOT, checksum, read
from pipeline.curate.cs_evidence import file_url, review_inputs

NATIVE = {"opencs", "ontomath-pro", "stato", "mathmoddb", "ml-schema"}
MAPPINGS = {"cso", "opencs", "ontomath-pro", "mathmoddb", "ml-schema", "wikidata"}
CLOSED_TERMS = ("nc-sa", "noncommercial", "by-sa", "gpl", "unverified", "permission unresolved")
DERIVED = {"native-labels", "source-axiom-projections", "selected-formal-expressions", "copied-text"}
COMPATIBLE_NATIVE = {"Apache-2.0", "CC-BY-4.0", "CC0-1.0", "CC-BY-3.0 (embedded imports have separate notices)"}
REVIEW_BASIS = {
    "openmath": "Selected dictionaries only. The embedded derivative-work notices and fingerprints are reviewed in the OpenMath evidence ledger.",
    "stato": "Native STATO scope only. Imported content has separate notices and does not inherit STATO's terms.",
}
POLICY = ROOT / "reviews/quality/source-rights.json"


def check_public_use(source, terms, uses, reviewed_scope):
    normalized = terms.lower()
    if set(uses) & DERIVED:
        if any(indicator in normalized for indicator in CLOSED_TERMS):
            raise ValueError(f"Incompatible unreviewed redistribution: {source} ({terms})")
        if terms not in COMPATIBLE_NATIVE and not (source == "openmath" and reviewed_scope == REVIEW_BASIS[source]):
            raise ValueError(f"No public redistribution scope for source: {source} ({terms})")
    if "copied-text" in uses:
        raise ValueError(f"Copied external text has no default release path: {source}")


def inventory(sources, provenance):
    policy = read(POLICY)
    uses = defaultdict(set)
    for source, row in sources.items():
        if row.get("admission"):
            if source not in NATIVE:
                raise ValueError(f"Unreviewed batch rights: {source}")
            uses[source].update({"native-labels", "source-identifiers"})
        if row.get("relations"):
            if source not in NATIVE:
                raise ValueError(f"Unreviewed axiom source: {source}")
            uses[source].update({"source-axiom-projections", "source-identifiers"})
        if row.get("formal_properties"):
            uses[source].update({"selected-formal-expressions", "source-identifiers"})
        if row.get("formal_declarations"):
            uses[source].update({"formal-fingerprints", "source-identifiers", "citations"})
    for row in read(ROOT / "reviews/approved/mappings.json"):
        source = row["source"]
        if source not in MAPPINGS:
            raise ValueError(f"Mapping lacks source rights review: {source}")
        uses[source].update({"editorial-mappings", "source-identifiers"})
    for source, channels in policy["external_material_channels"].items():
        if source not in sources:
            raise ValueError(f"Unregistered external material source: {source}")
        uses[source].update(channels)

    corpora, passages = review_inputs()
    expected_sources = {source for source, roles in uses.items() if roles} | set(corpora) | {"lean-kernel-fixture"}
    for entity in provenance.subjects(DCTERMS.rights):
        if str(entity).startswith(BASE + "source/"):
            if str(entity).removeprefix(BASE + "source/") not in expected_sources:
                raise ValueError(f"Unaccounted evidence source: {entity}")

    result = {}
    for source, entry in sources.items():
        channels = sorted(uses[source])
        terms = entry["license"]
        basis = REVIEW_BASIS.get(source, "Pinned source metadata and reviewed publication channels.")
        check_public_use(source, terms, channels, basis)
        status = "verified"
        if not channels:
            channels = ["reference-or-staging-only"]
            status = ("incompatible" if any(word in terms.lower() for word in ("nc-sa", "noncommercial"))
                      else "unresolved" if terms != "reference only" else "verified")
        elif source in REVIEW_BASIS:
            status = "unresolved"
        result[f"native:{source}"] = {
            "terms": terms, "attribution": entry["attribution"], "notice_or_source": entry["url"],
            "revision": entry["revision"], "source_sha256": entry["sha256"], "channels": channels,
            "disposition": status, "basis": basis,
        }
    for key, corpus in corpora.items():
        channels = ["citations", "passage-fingerprints", "independent-editorial-assertions"]
        if key == "opendsa":
            basis = "Repository README notice. Only independently reviewed facts, references and file fingerprints are published."
        else:
            basis = "Pinned notice and file digests. Published entries contain an editorial judgment and no upstream passage text."
        check_public_use(key, corpus["rights"], channels, basis)
        result[f"passage:{key}"] = {
            "terms": corpus["rights"], "attribution": corpus["attribution"],
            "notice_or_source": file_url(corpus, corpus["license_path"]),
            "revision": corpus["revision"], "source_sha256": corpus["files"][corpus["license_path"]],
            "channels": channels, "disposition": "unresolved" if key == "opendsa" else "verified", "basis": basis,
            "reviewed_passages": sum(row["corpus"] == key for row in passages),
        }
    return {
        "project": {"software": "MIT", "authored_rdf_and_editorial_mappings": "CC-BY-4.0",
                    "credit": "Curricula contributors", "notice": "LICENSE"},
        "sources": result,
        "distribution_notice": {"path": "NOTICE.md", "sha256": checksum(ROOT / "NOTICE.md"),
                                "applies_to": ["native:openmath", "native:stato", "passage:opendsa"]},
        "reference_policy": policy["reference_policy"],
        "scope": "Disposition refers to the reviewed publication channel. External material retains its own terms.",
    }
