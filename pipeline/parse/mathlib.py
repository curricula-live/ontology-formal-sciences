"""Extract direct local import declarations from the pinned Mathlib source headers."""
import re
import tarfile
from pathlib import PurePosixPath
from urllib.parse import quote

from pyoxigraph import Literal, NamedNode, Quad
from rdflib.namespace import DCTERMS, RDFS

COMMENT = re.compile(r"/-|-/|--")
IMPORT = re.compile(r"(?:(?:public|meta)\s+)*import\s+(?:all\s+)?([\w'.]+)")
MODULE_DECLARATION = re.compile(r"module(?:\s+--.*)?$")


def direct_imports(lines):
    depth = 0
    for line in lines:
        start = 0
        fragments = []
        for token in COMMENT.finditer(line):
            if depth == 0:
                fragments.append(line[start:token.start()])
            comment = token.group()
            if comment == "--" and depth == 0:
                break
            if comment == "/-":
                depth += 1
                fragments.append(" ")
            elif comment == "-/" and depth:
                depth -= 1
            start = token.end()
        else:
            if depth == 0:
                fragments.append(line[start:])
        text = "".join(fragments).strip()
        if not text or text == "prelude" or MODULE_DECLARATION.fullmatch(text):
            continue
        match = IMPORT.fullmatch(text)
        if match:
            yield match[1]
        elif re.match(r"(?:(?:public|meta)\s+)*import\b", text):
            raise ValueError(f"Unsupported Mathlib import declaration: {text}")
        else:
            return
    if depth:
        raise ValueError("Unclosed Mathlib header comment")


def stage_modules(store, path, revision, graph):
    prefix = f"https://github.com/leanprover-community/mathlib4/blob/{revision}/"
    label = NamedNode(str(RDFS.label))
    requires = NamedNode(str(DCTERMS.requires))
    names, imports = {}, {}
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            rel = member.name.partition("/")[2]
            if not member.isfile() or not rel.startswith("Mathlib/") or not rel.endswith(".lean"):
                continue
            module = ".".join(PurePosixPath(rel).with_suffix("").parts)
            if module in names:
                raise ValueError(f"Duplicate Mathlib archive module: {module}")
            names[module] = NamedNode(prefix + quote(rel))
            with archive.extractfile(member) as content:
                imports[module] = set(direct_imports(raw.decode("utf-8-sig") for raw in content))
    if not names:
        raise ValueError("Expected Mathlib sources in archive")
    store.bulk_extend(Quad(node, label, Literal(module), graph) for module, node in names.items())
    store.bulk_extend(Quad(names[module], requires, names[target], graph)
                      for module in imports for target in imports[module] if target in names)
