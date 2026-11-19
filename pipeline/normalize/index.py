"""A private normalized lookup graph derived from one immutable upstream graph."""
import shutil
import tempfile
from pathlib import Path
from pyoxigraph import Store, NamedNode, Literal, Quad
from rdflib import RDFS, SKOS
from pipeline.common import ROOT,BASE,read,write
from pipeline.parse import ingest, staged
from pipeline.normalize import label_key

KEY=NamedNode(BASE+"staging-vocabulary/labelKey")
LABELS=(RDFS.label,SKOS.prefLabel,SKOS.altLabel)


def index_path(source):
    return ROOT/".cache"/"index-v1"/source["id"]/source["sha256"]


def normalize(source,offline=False):
    raw=ingest(source,offline)
    path=index_path(source)
    if (path/"report.json").exists():
        return read(path/"report.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(tempfile.mkdtemp(dir=path.parent))
    try:
        dest=Store(str(tmp/"store"))
        src=staged(source)
        graph=NamedNode(raw["graph"]+"/normalized")
        def keys():
            for pred in LABELS:
                for q in src.quads_for_pattern(None,NamedNode(str(pred)),None,None):
                    if isinstance(q.subject,NamedNode) and isinstance(q.object,Literal):
                        yield Quad(q.subject,KEY,Literal(label_key(q.object.value),language=q.object.language),graph)
        dest.bulk_extend(keys())
        report=dict(source=source["id"],sha256=source["sha256"],upstream_graph=raw["graph"],
                    graph=graph.value,label_keys=len(dest),normalization="NFKC, casefold, whitespace; original language")
        write(tmp/"report.json",report)
        del dest
        try:
            tmp.rename(path)
        except OSError:
            if not (path/"report.json").exists():
                raise
        return read(path/"report.json")
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
