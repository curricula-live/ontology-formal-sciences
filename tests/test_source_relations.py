from pyoxigraph import NamedNode, RdfFormat, Store
import pytest
from rdflib import Graph, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import C, G, ROOT, V, read, registry, write
from pipeline.curate import authored, reviewed
from pipeline.curate import relations


def test_extractor_preserves_restriction_shape_and_graph():
    store = Store()
    graph = "urn:test:stage"
    store.load(input=f"""
        @prefix o: <{relations.OBO}> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        o:STATO_0000001 rdfs:subClassOf [
            a owl:Restriction ; owl:onProperty o:OBI_0000293 ; owl:someValuesFrom o:STATO_0000002
        ] .
        o:STATO_0000003 rdfs:subClassOf [
            a owl:Restriction ; owl:onProperty o:OBI_0000293 ; owl:allValuesFrom o:STATO_0000002
        ] .
        o:STATO_0000004 rdfs:subClassOf [
            a owl:Restriction ; owl:onProperty o:OBI_0000293 ; owl:someValuesFrom o:OBI_0000001
        ] .
        o:STATO_0000001 rdfs:subClassOf o:STATO_0000005 .
        """, format=RdfFormat.TURTLE, to_graph=NamedNode(graph))
    profile = relations.PROFILES["stato"]
    assert relations.extract(store, graph, profile) == [("0000001", "input", "0000002")]
    assert relations.extract(store, "urn:test:other", profile) == []


def test_approved_source_projection_keeps_evidence_and_rejections():
    canonical, provenance = authored()
    catalog = registry()
    mappings = reviewed(catalog, canonical, provenance)
    result = relations.apply_relations(catalog, canonical, mappings, provenance)
    accepted = (C["stato-0000073"], V.usesReferenceDistribution, C["stato-0000060"])
    assert accepted in canonical
    statement = relations.statement_for(accepted)
    witness, = provenance.objects(statement, PROV.wasDerivedFrom)
    assert str(provenance.value(witness, DCTERMS.type)) == "subclass-some"
    assert provenance.value(witness, RDF.predicate) == URIRef(relations.OBO + "OBI_0000293")
    assert (C["stato-0000077"], V.usesReferenceDistribution, C["normal-distribution"]) not in canonical
    assert (C["mathmoddb-q6684551"], V.appliesToModel, C["mathmoddb-q6675333"]) in canonical
    assert (C["mathmoddb-q6675333"], V.appliesToModel, C["mathmoddb-q6684551"]) not in canonical
    assert result["ontomath-pro"].get("approved", 0) == 0


def test_review_gate_rejects_revision_and_ambiguous_identity(tmp_path, monkeypatch):
    canonical, provenance = authored()
    catalog = registry()
    mappings = reviewed(catalog, canonical, provenance)
    monkeypatch.setattr(relations, "LEDGERS", tmp_path)
    for name in ("stato.json", "stato-decisions.json"):
        write(tmp_path / name, read(ROOT / "reviews/relations" / name))
    external = URIRef(relations.OBO + "STATO_0000060")
    mappings.add((C["normal-distribution"], SKOS.exactMatch, external))
    with pytest.raises(ValueError, match="ambiguous endpoints"):
        relations.apply_relations(catalog, canonical, mappings, Graph())

    evidence = tmp_path / "stato.json"
    record = read(evidence)
    record["sha256"] = "stale"
    write(evidence, record)
    with pytest.raises(ValueError, match="rights or revision"):
        relations.apply_relations(catalog, canonical, mappings, Graph())


def test_universal_restriction_cannot_be_promoted_by_an_approval(tmp_path, monkeypatch):
    canonical, provenance = authored()
    catalog = registry()
    mappings = reviewed(catalog, canonical, provenance)
    monkeypatch.setattr(relations, "LEDGERS", tmp_path)
    name = "ontomath-pro"
    evidence = read(ROOT / f"reviews/relations/{name}.json")
    write(tmp_path / f"{name}.json", evidence)
    approval = {key: evidence[key] for key in ("sha256", "profile_sha256")}
    approval["decisions"] = {"approved": [["E285", "P1", "E1030", "Test invalid promotion"]]}
    write(tmp_path / f"{name}-decisions.json", approval)
    with pytest.raises(ValueError, match="No sound relation projection"):
        relations.apply_relations(catalog, canonical, mappings, Graph())


def test_scoped_projection_reuses_existing_subject_and_preserves_original_role():
    canonical, provenance = authored()
    catalog = registry()
    mappings = reviewed(catalog, canonical, provenance)
    stats = relations.apply_relations(catalog, canonical, mappings, provenance)
    edge = (C["mathmoddb-q6775615"], V.hasFormulationComponent, C["ontomath-pro-e3187"])
    assert edge in canonical
    witness, = provenance.objects(relations.statement_for(edge), PROV.wasDerivedFrom)
    projection, = provenance.objects(witness, PROV.wasDerivedFrom)
    native = URIRef(relations.MARDI + "Q6775613")
    assert provenance.value(witness, RDF.object) == native
    assert provenance.value(projection, RDF.object) == native
    assert (C["ontomath-pro-e3187"], SKOS.exactMatch, native) not in mappings
    cross = (C["mathmoddb-q6684606"], V.hasFormulationComponent, C["poisson-log-likelihood"])
    assert cross in canonical
    assert stats["mathmoddb"]["endpoint_resolution"]["reviewed_projections"] == 5
    assert (C["mathmoddb-q6822086"], RDF.type, SKOS.Concept) not in canonical
    assert (C["mathmoddb-q6822091"], V.hasFormulationComponent, C["mathmoddb-q6822086"]) not in canonical
    assert (C["partial-least-squares-regression"], V.producesEstimate, C["stato-0000565"]) in canonical
    assert (C["partial-least-squares-regression"], V.producesEstimate, C["stato-0000569"]) not in canonical

    for source in stats.values():
        assert sum(source["candidate_actions"].values()) == source["extracted"]
    assert stats["mathmoddb"]["candidate_actions"]["exclude_profile_role"] > 0
    assert stats["mathmoddb"]["candidate_causes"]["out_of_scope_endpoint_role"] == (
        stats["mathmoddb"]["candidate_actions"]["exclude_profile_role"]
    )
    assert stats["ontomath-pro"]["candidate_causes"]["unsupported_relation_semantics"] == (
        stats["ontomath-pro"]["candidate_actions"]["outside_relation_profile"]
    )
    assert stats["mathmoddb"]["candidate_actions"]["exclude_reviewed_application"] > 0
    assert stats["ontomath-pro"]["candidate_actions"]["outside_relation_profile"] == 71


def test_lexical_suggestion_remains_pending():
    from pipeline.curate import endpoints
    from rdflib import Literal
    from pipeline.common import D

    graph = Graph()
    graph.add((C["kernel-method"], RDF.type, SKOS.Concept))
    graph.add((C["kernel-method"], SKOS.prefLabel, Literal("Kernel method", lang="en")))
    graph.add((C["kernel-method"], SKOS.inScheme, D.statistics))
    info = {"labels": ["Kernel method"], "role": "class", "parents": [], "definition_terms": []}
    result = endpoints.triage("stato", relations.OBO + "STATO_", {"edges": []},
                              {"0000540": info}, {}, graph, Graph())
    assert result["0000540"]["state"] == "review_mapping"
    assert result["0000540"]["canonical"] == []
    assert result["0000540"]["suggestions"][0]["label_match"]


def test_ml_schema_preserves_workflow_roles_and_existential_evidence():
    canonical, provenance = authored()
    catalog = registry()
    mappings = reviewed(catalog, canonical, provenance)
    stats = relations.apply_relations(catalog, canonical, mappings, provenance)
    projection = (C["mls-executable-implementation"], V.implementsAlgorithm, C.algorithm)
    assert projection in canonical
    witness, = provenance.objects(relations.statement_for(projection), PROV.wasDerivedFrom)
    assert provenance.value(witness, RDF.object) == URIRef(relations.MLS + "Algorithm")
    assert str(provenance.value(witness, DCTERMS.type)) == "subclass-some"
    assert (C["mls-evaluation-specification"], V.hasEvaluationComponent, C["mls-evaluation-measure"]) in canonical
    assert (C["mls-run"], V.documentsEvaluationOutput, C["mls-model-evaluation-result"]) in canonical
    assert stats["ml-schema"]["approved"] == 6
    assert stats["ml-schema"]["rejected"] == 2
