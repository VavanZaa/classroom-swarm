---
type: experiment
id: E4
status: LOCKED
date: 2026-09-18
locked: 2026-09-18
tags:
  - experiment
  - preregistration
---
# E4 · Preregistration: where is the V2 tipping point, and how robust is it? (LOCKED)

**Locked 2026-09-18 before any E4 code or run existed**, by Claude under Vavan's explicit approval of the same day ("approve decision 1 and 2"). Decision 1 was the boundary precision rule. Decision 2 listed three follow-ups (fine threshold, topology × routing, M3–M5); approval is read as "all three", run here as three blocks of one experiment. Any later change is a numbered deviation.

## 0. Background
E3 ([[docs/experiments/E3-results]]): with V2 peer exposure (share of friends who chose C), copying spreads, and there is a tipping point. On SBM, R = 3, M2: 0/400 classrooms tipped at $\beta_P=3$, 295/400 at 4.5, 400/400 at 6. The mean-field threshold was 4.5–4.6.

## 1. Questions
- **Q1 (block F, threshold):** where exactly is the tipping point on SBM, R = 3, M2? $\beta_P\in\{3,3.5,4,4.5,5,5.5,6\}$ against $\beta_P=0$.
- **Q2 (block T, robustness):** do the tipping and its threshold depend on topology (ER, WS, SBM) and routing depth ($R\in\{1,3\}$)? $\beta_P\in\{0,3,4.5,6\}$ in each family × R cell.
- **Q3 (block S, feedback):** does the contagion survive confidence → strategy (M3), exam → confidence (M4) and exam → effort (M5)? $\beta_P\in\{0,3,4.5,6\}$ at each of M3–M5, against M2.

## 2. Design
- **V2 everywhere** (`exposure="copying"`); every other parameter at `Params()` defaults. 400 replicates. Per replicate: one graph per family and one shared `Draws(R_max=3)` for all conditions (common random numbers).
- **40 conditions, 16,000 runs.** Block F: 8 (SBM, R3, M2, $\beta_P$ 0 and 3–6). Block T: the 20 family × R × $\beta_P$ cells not already in F (SBM R3 reuses F's). Block S: 12 (M3/M4/M5 × $\beta_P$ 0/3/4.5/6 at SBM R3; M2 reuses F's).
- Labels: `E4-F-b<β>`, `E4-T-<family>-R<R>-b<β>`, `E4-S-M<k>-b<β>`.
- Seeds: master **918005**, bootstrap **918500** ($B=10{,}000$), smoke 918995.

## 3. Outcomes
- As in E1–E3, plus a new confirmatory per-run outcome **tipped** = 1 if pC_late > 0.5, else 0. Its replicate mean is the share of classrooms that tipped. **δ(tipped) = 0.10** (10 percentage points of classrooms). **Primary: tipped, pC_late, pC_change.** All other confirmatory and secondary outcomes as before.
- **Threshold (Q1, primary descriptive):** $\beta^*$ = the $\beta_P$ where block F's tipped share first reaches 0.5, by linear interpolation on the grid 3–6 (`analysis.tipping_threshold_ci`), with a 95% percentile bootstrap CI on the shared resamples. Resamples that never reach 0.5, or reach it at 3, are counted and reported. The same estimate is reported for each block-T family × R cell on its 3 / 4.5 / 6 grid (coarser; descriptive).

## 4. Contrasts (58), paired by replicate
- **F (7):** each $\beta_P$ − b0.
- **T (39):** in every family × R cell, each $\beta_P\in\{3,4.5,6\}$ − its b0 (18); topology at each $\beta_P\in\{3,4.5,6\}$ and R: ER − SBM and WS − SBM (12); routing R3 − R1 per family and $\beta_P\in\{3,4.5,6\}$ (9).
- **S (12):** M3 − M2, M4 − M2, M5 − M2 at each $\beta_P\in\{0,3,4.5,6\}$.

## 5. Interpretation
- Labels as in E1 §6.
- **Adequacy: the boundary rule (Decision 1):** a contrast is adequate iff its 95% CI contains neither +δ nor −δ (`analysis.boundary_precision_check`). It was validated on synthetic data before this lock (`scripts/validate_boundary_rule.py`, commit `18402b3`), with all four pre-stated criteria met. Inadequate contrasts are reported and not interpreted.
- "Contagion spreads at b" (block F or a block-T cell) is claimed only if the pC_change contrast against that cell's b0 is detected above δ and adequate. "Classrooms tip at b" is claimed only if the tipped contrast is detected above δ and adequate.

## 6. Predictions
- **P1 (from E3 and the mean-field):** in block F, $\beta^*$ lies in **[3.5, 4.5]**.
- **P2:** block F's tipped share is non-decreasing in $\beta_P$ (point estimates).
- No predictions for block T or block S. They're open questions.

## 7. Known limits
$\beta_P\ge3$ is beyond the §32 plausible range (0–1.5) by design: E4 locates and stress-tests a threshold, it doesn't estimate real classrooms. The "tipped" cut at 0.5 is a convention, fixed here before any E4 run. All claims: "under these mechanisms and conditions" (§49).

## 8. Runner and smoke
`scripts/run_e2.py --experiment E4`: lock-hash check against `docs/experiments/E4-lock.json`, clean git tree, refuse if `runs/E4` exists. Smoke: `E4-smoke`, replicates 1–2, pipeline checks only, outputs deleted.
