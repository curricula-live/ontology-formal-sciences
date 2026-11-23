# ontomath-edu

complete Manchester document; 16 named-operand DisjointUnionOf frames translated to RDF lists.

Upstream: https://github.com/CLLKazan/OntoMathEdu

Attribution: CLLKazan/OntoMathEdu. Terms: unverified. See source.yaml for acquisition details and ingestion.json, when present, for the measured graph size.

## Verification of class partitions

The pinned Manchester document contains 16 `DisjointUnionOf` axioms on 15 named classes. One class has two distinct partitions. The 40 operand occurrences and their owners refer to 48 distinct classes. The adapter translates each partition into a separate `owl:disjointUnionOf` RDF list in source order and passes the remaining frames to ROBOT 1.9.8. The axiom says that every instance of the owner belongs to exactly one of the listed classes and each operand is a subclass of the owner. [OWL 2 Direct Semantics, Table 5](https://www.w3.org/TR/owl2-direct-semantics/#Class_Expression_Axioms)

This source-specific adapter handles named, locally declared operands and resolves their prefixes. It stops on unsupported class expressions, unknown prefixes, missing declarations, repeated operands and incomplete lists. A revision introducing annotated partitions or anonymous operands needs a conversion review.

With the repository dependencies, Java and the pinned ROBOT JAR installed, run from the checkout root:

```sh
python -m pipeline.cli fetch --source ontomath-edu
ROBOT_JAR=/path/to/robot.jar python -m pytest -q tests/test_ontomath_edu.py
```

The full-source check compares OWLAPI's reading of the emitted RDF with the original Manchester document after removing exactly the 16 partition frames. For the pinned snapshot, ROBOT reported zero lost axioms and exactly the 16 added partition axioms. Their owners and operand sets match a digest computed independently from the Manchester source. The output contained 7,867 triples. The reasoner check uses an isolated test partition. HermiT detects that membership in overlapping operands and membership in the owner outside every operand are each impossible. Both corresponding witness classes are satisfiable in the control ontology without that partition.

The OWLAPI and HermiT checks require `ROBOT_JAR`. The full-source check also needs the checksum-verified local snapshot. Offline CI can run the named-list and malformed-input tests using synthetic fixtures. Original OntoMathEdu content stays in private staging while redistribution terms remain unverified.
