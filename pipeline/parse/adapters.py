import json
import os
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from pyoxigraph import Literal, NamedNode, Quad, RdfFormat
from pipeline.common import checksum

LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")


def dictionary(store, root, graph):
    ns = "{http://www.openmath.org/OpenMathCD}"
    if root.tag != ns + "CD":
        raise ValueError("Expected an OpenMath CD document")
    cd = root.findtext(ns + "CDName")
    base = root.findtext(ns + "CDBase") or "http://www.openmath.org/cd"
    for symbol in root.findall(ns + "CDDefinition"):
        name = (symbol.findtext(ns + "Name") or "").strip()
        if not cd or not name:
            raise ValueError("Unnamed dictionary or symbol")
        subject = NamedNode(f"{base.rstrip('/')}/{cd}#{name}")
        store.add(Quad(subject, LABEL, Literal(name), graph))


def openmath_archive(store, path, graph):
    with tarfile.open(path, "r|gz") as tar:
        for member in tar:
            if "/cd/Official/" in member.name and member.name.endswith(".ocd") and member.isfile():
                with tar.extractfile(member) as stream:
                    dictionary(store, ET.parse(stream).getroot(), graph)


def openalex(store, path, graph):
    row = json.loads(path.read_bytes())
    subject = NamedNode(row["id"])
    store.add(Quad(subject,LABEL,Literal(row["display_name"]),graph))
    store.add(Quad(subject,NamedNode("http://www.w3.org/2004/02/skos/core#broader"),NamedNode(row["subfield"]["id"]),graph))


def manchester(store, path, graph):
    jar = Path(os.environ.get("ROBOT_JAR","tools/robot.jar"))
    expected = (Path(__file__).parent / "robot.sha256").read_text().strip()
    if not jar.exists() or checksum(jar) != expected:
        raise ValueError("Install pinned ROBOT 1.9.8 and set ROBOT_JAR (see docs/sources.md)")
    with tempfile.TemporaryDirectory() as tmp:
        rdf = Path(tmp) / "converted.owl"
        if path.parent.parent.name == "ontomath-edu":
            path, extra = edu_frames(path, Path(tmp))
            store.bulk_load(input=extra.serialize(format="nt").encode(),format=RdfFormat.N_TRIPLES,to_graph=graph)
        args = ["java","-jar",str(jar),"convert","--input",str(path),"--output",str(rdf)]
        # Resolve OWL/XML imports to empty local documents. Preserve the import
        # IRIs in the main ontology without silently staging remote closures.
        if path.read_bytes().lstrip().startswith(b"<?xml"):
            ns = "{http://www.w3.org/2002/07/owl#}"
            catalog = ET.Element("catalog", xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog")
            for i, node in enumerate(ET.parse(path).getroot().findall(ns+"Import")):
                local = Path(tmp) / f"import-{i}.owl"
                ont = ET.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")
                ET.SubElement(ont, ns+"Ontology", {"{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about":node.text})
                ET.ElementTree(ont).write(local,encoding="utf-8",xml_declaration=True)
                ET.SubElement(catalog,"uri",name=node.text,uri=local.as_uri())
            cat = Path(tmp) / "catalog.xml"
            ET.ElementTree(catalog).write(cat)
            args.extend(["--catalog",str(cat)])
        subprocess.run(args,check=True,timeout=120)
        store.bulk_load(path=rdf,format=RdfFormat.RDF_XML,to_graph=graph)


def references(store, path, source, graph):
    """Bibliographic and non-RDF resources: extract only the declared scope."""
    from rdflib.namespace import DCTERMS, RDF
    from urllib.parse import quote
    id = source["id"]
    subject = NamedNode(source["url"])
    if id == "mathlib4":
        with tarfile.open(path, "r|gz") as tar:
            for member in tar:
                rel = member.name.partition("/")[2]
                if rel.startswith("Mathlib/") and rel.endswith(".lean") and member.isfile():
                    iri = "https://github.com/leanprover-community/mathlib4/blob/"+source["revision"]+"/"+quote(rel)
                    store.add(Quad(NamedNode(iri), LABEL, Literal(rel[:-5].replace("/",".")),graph))
    elif id == "oeis":
        series = NamedNode("https://oeis.org/A000045")
        for line in path.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            index, number = map(int,line.split())
            point = NamedNode(source["url"]+"#index-"+str(index))
            store.add(Quad(point,NamedNode(str(DCTERMS.isPartOf)),series,graph))
            store.add(Quad(point,NamedNode(str(RDF.value)),Literal(number),graph))
    elif id == "zbmath-open":
        record = json.loads(path.read_bytes())["result"]
        if not record or not record["identifier"]:
            raise ValueError("No bibliographic record in response")
        store.add(Quad(subject,NamedNode(str(DCTERMS.identifier)),Literal(record["identifier"]),graph))
        store.add(Quad(subject,NamedNode(str(DCTERMS.title)),Literal(record["title"]["title"]),graph))
    elif id == "tptp":
        import re
        with tarfile.open(path) as archive:
            with archive.extractfile("PUZ001-1.p") as file:
                for line in file:
                    text = line.decode().strip()
                    if text.startswith("cnf("):
                        match = re.match(r"cnf\(\s*([\w-]+)\s*,\s*([\w-]+)\s*,",text)
                        if not match:
                            raise ValueError("Unsupported CNF formula header")
                        name, role = match.groups()
                        store.add(Quad(NamedNode(source["url"]+"#"+name),NamedNode(str(DCTERMS.type)),Literal(role),graph))
    elif id == "dlmf":
        value = path.read_text().strip()
        if not (value.startswith(r"\[") and value.endswith(r"\]")):
            raise ValueError("Expected a displayed TeX equation")
        store.add(Quad(subject,NamedNode(str(RDF.value)),Literal(value),graph))
    else:
        raise ValueError("Unknown reference adapter")


def edu_frames(path, folder):
    """Translate the source's DisjointUnionOf extension for named operands only."""
    import re
    from rdflib import Graph, BNode, URIRef, OWL
    from rdflib.collection import Collection
    text = path.read_text()
    prefixes = dict(re.findall(r"(?m)^Prefix: (\w+): <([^>]+)>",text))
    def iri(token):
        if re.fullmatch(r"<[^\s<>]+>",token):
            return URIRef(token[1:-1])
        if re.fullmatch(r"\w+:[\w.-]+",token):
            prefix, local = token.split(":",1)
            return URIRef(prefixes[prefix]+local)
        raise ValueError("Unsupported disjoint union operand "+token)
    lines = iter(text.splitlines())
    remaining, extra, owner = [], Graph(), None
    for line in lines:
        if line and not line[0].isspace():
            owner = line[7:].strip() if line.startswith("Class: ") else None
        if line.strip()=="DisjointUnionOf:":
            if owner is None:
                raise ValueError("Disjoint union outside class frame")
            operands = [iri(i.strip()) for i in next(lines).split(",")]
            if len(operands)<2:
                raise ValueError("Disjoint union needs multiple operands")
            node = BNode()
            Collection(extra,node,operands)
            extra.add((iri(owner),OWL.disjointUnionOf,node))
        else:
            remaining.append(line)
    converted = folder / "normalized.omn"
    converted.write_text("\n".join(remaining)+"\n")
    return converted, extra
