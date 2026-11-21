"""Replay the statistical subject selection from the pinned native STATO classes."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import re

from rdflib import Graph, Literal, RDF, SKOS

from pipeline.common import C, D, ROOT, read, registry, write
from pipeline.normalize import label_key
from pipeline.parse import ingest, staged

SOURCE = "stato"
NATIVE = "http://purl.obolibrary.org/obo/STATO_000"
CLASS_ID = re.compile(re.escape(NATIVE) + r"([0-9]{4})")
MODULE_DIR = "domains/statistics/modules/batches"
LEDGER = "reviews/approved/batches/stato.json"
POLICY = "sources/stato/admission.json"
LICENSE = "CC-BY-3.0 (embedded imports have separate notices)"
POLICY_NAME = "Native STATO statistical subjects, reviewed class families and hierarchy exceptions"
PREFIXES = f"""# Selected and adapted from STATO 1.5 by ISA-tools/STATO, CC BY 3.0.
# See sources/stato/README.md for license, authorship and the pinned revision.
@prefix c: <{C}> .
@prefix scheme: <{D}> .
@prefix skos: <{SKOS}> .
"""


def extract_classes(store, graph):
    """Return English labels and named native superclass links for the selected graph."""
    if not store.query(f"""
        ASK {{ GRAPH <{graph}> {{
            <http://purl.obolibrary.org/stato.owl> <http://purl.org/dc/terms/license> ?license .
            FILTER(STR(?license) = "http://creativecommons.org/licenses/by/3.0/")
        }} }}
    """):
        raise ValueError("STATO ontology does not declare the reviewed CC BY 3.0 license")
    labels, parents = defaultdict(set), defaultdict(set)
    deprecated = set()
    query = f"""
        SELECT DISTINCT ?term ?label ?parent ?deprecated WHERE {{ GRAPH <{graph}> {{
            ?term a <http://www.w3.org/2002/07/owl#Class> .
            FILTER(STRSTARTS(STR(?term), "{NATIVE}"))
            OPTIONAL {{
                ?term <http://www.w3.org/2000/01/rdf-schema#label> ?label .
                FILTER(LANG(?label) IN ("", "en"))
            }}
            OPTIONAL {{
                ?term <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
                FILTER(STRSTARTS(STR(?parent), "{NATIVE}"))
            }}
            OPTIONAL {{ ?term <http://www.w3.org/2002/07/owl#deprecated> ?deprecated }}
        }} }}
    """
    for row in store.query(query):
        term = CLASS_ID.fullmatch(row["term"].value)
        if term is None:
            continue
        term_id = term[1]
        parents[term_id]
        if row["label"] is not None:
            labels[term_id].add((row["label"].language == "en", row["label"].value.strip()))
        if row["parent"] is not None and (parent := CLASS_ID.fullmatch(row["parent"].value)):
            parents[term_id].add(parent[1])
        if row["deprecated"] is not None and row["deprecated"].value in {"true", "1"}:
            deprecated.add(term_id)
    return labels, parents, deprecated


def families_for(parents, families):
    children = defaultdict(set)
    for term, supers in parents.items():
        for parent in supers:
            children[parent].add(term)
    result = {}
    for family, roots in families.items():
        unseen_roots = set(roots) - parents.keys()
        if unseen_roots:
            raise ValueError(f"STATO family {family} has absent native roots: {sorted(unseen_roots)}")
        found = set()
        frontier = set(roots)
        while frontier:
            term = frontier.pop()
            found.add(term)
            frontier.update(children[term] - found)
        overlap = found & result.keys()
        if overlap:
            raise ValueError(f"Multiple STATO module owners: {sorted(overlap)}")
        result.update(dict.fromkeys(found, family))
    return result


def matching_label(text):
    return "".join(char for char in label_key(text) if char.isalnum())


def authored_concepts():
    graph = Graph()
    for path in sorted(ROOT.glob("domains/*/modules/**/*.ttl")):
        if "batches" not in path.parts:
            graph.parse(path)
    return graph


def review_terms(labels, parents, deprecated, policy, authored):
    owners = families_for(parents, policy["families"])
    exclusions = Counter({"native class outside the selected families": len(parents) - len(owners)})
    excluded_terms = set()
    for reason, terms in policy["exclusions"].items():
        if (set(terms) - owners.keys()) or (set(terms) & excluded_terms):
            raise ValueError(f"Invalid STATO exclusions for {reason}: {sorted(terms)}")
        excluded_terms.update(terms)
        exclusions[reason] = len(terms)
    pending = dict(policy["pending"])
    if (pending.keys() - owners.keys()) or (pending.keys() & excluded_terms):
        raise ValueError("STATO pending decisions must name distinct in-scope native classes")
    exclusions["deprecated native class"] = len(deprecated & owners.keys() - excluded_terms)
    omitted = excluded_terms | deprecated | pending.keys()
    reviewed = dict(policy["reuse"])
    if reviewed.keys() - owners.keys() or reviewed.keys() & omitted:
        raise ValueError("Reused STATO subjects must be in scope and approved")
    if len(set(reviewed.values())) != len(reviewed):
        raise ValueError("Reused STATO subjects must have distinct authored concepts")
    for term, canonical in reviewed.items():
        if (C[canonical], SKOS.inScheme, D.statistics) not in authored:
            raise ValueError(f"STATO reference {term} is not an existing statistics concept: {canonical}")

    authored_labels = {
        matching_label(str(label))
        for concept in authored.subjects(RDF.type, SKOS.Concept)
        for predicate in (SKOS.prefLabel, SKOS.altLabel)
        for label in authored.objects(concept, predicate)
    }
    proposed = {}
    candidate_labels = defaultdict(set)
    for term in sorted(owners.keys() - omitted - reviewed.keys()):
        choices = {name for english, name in labels.get(term, ()) if english and name}
        if not choices:
            choices = {name for _, name in labels.get(term, ()) if name}
        text = policy["labels"].get(term)
        if len(choices) != 1:
            pending[term] = "Missing or ambiguous source label."
            continue
        if not text:
            label = next(iter(choices))
            text = label[:1].upper() + label[1:]
        key = matching_label(text)
        if key in authored_labels or (C["stato-000" + term], RDF.type, SKOS.Concept) in authored:
            pending[term] = "Potential overlap with an existing authored concept."
            continue
        candidate_labels[key].add(term)
        proposed[term] = text

    for duplicates in candidate_labels.values():
        if len(duplicates) > 1:
            for term in duplicates:
                del proposed[term]
                pending[term] = "Ambiguous label among the selected native STATO classes."
    return owners, proposed, reviewed, pending, exclusions


def generate(source, labels, parents, deprecated, policy, authored):
    owners, proposed, identities, pending, exclusions = review_terms(labels, parents, deprecated, policy, authored)
    identities.update({term: f"stato-000{term}" for term in proposed})
    modules = defaultdict(list)
    for term, label in proposed.items():
        family = owners[term]
        if term in policy["parents"]:
            targets = [identities[p] if p.isdecimal() else p for p in policy["parents"][term]]
        else:
            targets = [identities[p] for p in parents[term] & identities.keys()]
            if not targets and term in policy["families"][family]:
                targets = [policy["families"][family][term]]
        for target in targets:
            if target not in identities.values() and (C[target], SKOS.inScheme, D.statistics) not in authored:
                raise ValueError(f"Unknown statistics parent for STATO {term}: {target}")
        if not targets:
            raise ValueError(f"No accepted parent for STATO {term}; review its hierarchy")
        broader = ", ".join(f"c:{p}" for p in sorted(set(targets)))
        modules[family].append(
            f"c:{identities[term]} a skos:Concept ;\n"
            f"    skos:prefLabel {Literal(label, lang='en').n3()} ;\n"
            f"    skos:inScheme scheme:statistics ;\n"
            f"    skos:broader {broader} .\n"
        )
    files = {
        f"{MODULE_DIR}/stato-{family}.ttl": PREFIXES + "\n" + "\n".join(terms)
        for family, terms in sorted(modules.items())
    }
    ledger = {
        "source": SOURCE,
        "sha256": source["sha256"],
        "revision": source["revision"],
        "license": LICENSE,
        "policy": POLICY_NAME,
        "eligible": len(identities) + len(pending),
        "pending": len(pending),
        "identities": {NATIVE + term: canonical for term, canonical in identities.items()},
        "exclusions": {reason: count for reason, count in exclusions.items() if count},
        "modules": {path: sha256(content.encode()).hexdigest() for path, content in files.items()},
    }
    return files, ledger, {NATIVE + term: reason for term, reason in sorted(pending.items())}


def _snapshot(offline):
    source = registry()[SOURCE]
    policy = read(ROOT / POLICY)
    if source["sha256"] != policy["sha256"] or source["license"] != LICENSE:
        raise ValueError("Review the STATO admission policy and rights for the new source revision")
    report = ingest(source, offline)
    with_source = extract_classes(staged(source), report["graph"])
    return generate(source, *with_source, policy, authored_concepts())


QUEUE = "reviews/pending/batches/stato.json"


def replay(offline=False):
    """Reproduce and verify the reviewed outputs without writing tracked files."""
    files, ledger, pending = _snapshot(offline)
    disk_files = {str(path.relative_to(ROOT)) for path in (ROOT / MODULE_DIR).glob("stato-*.ttl")}
    if files.keys() != disk_files or any(
        (ROOT / path).read_bytes() != content.encode() for path, content in files.items()
    ):
        raise ValueError("STATO modules differ from the pinned admission replay")
    if ledger != read(ROOT / LEDGER):
        raise ValueError("STATO ledger differs from the pinned admission replay")
    if pending != read(ROOT / QUEUE):
        raise ValueError("STATO review queue differs from the pinned admission replay")
    return {key: ledger[key] for key in ("source", "eligible", "pending", "exclusions")} | {
        "admitted": len(ledger["identities"]), "modules": len(files)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Require the local checksum-pinned snapshot")
    parser.add_argument("--write-proposal", action="store_true", help="Write proposed modules and approval ledger for review")
    args = parser.parse_args()
    if args.write_proposal:
        files, ledger, pending = _snapshot(args.offline)
        for path, content in files.items():
            path = ROOT / path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode())
        write(ROOT / LEDGER, ledger)
        write(ROOT / QUEUE, pending)
        for iri, reason in pending.items():
            print(f"{iri} pending — {reason}")
    else:
        print(replay(args.offline))
        return
    print(f"STATO accepted {len(ledger['identities'])}, pending {ledger['pending']}, modules {len(ledger['modules'])}")


if __name__ == "__main__":
    main()
