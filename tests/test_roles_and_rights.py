import pytest
from rdflib import Graph, Literal, RDF, SKOS

from pipeline.common import C, D, ROOT, V, read
from pipeline.curate.roles import role_profile
from pipeline.rights import check_public_use
from pipeline.validate import check


def test_missing_role_is_unresolved_existing_claim_not_deleted():
    graph = Graph()
    claim = C.a, V.implementsAlgorithm, C.b
    graph.add(claim)
    roles, findings = role_profile(graph)
    assert not findings and roles["predicate_review"]["implementsAlgorithm"] == {"unresolved": 1}
    assert claim in graph
    graph.add((C.b, V.hasScientificRole, V.Implementation))
    _, findings = role_profile(graph)
    assert findings and claim in graph


def test_shacl_rejects_known_incompatible_role_pair():
    graph = Graph()
    graph.parse(ROOT / "domains/_shared/vocabulary/scientific-roles.ttl")
    graph.add((D.logic, RDF.type, SKOS.ConceptScheme))
    graph.add((C.a, RDF.type, SKOS.Concept))
    graph.add((C.a, SKOS.inScheme, D.logic))
    graph.add((C.a, SKOS.prefLabel, Literal("Fixture", lang="en")))
    graph.add((C.a, V.hasScientificRole, V.Algorithm))
    graph.add((C.a, V.hasScientificRole, V.Method))
    assert check(graph)["conforms"]
    graph.add((C.a, V.hasScientificRole, V.Implementation))
    assert not check(graph)["conforms"]


@pytest.mark.parametrize("terms", ["CC-BY-NC-SA", "CC-BY-SA-4.0", "GPL-3.0", "unverified"])
def test_shared_or_restricted_terms_are_enforced_for_material_not_reference(terms):
    check_public_use("fixture", terms, ["citations", "source-identifiers"], "reference scope")
    with pytest.raises(ValueError, match="redistribution"):
        check_public_use("fixture", terms, ["native-labels"], "missing permission")
    with pytest.raises(ValueError, match="Copied external text"):
        check_public_use("fixture", "CC-BY-4.0", ["copied-text"], "absent path")


def test_release_inventory_distinguishes_channels():
    inventory = read(ROOT / "dist/manifest.json")["rights"]["sources"]
    assert inventory["native:msc2020"]["channels"] == ["reference-or-staging-only"]
    assert inventory["native:msc2020"]["disposition"] == "incompatible"
    assert "native-labels" in inventory["native:stato"]["channels"]
    assert "copied-text" not in inventory["passage:algs4"]["channels"]
    assert inventory["passage:algs4"]["notice_or_source"].startswith("https://")
