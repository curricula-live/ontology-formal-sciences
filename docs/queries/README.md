# Competency queries

Run `python -m pipeline.competency` from the checkout after building the release. An optional positional argument selects an alternate release N-Quads file. Each query is also ordinary SPARQL 1.1 and selects its required named graphs explicitly. JSON output retains complete identifiers and source references.

| Query | Results from the scientific-methods slice |
|---|---|
| shortest-paths | Dijkstra uses weighted graphs under its nonnegative-weight guarantee. Bellman–Ford permits negative edges and assumes no reachable negative cycle for finite distances to all reachable vertices. |
| sat-and-complexity | DPLL and CDCL both use unit propagation to solve Boolean satisfiability, an NP-complete decision problem. |
| distribution-properties | The exponential and geometric distributions are memoryless on their respective continuous and discrete time scales. |
| linear-regression | Ordinary least squares and the QR least-squares method solve the linear least-squares problem. The numerical method uses QR factorization. |
| factor-inference | Sum-product on a tree factor graph computes variable marginal distributions for a normalizable probability model. |
| languages | Finite automata recognize exactly the regular languages. Nondeterministic pushdown automata recognize exactly the context-free languages. |
| branching-time-verification | CTL state labeling uses fixed-point iteration over sets of states, with a reference to Clarke, Grumberg and Peled's Model Checking. |
| ground-euf-reasoning | The congruence-closure decision procedure uses a disjoint-set data structure for the ground equality fragment. |
| finite-field-factorization | The OpenCS Cantor–Zassenhaus subject connects to square-free inputs and irreducible factors in equal-degree finite-field factorization. |
| cso-ontomath-reconciliation | Shared canonical targets connect approved CSO topic mappings and OntoMathPro class references for number theory, numerical analysis, conditional probability, random walks and regression analysis. |
| source-discretization | The plate-with-hole elasticity model links to its weak form and discretized weak model. Both links expose the MathModDB property and the common source digest. |
| stato-opencs-reference-law | The OpenCS Welch test maps to a canonical subject whose Student t reference link comes from the pinned STATO subclass restriction. |
| theory-combination-assumptions | The standard Nelson–Oppen framework uses disjoint signatures and stable infiniteness as explicit assumptions. |
| finite-element-endpoint-resolution | The MathModDB plate discretization task uses the existing OntoMathPro finite element method subject. The evidence exposes both native IRIs. |
| poisson-optimization-bridge | The MathModDB likelihood-maximizing task links its mathematical formulation to the canonical statistical Poisson log-likelihood. |
| system-f-evidence | The OpenCS System F topic resolves to the canonical calculus, which carries a source-cited strong normalization property. |
| verification | Automata-theoretic LTL model checking uses a Büchi automaton. |
| information-measures | Six pairs connect a measure to its statistical ingredient, including conditional entropy to conditional distribution and mutual information to both joint distribution and product of marginals. |
| numerical-assumptions | The conjugate-gradient method assumes symmetric positive definiteness in its standard real linear-system guarantee. |
| mapping-evidence | Graph theory has reviewed exact matches to CSO graph_theory and OpenCS C14693, each with a source URL and pinned SHA-256. |
| algorithm-evidence | The 2-SAT implication-graph algorithm uses a directed graph, strongly connected components and material implication. |
| binomial-sampling-bridge | Trace binomial and hypergeometric probability mass through binomial coefficients to an OpenMath formula and its expression fingerprint. |
| hypergeometric-normalization | Follow hypergeometric mass normalization to Vandermonde's identity and its named Lean proof. |
| ml-schema-evaluation-chain | Trace evaluation output and measure through separate ML-Schema existential witnesses. |
| many-one-reduction-composition | Connect OpenCS reduction and function composition topics through a named Mathlib declaration, with distinct mapping strengths. |
| empirical-multiset-frequency | Follow a STATO empirical distribution to multiplicity and cardinality through the pinned Mathlib singleton formula. |
| automatic-differentiation-product-rule | Find the product rule used in forward-mode differentiation with independent OpenMath and Mathlib witnesses. |
| rice-halting-proof | Find the proof of fixed-input halting undecidability and the textual occurrence of Rice's theorem. |
| openmath-rounding-guard | Inspect the native guard symbols of the half-integer ties-to-even rule. |
| ontomath-complex-coordinates | Join an OntoMathPro class reference and a source-backed complex coordinate equivalence. |
| welch-test-input-roles | Distinguish Welch's statistic and reference distribution while retaining their shared native input predicate. |
| dijkstra-implementation-and-assumption | Join the Princeton executable, its indexed queue, and the abstract algorithm's edge-weight condition. |
| spectral-clustering-mathematics | Join the admitted OpenCS clustering topic to its normalized graph embedding and Laplacian. |
| nfa-subset-construction | Follow an NFA through the power-set construction to the DFA and its language guarantee. |
| naive-bayes-feature-independence | Find the conditional independence assumption and probability rule used in Naive Bayes. |
| compiler-alias-analysis | Trace the LLVM loop transformation to alias analysis and the property under analysis. |
| postgres-index-operations | Compare supported equality and range operations for specific PostgreSQL index access methods. |
| lean-boolean-property-evidence | Find OpenMath and checked local Lean evidence for the same Boolean property. |
| fixed-point-theorem-premises | Find the hypotheses and guarantee of Knaster–Tarski and the archived prior predicates. |

The source of each algorithm-evidence row is the published article [A linear-time algorithm for testing the truth of certain quantified boolean formulas](https://doi.org/10.1016/0020-0190(79)90002-4). The scientific assertions in these queries describe the scopes in their canonical definitions. In particular, the release associates exact marginal computation with the tree case. Loopy sum-product has different convergence and accuracy properties.

The v0.9.0 queries exercise A* identity resolution and applicability,
the bipartite input of the assignment problem, the elementary Bayes
premise with its evidence mode, and the subroutine documented for X-fast
trie lookup within a Y-fast trie. The stochastic-grammar query joins a
computing subject to the distribution over rules for one nonterminal.
A queried path joins explicit claims at
their stated scope. It supplies no transitive dependency or assumption rule.
