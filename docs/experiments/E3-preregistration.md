---
type: experiment
id: E3
status: LOCKED
date: 2026-09-18
locked: 2026-09-18
tags:
  - experiment
  - preregistration
---
# E3 · Preregistration: does friend contagion make copying spread? (V2) (LOCKED)

**Locked 2026-09-18 before any V2 experiment run existed**, by Claude under Vavan's explicit approval of the same day ("do decision 1 and 2": decision 1 was the V2 model revision). V2 = V1 + amendment A19 (`exposure="copying"`: $X_i$ = share of neighbours who chose C in the previous homework), implemented at commit `833a3ca`. Any later change is a numbered deviation.

## 1. Question
Vavan's hypothesis: *if my friends copy, I become more inclined to copy.* E2 showed V1 cannot express it, because V1's $X$ counts neighbours who *asked me*. E3 asks:
1. Does redefining peer exposure (V2 vs V1, same $\beta_P$) change copying?
2. In V2, how do copying level and growth depend on the peer-influence strength $\beta_P$? Is there a **tipping point** where copying spreads through the class?

## 2. A priori prediction (computed before any V2 run)
A mean-field approximation of V2 (every student sees $X\approx p$, the class copying rate; learning, network structure and copy success ignored) iterates $p_{h+1}=\sigma(b_C+\beta_P p_h)$ from $p_0=0.10$:

| $\beta_P$ | 0 | 0.5 | 1.5 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| mean-field $p$ at $h=20$ | 0.100 | 0.105 | 0.117 | 0.147 | 0.195 | 0.915 | 0.975 |

**Takeoff threshold between $\beta_P=4.5$ and 4.6.** Below it, copying settles slightly higher; above it, copying spreads to most of the class.

**Predictions tested by E3:**
- **E3-P1 (direction):** V2 − V1 pC_late ≥ 0 at every $\beta_P>0$.
- **E3-P2 (tipping):** at $\beta_P=6$, V2 copying growth (pC_change, V2-b6 − V2-b0) is above δ **and** V2-b6 mean pC_late exceeds 0.5; at $\beta_P\le3$, V2 pC_change against V2-b0 is negligible or below δ.

The mean-field ignores the fact that when most students copy, few hold answers, so copy success and copying's reward may collapse. E3 tests whether that feedback damps or shifts the tipping point. **No prediction is made for $\beta_P=4.5$** (it's at the mean-field threshold).

## 3. Design
- Stage **M2**, **R = 3, SBM**, `Params()` defaults except exposure and $\beta_P$. 400 replicates; one SBM graph and one shared `Draws` per replicate for all conditions (common random numbers).
- **11 conditions** (4,400 runs). $\beta_P>1.5$ are stress levels beyond the §32 plausible range, by design.

| Label | exposure | $\beta_P$ |
|---|---|---|
| E3-v2-b0 | copying | 0 (exposure inert, so it's also the V1 β = 0 reference) |
| E3-v2-b0.5 / b1.5 / b3 / b4.5 / b6 | copying | 0.5 / 1.5 / 3 / 4.5 / 6 |
| E3-v1-b0.5 / b1.5 / b3 / b4.5 / b6 | requests | 0.5 / 1.5 / 3 / 4.5 / 6 |

- Seeds: master **918004**, bootstrap **918400** ($B=10{,}000$), smoke 918996.

## 4. Outcomes, contrasts, interpretation
- Outcomes, windows and δ as in E1/E2 (same code). **Primary: pC_late and pC_change.**
- **15 contrasts**, paired by replicate:
  - **A (primary, exposure effect):** V2 − V1 at each $\beta_P\in\{0.5,1.5,3,4.5,6\}$.
  - **B (primary, V2 dose-response):** V2-b$\beta$ − V2-b0 for each $\beta_P>0$.
  - **C (secondary, V1 dose-response):** V1-b$\beta$ − V2-b0 (a valid V1 reference, since exposure is inert at $\beta_P=0$).
- Labels as in E1 §6. **Precision rule** (validated, `b199681`): CI half-width ≤ δ/4, otherwise imprecise and not interpreted.
- **"Copying spreads by friend contagion at $\beta_P=b$"** is claimed only if contrast B's pC_change at $b$ is detected with magnitude above δ and is precise.

## 5. Known limits
One stage (M2), one topology (SBM), one routing depth (R = 3). Stress levels of $\beta_P$ are beyond plausibility by design: they locate a threshold, they don't estimate real classrooms. All claims: "under these mechanisms and conditions" (§49).

## 6. Runner guards
`scripts/run_e2.py --experiment E3`: lock-hash check against `docs/experiments/E3-lock.json`, clean git tree, refuse if `runs/E3` exists. Smoke: `E3-smoke`, replicates 1–2, pipeline checks only, outputs deleted.
