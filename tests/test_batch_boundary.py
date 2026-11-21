import pytest
from rdflib import Graph, Literal, RDF, SKOS, URIRef
from rdflib.namespace import DCTERMS, PROV

from pipeline.common import BASE, C, checksum, registry, write
from pipeline.curate.batches import verify_batches


@pytest.fixture
def batch(tmp_path):
    catalog = registry()
    source = catalog["stato"]
    rel = "domains/statistics/modules/batches/distributions.ttl"
    module = tmp_path / rel
    module.parent.mkdir(parents=True)
    module.write_text('<urn:module> <urn:scope> "test" .\n')
    canonical, provenance = Graph(), Graph()
    canonical.add((C["normal-distribution"], RDF.type, SKOS.Concept))
    provenance.add((C["normal-distribution"], PROV.wasDerivedFrom,
                    URIRef(BASE + "module/" + rel.removeprefix("domains/"))))
    native = "http://purl.obolibrary.org/obo/STATO_0000227"
    decision = dict(source="stato", policy="A subject heading for a native STATO class",
                    sha256=source["sha256"], revision=source["revision"], license=source["license"],
                    identities={native: "normal-distribution"}, modules={rel: checksum(module)},
                    eligible=1, pending=0, exclusions={})
    path = tmp_path / "reviews/approved/batches/stato.json"
    return catalog, canonical, provenance, decision, path, native


def test_batch_origin_is_not_equivalence(batch, tmp_path):
    catalog, graph, prov, decision, path, src = batch
    write(path, decision)
    report = verify_batches(catalog, graph, prov, tmp_path)
    assert report["stato"]["new_concepts"] == 1
    assert (C["normal-distribution"], DCTERMS.source, URIRef(src)) in prov
    assert (None, SKOS.exactMatch, None) not in graph
    assert Literal(catalog["stato"]["sha256"]) in prov.objects(None, DCTERMS.identifier)


@pytest.mark.parametrize("mutation", ["import", "digest", "revision", "license", "coverage",
                                      "count", "target", "missing-ledger", "duplicate-key"])
def test_batch_fails_closed(batch, tmp_path, mutation):
    catalog, graph, prov, decision, path, src = batch
    if mutation == "import":
        decision["identities"] = {src.replace("STATO_", "OBI_"): "normal-distribution"}
    elif mutation == "digest":
        decision["modules"][next(iter(decision["modules"]))] = "stale"
    elif mutation in ("revision", "license"):
        decision[mutation] = "changed"
    elif mutation == "coverage":
        decision["identities"] = {}
    elif mutation == "count":
        decision["pending"] = 1
    elif mutation == "target":
        decision["identities"][src] = "missing"
    if mutation != "missing-ledger":
        write(path, decision)
    if mutation == "duplicate-key":
        path.write_text(path.read_text().replace(
            '"source": "stato"', '"source": "stato", "source": "stato"'))
    with pytest.raises(ValueError):
        verify_batches(catalog, graph, prov, tmp_path)

