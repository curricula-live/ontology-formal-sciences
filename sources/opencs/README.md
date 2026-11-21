# opencs

full stable N-Triples release, content pinned.

Upstream: https://opencs-ontology.github.io/

Attribution: OpenCS contributors. Terms: CC-BY-4.0. See source.yaml for acquisition details and ingestion.json, when present, for the measured graph size.

The 0.4.0 subject policy selects named SKOS topics from twelve computing
families. It uses upstream scope paths, source labels and concordant reference
titles to select records for review. The witness table records the selection
paths and any admitted local hierarchy edges. Curricula groups the projected
topics under reviewed editorial headings. OpenCS contributors supply the
original labels and source hierarchy under CC BY 4.0. The projected Turtle
contains adapted selections. See the license in the source manifest.

Replay with `python -m pipeline.cli replay-batch --source opencs`.
Source IDs determine the persistent canonical suffixes. The pending queue
preserves possible duplicates for review.
