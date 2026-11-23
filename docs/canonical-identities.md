# Canonical identity lifecycle

The asserted graph records each permanent canonical IRI and its current
status. A reviewed change in the existing
[identity migration ledger](../reviews/approved/identity-migrations.json)
is projected there with its review in the provenance graph. The ledger
records decisions and evidence. It does not allocate alternative concept
IRIs or replace concept ownership.

| Action | Effect on the permanent IRI |
|---|---|
| Editorial correction | Keep the same denotation. Record the correction and claim history. Changes to previous preferred labels, definitions or schemes require compatibility review. |
| Deprecate | Retain the original record and add the deprecation marker. There may be no successor. |
| Replace | Record one same-scheme successor for the prior scope. Keep original source provenance and reviewed mappings. |
| Merge | Point each retired duplicate to the one live canonical IRI. This action has an explicit identity review. |
| Split | Keep the original umbrella IRI as a deprecated subject with at least two reviewed successors. Resolve to the list, then choose the applicable branch based on scope. |

The marker is `owl:deprecated true`. One `dcterms:isReplacedBy`
edge names each target. Reified action and target statements share a
provenance witness with the action, rationale, source or editorial reference,
and a review identifier or native digest. This is a lifecycle projection
and carries no SKOS or OWL equivalence consequence.

A consumer keeps prior concept records resolvable. It checks a pinned
predecessor for accidental deletion, lost source origins, retired IRI reuse,
unexpected scope changes and lost reviewed mapping history. Targets must
be live subjects in the same scheme. Missing targets, chains, cycles and
cross-scheme redirects fail. Any scope-altering change requires fresh
identity decisions and publication approval.

OpenCS C3339 and the prior authored A-star subject refer to ordinary A*
search. `concept/a-star-search` is the active endpoint.
`concept/opencs-c3339` retains its OpenCS identity, taxonomy, and prior
admission. Replay the native evidence with
`python -m pipeline.cli replay-identity-migrations`.
