---
type: experiment
id: E7
status: LOCKED
date: 2026-09-20
tags:
  - experiment
  - preregistration
  - v3
  - ai-intervention
---
# E7 · Preregistration: universal answer AI, learning displacement and recovery

Locked on 2026-09-20 before any E7 simulation output existed.

E7 is a separate intervention engine layered on frozen V3. It does not modify `v3.py`, the V3 model
lock, or E5/E6 evidence. The user-specified focal intervention gives every eligible student access to
an AI answer service that produces a perfect homework score, gives no knowledge gain, and directly
reduces recorded confidence. E7 asks what adoption, displacement, dependency and recovery follow from
those assumptions. It does not claim those assumptions are universal empirical facts.

## 1. Evidence boundary

The focal scenario is motivated by peer-reviewed evidence that unguarded generative AI can separate
assisted performance from unaided learning:

- Bastani et al. (2025), *PNAS*, DOI
  [10.1073/pnas.2422633122](https://doi.org/10.1073/pnas.2422633122), randomized nearly 1,000 high-school
  mathematics students. Unguarded GPT raised assisted practice performance by 48% but reduced later
  unaided exam performance by 17% versus control; tutor guardrails largely removed the harm.
- Li, Liu and Dong (2025), *Australasian Journal of Educational Technology*, DOI
  [10.14742/ajet.9932](https://doi.org/10.14742/ajet.9932), reported improved task performance and
  self-efficacy alongside worse long-term knowledge transfer, with excessive reliance/cognitive
  outsourcing impeding acquisition.
- Azeem and Abbas (2025), *Education and Information Technologies*, DOI
  [10.1007/s10639-025-13489-6](https://doi.org/10.1007/s10639-025-13489-6), found in a three-wave
  observational survey that academic GenAI use was negatively associated with self-efficacy and
  performance and positively associated with learned helplessness.

The evidence does **not** identify a universal zero-learning effect, perfect AI accuracy, or a causal
per-use confidence decrement. Other peer-reviewed studies find positive learning or self-efficacy under
scaffolded use. Therefore `ai_grade=1`, `ai_learning_multiplier=0`, and the focal confidence decrement
are declared severe scenario inputs. E7 reports consequences conditional on them and includes no-loss
and learning-support controls. No empirical effect size is used to calibrate E7.

## 2. Questions

1. Does a perfect, low-effort AI answer service become widely adopted through neutral exploration and
   personal reinforcement, without an AI-prevalence term or assigned “AI-user” types?
2. Does adoption displace solving, discussion, human copying and persistent human source roles?
3. Does assisted homework performance separate from knowledge and unaided exam performance?
4. What happens when the AI is withdrawn halfway through the semester?
5. Which of access, effort cost, confidence loss, decision rule, withdrawal, learning support and
   symmetric social learning most affect adoption and learning?

## 3. Causal and network boundary

The AI is an external service, not an ordinary student node. It is not inserted into `graph_nodes` or
`graph_edges`, cannot discuss, copy, reciprocate, refuse, exhaust capacity or become a human source.
This preserves the student sociograph and prevents a universal star node from mechanically changing
degree, betweenness, path length or source-role metrics. “Connected to all” means universal eligibility
in the separate access layer.

No student is assigned an adopter, resistant student or dependent type. Static AI access is sampled
independently of student traits and graph position. There is no AI-use prevalence input. Students learn
the action value only through personal use; optional social learning treats S, D, C and AI symmetrically.
Confidence is measurement-only, as in frozen V3, and does not enter choice. Consequently the confidence
penalty cannot manufacture adoption; a confidence-feedback model would be a later, separately frozen
mechanism.

## 4. E7 action and state equations

Homework 1 is exact frozen V3 and AI is unavailable. From homework 2, an eligible student has a fourth
action A whenever the intervention is active. Initially

$$Q_i^A(0)=K_{0i}-\kappa_i,$$

identical to S, D and C. For A,

$$U_i^A=Q_i^A.$$

The V3 S/D/C utilities are unchanged. With probability $\epsilon$, choose uniformly among feasible
actions; otherwise use the condition's exploitation rule. Argmax is frozen V3 extended to A. Softmax is

$$P_i(a)=\epsilon/m_i+(1-\epsilon)
\frac{\exp((U_i^a-\max_bU_i^b)/\tau)}{\sum_b\exp((U_i^b-\max_cU_i^c)/\tau)}.$$

An AI action has grade 1, integer effort cost $c_A$, and reward $1-\kappa_i c_A$. In the focal scenario,
knowledge is unchanged. In the learning-support control,

$$K_i'=K_i+m_A\alpha_i(1-K_i),$$

where $m_A=1$ instead of 0. The control is a mechanism counterfactual, not a literal reproduction of a
particular tutor. Personal Q-learning is the frozen V3 update applied to the selected one of four actions.

For non-AI actions, confidence keeps the V3 measurement update. For AI use,

$$C_i'=\max(0,C_i-d_A).$$

The focal decrement is $d_A=.02$ per use; `.00` and `.05` structural controls and `.00`/`.04`
factorial endpoints test dependence on this uncalibrated input. Because C does not enter choice, a
confidence-penalty contrast on adoption is a locked negative control.

AI is always correct and draws no item randomness. Exams remain diagnostic, unaided and generated from
K exactly as in V3. A withdrawal condition masks A from homework 11 onward without resetting learned Q.

## 5. Seeds, replication and stopping

- Structural block S: master seed **920107**, 400 replicates, 12 conditions = **4,800 runs**.
- Factorial block F: master seed **920108**, 100 replicates, all 128 cells of a full $2^7$ design =
  **12,800 runs**.
- Bootstrap seed **920700**, 10,000 resamples. Smoke seed **920993**, two S and two F replicate worlds.
- AI-access stream code **701**, generated by `SeedSequence([master_seed, replicate, 701])` and shared
  across conditions within a block.
- Total full E7: **17,600 runs**. No optional stopping, interim inspection, tuning or condition removal.

Compatible conditions share graph, trait and semantic V3 draws. AI item answers consume no random draw.

## 6. Structural block S

The control calls frozen `simulate_v3` exactly. All intervention conditions use N=30, H=20, SBM, R=3,
unity weights and frozen V3 defaults except the listed change.

| Label | AI intervention |
|---|---|
| `E7-S-control` | no AI; exact frozen V3 |
| `E7-S-base` | universal from h2; grade 1; cost 0; learning 0; confidence decrement .02; argmax |
| `E7-S-conf0` | base, confidence decrement 0 |
| `E7-S-conf05` | base, confidence decrement .05 |
| `E7-S-cost1` | base, AI effort cost 1 |
| `E7-S-softmax010` | base, softmax tau=.10 |
| `E7-S-softmax025` | base, softmax tau=.25 |
| `E7-S-withdraw` | base, AI unavailable from h11 |
| `E7-S-learning` | base, AI learning multiplier 1 |
| `E7-S-access25` | base, 25% independently selected static access |
| `E7-S-social010` | base, action-symmetric social learning eta=.10 across four actions |
| `E7-S-H40` | base, H=40 |

For `access25`, exactly `ceil(.25N)` students with the lowest shared access uniforms are eligible.
Universal conditions include all N students.

## 7. Factorial block F

Every cell uses N=30, H=20, SBM, R=3 and the E7 engine.

| Bit | Factor | Low (0) | High (1) |
|---:|---|---:|---:|
| 0 | AI effort cost | 0 | 1 |
| 1 | confidence decrement | 0 | .04 |
| 2 | access fraction | .25 | 1.00 |
| 3 | decision rule | argmax | softmax tau=.10 |
| 4 | persistence | withdraw from h11 | available through h20 |
| 5 | AI learning multiplier | 0 | 1 |
| 6 | symmetric social learning | 0 | .10 |

Labels are `E7-F-<seven bits>` in this order. Report all seven main effects, all 21 two-way effects and
the targeted cost × choice and learning × persistence interactions for the primary outcomes.

## 8. Outcomes

Per run, reconstruct from raw canonical and E7 sidecar tables:

- `pA_available_late`: AI share over the last five homeworks on which A was available;
- `pA_late`, `pS_late`, `pD_late`, `pC_late`: action shares over final five homeworks;
- `adopter_share`: fraction using A at least once;
- `persistent_ai_share`: fraction using A at least three times over its final five available homeworks;
- `first_ai_mean`: mean first-use homework among adopters;
- `grade_late`, `reward_late`, `K_final`, `C_final`, `exam_final`, `grade_exam_gap`;
- human-copy success, human source top-20 share, human source Gini and strict residual source persistence;
- pre/post-withdrawal action shares for homeworks 6–10 and 11–15.

Primary factorial outcomes are `pA_available_late`, `pC_late`, `grade_late`, `K_final`, `C_final` and
`exam_final`. Importance is only over the stated endpoints.

## 9. Predictions and decision rules

All intervals are paired 95% percentile bootstrap intervals over replicate worlds. Practical deltas are
.02 for action shares, .05 for grade/exam, .01 for K, .05 for C and .10 for source persistence.

1. **P1 adoption:** base lower CI for `pA_available_late` > .20.
2. **P2 performance–learning separation:** base minus control is >+.10 for `grade_late` and <-.02 for
   `K_final`.
3. **P3 unaided deficit:** base minus control `exam_final` upper CI < -.03.
4. **P4 confidence scenario:** base minus control `C_final` upper CI < -.10. This validates the imposed
   scenario consequence; it is not an emergence claim.
5. **P5 human-copy displacement:** base minus control `pC_late` upper CI < -.05.
6. **P6 withdrawal dependence:** withdrawal minus control `exam_final` upper CI < -.03.
7. **P7 learning support:** learning-support minus base `K_final` lower CI > +.02.
8. **P8 confidence negative control:** conf05 minus conf0 on `pA_available_late` has its entire CI inside
   [-.02,+.02].
9. **P9 decision-rule adoption:** both softmax conditions independently have lower CI
   `pA_available_late` > .20. No direction versus argmax is predicted.

All structural contrasts and factorial effects are reported whether or not predicted. Boundary-inadequate
intervals are retained and not classified across their practical delta.

## 10. Raw data, integrity and claims

Canonical tables retain schema v3. E7 action A is stored in `decisions.action`; for AI rows,
`answer_id=h<h>-ai`, `root_id=-1`, `depth=0`, and `copy_success=null`. `P_S/P_D/P_C` remain their true
marginal probabilities and need not sum to one; `ai_decisions.parquet` supplies `P_A`, AI feasibility,
Q_A before/after, confidence before/after and mechanism inputs. `ai_access.parquet` stores static access.
The AI is absent from graph tables.

The runner must verify this preregistration and the V3 model lock, require a clean Git tree, run exact
control parity against frozen V3, refuse overwrite, run a deleting smoke, isolate full-run replicate
workers, hash every raw/derived file and report all failures. Calibration is omitted because no empirical
dataset is available.

E7 may support statements of the form “under this severe AI scenario, these patterns occur.” It may not
claim an expected real-world adoption rate, universal learning harm, causal confidence loss or a realistic
digital classroom.
