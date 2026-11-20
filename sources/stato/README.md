# stato

1.5 release ontology.

Upstream: https://github.com/ISA-tools/stato

Attribution: ISA-tools/stato. Terms: CC-BY-3.0 (embedded imports have separate notices). See source.yaml for acquisition details and ingestion.json, when present, for the measured graph size.

The batch policy projects selected native STATO classes as subject headings
from distributions, statistical measures, models, testing, design and
estimation. The selection and editorial hierarchy adjustments are recorded
in admission.json. The projection adapts labels and selected named hierarchy
from the ISA-tools/STATO 1.5 snapshot under CC BY 3.0. Embedded imported
classes, textual definitions and OWL restrictions stay in source staging.
Reviewed existing topics retain their canonical identifiers. See the
[upstream license declaration](https://github.com/ISA-tools/stato/tree/a5910e6115217a88ee86e2666e12983ef2ef2a42#license).

Replay with `python -m pipeline.cli replay-batch --source stato`.
