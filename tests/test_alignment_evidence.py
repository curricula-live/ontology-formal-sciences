from importlib import import_module

from rdflib import Graph, Literal, RDF, SKOS

from pipeline.align import candidates
from pipeline.common import C, checksum, write


def test_reference_can_suggest_without_a_matching_label_and_preserves_veto(tmp_path, monkeypatch):
    for module in ("pipeline.parse", "pipeline.fetch", "pipeline.align", "pipeline.normalize.index"):
        monkeypatch.setattr(import_module(module), "ROOT", tmp_path)
    source = "https://example.org/new/finite-machine"
    reference = "http://dbpedia.org/resource/Finite-state_machine"
    original = tmp_path / "sources/test/original/snapshot"
    original.parent.mkdir(parents=True)
    original.write_text(f'<{source}> <{SKOS.closeMatch}> <{reference}> .\n')
    content_hash = checksum(original)
    spec = dict(id="test", format="nt", sha256=content_hash, url="https://example.org/source.nt",
                validation_query="ASK { GRAPH ?g { ?s ?p ?o } }")
    topic = C["finite-automaton"]
    canonical = Graph()
    canonical.add((topic, RDF.type, SKOS.Concept))
    canonical.add((topic, SKOS.prefLabel, Literal("Finite automaton", lang="en")))
    prior = dict(id="prior", source="other", external="https://example.org/prior",
                 canonical=str(topic), predicate=str(SKOS.exactMatch),
                 evidence=f'<https://example.org/prior> <{SKOS.exactMatch}> <{reference}> .')
    write(tmp_path / "reviews/approved/mappings.json", [prior])
    rejected = dict(prior, id="veto", source="test", external=source, sha256=content_hash)
    write(tmp_path / "reviews/rejected/mappings.json", [rejected])
    row, = candidates(spec, canonical, True)
    assert row["rule"] == "shared-reference" and row["labels"] == []
    assert row["references"] == [dict(predicate=str(SKOS.closeMatch), reference=reference, review="prior")]
    assert row["state"] == "rejected"
    original.write_text(original.read_text() + "\n")
    spec["sha256"] = checksum(original)
    refreshed, = candidates(spec, canonical, True)
    assert refreshed["state"] == "needs-revalidation"
    assert refreshed["previous_decision"] == "veto"
    assert set(canonical.predicates()) == {RDF.type, SKOS.prefLabel}



def test_only_exact_match_can_resolve_a_scientific_projection_endpoint():
    from rdflib import RDFS, URIRef

    from pipeline.curate.relations import OBO, resolved_identities

    external = URIRef(OBO + "STATO_9999999")
    mappings = Graph()
    mappings.add((C.example, SKOS.closeMatch, external))
    mappings.add((C.example, RDFS.seeAlso, external))
    assert external not in resolved_identities("stato", mappings)
    mappings.add((C.example, SKOS.exactMatch, external))
    assert resolved_identities("stato", mappings)[external] == {C.example}
