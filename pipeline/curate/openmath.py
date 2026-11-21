"""Review formal mathematical properties from the pinned OpenMath dictionaries."""
from collections import Counter
from hashlib import sha256
from pathlib import PurePosixPath
import tarfile
import xml.etree.ElementTree as ET

from rdflib import Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, ROOT, V, checksum, read, registry, write
from pipeline.curate.relations import statement_for
from pipeline.fetch import fetch
from pipeline.parse import ingest

SOURCE = "openmath"
CD = "{http://www.openmath.org/OpenMathCD}"
OM = "{http://www.openmath.org/OpenMath}"
SYMBOL_BASE = "http://www.openmath.org/cd/"
NOTICE = "338d5f720b8b993a44729e4aafb0abc15017dc79488b347e78f3582a2870c98d"
OFFICIAL = {
    "alg1", "arith1", "bigfloat1", "calculus1", "complex1", "fns1", "fns2",
    "integer1", "interval1", "linalg1", "logic1", "multiset1", "nums1", "quant1",
    "relation1", "rounding1", "s_data1", "s_dist1", "set1", "setname1", "transc1",
    "veccalc1",
}
DICTIONARIES = {f"cd/Official/{name}.ocd": "official" for name in OFFICIAL} | {
    "cd/experimental/combinat1.ocd": "experimental"
}
EVIDENCE = ROOT / "reviews/formal-properties/openmath.json"
DECISIONS = ROOT / "reviews/formal-properties/openmath-decisions.json"


def symbol_iri(key):
    dictionary, symbol = key.split(":")
    return URIRef(f"{SYMBOL_BASE}{dictionary}#{symbol}")


def shape(fmp):
    """Keep binder, connective, and application structure at the top level."""
    if len(fmp) != 1:
        return "unsupported"
    expression = fmp[0]
    if expression.tag == OM + "OMOBJ":
        if len(expression) != 1:
            return "unsupported"
        expression = expression[0]
    steps = []
    while expression.tag == OM + "OMBIND" and len(expression) == 3 and expression[0].tag == OM + "OMS":
        operator = expression[0]
        steps.append(f"{operator.get('cd')}:{operator.get('name')}")
        expression = expression[2]
    if expression.tag != OM + "OMA" or len(expression) < 2 or expression[0].tag != OM + "OMS":
        return "unsupported"
    operator = expression[0]
    return "/".join([*steps, f"{operator.get('cd')}:{operator.get('name')}"])


def symbol_keys(expression):
    return {f"{ref.get('cd')}:{ref.get('name')}" for ref in expression.iter(OM + "OMS")}


def expression_regions(fmp):
    """Describe top-level implication premises separately from its consequence."""
    if len(fmp) != 1:
        return {}
    expression = fmp[0]
    if expression.tag == OM + "OMOBJ":
        if len(expression) != 1:
            return {}
        expression = expression[0]
    while expression.tag == OM + "OMBIND" and len(expression) == 3:
        expression = expression[2]
    if (expression.tag == OM + "OMA" and len(expression) == 3 and
            expression[0].tag == OM + "OMS" and
            expression[0].get("cd") == "logic1" and expression[0].get("name") == "implies"):
        return {"guard": sorted(symbol_keys(expression[1])),
                "body": sorted(symbol_keys(expression[2]))}
    return {"guard": [], "body": sorted(symbol_keys(expression))}


def extract(snapshot, source):
    dictionaries, declarations, properties = {}, {}, {}
    with tarfile.open(snapshot, "r|gz") as archive:
        for member in archive:
            relative = member.name.partition("/")[2]
            if not member.isfile() or not relative.startswith("cd/") or not relative.endswith(".ocd"):
                continue
            if relative not in DICTIONARIES:
                continue
            name = PurePosixPath(relative).stem
            with archive.extractfile(member) as stream:
                raw = stream.read()
            root = ET.fromstring(raw)
            notices = {" ".join("".join(comment.itertext()).split())
                       for comment in root.findall(CD + "CDComment")}
            if (root.tag != CD + "CD" or root.findtext(CD + "CDName") != name
                    or root.findtext(CD + "CDStatus") != DICTIONARIES[relative]
                    or root.findtext(CD + "CDBase", "").rstrip("/") + "/" != SYMBOL_BASE
                    or NOTICE not in {sha256(note.encode()).hexdigest() for note in notices}
                    or name in dictionaries):
                raise ValueError(f"OpenMath dictionary identity or approved notice changed: {relative}")
            dictionaries[name] = {
                "member": relative, "sha256": sha256(raw).hexdigest(),
                "license_notice_sha256": NOTICE, "status": DICTIONARIES[relative],
            }
            for definition in root.findall(CD + "CDDefinition"):
                symbol = definition.findtext(CD + "Name", "").strip()
                original = f"{name}:{symbol}"
                if not symbol or original in declarations:
                    raise ValueError(f"Missing or duplicate OpenMath symbol: {original}")
                declarations[original] = definition.findtext(CD + "Role", "unspecified")
                for ordinal, fmp in enumerate(definition.findall(CD + "FMP"), 1):
                    recognized_base = all(element.get("cdbase", SYMBOL_BASE).rstrip("/") + "/" == SYMBOL_BASE
                                          for element in fmp.iter())
                    symbols = symbol_keys(fmp)
                    properties[f"{original}/{ordinal}"] = {
                        "sha256": sha256(ET.canonicalize(ET.tostring(fmp, encoding="unicode")).encode()).hexdigest(),
                        "shape": shape(fmp) if recognized_base else "unsupported",
                        "symbols": sorted(symbols) if recognized_base else [],
                        "regions": expression_regions(fmp) if recognized_base else {},
                    }
    if set(dictionaries) != {PurePosixPath(path).stem for path in DICTIONARIES}:
        raise ValueError("Incomplete reviewed OpenMath dictionary slice")
    return {"sha256": source["sha256"], "revision": source["revision"],
            "dictionaries": dictionaries, "declarations": declarations, "properties": properties}


def verify_header(source, evidence):
    if (source["license"] != "per dictionary"
            or any(evidence[field] != source[field] for field in ("sha256", "revision"))):
        raise ValueError("Review the new OpenMath snapshot and dictionary licenses")
    expected = {PurePosixPath(path).stem: (path, status) for path, status in DICTIONARIES.items()}
    if evidence["dictionaries"].keys() != expected.keys():
        raise ValueError("OpenMath evidence contains dictionaries outside the rights review")
    for name, info in evidence["dictionaries"].items():
        if ((info["member"], info["status"]) != expected[name]
                or info["license_notice_sha256"] != NOTICE):
            raise ValueError(f"Missing selected OpenMath license witness: {name}")


def apply_formal_properties(source, graph, provenance):
    if not EVIDENCE.exists():
        if DECISIONS.exists():
            raise ValueError("OpenMath decisions require pinned formula evidence")
        return {}
    evidence, reviews = read(EVIDENCE), read(DECISIONS)
    verify_header(source, evidence)
    if reviews["sha256"] != source["sha256"]:
        raise ValueError("OpenMath formula decisions require renewed review")

    # Symbol bindings project a notation into a canonical subject for this
    # release. They are distinct from SKOS mappings of source topics.
    bindings = {}
    for native, decision in reviews["symbols"].items():
        canonical = C[decision["canonical"]]
        if (native not in evidence["declarations"] or not decision["scope"].strip()
                or (canonical, RDF.type, SKOS.Concept) not in graph):
            raise ValueError(f"Invalid OpenMath symbol binding: {native}")
        bindings[native] = canonical

    source_entity = URIRef(BASE + "source/openmath")
    provenance.add((source_entity, RDF.type, PROV.Entity))
    provenance.add((source_entity, DCTERMS.rights, Literal("Derived representation of selected OpenMath Content Dictionaries under their embedded derivative-work terms. The OpenMath Society and dictionary authors are credited. Published assertions refer to the original dictionaries.")))
    provenance.add((source_entity, PROV.hadPrimarySource, URIRef(source["url"])))
    counts, edges, laws, migrated = Counter(), set(), set(), set()
    for key, entry in evidence["properties"].items():
        review = reviews["decisions"].get(key)
        unrecognized = set(entry["symbols"]) - evidence["declarations"].keys()
        if review is None:
            if entry["shape"] == "unsupported":
                counts["unsupported_form"] += 1
            elif unrecognized:
                counts["unresolved_native_symbol"] += 1
            elif key.rsplit("/", 1)[0] not in bindings:
                counts["missing_symbol_binding"] += 1
            else:
                counts["review_statement"] += 1
            continue
        if entry["sha256"] != review["sha256"] or not review["rationale"].strip():
            raise ValueError(f"OpenMath statement evidence drifted: {key}")
        if review["state"] == "rejected":
            counts["rejected"] += 1
            continue
        if (review["state"] != "approved" or entry["shape"] == "unsupported" or unrecognized
                or not review["rationale"].strip()):
            raise ValueError(f"Invalid OpenMath statement decision: {key}")
        law = C[review["law"]]
        if (law, RDF.type, SKOS.Concept) not in graph:
            raise ValueError(f"Unknown OpenMath property subject: {law}")
        uses, properties = review["uses"], review["properties"]
        if not uses and not properties:
            raise ValueError(f"OpenMath approval has no projected edge: {key}")
        if not (set(uses) | set(properties)) <= (bindings.keys() & set(entry["symbols"])):
            raise ValueError(f"OpenMath projection lacks bound source occurrences: {key}")
        regions = entry["regions"]
        guard_only = set(regions.get("guard", ())) - set(regions.get("body", ()))
        if guard_only.intersection(properties) != set(review.get("guard_properties", ())):
            raise ValueError(f"OpenMath property target needs explicit guard scope: {key}")

        native, _ = key.rsplit("/", 1)
        cd_name = native.split(":")[0]
        cd_info = evidence["dictionaries"][cd_name]
        document = URIRef(f"{SYMBOL_BASE}{cd_name}.ocd")
        evidence_id = URIRef(BASE + "relation-evidence/openmath/" +
                             sha256(f"{source['sha256']}|{key}|{entry['sha256']}".encode()).hexdigest())
        provenance.add((evidence_id, RDF.type, PROV.Entity))
        provenance.add((evidence_id, DCTERMS.isPartOf, source_entity))
        provenance.add((evidence_id, PROV.hadPrimarySource, document))
        provenance.add((evidence_id, DCTERMS.identifier, Literal(source["sha256"])))
        provenance.add((evidence_id, DCTERMS.type, Literal("OpenMath formal mathematical property")))
        provenance.add((evidence_id, DCTERMS.title, Literal(f"{key} ({cd_info['status']})")))
        provenance.add((evidence_id, V.sourceExpressionDigest, Literal(entry["sha256"])))
        provenance.add((evidence_id, V.sourceExpressionShape, Literal(entry["shape"])))
        for symbol in regions.get("guard", []):
            provenance.add((evidence_id, V.sourceGuardSymbol, symbol_iri(symbol)))
        provenance.add((evidence_id, DCTERMS.description, Literal(review["rationale"], lang="en")))
        provenance.add((evidence_id, DCTERMS.references, symbol_iri(native)))
        facts = [(law, V.containsSymbol, bindings[symbol], symbol) for symbol in uses]
        facts.extend((bindings[symbol], V.hasProperty, law, symbol) for symbol in properties)
        for left, predicate, right, symbol in facts:
            triple = left, predicate, right
            if left == right:
                raise ValueError(f"Self-relation in OpenMath property projection: {key}")
            graph.add(triple)
            statement = statement_for(triple)
            provenance.add((statement, RDF.type, RDF.Statement))
            provenance.add((statement, DCTERMS.source, document))
            provenance.add((statement, PROV.wasDerivedFrom, evidence_id))
            for field, value in zip((RDF.subject, RDF.predicate, RDF.object), triple):
                provenance.add((statement, field, value))
            provenance.add((evidence_id, DCTERMS.references, symbol_iri(symbol)))
            if predicate == V.containsSymbol:
                former_triple = left, V.uses, right
                former = statement_for(former_triple)
                migrated.add(former_triple)
                provenance.add((statement, PROV.wasRevisionOf, former))
                provenance.add((former, RDF.type, RDF.Statement))
                provenance.add((former, DCTERMS.type, Literal("superseded interpretation")))
                provenance.add((former, DCTERMS.source, document))
                provenance.add((former, PROV.wasDerivedFrom, evidence_id))
                for field, value in zip((RDF.subject, RDF.predicate, RDF.object), former_triple):
                    provenance.add((former, field, value))
            edges.add(triple)
        laws.add(law)
        counts["approved"] += 1
    if set(reviews["decisions"]) - evidence["properties"].keys():
        raise ValueError("Unwitnessed OpenMath decisions")
    return {
        "properties": len(evidence["properties"]), "dictionaries": len(evidence["dictionaries"]),
        "symbols_bound": len(bindings), "canonical_laws": len(laws), "canonical_relations": len(edges),
        "scientific_property_relations": sum(p == V.hasProperty for _, p, _ in edges),
        "expression_symbol_relations": len(migrated),
        "dispositions": dict(counts), "evidence_sha256": checksum(EVIDENCE),
        "review_sha256": checksum(DECISIONS),
    }


def replay(offline=False, write_evidence=False):
    source = registry()[SOURCE]
    ingest(source, offline)
    record = extract(fetch(source, offline), source)
    if write_evidence:
        write(EVIDENCE, record)
        return {"dictionaries": len(record["dictionaries"]), "properties": len(record["properties"])}
    if record != read(EVIDENCE):
        raise ValueError("OpenMath formula extraction differs from pinned evidence")
    from pipeline.curate import authored

    graph, provenance = authored()
    return apply_formal_properties(source, graph, provenance)
