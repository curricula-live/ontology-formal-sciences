"""Conservatively inventory visible declaration headers in pinned Lean source text."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from tempfile import NamedTemporaryFile

from pipeline.common import ROOT, checksum, read, registry, write
from pipeline.fetch import fetch

SUMMARY = ROOT / "sources/mathlib4/declaration-inventory.json"
DECLARATION = re.compile(
    r"(?:(?:@\[[^\]\n]*\]|private|protected|public|noncomputable|unsafe|partial|meta)\s+)*"
    r"(theorem|lemma|def|abbrev|opaque|axiom)\s+"
    r"(«[^»\n]+»|[\w.][\w.'!?]*)"
    r"(?=$|[\s:({\[⦃])"
)
TOKEN = re.compile(r'/-|-/|--|"(?:[^"\\]|\\.)*"|«[^»]*»')
BLOCK = re.compile(r"/-|-/")
DELIMITER = re.compile(r'"(?:[^"\\]|\\.)*"|«[^»]*»|:=|:|\bwhere\b|[()\[\]{}⦃⦄]')
PAIRS = {")": "(", "]": "[", "}": "{", "⦄": "⦃"}
MAX_HEADER_LINES = 64


def uncomment(lines):
    """Mask comments while retaining source line numbers and indentation."""
    depth = 0
    for line in lines:
        offset = 0
        pieces = []
        while match := (BLOCK if depth else TOKEN).search(line, offset):
            token = match.group()
            if not depth:
                pieces.append(line[offset:match.start()])
                if token == "--":
                    break
                if token == "/-":
                    pieces.append(" " * len(token))
                else:
                    pieces.append(token)
            else:
                pieces.append(" " * (match.end() - offset))
            depth += token == "/-"
            if depth and token == "-/":
                depth -= 1
            offset = match.end()
        else:
            if not depth:
                pieces.append(line[offset:])
        yield "".join(pieces)


def header_end(lines, start, after_name):
    nesting = []
    explicit_type = False
    limit = min(start + MAX_HEADER_LINES, len(lines))
    for index in range(start, limit):
        text = lines[index]
        if index > start and text and not text[0].isspace() and not nesting:
            return index, 0, "layout", explicit_type
        for match in DELIMITER.finditer(text, after_name if index == start else 0):
            token = match.group()
            if token in PAIRS.values():
                nesting.append(token)
            elif token in PAIRS:
                if not nesting or nesting.pop() != PAIRS[token]:
                    return index, match.start(), "unfinished", explicit_type
            elif not nesting and token == ":":
                explicit_type = True
            elif not nesting and token in {":=", "where"}:
                return index, match.start(), token, explicit_type
    return limit, 0, "layout" if limit == len(lines) and not nesting else "unfinished", explicit_type


def headers(module, contents):
    lines = list(uncomment(contents.splitlines()))
    for index, line in enumerate(lines):
        match = DECLARATION.match(line)
        if not match:
            continue
        end, column, boundary, explicit_type = header_end(lines, index, match.end())
        if boundary == "unfinished":
            yield None
            continue
        signature = "\n".join([*lines[index:end], lines[end][:column] if end < len(lines) else ""]).strip()
        yield {
            "module": module, "line": index + 1, "token": match[2], "kind": match[1],
            "boundary": boundary, "has_explicit_result_type": explicit_type,
            "header_sha256": sha256(signature.encode("utf-8")).hexdigest(),
        }


def inventory(path, source, output=None):
    counts = Counter()
    families = defaultdict(Counter)
    seen = set()
    digest = sha256()
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            relative = member.name.partition("/")[2]
            if not member.isfile() or not relative.startswith("Mathlib/") or not relative.endswith(".lean"):
                continue
            if relative in seen:
                raise ValueError(f"Duplicate Lean source module: {relative}")
            seen.add(relative)
            parent = PurePosixPath(relative).parts[1].removesuffix(".lean")
            families[parent]["modules"] += 1
            with archive.extractfile(member) as content:
                for row in headers(relative, content.read().decode("utf-8-sig")):
                    if row is None:
                        counts["skipped_headers"] += 1
                        continue
                    counts[row["kind"]] += 1
                    families[parent][row["kind"]] += 1
                    serialized = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
                    digest.update(serialized.encode("utf-8"))
                    if output is not None:
                        output.write(serialized)
    if not seen:
        raise ValueError("Expected pinned Mathlib source files")
    return {
        "source": source["id"], "sha256": source["sha256"], "revision": source["revision"],
        "profile": "lean-textual-headers-v1", "modules": len(seen),
        "records": sum(value for key, value in counts.items() if key != "skipped_headers"),
        "index_sha256": digest.hexdigest(), "by_kind": dict(counts), "by_family": dict(families),
        "elaborated_signatures": 0, "kernel_proof_dependencies": 0,
    }


def replay(offline=False, write_evidence=False, output=None):
    source = registry()["mathlib4"]
    if source["license"] != "Apache-2.0":
        raise ValueError("Review Mathlib index rights for this revision")
    record = inventory(fetch(source, offline), source, output)
    if write_evidence:
        write(SUMMARY, record)
    elif record != read(SUMMARY):
        raise ValueError("Mathlib textual header inventory differs from the pinned report")
    return record


def release_summary(source):
    report = read(SUMMARY)
    if report["sha256"] != source["sha256"] or report["revision"] != source["revision"]:
        raise ValueError("Stale Mathlib declaration inventory")
    return {**report, "report_sha256": checksum(SUMMARY)}


def export(path, offline=False):
    """Write the private source index after its complete summary has replayed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            report = replay(offline=offline, output=handle)
            handle.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return report
