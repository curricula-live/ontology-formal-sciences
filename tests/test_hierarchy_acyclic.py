"""Project policy: canonical navigation uses an acyclic SKOS broader hierarchy.

SKOS source vocabularies are not globally required to be acyclic; only the
project's published canonical asserted hierarchy has this stronger invariant.
"""
from rdflib import Graph, RDF, SKOS

from pipeline.common import C, D
from pipeline.curate import authored
from pipeline.validate import check, hierarchy_cycle_issue


def _small_graph(edges):
    graph = Graph()
    for node in ("a", "b", "c"):
        graph.add((C[node], RDF.type, SKOS.Concept))
        graph.add((C[node], SKOS.inScheme, D["mathematics"]))
    for child, parent in edges:
        graph.add((C[child], SKOS.broader, C[parent]))
    return graph


def test_canonical_hierarchy_is_currently_acyclic():
    graph, _ = authored()
    assert hierarchy_cycle_issue(graph) is None


def test_two_node_cycle_is_rejected_by_the_editorial_validator():
    graph = _small_graph([("a", "b"), ("b", "a")])
    issue = hierarchy_cycle_issue(graph)
    assert issue and "cycle" in issue.lower()
    assert any("hierarchy cycle" in str(x) for x in check(graph)["findings"])


def test_longer_cycle_is_rejected_even_with_noncyclic_tail():
    graph = _small_graph([("a", "b"), ("b", "c"), ("c", "a")])
    assert hierarchy_cycle_issue(graph)


def test_dag_with_multiple_parents_is_valid_navigation():
    graph = _small_graph([("a", "b"), ("a", "c")])
    assert hierarchy_cycle_issue(graph) is None
