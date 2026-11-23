"""Release-candidate rc.3 adds qualified statement evidence without changing triples."""
from rdflib import Literal
from rdflib.namespace import DCTERMS
from pipeline.common import C, ROOT, V, read
from pipeline.curate.relations import statement_for

LEDGER = ROOT / "reviews/quality/rc3-delta.json"

def apply(graph, provenance):
    edits = read(LEDGER)
    for s,p,o,scope in edits["statement_scope_additions"]:
        triple=(C[s],V[p],C[o])
        if triple not in graph:
            raise ValueError(f"Missing candidate for scoped correction: {triple}")
        statement=statement_for(triple)
        if not provenance.value(statement,DCTERMS.source):
            raise ValueError(f"Scoped claim has no recorded citation: {triple}")
        note=Literal(scope,lang="en")
        if (statement,DCTERMS.description,note) in provenance:
            raise ValueError("Scope correction is already present")
        provenance.add((statement,DCTERMS.description,note))
