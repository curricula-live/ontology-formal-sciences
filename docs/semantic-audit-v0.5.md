# Endpoint and relation audit for v0.5.0

The review sampled six proposed MathModDB admissions and eight relations
with unresolved endpoints in v0.4.0. The review used version
`abbef1d` for the baseline and the proposed cohort in `ea5b0f2`.
Within each population, order by SHA-256 of the UTF-8 string
`"0.5.0-endpoint-audit\0" + key` and take the first six or eight.
A subject key is its complete native IRI and a relation key joins the
source ID and the three native edge fields with `|`. The NUL after the
salt is a single byte. Compare original descriptions, named profile
types, relation context and, where needed, the stored formula.

| Proposed subject | Audit judgment |
|---|---|
| Q6674367 | Accept the vanishing drag coefficient as an explicit modeling premise. Its placement and relation preserve the source approximation. |
| Q6822086 | Withdraw from this release. The small-angle damped solution has placeholder prose and a decaying-cosine formula using the undamped frequency. The missing approximation and initial conditions prevent projecting it as the documented solution. |
| Q6674260 | Accept Newton's equation in the constant-mass scope. The subject retains that qualification. |
| Q6821397 | Accept the pendulum initial-condition formulation. It stays a formulation subject rather than a particular measurement. |
| Q6822168 | Accept the small-angle, damped and driven model with all three qualifiers. |
| Q6821403 | Accept the general pendulum frequency record. The small-angle and damped-frequency topics are distinct source subjects. |

| Previously unresolved relation | Audit judgment |
|---|---|
| Q6821153 / P1674 / Q6674367 | The constant-length small-angle model carries the source's no-drag premise. |
| Q6684551 / P1560 / Q6673772 | The matrix record is the control input-to-state coefficient. Project that role in the documented linear reduction task. |
| Q6684561 / P1560 / Q6674147 | The bilinear time-evolution task includes a named initial condition. |
| Q6675406 / P1560 / Q6674368 | The drag model includes a specified initial-condition formulation. The link leaves its numerical values in the source. |
| Q6821405 / P147 / Q6821444 | The trajectory computation applies to the full pendulum model. The projection reverses the source's task direction. |
| Q6821405 / P147 / Q6821445 | The period calculation applies to the model. The original description mentions mass, which is absent from the dynamics of the ideal pendulum at fixed length and amplitude. The canonical relation records task applicability. |
| Q6684551 / P1560 / Q6673773 | The C matrix belongs to the linear output equation and projects to the output-matrix role, distinct from the B input-matrix role. |
| Q6674363 / P1674 / Q6674362 | The header names uniform gravitational acceleration and the source discussion contrasts it with inverse-square variation. The canonical link uses the spatially uniform field approximation. |

The follow-up review checked the related rejected relation
Q6822091 / P1560 / Q6822086 and retained its native key and rationale.
It also checked that the two example application-field exclusions derive
from actual MathModDB field, problem and model edges, that the finite
element method resolves to the existing OntoMathPro subject, and that
STATO's PLS score remains distinct from the regression coefficient
estimate. These are editorial observations on the selected sample.
