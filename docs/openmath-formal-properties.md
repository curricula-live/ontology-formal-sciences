# OpenMath property evidence

Curricula's RDF projection is a derived work from selected OpenMath
Content Dictionaries. The OpenMath Society and dictionary authors are
credited under the embedded derivative-work terms. The release names the
original dictionary for each projected claim and retains the symbol's
upstream IRI. The original XML remains in the checksum-pinned source archive.

The profile selects 22 official dictionaries and the experimental
`combinat1` dictionary after checking their embedded notices. The selected files and embedded conditions are recorded in [NOTICE](../NOTICE.md). Downstream rights review remains open. Each recorded property
retains its owner symbol, ordinal, full expression digest, referenced
symbols and outer expression shape. The review binds a symbol's
mathematical sense to an existing or newly curated subject. It does not
make the symbol an OWL class or assign global equivalence to it.

The projection publishes reviewed laws and the operations their
statements use. A property's target can be a law with explicit
applicability conditions, such as self-division for nonzero scalars.
Seeing a symbol in an expression supplies a candidate for review.
Approval requires a matching expression fingerprint and an editorial
reason about its scientific meaning. The provenance keeps the outer
quantifier or implication shape with the expression digest.

Replay with `python -m pipeline.cli replay-openmath --offline` after
restoring the pinned archive, or omit `--offline` to fetch it. With
`--write-evidence`, the command updates only the evidence inventory for
review. Ordinary release builds run from the reviewed inventory, and CI
reproduces that inventory from source.

- [Official logic dictionary](http://www.openmath.org/cd/logic1.ocd)
- [Official set dictionary](http://www.openmath.org/cd/set1.ocd)
- [Experimental combinatorics dictionary](http://www.openmath.org/cd/combinat1.ocd)

## v0.7.0 expression scope

The reviewed slice contains 23 content dictionaries and 190 formal
properties. The extractor records top-level implication guards and
consequences, including under outer binders. The RDF exposes the native
guard symbols alongside the original expression fingerprint. A property
target that occurs only in the guard requires an explicit scope decision.
An unresolved native symbol blocks approval and has a separate review
disposition from a missing canonical symbol binding.

Now-reviewed cohorts include ordinary differentiation, multiset
operations, real intervals, rounding, complex coordinates and density
integrals. The reasons for withholding statements include undeclared
symbol spellings, a sample formula that loses multiplicity, and a
distribution expression that omits the square root. The archive and
decision ledger retain these original identifiers.

## v0.8.0 semantic roles

The v0.7.0 OpenMath projection has 230 distinct edges. The current release
retains 63 scoped property assertions and migrates 167 expression
occurrences to `v:containsSymbol`. The historical `v:uses` statements are
preserved in provenance, where each replacement links to its former
interpretation with `prov:wasRevisionOf`. Both interpretations retain
the same native expression evidence and fingerprint.

Symbol occurrences describe syntax and retain guard evidence. The
scientific connectivity report excludes these edges and reports them in
the expression graph statistics. A query can still intentionally cross
from a formula subject to its symbols, as the binomial sampling query
demonstrates. The separate property assertions express scoped mathematical
facts, including hypotheses recorded for differentiability, distribution
moments and domain restrictions.
