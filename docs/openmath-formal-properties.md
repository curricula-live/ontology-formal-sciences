# OpenMath property evidence

Curricula's RDF projection is a derived work from selected OpenMath
Content Dictionaries. The OpenMath Society and dictionary authors are
credited under the embedded derivative-work terms. The release names the
original dictionary for each projected claim and retains the symbol's
upstream IRI. The original XML remains in the checksum-pinned source archive.

The profile selects ten official dictionaries and the experimental
`combinat1` dictionary after checking their embedded notices. This
permission is specific to the selected files. Each recorded property
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
