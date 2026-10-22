---
type: experiment
id: E6
status: LOCKED
date: 2026-09-20
locked: 2026-09-20
tags:
  - experiment
  - preregistration
  - v3
  - robustness
---
# E6 · Preregistration: structural robustness and global sensitivity of V3 (LOCKED)

Locked on 2026-09-20 after Vavan instructed “do E6, except calibration. I don't have the data.” No E6
simulation or outcome existed at lock time. E6 deliberately omits empirical calibration and makes no
claim about real-student parameter values. The frozen E5/V3 evidence remains unchanged. E6-only choice
and reward variants are separate experimental implementations and may not modify `v3.py` or its model lock.

## 1. Questions

1. Does prevalence-free copying survive homogeneous traits, probabilistic softmax choice, alternative
   reward/cost rules, removal of the reliability utility bonus, wider class sizes, longer/shorter horizons
   and lower/higher graph density?
2. Across deliberately broad factor endpoints, which of copying cost, reinforcement, exploration, seed,
   sharing, belief learning, symmetric social learning and routing depth most affect copying, learning,
   source persistence and multi-hop flow?
3. Which pairwise interactions, and specifically cost × reinforcement × exploration, are material?
4. Do persistent source roles remain after controlling degree, betweenness, community, traits and each
   half-semester's opportunity to originate an answer?

E6 is a structural and computational robustness study, not calibration. Endpoint importance means
importance over the ranges below, not universal parameter importance.

## 2. Seeds, replication and stopping

- Structural block S: master seed **920006**, 400 replicates, 14 conditions = **5,600 runs**.
- Factorial block F: master seed **920007**, 100 replicates, all 256 cells of a full $2^8$ design =
  **25,600 runs**.
- Bootstrap seed **920600**, 10,000 resamples. Source-null seed **920601**, 999 permutations per
  structural-baseline replicate. Smoke seed **920994**, two S replicates and two F replicates.
- Total full E6: **31,200 runs**. No optional stopping, interim inspection, tuning or condition removal.
- Compatible conditions within a block and replicate share graph seeds and semantic draws. Size changes
  are paired by replicate identifier but are not called strict common-random-number pairs.

## 3. Structural block S

The reference is frozen `V3Params()`, SBM, R=3, unity weights. Homework 1 always follows the frozen
seed rule. From homework 2, variants differ only as listed.

| Label | Difference from frozen baseline |
|---|---|
| `E6-S-base` | none; calls frozen `simulate_v3` |
| `E6-S-homogeneous` | K0_sd=alpha_log_sd=kappa_log_sd=0 |
| `E6-S-softmax010` | epsilon/feasible exploration plus softmax exploitation, temperature 0.10 |
| `E6-S-softmax025` | same, temperature 0.25 |
| `E6-S-knowledgeReward` | personal reward = committed K after homework − kappa_i × cost |
| `E6-S-noCostReward` | personal reward = homework grade; logged effort cost remains unchanged |
| `E6-S-noAccessUtility` | copying utility is Q_C; A still learns and routes requests |
| `E6-S-equalCost` | successful-copy cost=1 |
| `E6-S-N15` | N=15, mean degree 6 |
| `E6-S-N120` | N=120, mean degree 6 |
| `E6-S-H10` | H=10 |
| `E6-S-H80` | H=80 |
| `E6-S-d2` | mean degree 2 |
| `E6-S-d10` | mean degree 10 |

For a feasible student under softmax, with $m$ feasible actions,

$$P(a)=\epsilon/m+(1-\epsilon)\frac{\exp((U_a-\max_b U_b)/\tau)}
{\sum_b\exp((U_b-\max_c U_c)/\tau)}.$$

Isolates still choose S. The existing strategy uniform samples this distribution. Every action remains
treated symmetrically. The knowledge-reward and no-cost-reward variants change only the personal Q
target; state learning, answers, sharing and belief updates remain frozen V3.

Early is homeworks 1–5 (1–min(5,H)); post-seed is 2–min(5,H); late is the final five homeworks.
Source halves are 2–floor(H/2) and floor(H/2)+1–H.

## 4. Factorial block F

Every F cell uses the frozen `simulate_v3`, N=30, H=20, SBM, unity weights. Factor order and endpoints:

| Bit | Factor | Low (0) | High (1) |
|---:|---|---:|---:|
| 0 | successful-copy cost | 0 | 1 |
| 1 | eta_Q | 0 | 0.40 |
| 2 | epsilon | 0 | 0.12 |
| 3 | seed_fraction | 0 | 0.20 |
| 4 | share_p0 | 0.60 | 1.00 |
| 5 | eta_A | 0 | 0.40 |
| 6 | eta_social | 0 | 0.10 |
| 7 | R | 1 | 3 |

Labels are `E6-F-<eight bits>` in the order above. These endpoints are mechanistic stress ranges, not
plausible-value claims. Per replicate and outcome, a main effect is mean(high 128 cells) minus mean(low
128 cells). A two-way factorial effect is mean(cells where the product of the two ±1 codes is +1) minus
mean(product −1). The targeted three-way effect uses the same product contrast for bits 0×1×2.

Report all 8 main effects, all 28 two-way effects and the targeted cost×eta_Q×epsilon effect for the
five primary outcomes: `pC_late`, `succ_late`, `K_final`, `source_resid_persist_strict` and
`multihop_rate`. Rank main effects by absolute estimate separately for each outcome. Interaction or
nonlinearity is not inferred outside these endpoints.

## 5. Outcomes and stronger source-role test

Reuse E5 definitions for pC_late, pC_change, pC_postseed, succ_late, K_final, dHK_late, dGK_last,
Smax_mean, Lmax_mean, reach, CF, belief_sd_final, source_top20, source_gini, multihop_rate,
cascade5_rate, capacity_denial_rate and share_refusal_rate.

Replace the degree-only persistence claim metric with `source_resid_persist_strict`. For each student
and each half, regress successful-copy root count by ordinary least squares on:

- intercept, degree and unweighted betweenness centrality;
- two SBM community indicators (third is reference);
- K0, log(alpha), log(kappa);
- that half's holder opportunity: count of homeworks where the student chose S or D and originated a packet.

Compute Spearman correlation between first-half and second-half residuals. If either residual vector has
zero variance, the run is NA. For each S-baseline replicate, permute the late residual vector 999 times
using `SeedSequence([920601, replicate])`. The one-sided p-value is
$(1+\#\{\rho_{null}\ge\rho_{obs}\})/1000$.

Strict persistent-role evidence requires both:

1. lower 95% bootstrap CI for mean `source_resid_persist_strict` > 0.20; and
2. lower 95% bootstrap CI for the fraction of classrooms with permutation p<=.05 > 0.50.

This tests persistence beyond the named observables. It still does not prove psychological roles or
control unmeasured real-world traits.

## 6. Statistical rules

All intervals are 95% percentile bootstrap intervals over replicate worlds. Structural contrasts are
condition minus `E6-S-base`. Factorial effects are computed within replicate before bootstrapping.
Boundary adequacy is unchanged from E5: a contrast interval may not cross ±delta.

Practical deltas: pC outcomes .02; success .05; K and dHK .01; dGK .02; source_top20/source_gini .05;
strict source persistence .10; multihop/cascade5 .05; belief SD .02; denial/refusal .05; Smax 1;
Lmax .25; CF .05; reach .02.

Every S condition separately passes prevalence-free copying robustness only if the lower CI of its
pC_late mean exceeds .04. No omnibus pass count is used. Structural source-role robustness is reported
for every condition but only S-base has the permutation-null confirmatory claim.

Predictions:

- P1: S-base repeats E5 copying persistence and passes pC_late>.04.
- P2: S-base passes both strict persistent-role criteria.
- P3: equal cost reduces copying materially but still passes pC_late>.04.
- P4: softmax conditions still pass pC_late>.04; no direction is predicted versus argmax.
- P5: in block F, eta_social, routing depth, copy cost and eta_Q are the four largest absolute main
  effects on pC_late, in no preregistered order.
- P6: the targeted cost×eta_Q×epsilon interaction is reported without a directional prediction.

Every non-predicted contrast remains confirmatory robustness evidence and is reported regardless of sign.

## 7. Integrity and reporting

The runner must verify this file against `docs/experiments/E6-lock.json`, verify the frozen V3 model
lock, require a clean Git tree, refuse an existing full output, and run a no-outcome smoke that deletes
itself. It must test exact baseline parity between the E6 variant engine and frozen `simulate_v3` before
the full run. Raw schema-v3 tables remain canonical. Derived summaries, S contrasts, F main effects,
F two-way effects, the targeted three-way effect, strict source-null results, hashes and a report JSON
must all be written. All inadequate intervals and all failed predictions are reported. No E5 data are
pooled with E6.

## 8. Explicit omission

Empirical calibration, fitting and held-out real-classroom validation are omitted because no dataset is
available. This omission is a limitation, not a passed test. E6 cannot raise confidence in external
validity above “untested.”
