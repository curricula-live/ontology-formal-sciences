# Canonical identity migrations

A reviewed duplicate continues to resolve in the asserted graph as its original
SKOS concept, with its original labels, taxonomy, source identity, and admission
record. The publisher marks that IRI with \`owl:deprecated true\` and adds one
\`dcterms:isReplacedBy\` edge to a current concept in the same scheme. The
replacement has a cited editorial decision in the provenance graph and is
independent of SKOS mappings and OWL equivalence. Review decisions and source
identifiers remain available on historical IRIs.

Follow the replacement for current scientific queries and new assertions. The
release validator rejects chains, cycles, cross-scheme replacements, and new
scientific assertions using retired endpoints. Changes involving already
published scientific assertions require an explicit statement-level review and
revision record.

The pinned OpenCS A* topic and the authored A-star search subject both denote
the ordinary A* method. The authored IRI \`concept/a-star-search\` is the
preferred canonical endpoint. \`concept/opencs-c3339\` retains its earlier
OpenCS admission. Its native topic, snapshot digest, and scientific reference
are recorded in the reviewed migration ledger.

Replay the migration source evidence with
\`python -m pipeline.cli replay-identity-migrations\`.
