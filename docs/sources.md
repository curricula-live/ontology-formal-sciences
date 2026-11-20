# Source inventory and attribution

Counts refer to one separately staged graph per processed family. The scope column identifies what was actually parsed. The release includes source-derived subjects from three pinned batches. Source graphs stay separate.

| Source | Status | Staged triples | Published links | Snapshot scope | Rights and attribution |
|---|---|---:|---:|---|---|
| [acm-ccs](https://www.acm.org/publications/class-2012) | blocked | 0 | 0 | 2012 Computing Classification System | permission unresolved, Association for Computing Machinery |
| [cso](https://cso.kmi.open.ac.uk/downloads) | aligned | 166,518 | 50 | full N-Triples release | CC-BY-4.0, Salatino et al., The Open University |
| [dbpedia](https://dbpedia.org/data/Graph_theory.ttl) | staged | 2,086 | 0 | Graph theory resource document | unverified, DBpedia contributors |
| [dlmf](https://dlmf.nist.gov/) | staged | 1 | 0 | one formula resource 5.2.E1; private reference | reference only, NIST DLMF |
| [dmop](https://bioportal.bioontology.org/ontologies/DMOP) | failed | 0 | 0 | DMOP ontology | unverified, e-LICO |
| [dublin-core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl) | staged | 700 | 0 | vocabulary dependency | reference only, DCMI |
| [edam](https://github.com/edamontology/edamontology) | staged | 36,888 | 0 | 1.25 ontology | CC-BY-SA-4.0, edamontology/edamontology |
| [mathlib4](https://codeload.github.com/leanprover-community/mathlib4/tar.gz/35f494609c32653bae53eb33f0cf2d899808909a) | staged | 32,592 | 0 | 8,728 module paths and 23,864 direct local imports from the pinned Mathlib archive | Apache-2.0, mathlib community |
| [mathmoddb](https://github.com/MaRDI4NFDI/MathModDB) | aligned | 45,029 | 1 | full ontology file | CC-BY-4.0, MaRDI4NFDI/MathModDB |
| [ml-schema](https://github.com/ML-Schema/core) | aligned | 441 | 1 | core schema | CC-BY-4.0, ML-Schema/core |
| [msc2020](https://github.com/TIBHannover/MSC2020_SKOS) | staged | 48,524 | 0 | suggestion 4 edition | CC-BY-NC-SA, TIBHannover/MSC2020_SKOS |
| [oeis](https://oeis.org/) | staged | 4,002 | 0 | A000045 index-value table; private staging only | CC-BY-SA-4.0, OEIS Foundation and sequence contributors |
| [ontodm](https://github.com/panovp/ontodm-core) | staged | 7,531 | 0 | complete OWL/XML document; imported ontology IRIs retained, imports not dereferenced | unverified, Panče Panov and OntoDM contributors |
| [ontomath-edu](https://github.com/CLLKazan/OntoMathEdu) | staged | 7,867 | 0 | complete Manchester document; 16 named-operand DisjointUnionOf frames translated to RDF lists | unverified, CLLKazan/OntoMathEdu |
| [ontomath-pro](https://github.com/CLLKazan/OntoMathPro) | aligned | 21,731 | 22 | full Manchester ontology; OWLAPI conversion | Apache-2.0, CLLKazan/OntoMathPro |
| [openalex](https://api.openalex.org/topics/T10374) | staged | 2 | 0 | one graph theory research topic | CC0-1.0, OurResearch |
| [opencs](https://opencs-ontology.github.io/) | aligned | 538,056 | 131 | full stable N-Triples release, content pinned | CC-BY-4.0, OpenCS contributors |
| [openmath](https://codeload.github.com/OpenMath/CDs/tar.gz/cbf607561e3f90630ce7a57fe9a85f5bc0dfdd3c) | staged | 4,687 | 0 | complete repository archive; extract symbols, descriptions and dictionary membership from all 216 official, experimental and contributed CDs | per dictionary, OpenMath Society and dictionary authors |
| [openmath-rdf](https://github.com/OpenMath/om-rdf) | staged | 270 | 0 | math schema | unverified, OpenMath/om-rdf |
| [owl](https://www.w3.org/2002/07/owl.ttl) | staged | 450 | 0 | vocabulary dependency | reference only, W3C |
| [prov-o](https://www.w3.org/ns/prov-o.ttl) | staged | 1,146 | 0 | vocabulary dependency | reference only, W3C |
| [qudt](https://qudt.org/) | staged | 132,359 | 0 | complete release ZIP; stage official QUDT-all-in-one-OWL.ttl (schema and vocabularies) | CC-BY-4.0, QUDT.org |
| [rdf-rdfs](https://www.w3.org/2000/01/rdf-schema.ttl) | staged | 87 | 0 | vocabulary dependency | reference only, W3C |
| [shacl](https://www.w3.org/ns/shacl.ttl) | staged | 1,128 | 0 | vocabulary dependency | reference only, W3C |
| [skos](https://www.w3.org/2009/08/skos-reference/skos.rdf) | staged | 252 | 0 | vocabulary dependency | reference only, W3C |
| [stato](https://github.com/ISA-tools/stato) | staged | 20,288 | 0 | 1.5 release ontology | CC-BY-3.0 (embedded imports have separate notices), ISA-tools/stato |
| [swo](https://purl.obolibrary.org/obo/swo.owl) | staged | 34,428 | 0 | published ontology file | unverified, Software Ontology contributors |
| [tptp](https://tptp.org/) | staged | 12 | 0 | PUZ001-1 problem; inventory annotated CNF formula names and roles only | unverified, TPTP World |
| [wikidata](https://www.wikidata.org/wiki/Special:EntityData/Q11348.ttl) | aligned | 6,127 | 1 | Q11348 mathematical function entity document | CC0-1.0, Wikidata contributors |
| [zbmath-open](https://api.zbmath.org/) | staged | 2 | 0 | one formal-logic bibliographic record; retain identifier and title in private staging | field-specific, FIZ Karlsruhe |

Source originals retain their own terms. The project publishes its own curation, concept references and limited reviewed evidence. The ML-Schema core snapshot retains its embedded CC BY 4.0 notice. Bundled Wikidata and OpenAlex documents are CC0. The two current classification blockers are detailed in continuation.md.

ROBOT 1.9.8 is used for Manchester syntax and OWL/XML. Install a Java runtime and download https://github.com/ontodev/robot/releases/download/v1.9.8/robot.jar, then set ROBOT_JAR to its path. The adapter enforces the digest in pipeline/parse/robot.sha256. Source-specific formats and revisions are recorded under sources/. Source manifests use JSON syntax, a YAML subset.

The Curricula legacy ontology repository archives V1 and treats V2 as a federation and pedagogy project. Its catalog was reviewed as a possible migration input. No legacy assertions were admitted.
