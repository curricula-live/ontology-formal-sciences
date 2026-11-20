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
| branching-time-verification | CTL state labeling uses fixed-point iteration, with a reference to Clarke, Grumberg and Peled's Model Checking. |
| verification | Automata-theoretic LTL model checking uses a Büchi automaton. |
| information-measures | Six pairs connect a measure to its statistical ingredient, including conditional entropy to conditional distribution and mutual information to both joint distribution and product of marginals. |
| numerical-assumptions | The conjugate-gradient method assumes symmetric positive definiteness in its standard real linear-system guarantee. |
| mapping-evidence | Graph theory has reviewed exact matches to CSO graph_theory and OpenCS C14693, each with a source URL and pinned SHA-256. |
| algorithm-evidence | The 2-SAT implication-graph algorithm uses a directed graph and strongly connected components. Both assertions cite Aspvall, Plass and Tarjan (1979). |

The source of each algorithm-evidence row is the published article [A linear-time algorithm for testing the truth of certain quantified boolean formulas](https://doi.org/10.1016/0020-0190(79)90002-4). The scientific assertions in these queries describe the scopes in their canonical definitions. In particular, the release associates exact marginal computation with the tree case. Loopy sum-product has different convergence and accuracy properties.
