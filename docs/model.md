# Identity, evidence and inference

Each admitted topic owns one permanent concept IRI and one editorial scheme. The IRI suffix is assigned once. Changing a preferred label preserves the IRI. Introduce an explicit migration for a split, retirement or replacement. Namespace URLs are identifiers; dereferencing is future infrastructure.

Author topic membership in domains/<owner>/modules. skos:broader expresses broader subject scope. A named OWL subclass is a different kind of assertion. Add cross-module statements under links and cross-disciplinary statements under _shared/bridges. Definitions elaborate selected concepts. Bibliographic metadata, pedagogical placement, inferred relations and program implementation remain separate from topic identity.

Candidate keys normalize Unicode, case and whitespace for lookup. The original source graphs preserve lexical terms, including accents and language tags. Untagged labels may suggest English candidates. Multiple hits are retained. Review subject type, neighboring terms, upstream identifiers and known sense; approval records pin the original statements and their digest. A disagreement, such as the CSO finite automaton link to Finite_set, stays visible in the rejection register. Each upstream release has a separate staging store. Changed source bytes require renewed source evidence checks.

SKOS exactMatch identifies reviewed matching topics. RDFS seeAlso points to a relevant external class, individual or record without asserting identity. The two project properties v:uses and v:solves run from the method to its ingredient or problem and have no inferred closure. No transitive rules apply to an association. The release infers only inverse narrower edges and the reverse of related edges. Every inferred edge has a single reverse premise recoverable in graph/asserted. Inference remains queryable in graph/inferred.

Each authored topic has a PROV link to its owning module, whose digest is recorded. Link and bridge assertions are individually reified with their module provenance. Each published mapping has a reified review record, original entity, source URL and snapshot digest. The per-decision N-Triples witnesses are replayable against the disk-backed staged graph. Initial editorial decisions are proposed for maintainer review through the pull request.

## Competency queries

Run docs/cross-domain.rq against dist/formal-sciences.ttl to list methods using an ingredient owned by a different domain. For the SAT slice, query:

    PREFIX c: <https://curricula.live/id/formal-sciences/concept/>
    PREFIX v: <https://curricula.live/id/formal-sciences/vocab/>
    SELECT ?algorithm WHERE { ?algorithm v:solves c:boolean-satisfiability ; v:uses c:unit-propagation }

The expected subjects are c:dpll-algorithm and c:conflict-driven-clause-learning. To inspect a source mapping, bind rdf:subject to the canonical IRI inside graph/provenance and request rdf:object, prov:hadPrimarySource and dct:identifier.

The normalized lookup graph has its own graph name and disk store under .cache/index-v1. It preserves the language of each label and never replaces a raw RDF literal. Source-specific SPARQL ASK probes verify that each staged document contains expected content, including the OWL disjoint union in OntoMathEdu and a unit instance in QUDT. The normalization reports record how many lookup keys and proposed pairs were measured. The two rights-cleared CS vocabularies also have committed pending queues. Other candidate files are private build products. Project-specific uses and solves links with reviewed bibliography entries expose their scientific references via dct:source on the reified assertion.

## Scientific relations and applicability

The vocabulary declares each directional predicate's subject, object and scope. `represents` links an encoding to a structure it can express. `recognizesExactly` links a machine **model** to its language family, while individual machines recognize individual languages. `hasProperty` records an established property of a subject, such as memorylessness of the exponential law. `requiresAssumption` scopes a method's standard guarantee. `computes` identifies an output quantity, and `guarantees` identifies a property of the result or its relationship to the input. A Tseitin encoding, for example, guarantees equisatisfiability despite introducing auxiliary variables. The reasoner propagates none of these directional predicates.

The scientific-methods bridge and link modules pair each custom-predicate assertion with a bibliographic citation in `reviews/approved/citations.json`. The release publishes the citation on the reified assertion in the provenance graph. See the [competency queries](queries/README.md) for executable examples.
