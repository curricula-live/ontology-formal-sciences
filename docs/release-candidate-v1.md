# Formal sciences v1.0.0 Foundation candidate

Branch `feat/formal-sciences` advances the verified v0.9.0 baseline
`bb65b889cf8444ef66eb17860eeefec9d513aa10`. Use `git rev-parse HEAD`
for the immutable candidate commit and `sha256sum dist/manifest.json`
for the exact package digest at that commit. Preparation preserves
`curricula.rdf-release/v1` and the four logical graph names.

The candidate retains every permanent concept IRI and reviewed mapping.
The producer review corrected the transition-matrix carrier classification
from `uses` to `skos:broader` and retained the old claim and module
digest through an explicit revision witness. Scientific roles are assigned
to 19 reviewed subjects. Remaining role scopes are represented in the
manifest review queue. No source cohort was admitted during stabilization.

## Gates

| Gate | State | Evidence |
|---|---|---|
| WP0 baseline and regression | PASS | Local and remote feature HEAD matched the specified baseline. A clean Git archive rebuilt all six baseline files byte for byte. Core tests passed. The full-source OntoMathEdu check was skipped in that archive before the optional snapshot was staged. The current suite also verifies that a close match can suggest a candidate while only exact matches can resolve a scientific endpoint. |
| WP1 producer contract | PASS | Version and graph metadata validate against the existing contract. RDFLib and Oxigraph agree on all serializations, and the pinned successor comparison verifies the graph changes. |
| WP2 IRI lifecycle | PASS | A* retains its source IRI and reviewed merge lineage. Tests cover retired IRI reuse, deletion, invalid targets, cycles, splitting, and forbidden cross-scheme redirects. |
| WP3 predicate semantics and roles | PASS | Reviewed role provenance, SHACL, endpoint policy, and the single matrix revision are in the candidate. Unresolved role scopes are visible without suppressing assertions. |
| WP4 rights inventory and checks | PASS | The manifest records each source's channels, terms, attribution and notice or source reference. Regression cases enforce the restrictions on material publication. |
| Final rights clearance | BLOCKED | An owner or qualified reviewer must resolve downstream conditions for the selected OpenMath expressions and native STATO projections, and confirm the evidence-only OpenDSA notice. Reference-only sources remain scoped to their stated channels. |
| WP5 reference consumer | PASS | Tests exercise package corruption, identity resolution, repeat loading, successor replacement, rollback and an injected pointer-update failure. A fresh reader sees the prior snapshot during that failure. |
| Real Fuseki/TDB2 rehearsal | PASS | Apache Jena Fuseki 5.6.0 completed the recorded stages against the predecessor and candidate package digests. Exact quad comparisons covered repeated loading, a failing update, replacement, reopening the TDB2 store, and rollback. [Rehearsal result](../reviews/quality/rc-v1-fuseki.json) |
| WP6 independent audit preparation | PASS | The reproducible review packet has 100 representative selections, separate censuses and targeted risks, with unassessed verdict fields. [Review packet](../reviews/quality/rc-v1/independent-review.json) |
| Independent scientific verification | NOT RUN | An independent reviewer must assess the packet, source constraints, scope and negative controls. Technical conformance and pinned witness replay are producer checks. |
| WP7 coverage inventory | PASS | The report records domain breadth, editorial granularity, candidate dispositions, reviewed roles and source scope. [Coverage inventory](../reviews/quality/rc-v1/coverage.json) |
| WP8 checkout and CI verification | PASS | Checkout-based tests and deterministic build checks reproduce the package and review artifacts. CI runs the pinned predecessor comparison and source-evidence replay. Check the status for the exact candidate commit on PR #1. |
| WP9 documentation and WP10 readiness | PASS | The identity, source and consumer policies, verification procedure, and PR description draft are ready for owner review. [PR description draft](pr-v1-draft.md) |
| Publication approval | BLOCKED | Owner approval and outstanding rights and scientific reviews are required for promotion. |

The unassessed packet includes all six remaining scientific statements without
citations, the OntoMathPro universal-restriction control and cases for rejected
exact matches, scientific direction, theorem applicability and role
confusion. The earlier OntoMathPro reduced-group ambiguity stays unresolved.
The proof evidence is limited to the checked Lean fixtures. The Mathlib
declaration evidence remains textual. The sample design separates
proportional representative strata from risk-targeted cases and critical
censuses. Those targeted findings cannot estimate a graph-wide error rate.

## Ordered verification

1. Check out the candidate commit, install `requirements.lock` using
   Python 3.12, and resolve the predecessor commit from
   [the review plan](../reviews/quality/rc-v1-plan.json).
2. Run the unit and regression suite. The extended OntoMathEdu tests use
   the pinned ROBOT jar and the verified original snapshot. The GitHub
   evidence workflow records the exact acquisition steps.
3. Build the producer artifacts and verify the package, then run the
   competency suite. Compare the manifest and artifact bytes with those
   committed at the candidate SHA.
4. Extract the predecessor's `dist` from Git without activating either
   release in a production store. Run the pinned comparison and regenerate
   the independent review packet and coverage report.
5. Use Jena Fuseki 5.6.0 with a disposable local TDB2 store. Verify the
   downloaded archive and JAR against the checksums below. Run the
   rehearsal on both pinned packages.
6. Replay the source evidence and migration against the registered pinned
   bytes. Give the assessment templates and the cited source evidence to an
   independent reviewer. Record verdicts and any requested corrections
   separately. Review the open rights items with the owner.

```sh
python -m pytest -q
python -m pipeline.cli build
git diff --exit-code -- dist
python -m pipeline.package_check dist
python -m pipeline.competency

predecessor_dir=$(mktemp -d)
git archive bb65b889cf8444ef66eb17860eeefec9d513aa10 dist | tar -x -C "$predecessor_dir"
python -m pipeline.rc_review --predecessor "$predecessor_dir/dist" --output "$predecessor_dir/review"
diff -ru reviews/quality/rc-v1 "$predecessor_dir/review"

python -m pipeline.fuseki_rehearsal --jar "$fuseki_jar" \
  --predecessor "$predecessor_dir/dist" --candidate dist \
  --predecessor-digest 8b3395353d73cd3b3365933abfe9d3a0bdcc20f4be0757e01115994d8f278919 \
  --candidate-digest "$candidate_manifest_digest"
```

The Fuseki 5.6.0 Maven distribution archive
`apache-jena-fuseki-5.6.0.tar.gz` had SHA-256
`5833260ae40a4f0dadc92f11510ad836f00ef63f61ea25aabe16d02d697e818d`.
Its server JAR had SHA-256
`d28c1eaf703122ee628895a460c20fa4aa60a892f435d403ea8c036f241da1f8`.
The rehearsal starts a loopback-only server and disposes of its working
directory afterwards. [Maven distribution](https://repo.maven.apache.org/maven2/org/apache/jena/apache-jena-fuseki/5.6.0/)

This is a v1.0.0 release-candidate preparation. No stable release was published, PR #1 was not merged, and independent scientific verification remains a separate approval gate.
