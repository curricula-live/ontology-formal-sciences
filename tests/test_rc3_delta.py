"""Review-driven rc.3 changes are additive and retain predecessor histories."""
from copy import deepcopy
from rdflib import Dataset
from rdflib.namespace import DCTERMS
from pipeline.common import C, G, ROOT, V, read, checksum
from pipeline.curate.relations import statement_for
from pipeline.contract import validate_manifest

def _graphs():
    ds=Dataset()
    ds.parse(ROOT/"dist/formal-sciences.nq",format="nquads")
    return ds.graph(G.asserted),ds.graph(G.provenance)

def test_covariance_pca_mean_centering_is_scoped_on_original_statements():
    graph,provenance=_graphs()
    for subject,predicate,object_ in [
        ("svd-principal-component-analysis","computes","eigenvector"),
        ("svd-principal-component-analysis","uses","singular-value-decomposition"),
        ("principal-component-analysis","uses","singular-value-decomposition"),
    ]:
        triple=(C[subject],V[predicate],C[object_])
        assert triple in graph
        stmt=statement_for(triple)
        notes=[str(v).lower() for v in provenance.objects(stmt,DCTERMS.description)]
        assert any("center" in note for note in notes), (triple,notes)

def test_dpda_previous_scope_is_preserved_until_separately_approved_revision():
    graph,provenance=_graphs()
    triple=(C["opencs-c42922"],V.recognizesExactly,C["deterministic-context-free-language"])
    assert triple in graph
    stmt=statement_for(triple)
    notes=[str(x) for x in provenance.objects(stmt,DCTERMS.description)]
    assert any("final state" in x for x in notes)
    ledger=read(ROOT/"reviews/quality/rc3-delta.json")
    assert any("prefix-free" in issue for issue in ledger["known_limitations"])

def test_evidence_only_source_rights_unresolved_and_notice_pinned():
    manifest=read(ROOT/"dist/manifest.json")
    rights=manifest["rights"]
    notice=rights["distribution_notice"]
    assert notice["sha256"]==checksum(ROOT/"NOTICE.md")
    for source in ("passage:openstax-conditional","passage:d2l-gradient"):
        assert rights["sources"][source]["disposition"]=="unresolved"
        assert rights["sources"][source]["channels"]==[
            "citations","passage-fingerprints","independent-editorial-assertions"
        ]
        assert source in notice["applies_to"]
    txt=(ROOT/"NOTICE.md").read_text(encoding="utf-8")
    assert "CC BY-NC-SA 4.0" in txt
    assert "CC BY-SA 4.0" in txt

def test_consumer_accepts_previous_notice_profile():
    manifest=read(ROOT/"dist/manifest.json")
    previous=deepcopy(manifest)
    previous["rights"]["distribution_notice"]["applies_to"]=[
        "native:openmath","native:stato","passage:opendsa"
    ]
    assert validate_manifest(previous) is previous
