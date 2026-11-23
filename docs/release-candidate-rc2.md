# v1.0.0-rc.2 readiness and review

The Foundation candidate advances the reviewed rc.1 commit
083f22b2f25c5cb520838c6b3eec22fea0072b6c. The six-file package retains
`curricula.rdf-release/v1`, all four logical graphs, every canonical IRI,
and the approved and rejected mapping ledgers. Its manifest SHA-256 is
`f4a07846eec3be96093fd0f3db7417735549dbc08729d5105a8e191ca51b00c3`.

| Review finding | rc.2 disposition |
|---|---|
| Six uncited dependencies | The CDCL clause-learning, estimator-bias, and generic graph-algorithm assertions were withheld. Huffman coding is represented by its existing prefix-code output claim. Probabilistic graphical models retain the reviewed joint-distribution representation. Gradient descent points to the gradient, with a replayable Euclidean multivariate source. |
| Knaster–Tarski | The definition specifies the induced fixed-point order, with a regression showing an ambient join that is not fixed. The Result role survives. |
| Cantor–Zassenhaus | The reviewed equal-degree finite-field factorization task replaces the generic single-polynomial output interpretation. |
| Result and proof roles | The two propositional-resolution soundness dependencies, the Bayes generic dependency, and the comparison sorting lower bound's decision-tree dependency are archived as withdrawals. |
| Bayes ordinary ratios | The pinned OpenStax conditional-ratio definition supplies the ordinary denominator conditions via the stated derivation. The totalized Mathlib passage remains visible as contrasting evidence. |
| Welch, deterministic PDA, covariance PCA | Assertion-level scope specifies the approximate Welch law, DPDA final-state acceptance, and column-mean centering for the covariance/SVD correspondence. |
| Topic guidance | Notes distinguish structural recursion, stochastic transition matrices, observed behavioral regression, and individual versus family views of context-free languages. The active A* concept is a child of heuristic search. MathModDB coverage notes distinguish task and model granularity. |

[Original rc.1 findings supplied to this task](../reviews/quality/rc2-input/rc1-findings.md) ·
[Correction ledger](../reviews/quality/relation-revisions.json) ·
[Scoped definitions and judgments](../reviews/quality/rc2-corrections.json)

## Release gates

| Gate | Status | Evidence |
|---|---|---|
| Scientific correction implementation | PASS | Citation enforcement finds no uncited scientific assertions in its defined scope. Role and provenance regressions cover the corrected assertions. |
| Package, clean rebuild and CI | See exact candidate checks | The release workflow rechecks RDF conformance, pinned successor compatibility and deterministic review artifacts. |
| Source notices and channel checks | PASS | The separate notice identifies 22 official and one experimental OpenMath dictionary, native STATO material and the evidence-only OpenDSA channel. The manifest binds the notice digest. [NOTICE.md](../NOTICE.md) |
| Owner or qualified rights clearance | BLOCKED | Confirm downstream compatibility with the OpenMath derivative-work conditions, the native STATO and embedded OBI boundary, and the OpenDSA evidence-only scope. |
| Fuseki/TDB2 | PASS | Jena Fuseki 5.6.0 imported rc.1, repeated loading, rolled back an injected failure, replaced it with rc.2, reopened the store and rolled back to rc.1. [Rehearsal record](../reviews/quality/rc2-fuseki.json) |
| Independent review of rc.2 | NOT RUN | The assessment fields are unassessed. The 148 rc.1 packet items include seven corrected, five withheld, seven requiring re-review, and 129 unchanged. The impact inventory compares artifacts rather than transferring verdicts. [Review packet](../reviews/quality/rc2/independent-review.json) · [Impact](../reviews/quality/rc2/change-impact.json) |
| Stable publication | BLOCKED | Independent review of the corrected candidate and owner approval remain separate gates. |

The OntoMathPro reduced-group scope and unclassified role endpoints remain
open research questions. Mathlib passage replay remains textual evidence.
Existing kernel-checked fixtures are recorded separately. The [coverage
inventory](../reviews/quality/rc2/coverage.json) describes the reviewed source
scopes and limits.

Reproduce with the checkout-based commands in the [package contract](contract-v1.md).
The review plan pins v0.9.0 and rc.1. Extract v0.9.0's `dist` and rc.1's
`dist` plus its `reviews/quality/rc-v1/independent-review.json` from Git.
Pass these paths to `python -m pipeline.rc_review --predecessor PATH --review-predecessor PATH --output PATH`.
Repeat the [Fuseki procedure](release-candidate-v1.md#ordered-verification)
with rc.1 as the rehearsal predecessor and the rc.2 digest above.
