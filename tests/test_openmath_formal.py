import xml.etree.ElementTree as ET

import pytest
from rdflib import RDF, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, ROOT, V, read, registry, write
from pipeline.curate import authored, openmath
from pipeline.curate.relations import statement_for


def test_formal_shape_retains_a_quantified_guard():
    fmp = ET.fromstring("""
    <FMP xmlns:o="http://www.openmath.org/OpenMath">
      <o:OMOBJ>
        <o:OMBIND><o:OMS cd="quant1" name="forall"/><o:OMBVAR><o:OMV name="x"/></o:OMBVAR>
          <o:OMA><o:OMS cd="logic1" name="implies"/><o:OMV name="p"/><o:OMV name="q"/></o:OMA>
        </o:OMBIND>
      </o:OMOBJ>
    </FMP>
    """)
    assert openmath.shape(fmp) == "quant1:forall/logic1:implies"
    assert openmath.expression_regions(fmp) == {"guard": [], "body": []}


def test_openmath_statement_provenance_preserves_guard_and_source_symbol():
    graph, prov = authored()
    report = openmath.apply_formal_properties(registry()["openmath"], graph, prov)
    triple = C["scalar-division"], V.hasProperty, C["nonzero-scalar-self-division"]
    assert triple in graph
    witness, = prov.objects(statement_for(triple), PROV.wasDerivedFrom)
    assert str(prov.value(witness, V.sourceExpressionShape)) == "quant1:forall/logic1:implies"
    assert len(str(prov.value(witness, V.sourceExpressionDigest))) == 64
    assert prov.value(witness, PROV.hadPrimarySource) == URIRef("http://www.openmath.org/cd/arith1.ocd")
    assert (witness, DCTERMS.references, URIRef("http://www.openmath.org/cd/arith1#divide")) in prov
    assert report["dispositions"]["rejected"] >= 7
    assert report["expression_symbol_relations"] == 167
    assert report["scientific_property_relations"] == 63
    expression = C["nonzero-scalar-self-division"], V.containsSymbol, C["scalar-division"]
    former = C["nonzero-scalar-self-division"], V.uses, C["scalar-division"]
    assert expression in graph and former not in graph
    assert (statement_for(expression), PROV.wasRevisionOf, statement_for(former)) in prov
    assert not list(prov.subjects(DCTERMS.references, URIRef("http://www.openmath.org/cd/set1#notsubset")))


@pytest.mark.parametrize("defect", ["license", "unwitnessed-symbol", "unreviewed-guard", "unresolved-symbol"])
def test_review_gate_rejects_drift(tmp_path, monkeypatch, defect):
    evidence = read(openmath.EVIDENCE)
    decisions = read(openmath.DECISIONS)
    if defect == "license":
        evidence["dictionaries"]["logic1"]["license_notice_sha256"] = "incorrect"
    elif defect == "unwitnessed-symbol":
        decisions["decisions"]["logic1:not/1"]["uses"].append("arith1:plus")
    elif defect == "unreviewed-guard":
        del decisions["decisions"]["set1:prsubset/1"]["guard_properties"]
    else:
        evidence["properties"]["logic1:not/1"]["symbols"].append("missing:unknown")
    monkeypatch.setattr(openmath, "EVIDENCE", tmp_path / "evidence.json")
    monkeypatch.setattr(openmath, "DECISIONS", tmp_path / "reviews.json")
    write(openmath.EVIDENCE, evidence)
    write(openmath.DECISIONS, decisions)
    graph, prov = authored()
    with pytest.raises(ValueError, match="license witness|bound source occurrences|explicit guard scope|Invalid OpenMath statement"):
        openmath.apply_formal_properties(registry()["openmath"], graph, prov)
