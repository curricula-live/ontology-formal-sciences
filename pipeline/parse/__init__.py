"""Stream a source document into its own immutable, disk-backed named graph."""
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from pyoxigraph import Store, NamedNode, RdfFormat, Quad, Literal
from pipeline.common import BASE, ROOT, write, read
from pipeline.fetch import fetch

FORMATS = {"xml": RdfFormat.RDF_XML, "turtle": RdfFormat.TURTLE, "nt": RdfFormat.N_TRIPLES}


def load_graph(store, path, source, graph):
    fmt = source["format"]
    if fmt == "nt-zip":
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.namelist() if m.endswith(".nt") and not m.startswith("__MACOSX")]
            if len(members) != 1:
                raise ValueError("Expected one N-Triples document")
            with archive.open(members[0]) as stream:
                store.bulk_load(input=stream, format=RdfFormat.N_TRIPLES, to_graph=graph)
    elif fmt in {"lean-archive","bfile","tex-equation","tptp-archive","zbmath"}:
        from pipeline.parse.adapters import references
        references(store,path,source,graph)
    elif fmt in {"owlxml","manchester", "openmath-tar", "openalex"}:
        from pipeline.parse.adapters import manchester, openmath_archive, openalex
        {"owlxml": manchester,"manchester": manchester, "openmath-tar": openmath_archive, "openalex": openalex}[fmt](store, path, graph)
    else:
        store.bulk_load(path=path, format=FORMATS[fmt], to_graph=graph, base_iri=source["url"])


def ingest(source, offline=False):
    path = fetch(source, offline)
    folder = ROOT / ".cache" / "stage" / source["id"] / source["sha256"]
    report = folder / "report.json"
    if report.exists():
        return read(report)
    folder.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=folder.parent))
    try:
        name = BASE + "stage/" + source["id"] + "/" + source["sha256"]
        store = Store(str(tmp / "store"))
        load_graph(store, path, source, NamedNode(name))
        size = len(store)
        if not size:
            raise ValueError("Parsed source contained no statements")
        del store
        result = dict(source=source["id"], sha256=source["sha256"], triples=size, graph=name)
        write(tmp / "report.json", result)
        try:
            tmp.rename(folder)
        except OSError:
            if not report.exists():
                raise
        return read(report)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def staged(source):
    path = ROOT / ".cache" / "stage" / source["id"] / source["sha256"] / "store"
    return Store.read_only(str(path))
