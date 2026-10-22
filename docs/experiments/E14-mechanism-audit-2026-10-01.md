# Why the classroom comparisons failed: mechanism audit

2026-10-01. Read-only review of the A28 engine and E14 outputs, with separately declared E15 diagnostic sensitivities. The historical engines and E14 source/output locks are preserved. This is an audit and proposal, not a new classroom model or empirical calibration.

## Main finding

The main problem is a mismatch between the interactions represented by the simulation and those manipulated in the studies. Several encoded assumptions also suppress the very composition effect being tested. No new arithmetic or scheduling defect causing the E14 findings has been demonstrated. Correct execution of the specified equations does not establish that those equations describe the classroom intervention.

The strongest demonstrated issues are: learning per elapsed time is unfavorable to a guided path at nominal settings; many delivered hints go unused; help quality is a weak scalar boost with no concept or explanation correctness; low students receive substantial automatic learning from helping other low students; and high-grade peers are particularly attractive sources of copied answers. Teacher attention, adaptive instruction, teaching rewards and collaborative group work are absent.

## 1. Controlled learning paths reveal a time/benefit mismatch

In `v4_declared.py:128`, a completed attempt multiplies remaining ignorance by `1 − min(1, alpha / attempt_learning_divisor × (1 + hint_learning_multiplier × hint))`. Peer-hint strength is `0.15 + 0.35 × provider_K` (`v4_declared.py:225`). Request plus hint service plus attempt takes at least `1+2+3=6` ticks (`declared_settings.py:156`), versus three ticks for an unaided attempt. Request delays can increase the guided cost further.

For a fixed learner at K=0.35 and nominal alpha=0.0584, compare predetermined activities over the same six ticks:

| Fixed path | Knowledge gain in normalized points |
|---|---:|
| Two unaided attempts | 2.506 |
| Hint from provider K=0.00, then one attempt | 1.455 |
| Hint from provider K=0.35, then one attempt | 1.610 |
| Hint from provider K=0.75, then one attempt | 1.787 |
| Hint from provider K=1.00, then one attempt | 1.898 |

With `a=alpha/3`, the break-even hint strength is `1−a≈0.981`, but the present default strength tops out at 0.5. This is an analytical identity at these fixed actions/nominal alpha, not a treatment estimate or a claim that teaching cannot help overall. Helping others, idle time, changed choices, feedback and future learning are excluded from this controlled comparison. The coefficient was chosen in the existing model trajectory, not estimated from students.

It explains why improving provider knowledge has a small direct learning benefit relative to the cost. Simply increasing the multiplier until a target result appears would fit the conclusion into the assumptions. Better measurements are the duration of explanation, learner practice during discussion, and learning conditional on the content actually explained.

## 2. Available hints are often not used

The A26 deadline guard works: a full attempt can fit after delivery. It guarantees the opportunity, not actual follow-through. Match E14 peer-hint receipts to completed attempts with `hint_source='peer'`; each stored hint is consumed at most once. Receipts that are overwritten, abandoned, or followed by submission/copying count as not consumed. These are descriptive pathway counts, not student subgroups for treatment effects.

| E14 condition | Delivered hints/student/episode | Guided attempts/student/episode | Hints not consumed, average replicate fraction |
|---|---:|---:|---:|
| Mixed four-person teaching | 0.193 | 0.121 | 37.8% |
| Homogeneous four-person teaching | 0.175 | 0.109 | 38.2% |
| Higher-knowledge peers, hint only | 0.194 | 0.124 | 36.0% |
| Higher-knowledge peers, copying allowed | 0.067 | 0.030 | 55.5% |

The lab intervention involved a shared puzzle and simultaneous group discussion with visible within-group performance ranks, rather than isolated paid-time requests followed by a separate optional attempt. This is a significant protocol mismatch. [Kimbrough, McGee and Shigeoka, author manuscript](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf).

**Proposed interaction:** a structured guided-practice activity with explanation and learner work during the same session, observable abandonment, and optional group discussion/broadcast. Keep voluntary homework help separate from the structured study protocol. Log both attendance and consumption; do not force every delivered hint to cause learning.

## 3. The current teaching model lets low groups teach almost like high groups

A provider with K=0 produces a positive-strength hint. A provider below the learner's skill still increases the learner's potential gain. No concept mastery, prerequisite, explanation accuracy, pedagogical ability or comprehension probability is checked. In contrast, a copied answer has stochastic item-level correctness. Thus hints are always beneficial when used, and copying has detailed success information; the representations are asymmetric.

Hint-provider selection uses contact closeness and delivery availability (`v4_public_ai.py:74`). Public grades influence answer-provider selection, not hint-provider quality selection. The directed access belief learns whether something arrives, not whether an explanation helps. A single global `B_hint` cannot distinguish effective and ineffective teachers. This does not leak hidden K into policy; rather, the agent lacks an observable source-quality channel.

**Proposed interactions:** task/topic mastery, explanation correctness, learner readiness and pedagogical skill; a private source-quality belief updated from observed guided outcomes, separate from availability. Policy must use that belief or disclosed assessment information, never another student's latent K. A scalar knowledge-gap transfer term is a possible interim approximation; concept-specific mastery is preferable because students with equal aggregate ability can know complementary material.

## 4. Automatic helper learning cancels much of the composition effect

Every completed hint service gives the provider learning proportional to its own remaining ignorance (`v4_declared.py:131`), regardless of whether the explanation is correct or later used. This is an assumption about learning by teaching, not a code error. Low helpers have more headroom, and in homogeneous groups they help other low students frequently.

The following arithmetic partition reconstructs every focal student's knowledge change from events; all per-student/episode sums agree within 1e−12. Values are normalized knowledge points per focal student over twenty episodes. The partition follows realized paths and is not a set of independent causal mediation effects.

| Condition | Own-attempt base gain | Extra gain from consumed hints | Gain while helping | Total gain |
|---|---:|---:|---:|---:|
| Mixed teaching | 29.093 | 0.884 | 1.267 | 31.244 |
| Homogeneous teaching | 28.911 | 0.650 | 1.623 | 31.184 |
| Low-knowledge peers, hint only | 29.028 | 0.700 | 1.692 | 31.421 |
| High-knowledge peers, hint only | 29.114 | 0.874 | 1.412 | 31.400 |

Mixed groups give stronger explanations, but low starters obtain less learning from being helpers: +0.234 hint-bonus points are offset by −0.356 helper-learning points, alongside +0.182 own-attempt base points. This is why the net knowledge advantage is only +0.060. The higher-peer-knowledge comparison has a similar cancellation. The simulation did not merely lack exposure to stronger peers; multiple encoded paths offset it.

**Proposed interaction:** learning from explaining material the provider can actually explain, with retrieval, explanation quality and opportunity cost represented separately. Preserve plausible learning by teaching among novices; do not set their helper gain to zero solely to reproduce the mixed-group advantage. Test this channel in isolation before changing the default.

## 5. Copying incentives are strong, and future test grades are not valued explicitly

The current objective follows the user's grade-at-low-effort specification. It prices immediate expected homework improvement and effort, while giving answer requests a shortfall bonus. Copying costs two ticks versus at least six for guidance. Public grades favor high-grade sources and blend their grades into copying predictions. In E14, higher-knowledge peers increased final copied share by 15.53 points and reduced attempts by 0.124 per episode; exam scores fell 2.01 points while homework rose 9.01.

`learning_value=0` deliberately removes intrinsic learning utility. Consequently `control` has no effect on the current score dictionary: perturbing it from zero to one produces identical scores. Exam feedback can change confidence, but it does not teach an action-specific value of studying for a future exam. Raising `eta_control` or changing the initial control distribution will therefore not repair this mechanism under the current objective.

**Proposed interaction:** an explicit weight on anticipated future unaided assessment grades, learned from observable assessment feedback and practice history, alongside current homework grades and effort. This can retain a grade/effort objective without inserting a hidden reward for true knowledge. Declare assessment timing, importance and policy permissions. Model inspection/detection or penalties only for protocols where they are present, rather than assuming all classrooms forbid or tolerate copying identically.

AI answer results should remain distinguished from peer tutoring. The field study's analysis emphasizes reduced engagement with practice as a mechanism, and guardrailed tutoring differs in how students interact with it. Matching an assisted/unassisted score direction is not independent validation of our assumed zero direct learning from copied answers. [Bastani et al., PNAS](https://www.pnas.org/doi/10.1073/pnas.2422633122).

## 6. The teacher channels needed for class size and some tracking results do not exist

E14 held expected friend degree at six. Smaller classes therefore did not give each student more teacher time, change explanation pacing, or reduce classroom disruptions. There is no teacher or curriculum in the engine. A weak/inconclusive size effect through this peer channel cannot adjudicate the class-size result. [Project STAR / Krueger](https://www.nber.org/papers/w6051).

**Proposed interactions:** a finite teacher-attention budget and queue/allocation policy; a task or instruction level; and fit between that level and students' observed readiness. Teacher targeting should use assessments, not an oracle reading latent student knowledge. Compare fixed versus adaptive instruction explicitly. Tracking in Kenya benefited students partly through instructional adaptation, whereas the university study found peer involvement differences without evidence of teacher adjustment. These contexts cannot be represented by one universal grouping coefficient. [Duflo, Dupas and Kremer](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf), [Booij, Leuven and Oosterbeek](https://leuven.economists.nl/pdf/ability_final.pdf).

A fixed total attention budget divided among more students mechanically changes available attention; that scaling is an identity. Its uptake, allocation and resulting class-level outcomes must still be tested, not presented as an emerged discovery.

## 7. Helper rewards and social involvement need explicit treatment arms

Helper willingness currently depends on a constant base, reciprocal availability and deadline urgency. It does not price the helper's effort trait, financial/grade rewards, or the learner's progress. Study interventions that reward helping cannot be recreated by seating changes alone. Seating with rewards and seating without rewards had different results in the field study. [Wu, Zhang and Wang, accepted manuscript](https://www.aeaweb.org/content/file?id=15848).

**Proposed interactions:** a helper choice comparing expected reward, reciprocal benefit and own time/effort costs; task-specific teaching feasibility; and observable engagement or peer norms. Keep financial/helper rewards separate from tournament rewards and student grade pressure. Static networks can still support learned participation and trust; graph rewiring is a separate, larger extension and is not needed for the first test.

## Minimal extension order and tests

| Priority | Interaction to add | Parameters to declare | Main test |
|---|---|---|---|
| 1 | Structured, content-dependent guided practice | Explanation duration, practice overlap, correctness/comprehension, pedagogical skill, topic/prerequisite settings | Mixed vs homogeneous under shared tasks; guidance completed vs abandoned; source-quality null |
| 2 | Helper decision and learning by explaining | Helper reward, effort weight, deadline cost, teaching feasibility, retrieval/explanation gain | Reward on/off at identical seating; helper-learning ablation; same students and graph |
| 3 | Teacher capacity and instructional fit | Total attention budget, allocation, instruction target/width, response to observed assessment | N=15/24 with identical pedagogy; fixed/adaptive instruction at identical grouping |
| 4 | Current and future assessment incentives | Homework/exam weight, horizon/discount, delayed credit, permission/inspection settings | Same resources and difficulty, different exam stakes; beliefs use observable evidence |

Each addition should be a separate fork with legacy parity at zero exposure, preserved semantic streams and raw logs of actual exposure, consumption, quality and feedback. Capacity/time conservation, no oracle information, impossible-provider controls, zero-dose controls and intervention-null controls are required. Compare one parameter at a time, or label bundled treatments and estimate their interaction explicitly. Validate intermediate quantities such as tutoring frequency and time use before comparing final scores. Empirically estimate rates where data permit; keep held-out conditions for prediction. Retain contrary results.

No universal effect of mean or SD is implied by these proposals. Hold focal students' knowledge fixed when isolating contextual peer distribution effects. The prior wide-distribution run changed own skills and peers jointly, and the truncated distribution changed its realized mean; it cannot identify a pure peer-SD effect.

## Audit and recovery record

The original E14 engine/source and derived-output hashes remain checked. The descriptive pathway audit reads 1,400 existing runs; the learning partition reads 400 of those runs and checks individual episode sums. Raw file hashes are checked for every table used. Code and tables are in `scripts/audit_e14_mechanisms.py`, `scripts/e14_learning_decomposition.py`, and `runs/E14-audit/` (successful partition under `learning_decomposition-r1`; the initial unfinished empty directory is retained).

E15 adds 1,000 diagnostic runs with settings locked before their outcomes: [diagnostic plan](E15-diagnostic-plan.md), `scripts/e15_diagnostic.py`, and `runs/E15-diagnostic/`. The first execution was interrupted. Recovery reused 471 hash-verified runs (246 hint / 225 copy), regenerated the remaining 529, and preserved ten partial/damaged directories plus interrupted inventories in the group recovery folders. Eight completion records were unreadable; mere presence of a completion marker was insufficient. The new resume utility checks configuration, engine hashes, software versions and raw hashes before reuse. Regression tests cover missing and damaged markers and byte-identical recovery. This interruption is separate from the numerical-model shortcomings above. All 114 targeted tests passed.

The diagnostic parameter results are exploratory and appear below after raw auditing. They are sensitivity probes, not fitted coefficients, recommended defaults, or evidence that we have reproduced the human studies.

## E15 diagnostic results

All 1,000 runs passed full raw-table audits; source/configuration/output hashes match the diagnostic locks. Outcomes below are high-peer minus low-peer final unaided exam points for the fixed low starters. The last column is the paired change in that peer effect relative to its family's reference. Fifty classroom replicates, pointwise 95% bootstrap Monte Carlo intervals, no multiplicity adjustment. The values are deliberately not an optimization grid or a new default selection.

| Channel and one-parameter probe | Peer effect (pp) | Pointwise interval (pp) | Change from reference (pp) |
|---|---:|---|---:|
| Hint only: reference | −0.058 | [−0.160, +0.036] | 0.000 |
| Provider-knowledge weight 0.35 → 0 | −0.116 | [−0.222, −0.013] | −0.058 |
| Generic hint boost 0.15 → 0 | +0.013 | [−0.107, +0.133] | +0.071 |
| Hint service two ticks → one | −0.049 | [−0.187, +0.084] | +0.009 |
| Provider-knowledge weight 0.35 → 0.85 | +0.133 | [approximately 0, +0.271] | +0.191 |
| Hint learning multiplier 1 → 2 | +0.098 | [−0.009, +0.196] | +0.156 |
| Copying allowed: reference | −1.933 | [−2.204, −1.640] | 0.000 |
| Grade shortfall pressure 0.4 → 0 | −2.173 | [−2.462, −1.907] | −0.240 |
| Public-grade blend 0.5 → 0 | −1.231 | [−1.493, −0.969] | +0.702 |
| Grade target weighting 3 → 0 | −2.107 | [−2.351, −1.867] | −0.173 |

Increasing quality sensitivity or the learning multiplier shifts the peer effect upward, but the resulting exam advantage remains small. The steeper-quality lower bound is numerically at zero and should not be promoted as robust evidence of replication. Shortening service alone scarcely changes the peer effect. Weak quality sensitivity is one cause, while hint consumption and offsetting helper gains remain important.

Removing public-grade blending reduces the negative peer effect by +0.702 pp (pointwise interaction interval [+0.329,+1.085]), identifying a contribution of this channel within the current model. Copying is still relatively fast, higher-grade eligibility still holds, and an outcome-trained copying belief still exists, so the effect remains negative. Removing either the explicit grade-pressure bonus or grade-based target weighting does not eliminate it; their interaction intervals include zero. It would be incorrect to blame only one pressure parameter or assume their contributions are additive.

The first extension should therefore address the tutoring activity and its content, including helper learning and observed quality. Teacher capacity/instruction and helper rewards are subsequent, separately specified interventions for the corresponding field studies. These changes should improve the causal representation, not promise the same sign in every setting.
