---
type: experiment
id: E5
status: LOCKED
date: 2026-09-20
locked: 2026-09-20
tags:
  - experiment
  - preregistration
  - v3
---
# E5 · Preregistration: can copying and source roles emerge in V3 without prevalence? (LOCKED)

Locked on 2026-09-20 after Vavan instructed: “now freeze v3 and then do the scientific run.” The
V3 model was frozen first at commit `876556ae5a4d9b429ca1e5c5355f903d9efc8cba` and is independently
hashed in `docs/V3-model-lock.json`. No E5 scientific output existed when this document was locked.
Any later change to this document, model equations, conditions, outcomes or decision rules is a
numbered deviation. Implementation-only smoke output is excluded and deleted.

## 1. Questions and claim boundary

1. Does copying persist above its action-neutral injection rate without a neighbour-copying prevalence
   term, predefined roles or dynamic graph weights?
2. Can neutral exploration alone introduce copying when the one-time seed is removed, and can the
   one-time seed support persistence when later exploration is removed?
3. How much do personal reinforcement, learned source beliefs, the successful-copy cost advantage,
   sharing willingness/capacity and optional symmetric social learning contribute?
4. Do multi-hop routes, concentrated sources and degree-adjusted persistent source roles arise?
5. Are conclusions robust to topology, routing depth, horizon, class size and frozen contact weights?

“Emergent” here means a macro-pattern not inserted as a prevalence reward or role label. It does not
mean behavior from no mechanism: actions enter through the declared seed or neutral exploration and
are selected through specified rewards, costs, local learning and exchange constraints. Results are
claims about this model, not estimates of real classrooms.

The primary emergence evidence uses **unity contact weights**. Weighted conditions are sensitivity
checks only. E5 makes no weighted-broker claim and therefore does not substitute the simple edge
shuffle for a degree-and-strength-preserving broker null.

## 2. Fixed design

- **400 replicates**, numbered 1–400; no optional stopping and no pilot-data tuning.
- Master seed **920005**; bootstrap seed **920500**, 10,000 shared replicate resamples; smoke seed
  **920995**, replicates 1–2.
- Baseline: `V3Params()`; SBM, R=3, N=30, H=20, unity weights.
- Every compatible condition in a replicate reuses the same graph, traits and semantic draws. R=1
  consumes the first routing/sharing row. H=40 shares the first 20 homework draws with baseline.
  ER/WS share non-graph draws. N=60 is matched by replicate seed but is not called a strict CRN pair.
- Early window is homeworks 1–5. Post-seed window is 2–5. Late window is the final five homeworks
  (16–20 normally; 36–40 for H=40). Source halves are 2 through floor(H/2), and floor(H/2)+1 through H.

### Conditions (19; 7,600 runs)

| Label | Difference from baseline |
|---|---|
| `E5-base` | none |
| `E5-seed0` | seed_fraction=0 |
| `E5-seed05` | seed_fraction=0.05 |
| `E5-seed20` | seed_fraction=0.20 |
| `E5-eps0` | epsilon=0 after homework 1 |
| `E5-etaA0` | eta_A=0; beliefs stay at A0 |
| `E5-etaQ0` | eta_Q=0; no personal action-value reinforcement |
| `E5-copycost1` | successful-copy cost=1, equal to S/D/fallback |
| `E5-traitshuffle` | complete trait bundles permuted over the same SBM nodes |
| `E5-unlimited` | sharing capacity=N |
| `E5-share1` | baseline share probability=1 |
| `E5-social010` | eta_social=0.10, applied symmetrically to S/D/C |
| `E5-weighted` | frozen independent lognormal edge weights |
| `E5-weightshuffle` | the exact weighted-condition multiset shuffled over the same edges |
| `E5-ER` | ER topology |
| `E5-WS` | WS topology |
| `E5-R1` | R=1 |
| `E5-H40` | H=40 |
| `E5-N60` | N=60, mean degree still 6 |

Trait permutation uses `default_rng(null_seed(master, replicate, "SBM", 502)).permutation(N)`.
For the weighted condition, canonical SBM edges receive
`exp(0.5 Z - 0.5*0.5^2)`, where Z comes from PCG64 with
`SeedSequence([master, replicate, 11, FAMILY_CODE["SBM"], N])`. Code 11 is experiment-only
`v3_weight`; weights are positive, exogenous, mean-one in expectation and never update. The shuffled
condition applies `shuffle_edge_weights` with `null_seed(master, replicate, "SBM", 501)`.

## 3. Per-run outcomes reconstructed from raw tables

Standard outcomes retain their E1 definitions with the condition-specific late window:
`pC_late`, `pC_change`, `succ_late`, `K_final`, `dHK_late`, `dGK_last`, `Smax_mean`, `Lmax_mean`,
`reach`, and route concentration `CF`.

V3-specific outcomes are fixed as follows:

- `pC_postseed`: mean copying fraction over homeworks 2–5.
- `belief_sd_final`: population SD of all finite directed A values at the final homework.
- `source_top20`: among successful late-window copied decisions, the share rooted at the most-used
  ceil(0.2N) students; NA if there are no successful copies.
- `source_gini`: zero-inclusive Gini coefficient of late-window successful-copy root counts across all
  N students; NA if there are no successful copies.
- `source_resid_persist`: Spearman correlation across students between early-half and late-half source
  counts after separately residualizing each count vector on an intercept and node degree. NA if a
  residual vector has zero variance. This adjusts the unity-weight role test for degree; it is not a
  weighted-broker null.
- `multihop_rate`: fraction of late homeworks with at least one successful copied decision of depth>=2.
- `cascade5_rate`: fraction of late homeworks where at least five successful copied decisions share a
  root. The root itself is not counted.
- `capacity_denial_rate`: late target-had-packet and willing events denied by capacity divided by late
  target-had-packet and willing events; NA if the denominator is zero.
- `share_refusal_rate`: late target-had-packet events with willing=false divided by all late
  target-had-packet events; NA if the denominator is zero.

All derived files are secondary artifacts. Raw schema-v3 Parquet tables remain the evidence.

## 4. Confirmatory tests and thresholds

All intervals are 95% percentile bootstrap intervals over replicates. Paired contrasts are condition
minus `E5-base` except the mechanism directions named below. Contrast adequacy uses the E4 boundary
rule: an interval must not cross either +/-delta. Inadequate contrasts are reported but not interpreted.

Practical deltas: pC outcomes 0.02; success 0.05; K and dHK 0.01; dGK 0.02; source_top20 and
source_gini 0.05; source_resid_persist 0.10; multihop_rate and cascade5_rate 0.05; belief_sd_final
0.02; capacity/refusal rates 0.05; Smax 1; Lmax 0.25; CF 0.05; reach 0.02.

### Absolute emergence criteria

1. **Baseline persistence:** lower CI for `E5-base.pC_late` > 0.04. The neutral copying injection is
   epsilon/3=0.02; 0.04 is that floor plus delta=0.02.
2. **Seed-free entry:** lower CI for `E5-seed0.pC_late` > 0.04.
3. **Seed-only persistence:** lower CI for `E5-eps0.pC_late` > 0.02. There is no post-homework-1
   random injection in this condition.
4. **Cost-independent persistence:** lower CI for `E5-copycost1.pC_late` > 0.04. Failure means any
   baseline emergence claim must explicitly depend on the successful-copy cost advantage.
5. **Persistent source roles:** lower CI for baseline `source_resid_persist` > 0.20.
6. **Multi-hop routing:** lower CI for baseline `multihop_rate` > 0.10.
7. **Large repeated-root events:** lower CI for baseline `cascade5_rate` > 0.10.

These seven criteria are evaluated separately; E5 is not reduced to one omnibus pass/fail label.

### Mechanism contrasts

- Reinforcement contribution: `E5-base - E5-etaQ0` on pC_late is above +0.02.
- Learned-targeting contribution: `E5-base - E5-etaA0` on succ_late is above +0.05.
- The remaining condition-minus-baseline contrasts are confirmatory sensitivity estimates for all
  outcomes above, without directional predictions. Seed dose point estimates are additionally checked
  for monotonicity across 0, .05, .10 and .20; this descriptive check is not a claim criterion.
- Trait shuffle and weight shuffle are negative controls. A difference is not automatically treated as
  a failure, but any detected above-delta difference must qualify assignment/weight robustness claims.

## 5. Predictions

- P1: baseline persistence passes criterion 1.
- P2: neutral exploration is sufficient for seed-free entry (criterion 2).
- P3: a one-time seed can persist without later exploration (criterion 3).
- P4: personal reinforcement contributes positively by the locked mechanism contrast.
- P5: local belief learning improves late copying success by the locked mechanism contrast.
- P6: no directional prediction is made for cost-independent persistence or structural-role criteria;
  they are deliberately stringent open tests against calling a payoff or graph artifact “emergence.”

## 6. Precision, missingness and stopping

The run always completes all 400 replicates unless interrupted by technical failure. A restart must
reproduce and overwrite no completed scientific directory; otherwise it is a deviation. No condition,
outcome, threshold or replicate count changes after looking at E5 outcomes. NA is expected only where
an outcome has an explicitly zero denominator or zero residual variance. The report gives the valid n
for every interval. Conclusions with an inadequate contrast are withheld.

## 7. Runner guards and validation

The future E5 runner must:

1. verify this file against `docs/experiments/E5-lock.json` and verify `docs/V3-model-lock.json`;
2. require a clean Git tree and record the exact commit;
3. refuse a full run if `runs/E5` exists;
4. run a two-replicate smoke that prints no outcome values and deletes its output;
5. prove all 19 labels, canonical tables, manifests, summaries, contrasts and seven absolute tests exist;
6. record raw/derived SHA-256 hashes and any deviation.

## 8. Reporting

Report every absolute criterion, every confirmatory contrast and all inadequacies, including null or
contrary findings. Wording is limited to “under these frozen mechanisms and conditions.” A baseline
result may be called prevalence-free because that term is absent by construction. It may be called
seed-free, exploration-free or cost-independent only if the corresponding locked criterion passes.
No result from E1–E4 is pooled with E5.
