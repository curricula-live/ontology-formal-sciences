import os
import tempfile
from pathlib import Path
from rdflib import Dataset, Graph, URIRef, Literal, RDF, SKOS, BNode
from rdflib.namespace import DCTERMS, PROV
from pipeline.common import ROOT, BASE, G, checksum, registry, write, read, require_checkout
from pipeline.contract import metadata, validate_manifest
from pipeline.curate import authored, reviewed
from pipeline.curate.batches import verify_batches
from pipeline.curate.relations import apply_relations
from pipeline.curate.openmath import apply_formal_properties
from pipeline.curate.mathlib_evidence import apply_declarations
from pipeline.curate.cs_evidence import apply_reviewed_claims
from pipeline.curate.revisions import apply_revisions
from pipeline.curate.identities import apply_migrations
from pipeline.curate.roles import apply_roles, role_profile
from pipeline.rights import inventory as rights_inventory
from pipeline.lean_probe import apply_kernel_probe
from pipeline.curate.neighborhoods import release_summaries as neighborhood_summaries
from pipeline.parse.lean_index import release_summary as mathlib_index_summary
from pipeline.validate import check
from pipeline.reason import reason
from pipeline.quality import quality
from pipeline.semantic_audit import release_audit


def lines(graph):
    if any(isinstance(term,BNode) for triple in graph for term in triple):
        raise ValueError("Published profile requires named resources (blank nodes remain valid in staging)")
    return sorted(graph.serialize(format="nt").splitlines())


def build(dest=None):
    require_checkout()
    dest = Path(dest or ROOT / "dist")
    graph, prov = authored()
    sources = registry()
    maps = reviewed(sources,graph,prov)
    admissions = verify_batches(sources, graph, prov)
    relation_sources = apply_relations(sources, graph, maps, prov)
    formal_properties = apply_formal_properties(sources['openmath'], graph, prov)
    primary_claims = apply_reviewed_claims(graph, prov)
    declarations = apply_declarations(sources["mathlib4"], graph, prov)
    revisions = apply_revisions(graph, prov)
    migrations = apply_migrations(graph, prov)
    kernel_probe = apply_kernel_probe(graph, prov)
    apply_roles(graph, prov)
    roles, role_errors = role_profile(graph, prov)
    report = check(graph, prov)
    if role_errors:
        report["conforms"] = False
        report["findings"].extend(sorted(role_errors))
    if not report["conforms"]:
        raise ValueError(report)
    inferred = reason(graph)
    prov.add((G.inferred,PROV.wasDerivedFrom,G.asserted))
    prov.add((G.inferred,DCTERMS.description,Literal("Inverse of skos:broader and symmetry of skos:related; reverse the edge to recover each premise.")))
    graphs = {"asserted":graph,"alignments":maps,"provenance":prov,"inferred":inferred}
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        out = Path(tmp)
        trig, nq = [], []
        for name,part in graphs.items():
            values = lines(part)
            if name == "asserted":
                (out / "formal-sciences.ttl").write_text("\n".join(values)+"\n")
            block = G[name].n3()+" {\n"+"\n".join(values)+"\n}\n"
            trig.append(block)
            if name == "alignments":
                (out / "source-alignments.trig").write_text(block)
            nq.extend(v[:-2]+" "+G[name].n3()+" ." for v in values)
        (out / "formal-sciences.trig").write_text("".join(trig))
        (out / "formal-sciences.nq").write_text("\n".join(sorted(nq))+"\n")
        expected = {(s,p,o,G[n]) for n,g in graphs.items() for s,p,o in g}
        for ext,fmt in [("trig","trig"),("nq","nquads")]:
            ds = Dataset(); ds.parse(out/("formal-sciences."+ext),format=fmt)
            if set(ds.quads()) != expected:
                raise ValueError(f"Dataset round-trip mismatch: {ext}")
        write(out / "validation-report.json",report)
        inventory = {}
        for id,source in sources.items():
            path = ROOT / "sources" / id / "ingestion.json"
            stats = read(path) if path.exists() else {}
            if stats and (stats["sha256"] != source.get("sha256") or stats.get("validation") != "passed"):
                raise ValueError(f"Outdated staging report: {id}")
            inventory[id] = {k:source.get(k) for k in ("revision","sha256","license","attribution","scope","url")}
            normalized_path = path.with_name("normalization.json")
            normalized = read(normalized_path) if normalized_path.exists() else {}
            if normalized and normalized["sha256"] != source.get("sha256"):
                raise ValueError(f"Outdated normalization report: {id}")
            inventory[id].update(staged_triples=stats.get("triples",0),status=source["status"],
                                 normalized_label_keys=normalized.get("label_keys",0),
                                 candidate_pairs=normalized.get("candidates",0),
                                 stage_validation=stats.get("validation","unprocessed"))
        for source_id, admission in admissions.items():
            inventory[source_id]["admission"] = admission
        for source_id, relations in relation_sources.items():
            inventory[source_id]["relations"] = relations
        if formal_properties:
            inventory["openmath"]["formal_properties"] = formal_properties
        inventory["mathlib4"]["formal_declarations"] = declarations
        inventory["mathlib4"]["textual_declaration_index"] = mathlib_index_summary(sources["mathlib4"])
        for source_id, neighborhood in neighborhood_summaries(sources):
            inventory[source_id]["native_neighborhood"] = neighborhood
        config = read(ROOT / "ontology.yaml")
        if config["namespace"] != BASE:
            raise ValueError("Namespace differs from identifier policy")
        manifest = dict(contract=config["contract"],namespace=BASE,version=config["version"],conforms=True,
                        counts={name:len(g) for name,g in graphs.items()},
                        concepts=len(set(graph.subjects(RDF.type,SKOS.Concept))),predicates=len(set(graph.predicates())),
                        sources=inventory,artifacts={p.name:checksum(p) for p in sorted(out.iterdir())})
        manifest["quality"] = quality(graph, maps, prov, inferred, inventory, report)
        manifest["quality"]["computer_science_evidence"] = primary_claims
        manifest["quality"]["relation_revisions"] = revisions
        manifest["quality"]["canonical_identity_migrations"] = migrations
        manifest["quality"]["lean_kernel_probe"] = kernel_probe
        audit = release_audit(config["version"], graph, sources, prov)
        if audit:
            manifest["quality"]["semantic_audit"] = audit
        if "release" in config:
            manifest["release"] = metadata(**config["release"])
            manifest["rights"] = rights_inventory(inventory, prov)
        manifest["quality"]["scientific_roles"] = roles
        write(out / "manifest.json", validate_manifest(manifest))
        dest.mkdir(exist_ok=True)
        for path in sorted(out.iterdir(),key=lambda p:p.name=="manifest.json"):
            os.replace(path,dest/path.name)
    return manifest
