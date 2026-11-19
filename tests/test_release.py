import gzip
import pytest
from rdflib import RDF, RDFS, SKOS, OWL, Literal, URIRef, Graph, Dataset
from rdflib.namespace import PROV
from pipeline.common import ROOT, C, G, V, read, checksum, registry
from pipeline.curate import authored, reviewed
from pipeline.publish import build
from pipeline.reason import reason
from pipeline.validate import check
from pipeline.fetch import fetch
from pipeline.parse import ingest
from pipeline.align import candidates


@pytest.fixture
def canonical():
    return authored()[0]


def test_bad_shacl_fixture():
    result = check(Graph().parse(ROOT/"tests/fixtures/bad-label.ttl"))
    assert not result["conforms"] and "UniqueLang" in str(result["findings"])


@pytest.mark.parametrize("p,o", [(V.uses,C.missing),(OWL.sameAs,C.algorithm),(SKOS.broader,C.algorithm)])
def test_unsafe_relations(canonical,p,o):
    canonical.add((C.algorithm,p,o))
    assert not check(canonical)["conforms"]


def test_reconciliation(canonical):
    mapping = reviewed(registry(),canonical,Graph())
    assert len(list(mapping.objects(C["graph-theory"],SKOS.exactMatch)))>=2
    for row in read(ROOT/"reviews/rejected/mappings.json"):
        assert (URIRef(row["canonical"]),None,URIRef(row["external"])) not in mapping


def test_rights_and_version(canonical):
    for key,value in [("license","unverified"),("sha256","changed"),("allow_mapping",False)]:
        catalog = registry()
        catalog["opencs"][key] = value
        with pytest.raises(ValueError,match="Rights or evidence"):
            reviewed(catalog,canonical,Graph())


def test_concept_origin_and_ownership():
    graph,prov = authored()
    for concept in graph.subjects(RDF.type,SKOS.Concept):
        assert len(list(prov.objects(concept,PROV.wasDerivedFrom)))==1
    assert (None,RDF.predicate,V.uses) in prov


def test_inference_isolation(canonical):
    inf = reason(canonical)
    assert (C["graph-algorithm"],SKOS.narrower,C["dijkstra-s-algorithm"]) in inf
    assert (C["graph-algorithm"],SKOS.narrower,C["dijkstra-s-algorithm"]) not in canonical
    assert not set(inf) & set(canonical)
    assert not list(inf.triples((None,V.uses,None)))


def test_sparql(canonical):
    rows = {tuple(map(str,row)) for row in canonical.query((ROOT/"docs/cross-domain.rq").read_text())}
    assert ("Bayesian network","Directed acyclic graph") in rows
    assert ("Gradient descent","Derivative") in rows


def test_build_reproducibility(tmp_path):
    a,b = tmp_path/"one",tmp_path/"two"
    assert build(a)==build(b)
    for p in a.iterdir():
        assert p.read_bytes()==(b/p.name).read_bytes()
    ds=Dataset()
    ds.parse(a/"formal-sciences.nq",format="nquads")
    ttl=Graph().parse(a/"formal-sciences.ttl")
    assert set(ds.graph(G.asserted))==set(ttl)
    assert set(ds.graph(G.inferred))==set(reason(ttl))
    manifest=read(a/"manifest.json")
    for name,digest in manifest["artifacts"].items():
        assert checksum(a/name)==digest


def test_real_offline_input(tmp_path,monkeypatch):
    import importlib
    f=importlib.import_module("pipeline.fetch")
    parser=importlib.import_module("pipeline.parse")
    for mod in (f,parser):
        monkeypatch.setattr(mod,"ROOT",tmp_path)
    s=registry()["ml-schema"]
    directory=tmp_path/"sources/ml-schema/original"
    directory.mkdir(parents=True)
    (directory/"snapshot.gz").write_bytes((ROOT/"sources/ml-schema/original/snapshot.gz").read_bytes())
    first=ingest(s,True)
    assert first==ingest(s,True)
    assert first["triples"]==read(ROOT/"sources/ml-schema/ingestion.json")["triples"]
    (directory/"snapshot").write_bytes(b"corrupt")
    (directory/"snapshot.gz").write_bytes(gzip.compress(b"also corrupt"))
    with pytest.raises(ValueError,match="checksum"):
        fetch(s,True)


def test_snapshot_attribution():
    for id,s in registry().items():
        if s.get("sha256"):
            r=read(ROOT/"sources"/id/"ingestion.json")
            assert s["attribution"] and s["license"] and r["triples"]>0
            assert r["sha256"]==s["sha256"]


def test_identity_and_cycle_policy(canonical):
    canonical.add((C["first-order-logic"],SKOS.related,C["propositional-logic"]))
    canonical.add((C["propositional-logic"],SKOS.related,C["first-order-logic"]))
    assert check(canonical)["conforms"]
    canonical.add((C["first-order-logic"],SKOS.prefLabel,Literal("Predicate logic",lang="en")))
    assert not check(canonical)["conforms"]


def test_offline_normalization_and_candidates(tmp_path,monkeypatch):
    from importlib import import_module
    import json
    from pipeline.normalize import label_key
    from pipeline.normalize.index import normalize
    for module in ("pipeline.parse","pipeline.fetch","pipeline.align","pipeline.normalize.index"):
        monkeypatch.setattr(import_module(module),"ROOT",tmp_path)
    assert label_key("  Ｒing  THEORY ")=="ring theory"
    for state in ("approved","rejected"):
        p=tmp_path/"reviews"/state/"mappings.json"
        p.parent.mkdir(parents=True)
        p.write_text("[]")
    raw=tmp_path/"sources"/"small"/"original"/"snapshot"
    raw.parent.mkdir(parents=True)
    raw.write_text('<https://example.org/ring> <http://www.w3.org/2000/01/rdf-schema#label> "Ring"@en .')
    source=dict(id="small",sha256=checksum(raw),format="nt",url="https://example.org/ring.nt",
                validation_query="ASK { GRAPH ?g { <https://example.org/ring> ?p ?o } }")
    graph=Graph()
    for term in ("ring-algebra","ring-jewelry"):
        graph.add((C[term], RDF.type, SKOS.Concept))
        graph.add((C[term],SKOS.prefLabel,Literal("Ring",lang="en")))
    result=candidates(source,graph,True)
    assert {r["canonical"] for r in result}=={str(C["ring-algebra"]),str(C["ring-jewelry"])}
    assert {r["state"] for r in result}=={"pending"}
    assert normalize(source,True)["label_keys"]==1
    source["validation_query"]="ASK { GRAPH ?g { <https://example.org/absent> ?p ?o } }"
    with pytest.raises(ValueError,match="competency query"):
        ingest(source,True)


def test_invalid_rdf_fails_before_staging(tmp_path,monkeypatch):
    from importlib import import_module
    for module in ("pipeline.parse","pipeline.fetch"):
        monkeypatch.setattr(import_module(module),"ROOT",tmp_path)
    p=tmp_path/"sources"/"broken"/"original"/"snapshot"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"this is not Turtle")
    s=dict(id="broken",sha256=checksum(p),format="turtle",url="https://example.org/broken.ttl")
    with pytest.raises(SyntaxError):
        ingest(s,True)
    assert not list((tmp_path/".cache").rglob("report.json"))


def test_every_admitted_concept_is_connected(canonical):
    from pipeline.validate import RELATIONS
    from collections import defaultdict
    neighbors=defaultdict(set)
    for s,p,o in canonical:
        if p in RELATIONS:
            neighbors[s].add(o)
            neighbors[o].add(s)
    visited=set()
    queue=[C.mathematics]
    while queue:
        item=queue.pop()
        if item not in visited:
            visited.add(item)
            queue.extend(neighbors[item]-visited)
    assert visited==set(canonical.subjects(RDF.type,SKOS.Concept))


def test_sat_competency(canonical):
    assert set(canonical.subjects(V.solves,C["boolean-satisfiability"])) & set(canonical.subjects(V.uses,C["unit-propagation"]))=={C["dpll-algorithm"],C["conflict-driven-clause-learning"]}


def test_immutable_review_ids():
    ids=[]
    for state in ("approved","rejected"):
        for row in read(ROOT/"reviews"/state/"mappings.json"):
            ids.append(row["id"])
    assert len(set(ids))==len(ids)
