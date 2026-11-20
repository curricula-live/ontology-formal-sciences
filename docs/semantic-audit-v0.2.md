# Semantic audit of the v0.2.0 source batches

This review sampled 30 of the 2,091 newly minted topics at commit
`018153059cc604390c43e79f623a2c9921c2928f`. Each batch contributed ten topics.
Within each batch, select the ten earliest SHA-256 values of the UTF-8
string `"0.2.0-semantic-audit\0" + upstream_iri`, where `\0` is a NUL.
Use the source-to-canonical identities under `reviews/approved/batches/`
and keep the canonical slugs beginning with the batch name and a hyphen.
This excludes the 17 reused STATO identities from the sampling frame.

The review checked whether each name denotes a coherent subject, whether
the selected source provides evidence for the sense and whether the
canonical parent expresses a defensible topical scope. OpenCS checks used
the pinned SKOS labels, broader paths and reference targets. OntoMathPro
checks used the pinned English and Russian labels and named superclasses
where relevant. STATO checks used the pinned labels, definitions and named
superclasses. These are editorial judgments on one fixed sample.

## OpenCS

| Source ID | Topic | Finding |
|---|---|---|
| C29123 | Population protocol | **Adjusted.** The referenced model concerns distributed computation by interacting finite-state agents. Distributed computing is the appropriate heading for this computation model. |
| C44634 | Interaction design pattern | **Follow-up.** The source names the HCI pattern sense. A future HCI heading would give it a more specific home within the software topic area. |
| C40214 | Dirty paper coding | Accept. The reference denotes channel coding with state known to the encoder, within information theory. |
| C19404 | Integration testing | Accept. Both the source reference and topical path identify testing of software components in combination. |
| C37722 | Metro Ethernet | Accept. The referenced use of Ethernet for metropolitan networks fits the computer-networks scope. |
| C39005 | Stereoscopic Video Coding | Accept. Encoding stereoscopic video belongs in coding, with scope for a future media-compression heading. |
| C39942 | Cantor–Zassenhaus algorithm | Accept. The reference identifies finite-field polynomial factorization. Connect the existing topic to that problem rather than minting a second algorithm. |
| C44351 | Brown clustering | Accept. The reference denotes the class-based language-model clustering method, so machine learning is a reasonable editorial scope. |
| C39250 | Combinatory categorial grammar | Accept. The source reference identifies the formal grammar framework and supports its computing-foundations placement. |
| C6712 | Odlyzko–Schönhage algorithm | Accept. The reference identifies the algorithm for evaluating the Riemann zeta function at many points. A mathematical-use link would add precision. |

Population protocols originate in the model of computation described by
[Angluin et al., 2006](https://doi.org/10.1007/s00446-005-0138-3).
The editorial placement override preserves the source identity and the
original OpenCS selection witness.

## OntoMathPro

| Source ID | Topic | Finding |
|---|---|---|
| E775 | Penalty function method | Accept. The method fits numerical analysis, particularly numerical optimization. |
| E1690 | Bivector | Accept. An exterior-algebra object whose linear-algebra placement is valid. |
| E1575 | Spherical metric | **Follow-up.** The source gives the bilingual name and a generic metric superclass. Distinguish the spherical and chordal distance conventions before adding a definition or an equivalence link. |
| E290 | Fundamental group | **Adjusted.** The source labels and links to the based-loop homotopy invariant. The topology heading is more precise for this algebraic-topological construction. |
| E2211 | Nilpotent-by-finite polycyclic group | Accept. The label carries both qualifications and denotes a group-theoretic subject. |
| E1841 | Lindeberg theorem | Accept. The named topic belongs in probability theory. Use a qualified central-limit statement when adding a relationship for the result. |
| E2344 | Simple module | Accept. The source places the term under module, consistent with the algebra sense. |
| E2260 | Primary ideal | Accept. The source relationship to ideal fits the algebraic sense. |
| E1691 | Simple bivector | Accept. The source superclass is E1690. The decomposable special case is distinct from a general bivector. |
| E2149 | Free Abelian group | Accept. Both adjectives constrain the group topic and fit the current group heading. |

The fundamental group construction and its scope are explained in
[Hatcher, Algebraic Topology, Chapter 1](https://pi.math.cornell.edu/~hatcher/AT/AT.pdf).

## STATO

| Source ID | Topic | Finding |
|---|---|---|
| STATO_0000630 | Cohen's kappa | Accept. The definition identifies the chance-adjusted two-rater statistic, within measures of agreement. |
| STATO_0000427 | Restricted maximum likelihood estimation | Accept. The definition identifies variance-component estimation by REML. Retain the editorial likelihood-estimation grouping and avoid a claim of universally unbiased estimation. |
| STATO_0000529 | Scaled t distribution | **Adjusted.** The source describes both a shift and a scale. Use the label “Location-scale t distribution” and place it directly under probability distributions, since its own location and scale distinguish the family from the standard Student t density. |
| STATO_0000452 | Hotelling-Lawley trace | Accept. The alternate source name and cited test criterion identify a multivariate statistic. |
| STATO_0000079 | Bartlett's test for equal variances | Accept. The precise label distinguishes this use of Bartlett's name from other tests. The equal-variance-test heading matches the scope. |
| STATO_0000555 | Number of predictive components | **Follow-up.** The source describes a count input for PCA. The broad label is insufficient to distinguish retained principal components from predictive components in other models. |
| STATO_0000292 | Decile | Accept. The definition identifies a ten-part quantile and supports the quantile parent. |
| STATO_0000107 | Statistical model | Accept. The definition supports the general statistical sense. |
| STATO_0000003 | Balanced design | Accept. The source gives the equal group-size sense in experimental design. |
| STATO_0000464 | Linear mixed model | Accept. The named superclass supports the mixed-model interpretation. |

The location-scale parameterization is described by
[Stan's Student t distribution reference](https://mc-stan.org/docs/functions-reference/unbounded_continuous_distributions.html#student-t-distribution).

## Interpretation

The review accepted 24 sampled entries in their existing scope, corrected
three and left three for follow-up before asserting a more specific meaning.
The sample has equal allocation across sources of different sizes. Report
these as counts of reviewed entries and keep the per-source breakdown.
Candidate identity overlaps and scientific claims outside the sample require
their own review. The release manifest measures participation and components
using specific scientific predicates separately from the full topical graph.
