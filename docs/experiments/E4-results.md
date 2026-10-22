---
type: experiment-results
id: E4
status: REPORTED
date: 2026-09-18
tags:
  - experiment
  - results
---
# E4 · Results: the V2 tipping point is sharp, near β_P ≈ 4.3, and robust

Results of [[docs/experiments/E4-preregistration]] (locked `6618eaf`). 16,000 runs (40 conditions × 400 replicates, V2 exposure) in 8.8 min from commit `b9b0ad1` (clean), preregistration SHA-256 `78ed07d9…d428` verified, seed 918005. **No deviations.** Boundary precision rule: **560 of 580 confirmatory contrasts adequate.** The 20 inadequate ones all straddle δ or are inconclusive; they are listed in `runs/E4/derived/contrasts.parquet` and none is interpreted. Derived outputs (SHA-256 prefixes): `contrasts.parquet` 92cff6276b46bea0, `run_summaries.parquet` c675fedd4d8010ec, `extra.json` f4f99f4d63a6876d, `report.json` 3e2740b885425765.

## Q1 · Where is the tipping point? (block F: SBM, R = 3, M2)
**β\* = 4.34 [4.31, 4.37]**: the peer-influence strength at which half of the classrooms tip (all 10,000 resamples interpolated).

| β_P | 0 | 3 | 3.5 | 4 | 4.5 | 5 | 5.5 | 6 |
|---|---|---|---|---|---|---|---|---|
| classrooms tipped | 0% | 0% | 0.3% | 10.8% | 68.5% | 98.0% | 100% | 100% |
| late copying | 0.095 | 0.167 | 0.212 | 0.325 | 0.610 | 0.878 | 0.951 | 0.974 |
| copy success (late) | 1.00 | 1.00 | 1.00 | 0.99 | 0.84 | 0.45 | 0.24 | 0.14 |
| K_final | 0.833 | 0.822 | 0.815 | 0.800 | 0.760 | 0.701 | 0.660 | 0.630 |

- **P1 (β\* ∈ [3.5, 4.5]): confirmed.** **P2 (tipped share non-decreasing): confirmed.**
- **Contagion spreads** (pC_change above δ, adequate) from **β_P = 3** on (+0.032), as in E3. **Classrooms tip** (tipped above δ, adequate) from **β_P = 4.5** on. At 4.0 the tipped contrast (+0.108 [+0.078, +0.138]) straddles δ = 0.10 and is inadequate.
- The transition is **sharp**: from 11% to 98% of classrooms between β_P 4.0 and 5.0. **Knowledge falls** monotonically (K_final −0.012 at β_P 3 to −0.203 at 6, all above δ). **Copying defeats itself**: as copying spreads, copy success collapses from 1.00 to 0.14.

## Q2 · Does it depend on topology or routing depth? (block T)
| Family × R | tipped at β_P 3 / 4.5 / 6 | coarse-grid β\* [95% CI] |
|---|---|---|
| ER R1 | 0 / 61.5% / 100% | 4.22 [4.13, 4.32] |
| ER R3 | 0 / 68.8% / 100% | 4.09 [4.02, 4.17] |
| WS R1 | 0 / 65.8% / 100% | 4.14 [4.07, 4.23] |
| WS R3 | 0 / 77.0% / 100% | 3.97 [3.93, 4.03] |
| SBM R1 | 0 / 60.3% / 100% | 4.25 [4.15, 4.35] |
| SBM R3 | 0 / 68.5% / 100% | 4.10 [4.03, 4.17] |

*Coarse-grid β\* interpolates between 3, 4.5 and 6 only, so it runs low against block F's fine-grid 4.34 (the transition is sharper than linear). Compare these values only with each other.*

- **Topology:** ER − SBM tipping is negligible and adequate (R1 +0.013, R3 +0.003). WS − SBM is higher (R1 +0.055, R3 +0.085) but straddles δ, so it's inadequate and not interpreted. Every cell has 0% tipped at β_P 3 and 100% at 6.
- **Routing depth:** R3 − R1 at β_P 4.5: ER +0.073 (below δ, adequate); WS +0.113 and SBM +0.083 straddle δ (inadequate). With R = 1, copy success at mass copying falls even further (about 0.03 against 0.13).
- **Answer: the tipping point is robust.** Across three topologies and two routing depths it sits in the same place (coarse β\* 3.97–4.25). No topology or routing contrast is adequately above δ.

## Q3 · Does it survive confidence and exam feedback? (block S)
- At **β_P 4.5** (near the threshold), M3, M4 and M5 all **tip less than M2**: tipped −0.135 / −0.140 / −0.143 (above δ, adequate), and pC_change −0.065 / −0.067 / −0.067 (above δ, adequate).
- At β_P 3 and 6 there's no difference (none tip / all tip).
- **M4 and M5 add nothing beyond M3**: their numbers are almost identical to M3's.
- **Answer: contagion survives feedback, but confidence → strategy (M3) damps it near the threshold** (about 14 fewer classrooms in 100 tip). Exam → confidence and exam → effort make no further difference.
- *Post hoc, untested:* copied answers raise grades and so confidence, and in M3 higher confidence makes independent work more attractive ($U^S$ gains $\beta_C(C-0.5)$). That would push back against copying.

## Grade–knowledge decoupling
Still absent: Δ_HK and Δ_GK stay below δ or straddle it (largest Δ_HK +0.0114, WS R3 at β_P 4.5, inadequate). As in E3, failed copiers answer from their own knowledge, so grades fall with knowledge instead of detaching from it.

## Summary
Under V2 (peer exposure = friends who chose to copy), the model has a **sharp contagion tipping point at β_P ≈ 4.3**. It is robust to topology and routing depth. Confidence feedback damps it slightly; exam feedback doesn't. Beyond it, copying becomes near-universal, collapses on itself (nobody left to copy from), and knowledge falls by up to 0.2. The threshold is about 3× the top of the blueprint's plausible β_P range (0–1.5), which was itself an unfitted guess. So whether real classrooms sit below or above it is an empirical question this model can't answer. All claims: "under these mechanisms and conditions" (§49).
