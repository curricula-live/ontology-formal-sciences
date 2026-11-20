"""Verify the scope of source-derived topic admissions at the publication boundary."""
import json
import re

from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, checksum
from pipeline.curate import DOMAINS

# Scope covers native subjects only. Imported OWL classes have their own rights.
SOURCE_POLICIES = {
    "mathmoddb": ("CC-BY-4.0", r"https://portal\.mardi4nfdi\.de/entity/Q[0-9]+"),
    "opencs": ("CC-BY-4.0", r"https://w3id\.org/ocs/ont/C[0-9]+"),
    "ontomath-pro": ("Apache-2.0", r"http://cll\.niimm\.ksu\.ru/ontologies/mathematics#E[0-9]+"),
    "stato": ("CC-BY-3.0 (embedded imports have separate notices)",
              r"http://purl\.obolibrary\.org/obo/STATO_[0-9]{7}"),
}


def distinct_keys(items):
    obj = {}
    for key, value in items:
        if key in obj:
            raise ValueError(f"Duplicate admission registry key: {key}")
        obj[key] = value
    return obj


def verify_batches(catalog, graph, provenance, root=ROOT):
    modules = {p.relative_to(root).as_posix(): p for domain in DOMAINS
               for p in (root / "domains" / domain / "modules/batches").rglob("*.ttl")}
    reports = {}
    covered = set()
    for path in sorted((root / "reviews/approved/batches").glob("*.json")):
        record = json.loads(path.read_text(), object_pairs_hook=distinct_keys)
        key = path.stem
        if record["source"] != key or key not in SOURCE_POLICIES:
            raise ValueError(f"No admission policy for {key}")
        source = catalog[key]
        license_name, native_id = SOURCE_POLICIES[key]
        if (license_name != record["license"] or not record["policy"].strip()
                or any(record[k] != source[k] for k in ("sha256", "revision", "license"))):
            raise ValueError(f"Admission rights or source revision changed: {key}")

        batch = URIRef(BASE + "admission/" + key + "/" + checksum(path))
        provenance.add((batch, RDF.type, PROV.Entity))
        provenance.add((batch, DCTERMS.description, Literal(record["policy"], lang="en")))
        provenance.add((batch, DCTERMS.rights, Literal(license_name)))
        provenance.add((batch, DCTERMS.bibliographicCitation, Literal(source["attribution"])))
        provenance.add((batch, PROV.hadPrimarySource, URIRef(source["url"])))
        provenance.add((batch, DCTERMS.identifier, Literal(source["sha256"])))
        provenance.add((batch, DCTERMS.hasVersion, Literal(source["revision"])))

        if not record["modules"]:
            raise ValueError(f"Empty batch: {key}")
        owned = set()
        for name, digest in record["modules"].items():
            if name not in modules or name in covered or checksum(modules[name]) != digest:
                raise ValueError(f"Unreviewed or conflicting batch module: {name}")
            covered.add(name)
            module = URIRef(BASE + "module/" + name.removeprefix("domains/"))
            owned.update(provenance.subjects(PROV.wasDerivedFrom, module))
            provenance.add((module, PROV.wasDerivedFrom, batch))

        identities = record["identities"]
        topics = set()
        for external, slug in identities.items():
            if not re.fullmatch(native_id, external) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
                raise ValueError(f"Identity outside admitted namespace: {external} / {slug}")
            topic = C[slug]
            if (topic, RDF.type, SKOS.Concept) not in graph or topic in topics:
                raise ValueError(f"Missing topic or ambiguous identity within {key}: {topic}")
            topics.add(topic)
            # Origin of a subject heading is weaker than class or SKOS equivalence.
            provenance.add((topic, DCTERMS.source, URIRef(external)))
        if not owned or not owned <= topics:
            raise ValueError(f"Missing source identities for concepts in {key} modules")

        eligible, pending = record["eligible"], record["pending"]
        measures = [eligible, pending, *record["exclusions"].values()]
        if (any(type(n) is not int or n < 0 for n in measures)
                or eligible < len(identities) + pending):
            raise ValueError(f"Inconsistent admission counts for {key}")
        reports[key] = {k: record[k] for k in ("eligible", "pending", "exclusions", "policy", "modules")}
        reports[key].update(identities=len(identities), new_concepts=len(owned),
                            registry_sha256=checksum(path))
    if covered != modules.keys():
        raise ValueError(f"Batch modules missing admission records: {sorted(modules.keys() - covered)}")
    return reports

