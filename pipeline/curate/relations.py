"""Extract and replay reviewed scientific relation projections from pinned RDF graphs."""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re

from rdflib import Graph, Literal, OWL, RDF, RDFS, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read, registry, write
from pipeline.curate import authored, reviewed
from pipeline.parse import ingest, staged

LEDGERS = ROOT / "reviews/relations"


@dataclass(frozen=True)
class Rule:
    source_predicate: str
    relation: str | None = None
    reverse: bool = False


@dataclass(frozen=True)
class Profile:
    namespace: str
    native_id: str
    license: str
    shape: str
    rules: dict[str, Rule]


MARDI = "https://portal.mardi4nfdi.de/entity/"
ONTO = "http://cll.niimm.ksu.ru/ontologies/mathematics#"
OBO = "http://purl.obolibrary.org/obo/"
PROFILES = {
    "mathmoddb": Profile(MARDI, r"Q[0-9]+", "CC-BY-4.0", "direct", {
        "P147": Rule(MARDI + "P147", "appliesToModel", reverse=True),
        "P1560": Rule(MARDI + "P1560", "hasFormulationComponent"),
        "P1655": Rule(MARDI + "P1655", "hasApproximation"),
        "P1656": Rule(MARDI + "P1656", "hasDiscretization"),
        "P1674": Rule(MARDI + "P1674", "hasModelingAssumption"),
        "P1736": Rule(MARDI + "P1736", "hasWeakFormulation"),
    }),
    "stato": Profile(OBO + "STATO_", r"[0-9]{7}",
                     "CC-BY-3.0 (embedded imports have separate notices)", "subclass-some", {
        "input": Rule(OBO + "OBI_0000293", "usesReferenceDistribution"),
        "target": Rule(OBO + "STATO_0000403", "estimates"),
    }),
    "ontomath-pro": Profile(ONTO, r"E[0-9]+", "Apache-2.0", "equivalent-all", {
        "P1": Rule(ONTO + "P1"),
        "P2": Rule(ONTO + "P2"),
    }),
}


def extract(store, graph_name, profile):
    """Keep only named local endpoints. Blank-node identifiers stay in staging."""
    predicates = {rule.source_predicate: key for key, rule in profile.rules.items()}
    values = " ".join(URIRef(p).n3() for p in predicates)
    if profile.shape == "direct":
        pattern = "?subject ?property ?object ."
    else:
        link, filler = ((RDFS.subClassOf, OWL.someValuesFrom) if profile.shape == "subclass-some"
                        else (OWL.equivalentClass, OWL.allValuesFrom))
        pattern = f"""
            ?subject {URIRef(link).n3()} ?restriction .
            ?restriction a {OWL.Restriction.n3()} ;
                {OWL.onProperty.n3()} ?property ;
                {URIRef(filler).n3()} ?object .
            FILTER(isBlank(?restriction))
        """
    query = f"""SELECT DISTINCT ?subject ?property ?object WHERE {{
        VALUES ?property {{ {values} }}
        GRAPH {URIRef(graph_name).n3()} {{ {pattern} }}
        FILTER(isIRI(?subject) && isIRI(?object))
        FILTER(STRSTARTS(STR(?subject), "{profile.namespace}") &&
               STRSTARTS(STR(?object), "{profile.namespace}"))
    }}"""
    rows = set()
    for subject, predicate, obj in store.query(query):
        left = subject.value.removeprefix(profile.namespace)
        right = obj.value.removeprefix(profile.namespace)
        if re.fullmatch(profile.native_id, left) and re.fullmatch(profile.native_id, right):
            rows.add((left, predicates[predicate.value], right))
    return sorted(rows)


def resolved_identities(source_id, mappings):
    """Resolve reviewed subject projections and exact matches with an ambiguity veto."""
    targets = defaultdict(set)
    path = ROOT / f"reviews/approved/batches/{source_id}.json"
    if path.is_file():
        for external, slug in read(path)["identities"].items():
            targets[URIRef(external)].add(C[slug])
    for canonical, external in mappings.subject_objects(SKOS.exactMatch):
        if str(external).startswith(PROFILES[source_id].namespace):
            targets[external].add(canonical)
    return targets


def profile_digest(profile):
    data = json.dumps(asdict(profile), sort_keys=True, separators=(",", ":"))
    return sha256(data.encode()).hexdigest()


def verify_source(source_id, catalog, record):
    source, profile = catalog[source_id], PROFILES[source_id]
    if (source["license"] != profile.license
            or record["sha256"] != source["sha256"] or record["revision"] != source["revision"]
            or record["profile_sha256"] != profile_digest(profile)):
        raise ValueError(f"Relation source rights or revision changed: {source_id}")
    return source, profile


def decisions_for(source_id, known, record):
    path = LEDGERS / f"{source_id}-decisions.json"
    if not path.exists():
        return {}
    review = read(path)
    if any(review[field] != record[field] for field in ("sha256", "profile_sha256")):
        raise ValueError(f"Relation decisions require review for the new source or profile: {source_id}")
    decisions = {}
    for state, entries in review["decisions"].items():
        if state not in {"approved", "rejected"}:
            raise ValueError(f"Unknown relation review state for {source_id}: {state}")
        for left, predicate, right, rationale in entries:
            key = (left, predicate, right)
            if key not in known or key in decisions or not rationale.strip():
                raise ValueError(f"Unsupported or conflicting relation decision: {source_id} {key}")
            decisions[key] = state, rationale
    return decisions


def statement_for(triple):
    digest = sha256(" ".join(term.n3() for term in triple).encode()).hexdigest()
    return URIRef(BASE + "assertion/" + digest)


def annotate(provenance, source, profile, edge, triple, rationale):
    statement = statement_for(triple)
    fields = (RDF.subject, RDF.predicate, RDF.object)
    provenance.add((statement, RDF.type, RDF.Statement))
    for predicate, value in zip(fields, triple):
        provenance.add((statement, predicate, value))
    url = URIRef(source["url"])
    provenance.add((statement, DCTERMS.source, url))

    left, rule_key, right = edge
    witness = tuple(map(URIRef, (profile.namespace + left, profile.rules[rule_key].source_predicate,
                               profile.namespace + right)))
    key = "|".join((source["sha256"], profile.shape, *map(str, witness)))
    evidence = URIRef(BASE + "relation-evidence/" + sha256(key.encode()).hexdigest())
    provenance.add((statement, PROV.wasDerivedFrom, evidence))
    provenance.add((evidence, RDF.type, PROV.Entity))
    for predicate, value in zip(fields, witness):
        provenance.add((evidence, predicate, value))
    provenance.add((evidence, DCTERMS.type, Literal(profile.shape)))
    provenance.add((evidence, DCTERMS.description, Literal(rationale, lang="en")))
    provenance.add((evidence, DCTERMS.identifier, Literal(source["sha256"])))
    provenance.add((evidence, PROV.hadPrimarySource, url))
    return evidence


def describe_source(provenance, source_id, source):
    node = URIRef(BASE + "source/" + source_id)
    provenance.add((node, RDF.type, PROV.Entity))
    provenance.add((node, PROV.hadPrimarySource, URIRef(source["url"])))
    provenance.add((node, DCTERMS.rights, Literal(source["license"])))
    provenance.add((node, DCTERMS.bibliographicCitation, Literal(source["attribution"])))


def apply_relations(catalog, canonical, mappings, provenance):
    """Publish only adjudicated rows and retain counts of the other candidates."""
    report = {}
    for source_id in sorted(PROFILES):
        path = LEDGERS / f"{source_id}.json"
        if not path.exists():
            if path.with_name(f"{source_id}-decisions.json").exists():
                raise ValueError(f"Relation decisions lack extracted evidence: {source_id}")
            continue
        record = read(path)
        source, profile = verify_source(source_id, catalog, record)
        edges = [tuple(row) for row in record["edges"]]
        if edges != sorted(set(edges)):
            raise ValueError(f"Unordered or duplicate relation evidence for {source_id}")
        decisions = decisions_for(source_id, set(edges), record)
        targets = resolved_identities(source_id, mappings)
        counts = Counter(dict.fromkeys(("approved", "rejected", "pending", "unresolved", "ambiguous"), 0))
        source_node = URIRef(BASE + "source/" + source_id)
        for edge in edges:
            left, rule_key, right = edge
            rule = profile.rules[rule_key]
            if not all(re.fullmatch(profile.native_id, endpoint) for endpoint in (left, right)):
                raise ValueError(f"Foreign relation endpoint: {source_id} {edge}")
            state, rationale = decisions.get(edge, ("pending", ""))
            if state == "rejected":
                counts[state] += 1
                continue
            subjects, objects = (targets[URIRef(profile.namespace + endpoint)] for endpoint in (left, right))
            if len(subjects) != 1 or len(objects) != 1:
                if state == "approved":
                    raise ValueError(f"Approved relation has unresolved or ambiguous endpoints: {source_id} {edge}")
                counts["ambiguous" if max(len(subjects), len(objects)) > 1 else "unresolved"] += 1
                continue
            if state == "pending":
                counts[state] += 1
                continue
            if rule.relation is None or profile.shape == "equivalent-all":
                raise ValueError(f"No sound relation projection for {source_id} {edge}")
            subject, = subjects
            obj, = objects
            if rule.reverse:
                subject, obj = obj, subject
            if subject == obj or any((node, RDF.type, SKOS.Concept) not in canonical for node in (subject, obj)):
                raise ValueError(f"Invalid canonical relation endpoints: {source_id} {edge}")
            triple = subject, V[rule.relation], obj
            canonical.add(triple)
            evidence = annotate(provenance, source, profile, edge, triple, rationale)
            provenance.add((evidence, DCTERMS.isPartOf, source_node))
            counts["approved"] += 1
        if counts["approved"]:
            describe_source(provenance, source_id, source)
        review_path = path.with_name(f"{source_id}-decisions.json")
        report[source_id] = dict(counts, extracted=len(edges), evidence_sha256=checksum(path))
        if review_path.exists():
            report[source_id]["review_sha256"] = checksum(review_path)
    return report


def replay(source_id, offline=False, write_evidence=False):
    path = LEDGERS / f"{source_id}.json"
    source = registry()[source_id]
    profile = PROFILES[source_id]
    if source["license"] != profile.license:
        raise ValueError(f"Review relation extraction rights for {source_id}")
    stats = ingest(source, offline)
    edges = extract(staged(source), stats["graph"], profile)
    record = dict(sha256=source["sha256"], revision=source["revision"],
                  profile_sha256=profile_digest(profile), edges=[list(r) for r in edges])
    if write_evidence:
        write(path, record)
        return {"extracted": len(edges), "profile_sha256": record["profile_sha256"]}
    if read(path) != record:
        raise ValueError(f"Relation evidence drifted for {source_id}")
    canonical, provenance = authored()
    catalog = registry()
    mappings = reviewed(catalog, canonical, provenance)
    return apply_relations(catalog, canonical, mappings, provenance)[source_id]
