# mathlib4

complete mathlib4 source archive; index Mathlib module paths only.

Upstream: https://codeload.github.com/leanprover-community/mathlib4/tar.gz/35f494609c32653bae53eb33f0cf2d899808909a

Attribution: mathlib community. Terms: Apache-2.0. See source.yaml for acquisition details and ingestion.json, when present, for the measured graph size.

The source adapter indexes all 8,728 Mathlib modules in the pinned archive and
23,864 direct imports among those modules. An import is a source-file
dependency. Imports outside the archive and dependencies between individual
Lean declarations are outside this index. The index is available for source
analysis and stays outside the public canonical RDF.

A separate editorial profile cites named declarations from the pinned archive.
It checks the exact declaration and proof ranges with
`python -m pipeline.cli replay-mathlib --offline`. The published graph preserves
the declaration name, upstream revision, range and excerpt digest for each
reviewed claim. The replay verifies the cited text against the archive; the
Lean statements and proofs are maintained upstream. Rejected readings
remain in `reviews/formal-properties/mathlib4-declarations.json`.

v0.7.0 also inventories 230,400 visible named declaration headers in
8,728 Mathlib files. The index stores the written name, command kind,
file, line, explicit result-type indicator and a textual header digest.
The source archive remains authoritative for names and ranges. The
bounded lexical scanner recognizes common declaration layout and masks
comments. Its coverage depends on textual syntax. Namespace resolution,
macro expansion, inferred types and kernel dependency extraction require
Lean and are outside this inventory.

Run `python -m pipeline.cli replay-mathlib-index --offline` to recompute
the inventory. Add `--export .cache/mathlib-declarations.jsonl` for a
local searchable index. Reviewed canonical claims use separate declaration
ranges. A small set of source spellings is replayed within those reviewed
proof fragments and published as textual proof references.
