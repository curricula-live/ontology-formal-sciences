import json
import os
import re
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
    cd = (root.findtext(ns + "CDName") or "").strip()
    base = root.findtext(ns + "CDBase") or "http://www.openmath.org/cd"
    for symbol in root.findall(ns + "CDDefinition"):
        name = (symbol.findtext(ns + "Name") or "").strip()
        if not cd or not name:
            raise ValueError("Unnamed dictionary or symbol")
        subject = NamedNode(f"{base.rstrip('/')}/{cd}#{name}")
        store.add(Quad(subject, LABEL, Literal(name), graph))
        description = symbol.find(ns+"Description")
        if description is not None:
            store.add(Quad(subject,NamedNode("http://www.w3.org/2000/01/rdf-schema#comment"),
                           Literal("".join(description.itertext()).strip()),graph))
        store.add(Quad(subject,NamedNode("http://purl.org/dc/terms/isPartOf"),
                       NamedNode(base.rstrip("/")+"/"+cd),graph))


def openmath_archive(store, path, graph):
    with tarfile.open(path, "r|gz") as tar:
        for member in tar:
            if member.name.endswith(".ocd") and member.isfile():
                with tar.extractfile(member) as stream:
                    dictionary(store, ET.parse(stream).getroot(), graph)


def openalex(store, path, graph):
    row = json.loads(path.read_bytes())
    subject = NamedNode(row["id"])
    store.add(Quad(subject,LABEL,Literal(row["display_name"]),graph))
    store.add(Quad(subject,NamedNode("http://www.w3.org/2004/02/skos/core#broader"),NamedNode(row["subfield"]["id"]),graph))


def manchester(store, path, graph, *, edu=False):
    jar = Path(os.environ.get("ROBOT_JAR","tools/robot.jar"))
    expected = (Path(__file__).parent / "robot.sha256").read_text().strip()
    if not jar.exists() or checksum(jar) != expected:
        raise ValueError("Install pinned ROBOT 1.9.8 and set ROBOT_JAR (see docs/sources.md)")
    with tempfile.TemporaryDirectory() as tmp:
        rdf = Path(tmp) / "converted.owl"
        if edu:
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
    id = source["id"]
    subject = NamedNode(source["url"])
    if id == "mathlib4":
        from pipeline.parse.mathlib import stage_modules

        stage_modules(store, path, source["revision"], graph)
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
    """Translate OntoMathEdu's named-class partition frames per OWL 2 Mapping to RDF §3.2.5."""
    from rdflib import BNode, Graph, OWL, URIRef
    from rdflib.collection import Collection

    text = path.read_text(encoding="utf-8")
    prefixes = dict(re.findall(r"(?m)^Prefix:\s*([\w-]*):[ \t]*<([^>\s]+)>", text))
    token = r"(?:<[a-zA-Z][a-zA-Z0-9+.\-]*:[^<>\s]+>|[\w-]*:[\w.\-]+)"
    named_list = re.compile(rf"{token}(?:\s*,\s*{token})+")

    def iri(name):
        if name.startswith("<"):
            return URIRef(name[1:-1])
        prefix, local = name.split(":", 1)
        if prefix not in prefixes:
            raise ValueError(f"Unknown OntoMathEdu prefix in {name!r}")
        return URIRef(prefixes[prefix] + local)

    remaining, extra = [], Graph()
    declared, participants = set(), set()
    owner = None
    lines = iter(text.splitlines(keepends=True))
    for line in lines:
        if line and not line[0].isspace():
            header = re.fullmatch(rf"Class:[ \t]+({token})", line.rstrip())
            owner = iri(header[1]) if header else None
            if owner is not None:
                declared.add(owner)
        body = line.strip()
        if not body.startswith("DisjointUnionOf:"):
            remaining.append(line)
            continue
        if owner is None:
            raise ValueError("DisjointUnionOf outside a named class frame")
        names = body.removeprefix("DisjointUnionOf:").strip()
        while not names or names.endswith(","):
            continuation = next(lines, "")
            if not continuation or not continuation[0].isspace():
                raise ValueError(f"Incomplete DisjointUnionOf on {owner}")
            names += " " + continuation.strip()
            names = names.strip()
        if not named_list.fullmatch(names):
            raise ValueError(f"Unsupported DisjointUnionOf expression on {owner}: {names}")
        operands = [iri(name) for name in re.findall(token, names)]
        if len(set(operands)) != len(operands):
            raise ValueError(f"Repeated DisjointUnionOf operand on {owner}")
        participants.update(operands)
        node = BNode()
        Collection(extra, node, operands)
        extra.add((owner, OWL.disjointUnionOf, node))
    undeclared = participants - declared
    if undeclared:
        raise ValueError("Expected locally declared partition classes: " + ", ".join(sorted(undeclared)))
    converted = folder / "normalized.omn"
    converted.write_text("".join(remaining), encoding="utf-8")
    return converted, extra
