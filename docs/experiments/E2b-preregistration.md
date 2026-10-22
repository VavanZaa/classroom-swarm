---
type: experiment
id: E2b
status: LOCKED
date: 2026-09-18
locked: 2026-09-18
tags:
  - experiment
  - preregistration
---
# E2b · Preregistration: does copying grow at the plausible maximum? (LOCKED)

**Locked 2026-09-18 before any E2b code or run existed**, by Claude under Vavan's explicit approval of the same day ("do decision 1 and 2"). Any later change is a numbered deviation.

## 1. Question
In E2 ([[docs/experiments/E2-results]]), the plausible-max condition was the only one where copying grew over time: pC_change +0.049 [+0.043, +0.055] against the reference. The locked precision rule withheld the claim, because the CI half-width (0.0059) exceeded δ/4 = 0.0050. E2b asks the same question on **new data, with enough replicates to meet the rule**. E2's data are **not** pooled with E2b's.

## 2. Design
- Two conditions, stage M2, R = 3, SBM, exactly as in E2: **E2b-ref** (`Params()` defaults) and **E2b-plausible-max** ($\beta_P$ 1.5, $\kappa$ 0.40, $\eta_Q$ 0.40, $p_C^0$ 0.20).
- **400 replicates** (800 runs). Reason: E2's half-width 0.0059 at n = 200 scales to about 0.0042 at n = 400, safely below 0.0050. At n = 300 it would be about 0.0048, too close to the limit. One SBM graph and one shared `Draws` per replicate (common random numbers).
- Seeds: master **918003**, bootstrap **918300** ($B=10{,}000$), smoke 918997.

## 3. Outcomes, contrasts, interpretation
- Outcomes, windows and δ as in E1 and E2. **Primary: pC_change** (copying growth). All other confirmatory and secondary outcomes are reported.
- One contrast: plausible-max − ref, paired by replicate, 95% percentile bootstrap CI. Labels as in E1 §6.
- **Precision rule** (validated, `b199681`): CI half-width ≤ δ/4.
- **"Copying grows at the plausible maximum"** is claimed only if the pC_change contrast is detected with magnitude above δ (> +0.02) **and** is adequately precise. If E2b is again imprecise, it is reported as such and nothing is extended.

## 4. Prediction
From E2: the pC_change contrast is **above δ** (E2 estimate +0.049). The outcome is reported either way.

## 5. Runner guards
Lock-hash check against `docs/experiments/E2b-lock.json`, clean git tree, refuse if `runs/E2b` exists. Smoke: `E2b-smoke`, replicates 1–2, pipeline checks only, outputs deleted.
