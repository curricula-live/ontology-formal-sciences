"""Regression cases for conditional scientific claims and published query evidence."""
from rdflib import Graph, SKOS

from pipeline.common import C, ROOT, V, read
from pipeline.competency import answers
from pipeline.reason import reason


def test_published_competencies():
    result = answers(ROOT / "dist/formal-sciences.nq")
    assert result and all(result.values())

    def pairs(name, left, right):
        return {(row[left], row[right]) for row in result[name]}

    assert (str(C["dijkstra-s-algorithm"]), str(C["nonnegative-edge-weights"])) in pairs(
        "shortest-paths", "algorithm", "assumption"
    )
    assert (str(C["bellman-ford-algorithm"]), str(C["nonnegative-edge-weights"])) not in pairs(
        "shortest-paths", "algorithm", "assumption"
    )
    assert (str(C["bellman-ford-algorithm"]), str(C["no-reachable-negative-cycle"])) in pairs(
        "shortest-paths", "algorithm", "assumption"
    )
    assert {str(C["exponential-distribution"]), str(C["geometric-distribution"])} <= {
        row["distribution"] for row in result["distribution-properties"]
    }
    assert str(C["normal-distribution"]) not in {row["distribution"] for row in result["distribution-properties"]}
    assert (str(C["finite-automaton"]), str(C["regular-language"])) in pairs("languages", "machine", "family")
    assert (str(C["finite-automaton"]), str(C["context-free-language"])) not in pairs("languages", "machine", "family")
    assert (str(C["tree-sum-product"]), str(C["marginal-distribution"])) in pairs("factor-inference", "method", "quantity")
    assert (str(C["sum-product-algorithm"]), str(C["marginal-distribution"])) not in pairs("factor-inference", "method", "quantity")
    assert (str(C["ordinary-least-squares"]), str(C["qr-least-squares-method"])) in pairs("linear-regression", "estimator", "method")
    assert {row["ingredient"] for row in result["algorithm-evidence"]} == {
        str(C["strongly-connected-component"]), str(C["directed-graph"])
    }
    assert all(len(row["digest"]) == 64 for row in result["mapping-evidence"])
    assert pairs("branching-time-verification", "method", "technique") == {
        (str(C["ctl-state-labeling-algorithm"]), str(C["fixed-point"])),
        (str(C["ctl-state-labeling-algorithm"]), str(C["power-set"])),
    }
    assert all(row["reference"] for row in result["branching-time-verification"])
    assert pairs("source-discretization", "weak", "discrete") == {
        (str(C["mathmoddb-q6822179"]), str(C["mathmoddb-q6775736"]))
    }
    assert {row["weakSourcePredicate"].rsplit("/", 1)[-1] for row in result["source-discretization"]} == {"P1736"}
    assert {row["discreteSourcePredicate"].rsplit("/", 1)[-1] for row in result["source-discretization"]} == {"P1656"}
    assert pairs("stato-opencs-reference-law", "test", "distribution") == {
        (str(C["stato-0000304"]), str(C["stato-0000059"]))
    }
    assert {row["axiom"] for row in result["stato-opencs-reference-law"]} == {"subclass-some"}
    assert {row["assumption"] for row in result["theory-combination-assumptions"]} == {
        str(C["disjoint-theory-signatures"]), str(C["stable-infiniteness"]),
    }

    assert pairs("ground-euf-reasoning", "method", "structure") == {
        (str(C["congruence-closure-decision-procedure"]), str(C["disjoint-set-data-structure"]))
    }
    assert pairs("finite-field-factorization", "method", "assumption") == {
        (str(C["opencs-c39942"]), str(C["square-free-polynomial"]))
    }
    assert pairs("finite-field-factorization", "method", "output") == {
        (str(C["opencs-c39942"]), str(C["irreducible-polynomial"]))
    }
    assert {
        str(C["number-theory"]), str(C["numerical-analysis"]),
        str(C["conditional-probability"]), str(C["random-walk"]), str(C["regression-analysis"]),
    } <= {row["concept"] for row in result["cso-ontomath-reconciliation"]}



def test_every_new_scientific_claim_has_a_citation_and_no_implicit_inverse():
    cited = {(C[s], V[p], C[o]) for s, p, o, _ in read(ROOT / "reviews/approved/citations.json")}
    claims = Graph()
    for path in (ROOT / "domains").rglob("*.ttl"):
        if path.name in {"scientific-methods.ttl", "foundations.ttl", "advanced-methods.ttl"}:
            claims.parse(path)
    directional = {triple for triple in claims if triple[1] != SKOS.broader}
    assert directional and directional <= cited
    assert not any(predicate in set(claims.predicates()) - {SKOS.broader}
                   for _, predicate, _ in reason(claims))
