---
type: experiment-results
id: E3
status: REPORTED
date: 2026-09-18
tags:
  - experiment
  - results
---
# E3 · Results: friend contagion (V2) produces a copying tipping point

Results of [[docs/experiments/E3-preregistration]] (locked `1c350a7`). 4,400 runs (11 conditions × 400 replicates, M2, R = 3, SBM) in 3.0 min from commit `00598cf` (clean), preregistration SHA-256 `d01856ba…002a` verified, seed 918004. **No deviations.** 123 of 135 confirmatory contrasts are adequately precise (the 12 that aren't are listed below).

## Copying by exposure definition and peer-influence strength (condition means)
| $\beta_P$ | V1 "asked me": pC early → late | **V2 "friends copy": pC early → late** | V2 copy success (late) | V2 K_final |
|---|---|---|---|---|
| 0 | — | 0.100 → 0.094 | ≈1.00 | 0.833 |
| 0.5 | 0.101 → 0.095 | 0.104 → 0.098 | ≈1.00 | 0.833 |
| 1.5 | 0.102 → 0.097 | 0.115 → 0.113 | ≈1.00 | 0.830 |
| 3 | 0.105 → 0.101 | 0.141 → **0.161** | ≈1.00 | 0.822 |
| 4.5 | 0.109 → 0.106 | 0.200 → **0.627** | 0.82 | 0.756 |
| 6 | 0.114 → 0.113 | 0.302 → **0.975** | **0.12** | **0.630** |

**Share of classrooms whose late copying exceeds 50%** (exploratory): β 3: **0/400**; β 4.5: **295/400** (late copying quantiles 5% 0.27, median 0.66, 95% 0.89); β 6: **400/400** (0.94–0.99).

## Preregistered claims
**"Copying spreads by friend contagion at β_P = b"** (contrast B pC_change above δ **and** precise):

| $\beta_P$ | B: V2 pC_change − V2-b0 | Claim |
|---|---|---|
| 0.5 | +0.0002 [−0.0005, +0.0009], negligible | no |
| 1.5 | +0.0039 [+0.0022, +0.0055], below δ | no |
| **3** | **+0.0255 [+0.0215, +0.0297], above δ, precise** | **yes** |
| 4.5 | +0.4336 [+0.4157, +0.4508], above δ, *imprecise* (half-width 0.0176) | withheld by rule |
| 6 | +0.6796 [+0.6691, +0.6898], above δ, *imprecise* (half-width 0.0104) | withheld by rule |

**Exposure effect** (contrast A, V2 − V1, pC_late): +0.0033, +0.0157, +0.0600, +0.5215, +0.8627 for β_P 0.5 / 1.5 / 3 / 4.5 / 6. Every estimate is positive. It's above δ from β_P = 3, precise everywhere except β_P = 4.5.

**V1 dose-response** (contrast C) replicates E2 on new data: even β_P = 6 adds only +1.9 points of copying level and +0.5 points of growth (below δ).

## Predictions
- **E3-P1 (V2 − V1 ≥ 0 at every β_P > 0): confirmed.**
- **E3-P2 (tipping): partly confirmed, partly refuted.**
  - At β_P = 6, V2 late copying exceeds 0.5 (mean 0.975; 400/400 classrooms). The growth contrast is above δ, but imprecise by the locked rule, so that half of the prediction can't be formally confirmed.
  - **Refuted:** at β_P = 3 copying *does* grow above δ (+0.026, precise), although no classroom tips. The mean-field predicted a stable 0.147; the network gives 0.161 and rising.
  - The takeoff happens around the mean-field threshold (4.5–4.6): at 4.5, 74% of classrooms tip.

## What happens to grades and knowledge
- **Knowledge collapses as copying spreads:** K_final 0.833 → 0.756 (β_P 4.5) → 0.630 (β_P 6), about 0.2 lower at β_P 6 (above δ).
- **Copying defeats itself.** At β_P 6, copy success falls from about 1.00 to 0.12: when almost everyone copies, almost nobody holds an answer.
- **Grade–knowledge decoupling still does not emerge.** Δ_HK and Δ_GK stay below δ in every condition (largest: Δ_HK +0.0095 at β_P 4.5, straddling δ = 0.01). At mass copying, failed copiers fall back on their own knowledge, so grades track knowledge downwards rather than detaching from it.
- **Cascades:** they grow near the tipping point (largest cascade +2.2 students, depth +0.75 at β_P 4.5, both above δ) and shrink again at β_P 6, when there are too few sources.

## Imprecise contrasts (12)
A and B at β_P 4.5: pC_late, pC_change, succ_late, K_final. A and B at β_P 6: pC_change, K_final. All come from **heterogeneous classroom fates near and beyond the tipping point** (a wide spread of when and whether a class tips), not from too few replicates. Every one of these CIs lies entirely beyond ±δ. **Rule note for Vavan:** the δ/4 half-width rule withholds claims whose whole CI is several δ from zero. For future preregistrations, a decision-relevant precision rule (e.g. "the CI must not cross a ±δ boundary") may fit better. Not applied retroactively.

## Answer to Vavan's question
**Yes: "my friends copy, so I copy" produces spreading copying, and a tipping point, once peer exposure measures friends' copying (V2).** But it needs strong peer influence: β_P ≥ 3, which is 2× the top of the blueprint's plausible range (§32, 0–1.5, itself an unfitted guess). Within the plausible range the effect stays below δ (+1.9 points at 1.5). Past the tipping point (β_P ≈ 4.5) the class flips to near-universal copying, knowledge falls sharply, and copying stops working because nobody is left to copy from. All under these mechanisms and conditions (M2, SBM, R = 3); stress levels locate the threshold, they don't describe real classrooms.

Derived outputs: `runs/E3/derived/` (SHA-256 prefixes: `contrasts.parquet` 38bc31c8c4b82249, `run_summaries.parquet` 396d24f6c4b37da6, `report.json` bfd8407dd12dc060).
