from itertools import combinations

from rdflib import Dataset, Graph, Literal, RDF, SKOS
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, G, ROOT, V, checksum, read
from pipeline.curate.rc2 import findings
from pipeline.curate.relations import statement_for


def test_induced_fixed_point_join_can_differ_from_ambient_join():
    points = {frozenset(group) for size in range(4) for group in combinations("abc", size)}
    def close(point):
        return point | {"c"} if {"a", "b"} <= point else point
    assert all(close(a) <= close(b) for a in points for b in points if a <= b)
    fixed = {a for a in points if close(a) == a}
    ambient = frozenset("ab")
    upper_bounds = {a for a in fixed if ambient <= a}
    assert ambient not in fixed and upper_bounds == {frozenset("abc")}


def test_rc2_scientific_corrections_and_history():
    data = Dataset()
    data.parse(ROOT / "dist/formal-sciences.nq", format="nquads")
    asserted, prov = data.graph(G.asserted), data.graph(G.provenance)
    assert not findings(asserted, prov)
    for s, p, o in [
        ("opencs-c39942", "computes", "irreducible-polynomial"),
        ("propositional-resolution-soundness", "uses", "logical-disjunction"),
        ("propositional-resolution-soundness", "uses", "logical-negation"),
        ("gradient-descent", "uses", "derivative"),
        ("bias-of-an-estimator", "uses", "expected-value"),
    ]:
        triple = C[s], V[p], C[o]
        assert triple not in asserted
        assert (statement_for(triple), RDF.type, RDF.Statement) in prov

    assert (C["a-star-search"], SKOS.broader, C["heuristic-search"]) in asserted
    assert (C["gradient-descent"], V.uses, C["ontomath-pro-e1700"]) in asserted
    assert (C["knaster-tarski-fixed-point-theorem"], V.hasScientificRole, V.Result) in asserted
    for s, p, o, word in [
        ("stato-0000304", "usesReferenceDistribution", "stato-0000059", "approximate"),
        ("principal-component-analysis", "uses", "singular-value-decomposition", "mean-centered"),
        ("opencs-c42922", "recognizesExactly", "deterministic-context-free-language", "final state"),
    ]:
        statement = statement_for((C[s], V[p], C[o]))
        assert any(word in str(note) for note in prov.objects(statement, DCTERMS.description))


def test_citation_policy_rejects_uncited_claim_and_result_ingredient():
    graph, prov = Graph(), Graph()
    graph.add((C.result, V.hasScientificRole, V.Result))
    graph.add((C.result, V.uses, C.structure))
    graph.add((C.other, SKOS.broader, C.structure))
    errors = findings(graph, prov)
    assert len(errors) == 2 and any("requires a citation" in error for error in errors)
    assert any("Result-only" in error for error in errors)


def test_native_stato_attribution_and_projection_boundary():
    data = Dataset()
    data.parse(ROOT / "dist/formal-sciences.nq", format="nquads")
    prov = data.graph(G.provenance)
    obo = "http://purl.obolibrary.org/obo/"
    assert all(id.startswith(obo + "STATO_") for id in
               read(ROOT / "reviews/approved/batches/stato.json")["identities"])
    from rdflib import URIRef
    witnesses = {s for s in prov.subjects(DCTERMS.isPartOf, URIRef(BASE + "source/stato"))
                 if prov.value(s, RDF.predicate)}
    assert witnesses
    assert all(str(prov.value(w, p)).startswith(obo + "STATO_")
               for w in witnesses for p in (RDF.subject, RDF.object))
    notice = read(ROOT / "dist/manifest.json")["rights"]["distribution_notice"]
    assert notice["sha256"] == checksum(ROOT / notice["path"])
