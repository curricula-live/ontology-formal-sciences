# ontomath-pro

full Manchester ontology; OWLAPI conversion.

Upstream: https://github.com/CLLKazan/OntoMathPro

Attribution: CLLKazan/OntoMathPro. Terms: Apache-2.0. See source.yaml for acquisition details and ingestion.json, when present, for the measured graph size.

The review scope records a native E-number, a checked English label and an
editorial subject heading for each selected class. The generator emits SKOS
subjects and links to their editorial headings. Projected labels are adapted
from the pinned Apache-2.0 source, with its license included here.
Potential overlaps with authored concepts, OpenCS, STATO or another selected
class enter the review queue. OWL restrictions and class-level relationships
remain available in the staged source graph.

Replay with `ROBOT_JAR=/path/to/robot.jar python -m pipeline.cli replay-batch --source ontomath-pro`.
