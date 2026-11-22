# Identity, evidence and inference

Each admitted topic owns one permanent concept IRI and one editorial scheme. The IRI suffix is assigned once. Changing a preferred label preserves the IRI. Introduce an explicit migration for a split, retirement or replacement. Namespace URLs are identifiers; dereferencing is future infrastructure.

Author topic membership in domains/<owner>/modules. skos:broader expresses broader subject scope. A named OWL subclass is a different kind of assertion. Add cross-module statements under links and cross-disciplinary statements under _shared/bridges. Definitions elaborate selected concepts. Bibliographic metadata, pedagogical placement, inferred relations and program implementation remain separate from topic identity.

Candidate keys normalize Unicode, case and whitespace for lookup. The original source graphs preserve lexical terms, including accents and language tags. Untagged labels may suggest English candidates. Multiple hits are retained. Review subject type, neighboring terms, upstream identifiers and known sense; approval records pin the original statements and their digest. A disagreement, such as the CSO finite automaton link to Finite_set, stays visible in the rejection register. Each upstream release has a separate staging store. Changed source bytes require renewed source evidence checks.

SKOS exactMatch identifies reviewed matching topics. A closeMatch can support topical review but does not resolve a scientific endpoint. RDFS seeAlso points to a relevant external class, individual or record. The two project properties v:uses and v:solves run from the method to its ingredient or problem and have no inferred closure. No transitive rules apply to an association. The release infers only inverse narrower edges and the reverse of related edges. Every inferred edge has a single reverse premise recoverable in graph/asserted. Inference remains queryable in graph/inferred.

Each authored topic has a PROV link to its owning module, whose digest is recorded. Link and bridge assertions are individually reified with their module provenance. Each published mapping has a reified review record, original entity, source URL and snapshot digest. The per-decision N-Triples witnesses are replayable against the disk-backed staged graph. Initial editorial decisions are proposed for maintainer review through the pull request.

## Competency queries

Run docs/cross-domain.rq against dist/formal-sciences.ttl to list methods using an ingredient owned by a different domain. For the SAT slice, query:

    PREFIX c: <https://curricula.live/id/formal-sciences/concept/>
    PREFIX v: <https://curricula.live/id/formal-sciences/vocab/>
    SELECT ?algorithm WHERE { ?algorithm v:solves c:boolean-satisfiability ; v:invokesAlgorithm c:unit-propagation }

The expected subjects are c:dpll-algorithm and c:conflict-driven-clause-learning. To inspect a source mapping, bind rdf:subject to the canonical IRI inside graph/provenance and request rdf:object, prov:hadPrimarySource and dct:identifier.

The normalized lookup graph has its own graph name and disk store under .cache/index-v1. It preserves the language of each label and never replaces a raw RDF literal. Source-specific SPARQL ASK probes verify that each staged document contains expected content, including the OWL disjoint union in OntoMathEdu and a unit instance in QUDT. The normalization reports record how many lookup keys and proposed pairs were measured. The two rights-cleared CS vocabularies also have committed pending queues. Other candidate files are private build products. Project-specific uses and solves links with reviewed bibliography entries expose their scientific references via dct:source on the reified assertion.

## Scientific relations and applicability

The vocabulary declares each directional predicate's subject, object and scope. `represents` links an encoding to a structure it can express. `recognizesExactly` links a machine **model** to its language family, while individual machines recognize individual languages. `hasProperty` records an established property of a subject, such as memorylessness of the exponential law. `requiresAssumption` scopes a method's standard guarantee. `computes` identifies an output quantity, and `guarantees` identifies a property of the result or its relationship to the input. A Tseitin encoding, for example, guarantees equisatisfiability despite introducing auxiliary variables. The reasoner propagates none of these directional predicates.

The scientific-methods bridge and link modules pair each custom-predicate assertion with a bibliographic citation in `reviews/approved/citations.json`. The release publishes the citation on the reified assertion in the provenance graph. See the [competency queries](queries/README.md) for executable examples.

## Scientific roles

A canonical entity remains a SKOS concept. Optional
`v:hasScientificRole` statements use role resources in the existing
vocabulary namespace. They classify the reviewed scientific scope of a
subject and do not establish OWL class membership or subtype inference.
One subject may carry several agreed roles. The candidate assigns roles
only where a definition or cited statement warrants them. SKOS hierarchy,
label similarity and source ontology class membership do not generate roles.

The initial choices include subject area, topic, structure, property, result,
problem, algorithm, method, model, formalism, implementation and assumption.
SHACL checks that role values are declared and used by canonical concepts.
It rejects an abstract algorithm conflated with the concrete implementation.
The [predicate review policy](../reviews/quality/predicate-roles.json)
checks positively known incompatible endpoints, records explicit exceptions
when backed by review, and reports unknown classifications for inspection in
the manifest. A missing role does not remove an assertion.

The [relation vocabulary](../domains/_shared/vocabulary/relations.ttl)
defines each directional predicate and its intended scope. The following
distinctions guide typed reviews.

| Predicate family | Intended direction and scope |
|---|---|
| `solves`, `hasInputStructure`, `computes`, `analyzes` | Method to task, task to mathematical input structure, method to result quantity, analysis to subject of examination. Solvers of one problem need not coincide. |
| `uses`, `invokesAlgorithm`, `implementsAlgorithm`, `executesImplementation`, `supportsOperation` | Method to ingredient, calling procedure to subroutine, artifact to abstract algorithm, run to concrete implementation, structure to operation it provides. Topical associations are insufficient evidence. |
| `hasProperty`, `guarantees`, `requiresAssumption`, `requiresPremise`, `proves`, `recognizesExactly` | Distinguish stated condition, applicability, theorem hypothesis, proof, result, and families of recognized languages. Domain restrictions travel with the evidence. |
| `represents`, `containsSymbol`, discretization and modeling predicates | Keep encoded objects, expression occurrences, models and assumptions distinct from equivalence and mathematical dependencies. |
| `usesReferenceDistribution`, estimation and evaluation predicates | Distinguish test reference law from model assumption, estimator from estimate, evaluation specification from result and measure. |

Rules supplied by external OWL restrictions retain their native axiom shape.
The asserted graph carries only projections licensed by the reviewed
shape and scientific scope. An all-values restriction supplies a conditional
constraint and cannot introduce an existential relation. The inference
graph still contains only the two documented SKOS rules.

Provenance distinguishes bibliography, source replay of exact passages or
axioms, textual declarations, and the small set of locally checked Lean
fixtures. Role and predicate QA and independent scientific agreement are
separate checks.
