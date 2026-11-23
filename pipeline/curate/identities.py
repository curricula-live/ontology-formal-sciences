"""Publish reviewed canonical replacements while retaining historical subjects."""
from hashlib import sha256

from rdflib import Graph, Literal, OWL, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read, registry
from pipeline.curate.relations import statement_for
from pipeline.parse import ingest, staged

LEDGER = ROOT / "reviews/approved/identity-migrations.json"


CARDINALITIES = {"deprecate": (0, 0), "replace": (1, 1), "merge": (1, 1), "split": (2, None)}


def action_and_targets(row):
    if row["decision"] == "duplicate":
        return "merge", [row["preferred"]]
    return row["decision"], row["targets"]


def reviewed_migrations():
    catalog = registry()
    rows = read(LEDGER)
    seen = set()
    for row in rows:
        action, targets = action_and_targets(row)
        former = row["former"]
        minimum, maximum = CARDINALITIES[action]
        if (former in seen or len(targets) != len(set(targets)) or former in targets
                or len(targets) < minimum or maximum is not None and len(targets) > maximum
                or not row["rationale"].strip() or not row["scientific_reference"].startswith("https://")):
            raise ValueError(f"Invalid identity decision: {former}")
        seen.add(former)
        if "source" not in row:
            if row["decision"] == "duplicate" or not row.get("review_id", "").strip():
                raise ValueError(f"Missing identity review basis: {former}")
            continue
        source = catalog[row["source"]]
        if row["snapshot_sha256"] != source["sha256"]:
            raise ValueError(f"Invalid identity snapshot: {former}")
        batch = read(ROOT / f"reviews/approved/batches/{row['source']}.json")
        if batch["identities"].get(row["native"]) != former:
            raise ValueError(f"Identity change lost its original admission: {former}")
        native = URIRef(row["native"])
        evidence = Graph().parse(data=row["source_evidence"], format="nt")
        if not any(evidence.predicate_objects(native)):
            raise ValueError(f"Incomplete native identity witness: {former}")
        if row["decision"] == "duplicate" and not (
            any(evidence.objects(native, SKOS.prefLabel)) and any(evidence.objects(native, SKOS.closeMatch))
        ):
            raise ValueError(f"Incomplete duplicate witness: {former}")
    return rows


def apply_migrations(graph, provenance):
    rows = reviewed_migrations()
    for row in rows:
        original = C[row["former"]]
        action, targets = action_and_targets(row)
        marker = original, OWL.deprecated, Literal(True)
        triples = [marker] + [(original, DCTERMS.isReplacedBy, C[target]) for target in targets]
        witness = URIRef(BASE + "identity-review/" + sha256(str(original).encode()).hexdigest())
        provenance.add((witness, RDF.type, PROV.Entity))
        provenance.add((witness, V.identityAction, V[action]))
        provenance.add((witness, DCTERMS.source, URIRef(row["scientific_reference"])))
        provenance.add((witness, DCTERMS.description, Literal(row["rationale"], lang="en")))
        if "native" in row:
            native = URIRef(row["native"])
            if (original, DCTERMS.source, native) not in provenance:
                raise ValueError(f"Missing source origin for retired concept: {original}")
            provenance.add((witness, DCTERMS.identifier, Literal(row["snapshot_sha256"])))
            provenance.add((witness, DCTERMS.references, native))
        else:
            provenance.add((witness, DCTERMS.identifier, Literal(row["review_id"])))
        if row["decision"] == "duplicate":
            provenance.add((witness, DCTERMS.type, Literal("reviewed canonical duplicate")))
        for triple in triples:
            graph.add(triple)
            statement = statement_for(triple)
            provenance.add((statement, RDF.type, RDF.Statement))
            provenance.add((statement, PROV.wasDerivedFrom, witness))
            for field, value in zip((RDF.subject, RDF.predicate, RDF.object), triple):
                provenance.add((statement, field, value))
    return {"retired_duplicates": sum(row["decision"] == "duplicate" for row in rows),
            "reviewed_migrations": len(rows), "ledger_sha256": checksum(LEDGER)}


def lifecycle_errors(graph, provenance):
    """Check the projected lifecycle without needing access to authoring files."""
    errors = []
    for former in graph.subjects(OWL.deprecated, Literal(True)):
        marker = former, OWL.deprecated, Literal(True)
        witnesses = [w for w in provenance.objects(statement_for(marker), PROV.wasDerivedFrom)
                     if provenance.value(w, V.identityAction)]
        copies = [(former, DCTERMS.isReplacedBy, target)
                  for target in graph.objects(former, DCTERMS.isReplacedBy)]
        if len(witnesses) != 1:
            errors.append(f"Missing unique reviewed identity action: {former}")
            continue
        witness, = witnesses
        actions = set(provenance.objects(witness, V.identityAction))
        action = next(iter(actions)) if len(actions) == 1 else None
        limits = next((limits for name, limits in CARDINALITIES.items() if V[name] == action), None)
        if limits is None or not (limits[0] <= len(copies) and (limits[1] is None or len(copies) <= limits[1])):
            errors.append(f"Invalid target cardinality for identity action: {former}")
        if (not provenance.value(witness, DCTERMS.source) or not provenance.value(witness, DCTERMS.description)
                or any((statement_for(triple), PROV.wasDerivedFrom, witness) not in provenance
                       or any((statement_for(triple), field, value) not in provenance
                              for field, value in zip((RDF.subject, RDF.predicate, RDF.object), triple))
                       for triple in [marker, *copies])):
            errors.append(f"Incomplete migration provenance: {former}")
    return errors


def replay(offline=False):
    catalog = registry()
    stores = {}
    rows = reviewed_migrations()
    verified = 0
    for row in rows:
        if "source" not in row:
            continue
        key = row["source"]
        if key not in stores:
            source = catalog[key]
            name = ingest(source, offline)["graph"]
            stores[key] = staged(source), name
        store, name = stores[key]
        answer = store.query(f"ASK {{ GRAPH <{name}> {{ {row['source_evidence']} }} }}")
        if not bool(answer):
            raise ValueError(f"Native identity witness differs: {row['native']}")
        verified += 1
    return {"verified_migrations": verified, "editorial_migrations": len(rows) - verified}
