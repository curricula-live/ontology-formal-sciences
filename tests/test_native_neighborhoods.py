from pipeline.curate.neighborhoods import resolution


def test_source_neighborhood_distinguishes_exact_ambiguity_and_review():
    exact = {"left": {"canonical-a"}, "peer": {"canonical-b"},
             "alias": {"canonical-a"}, "conflict": {"canonical-b", "canonical-c"}}
    references = {"class-ref": {"canonical-a"}}
    rejected = {"negative": {"canonical-a"}}
    assert resolution("left", "peer", exact, references, rejected) == "two_canonical_subjects"
    assert resolution("left", "alias", exact, references, rejected) == "same_canonical_subject"
    assert resolution("left", "conflict", exact, references, rejected) == "ambiguous_admitted_identity"
    assert resolution("left", "class-ref", exact, references, rejected) == "needs_scoped_endpoint_review"
    assert resolution("left", "negative", exact, references, rejected) == "unresolved_with_negative_history"
