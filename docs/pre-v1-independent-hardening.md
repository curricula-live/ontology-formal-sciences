# Independent pre-v1 quality checks

This branch starts from the published v0.9.0 feature-head commit `bb65b88`.
It deliberately does **not** include the unpublished Codex v1 stabilization
workspace. Apply these small changes to the eventual release candidate only
after checking for conflicts with that workspace.

## New regression coverage

- The published canonical **asserted** SKOS broader hierarchy must be
  acyclic. This is a project editorial constraint, not a claim that all valid
  SKOS vocabularies are acyclic. Multiple parents remain valid. Source-native
  staging is unchanged.
- Real alignment decisions are invariant to the ordering of `closeMatch`
  and `exactMatch`. Two distinct exact targets for the same native entity
  remain disallowed.
- A synthetic RDF release is independently checked against the package
  verifier, including deliberately **rehashed** semantic discrepancies.
  Re-signing a corrupted artifact with an updated digest must not conceal
  TriG/N-Quads disagreement, standalone alignment drift, wrong graph names,
  incorrect counts, or failed validation.

These tests check editorial/technical invariants. They do not claim any
new scientific assertions or an independent scientific verification.

## Commands

From a clean checkout with the locked requirements installed:

```sh
python -m pytest -q tests/test_hierarchy_acyclic.py \
    tests/test_mapping_order_regression.py \
    tests/test_package_adversarial.py
python -m pytest -q
python -m pipeline.package_check dist
```

## Not a release approval

The following gates remain separate and cannot be inferred from passing
these tests: the unpublished v1 workspace, complete identity and relation
audits, source-rights adjudication, the consumer activation/rollback rehearsal
against the final candidate, independent scientific verification, and
explicit maintainer approval of the final merge/tag.

This hardening branch makes no tags, changes no stable version and does not
modify `main` or the formal-sciences feature branch.
