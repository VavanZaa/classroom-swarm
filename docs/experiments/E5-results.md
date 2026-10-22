---
type: experiment
id: E5
status: REPORTED
date: 2026-09-20
tags:
  - experiment
  - results
  - v3
---
# E5 · Results: prevalence-free copying and source roles emerge, but large cascades do not

Results of [[docs/experiments/E5-preregistration]] under the frozen [[docs/10-v3-generative-model|V3 model]].
The one-shot run completed **7,600 runs** (19 conditions × 400 replicates) in 7.7 minutes at clean
commit `2be1667`; frozen model commit `876556a`; preregistration SHA-256
`02c9fece…1ca94f`; master seed 920005 and bootstrap seed 920500. **No deviations.** All 4,806
recorded raw/derived file hashes were independently rechecked with zero mismatches, and all 203 tests
passed after the run.

## Main answer

Under these frozen mechanisms, V3 produces substantial copying without a copying-prevalence reward,
preassigned behavioral roles or dynamic graph weights. Baseline late copying was **40.6%** (95% CI
[39.9%, 41.3%]), far above the 4% preregistered persistence boundary. Copying also persisted with no
one-time seed (**36.6%**) and with no exploration after homework 1 (**38.1%**). With the successful-copy
effort advantage removed, it fell sharply but remained **28.3%**, passing the cost-independent criterion.

This is conditional emergence, not behavior from nothing: copying must still be introduced by neutral
exploration or the declared seed, and students still respond to rewards, costs and exchange success.
The simulation does not establish prevalence or causal effects in real classrooms.

Six of seven absolute criteria passed. The exception matters: baseline V3 produced persistent source
roles and multi-hop routing, but **not large repeated-root cascades** of five or more copiers.

| Preregistered criterion | Estimate | 95% CI | Boundary | Result |
|---|---:|---:|---:|---|
| Baseline late copying | 0.406 | [0.399, 0.413] | >0.04 | pass |
| Seed-free late copying | 0.366 | [0.359, 0.374] | >0.04 | pass |
| Seed-only late copying | 0.381 | [0.373, 0.389] | >0.02 | pass |
| Equal-cost late copying | 0.283 | [0.275, 0.290] | >0.04 | pass |
| Degree-adjusted source persistence | 0.779 | [0.769, 0.788] | >0.20 | pass |
| Late-homework multi-hop rate | 0.635 | [0.609, 0.661] | >0.10 | pass |
| Late-homework five-copier cascade rate | 0.003 | [0.001, 0.006] | >0.10 | **fail** |

## What generated the pattern

Personal action-value reinforcement made a practically important contribution: baseline minus the
no-reinforcement condition was **+4.07 percentage points** of late copying [3.18, 4.93], exceeding the
locked 2-point criterion.

Learned source beliefs improved copying success by only **+1.72 points** [1.36, 2.07]. This was precise
but below the locked 5-point criterion, so the predicted material learned-targeting contribution
**failed**. Turning belief learning off barely changed copying level (-0.26 points), and actually raised
the multi-hop rate by 8.4 points. Learned reliability mainly pruned unsuccessful routes; it was not the
main cause of copying prevalence or source persistence.

The baseline successful-copy cost advantage was influential but not necessary. Making successful
copying cost the same as solving/discussing reduced late copying by **12.32 points**
[-12.89, -11.76], yet the remaining 28.3% still passed the absolute cost-independent test. The
equal-cost condition also raised final knowledge by 2.70 points [2.57, 2.83].

The one-time seed changed the eventual level monotonically: late copying was 36.6%, 38.7%, 40.6% and
44.0% for seed fractions 0, .05, .10 and .20. It changed initial conditions, but did not determine
whether copying could exist.

## Roles, routes and concentration

In baseline V3, the most-used 20% of students supplied **62.3%** of successful late copied answers;
the zero-inclusive source Gini was 0.645. More importantly for the locked claim, early- versus late-half
source activity remained strongly correlated after separately residualizing node degree
(mean Spearman 0.779). Thus persistent source roles arose without assigning source or broker types.

Multi-hop paths appeared in 63.5% of late homeworks, but large same-root events were rare: only 0.3%
of late homeworks had at least five successful copiers sharing a root. Unlimited holder capacity raised
that rate to 4.1%, still below the 10% absolute criterion. Baseline V3 therefore supports persistent
sources and distributed multi-hop flow, not large cascades.

Optional action-symmetric social learning changed the regime dramatically: late copying rose to 72.2%
(+31.62 points [30.78, 32.46]), success fell to 63.6% (-30.65 points), final knowledge fell by 6.71
points, and the five-copier cascade rate reached 23.6%. Because this rule treats S, D and C symmetrically,
the result shows that generic outcome observation can amplify copying; it does not make the baseline
large-cascade criterion pass.

## Robustness and weighted graph result

- Trait-bundle shuffling was negligible for copying (-0.12 points [-0.92, 0.69]), success, knowledge
  and source persistence. This is the expected ensemble-level null for traits sampled independently of
  graph position.
- Independent frozen lognormal weights were negligible for late copying (-0.05 points
  [-0.48, 0.40]); shuffling the identical weight multiset was also negligible (+0.36
  [-0.10, 0.82]). Weighted edges are therefore unnecessary for the main result, and no weighted-broker
  claim is made.
- ER (-0.29 points [-0.88, 0.32]) and WS (+0.02 [-0.60, 0.66]) produced negligible copying-level
  differences from SBM.
- R=1 reduced late copying by 8.53 points, success by 30.77 points and source persistence by 0.132.
  Routing depth is materially important.
- Extending to H=40 changed late copying by only +0.26 points; N=60 changed it by -0.22 points.
  The copying-level conclusion is robust to those locked horizon and class-size checks.
- Removing capacity limits changed late copying by only +0.30 points. Setting sharing willingness to
  one changed it by +1.23 points. Baseline scarcity affects flow details more than copying prevalence.

## Precision and complete contrast record

The canonical `runs/E5/derived/contrasts.parquet` contains every one of the **342 preregistered
condition × outcome contrasts**. Under the locked boundary rule, 323 were adequate and 19 were not.
Inadequate contrasts are reported here and not interpreted across their practical boundary:

| Condition | Outcome | Estimate | 95% CI |
|---|---|---:|---:|
| seed0 | pC_change | +0.0203 | [0.0177, 0.0230] |
| seed05 | pC_late | -0.0190 | [-0.0221, -0.0160] |
| seed05 | reach | -0.0184 | [-0.0208, -0.0159] |
| seed05 | multihop_rate | -0.0365 | [-0.0530, -0.0195] |
| seed20 | pC_change | -0.0201 | [-0.0227, -0.0175] |
| seed20 | multihop_rate | +0.0630 | [0.0425, 0.0835] |
| eps0 | pC_change | -0.0205 | [-0.0242, -0.0170] |
| eps0 | CF | +0.0467 | [0.0433, 0.0502] |
| etaQ0 | dGK_last | -0.0210 | [-0.0235, -0.0185] |
| etaQ0 | reach | +0.0147 | [0.0084, 0.0210] |
| copycost1 | CF | +0.0508 | [0.0475, 0.0542] |
| copycost1 | source_resid_persist | -0.1029 | [-0.1159, -0.0902] |
| traitshuffle | multihop_rate | -0.0190 | [-0.0510, 0.0140] |
| share1 | succ_late | +0.0467 | [0.0433, 0.0503] |
| ER | multihop_rate | -0.0185 | [-0.0540, 0.0160] |
| WS | multihop_rate | -0.0310 | [-0.0635, 0.0025] |
| H40 | source_resid_persist | +0.1017 | [0.0934, 0.1103] |
| H40 | multihop_rate | -0.0690 | [-0.0970, -0.0405] |
| N60 | Lmax_mean | +0.2454 | [0.2213, 0.2698] |

## Evidence files

- `runs/E5/derived/run_summaries.parquet` — SHA-256 `63e498fa13f4dfbf…`
- `runs/E5/derived/contrasts.parquet` — SHA-256 `5562fbde8667a13c…`
- `runs/E5/derived/absolute_tests.parquet` — SHA-256 `755b33cef7021245…`
- `runs/E5/derived/mechanism_tests.parquet` — SHA-256 `fddae8caa13ca015…`
- `runs/E5/derived/report.json` — SHA-256 `ad034847b63645fa…`
- `runs/E5/derived/hashes.json` records all 4,806 raw and derived hashes.

## Conclusion

V3 meets the narrow objective: copying level, persistent source roles and multi-hop flow arise without
an explicit copying-prevalence utility or assigned behavioral types. The result survives removal of the
seed, removal of ongoing exploration, equal copying cost, trait shuffling, unweighted graphs, alternate
topologies, longer horizon and larger class size. It does **not** show that every requested pattern
emerges: large baseline cascades fail, learned targeting has only a small success effect, routing depth
matters, and the cost advantage materially raises copying. Those limits should remain part of every V3
claim.
