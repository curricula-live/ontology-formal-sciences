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
        str(C["strongly-connected-component"]), str(C["directed-graph"]), str(C["material-implication"])
    }
    assert all(len(row["digest"]) == 64 for row in result["mapping-evidence"])
    assert pairs("branching-time-verification", "method", "technique") == {
        (str(C["ctl-state-labeling-algorithm"]), str(C["fixed-point"])),
        (str(C["ctl-state-labeling-algorithm"]), str(C["power-set"])),
    }
    assert all(row["reference"] for row in result["branching-time-verification"])
    assert pairs("finite-element-endpoint-resolution", "task", "method") == {
        (str(C["mathmoddb-q6775615"]), str(C["ontomath-pro-e3187"]))
    }
    resolved, = result["finite-element-endpoint-resolution"]
    assert resolved["mathmoddb"].endswith("/Q6775613")
    assert resolved["ontomath"].endswith("#E3187")
    assert pairs("poisson-optimization-bridge", "task", "likelihood") == {
        (str(C["mathmoddb-q6684606"]), str(C["poisson-log-likelihood"]))
    }
    assert pairs("system-f-evidence", "system", "property") == {
        (str(C["system-f"]), str(C["strong-normalization"]))
    }

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

    assert pairs("binomial-sampling-bridge", "distribution", "mass") == {
        (str(C["stato-0000060"]), str(C["hypergeometric-mass-formula"])),
        (str(C["stato-0000276"]), str(C["binomial-mass-formula"])),
    }
    assert {row["identity"] for row in result["binomial-sampling-bridge"]} == {
        str(C["binomial-factorial-identity"]),
    }
    assert all(len(row["digest"]) == 64 for row in result["binomial-sampling-bridge"])
    normalization, = result["hypergeometric-normalization"]
    assert normalization["declaration"] == "Nat.add_choose_eq"
    assert normalization["identity"] == str(C["vandermonde-convolution"])
    evaluation, = result["ml-schema-evaluation-chain"]
    assert evaluation["evaluation"] == str(C["mls-model-evaluation-result"])
    assert evaluation["measure"] == str(C["mls-evaluation-measure"])
    assert evaluation["measurePredicate"] == "http://www.w3.org/ns/mls#specifiedBy"
    reduction, = result["many-one-reduction-composition"]
    assert reduction["composition"] == str(C["many-one-reduction-transitivity"])
    assert reduction["topic"] == str(C["function-composition"])
    assert reduction["declaration"] == "ManyOneReducible.trans"


def test_every_new_scientific_claim_has_a_citation_and_no_implicit_inverse():
    cited = {(C[s], V[p], C[o]) for s, p, o, _ in read(ROOT / "reviews/approved/citations.json")}
    claims = Graph()
    for path in (ROOT / "domains").rglob("*.ttl"):
        if path.parent.name in {"links", "bridges"} and path.name in {
            "scientific-methods.ttl", "foundations.ttl", "advanced-methods.ttl", "semantic-resolution.ttl",
            "interdisciplinary.ttl",
        }:
            claims.parse(path)
    directional = {triple for triple in claims if triple[1] != SKOS.broader}
    assert directional and directional <= cited
    assert not any(predicate in set(claims.predicates()) - {SKOS.broader}
                   for _, predicate, _ in reason(claims))
