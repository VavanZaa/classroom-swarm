---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 02 · State and parameters

Current spec. Rationale for each item is in [[docs/00-blueprint-v1]] (§ numbers given).

## Persistent state per student (§4)

| State | Domain | Initial | Notes |
|---|---|---|---|
| $K_i$ knowledge | [0,1] | $K_0$ | $P$(correct on a standard item, independently) |
| $C_i$ confidence | [0,1] | $K_0$ (+ robustness offset) | updated after every homework in every model (A5) |
| $E_i$ effort | ≥ 1 | 1 | changes only in M5 (exam → effort) |
| $\alpha_i$ learning efficiency | > 0 | $\alpha$ for all | heterogeneous $\alpha_i$ is a later robustness run |
| $Q_i^S, Q_i^D, Q_i^C$ | reals | **$q_0$ for all three** (A6) | learned expected reward, not probabilities |

**Per-homework (not persistent):** $X_i$ peer exposure (measured; §7/§23 under `exposure="requests"`, the V1 default; the share of neighbours who chose C last homework under `exposure="copying"`, V2, A19), action, answer packet $\Pi_i$ (answers, root, path), queried set $\mathcal Q_i$, incoming requesters.

**Derived observables:** $M_i=C_i-K_i$; $P_i(S,D,C)$; $G^H_i$, $G^E_i$; $\Delta_{GK}=\overline{G_H}-\overline{G_E}$.

## Derived constants

- Copy bias (§8): $b_C=\ln\!\left(\frac{2p_C^0}{1-p_C^0}\right)$, with $b_S=b_D=0$. For $p_C^0=0.10$, $b_C=\ln(2/9)\approx-1.504$. It reproduces $p_C^0$ exactly only while $\beta_C(C-0.5)=0$ and $X=0$.
- Uniform $q_0$ (A6) shifts all three utilities equally, so it leaves initial choice probabilities unchanged. It only moves the reference point of the first prediction errors. **$q_0=K_0-\kappa$ is derived** whenever $K_0$ or $\kappa$ changes, and is never clipped (a negative value is fine). Only the explicit $q_0$ robustness run overrides it (A12). This separates *initial strategy prevalence* ($b_C$) from the *expected-reward prior* ($q_0$).
- Feasibility (A11): if $\deg(i)=0$, D and C are masked ($U=-\infty$), so $P(S)=1$. $p_C^0$ is therefore the initial copying tendency **when copying is feasible**.
- Learning efficiency (§31): $\alpha = 1-\left(\frac{1-K_T}{1-K_0}\right)^{1/T}$. With $K_0=0.5$, $K_{20}=0.85$, this gives $\alpha\approx0.0584$ (checked); $K_{20}\in[0.80,0.90]$ gives $\alpha\in[0.045,0.077]$ (checked). **These values come from the desired trajectory, not educational data. Always report that.**

## Parameter registry (reference; sweep)

| Group | Parameter | Reference | Sweep | Status |
|---|---|---|---|---|
| Environment | $N$ | 30 | 20–40 | scenario |
| | $H$ | 20 | 12–30 | horizon |
| | $F_E$ | 5 | 2–10, none | scenario |
| | $R$ | 3 | {1, 3} crossed; 1–5 | structural (A3) |
| | $M_H$ / $M_E$ | 10 / 30 | 5–20 / 10–50; →1000 | measurement |
| Network | $\bar d$ | 6 | {4, 6, 8, 10} | input condition (even, A14) |
| | family | SBM | ER, WS, SBM | input condition |
| | $\omega$ (WS) | 0.1 | 0.05–0.3 | input condition |
| | $r=p_{in}/p_{out}$ (SBM) | 5 | 2–10 | input condition |
| | $w_{ij}$ contact weight (A20) | 1 on every edge | explicit positive finite edge values | frozen network input; not a `Params` field |
| Learning / init | $K_0$ | 0.50 | 0.30–0.70 | user-defined |
| | $\alpha$ | 0.0584 | 0.045–0.077 | from trajectory |
| | $p_C^0$ | 0.10 | 0.01–0.20 | scenario |
| | $q_0$ | derived $K_0-\kappa$ = 0.35 | {0, 0.35, 0.5} | A6, A12 |
| Behaviour | $\eta_Q$ | 0.20 | 0.05–0.40; ablation 0 | timescale, not estimated |
| | $\kappa$ | 0.15 | 0–0.40; ablation 0 | hypothesis |
| | $\beta_C$ | 0 → 0.5 from M3 | 0–1.5 | magnitude uncalibrated |
| | $\beta_P$ | 0 → 0.5 from M2 | 0–1.5 | mapping unknown; **0 is mandatory** |
| | exposure (A19) | "requests" (V1) | {"requests", "copying"} | structural: what $X$ measures |
| | $\chi_C$ | 0.10 | 0–1; {0, 0.5, 1} | unknown |
| | $\eta_C$ | 0.20 (fixed first) | 0.10–0.40; ablation 0 | direction supported |
| | $\eta_E$ | 0 → 0.30 in M5 | 0–0.60 | user hypothesis |
| | $\tau_E$ | 0.70 | 0.60–0.80 | scenario |

## Fixed structural constants (§33): not tunable in V1

Softmax temperature = 1. Costs: $c_S=c_D=1$, $c_C=0$ on success and 1 on failure. Share probability = 1. Transmission error = 0. A20 contact weights may be non-uniform but are frozen and exogenous. The following are all off or absent: friendship dynamics, forgetting, exam → direct $Q$ update, dynamic cheating-edge strength, reputation, persistent norm state, detection belief, eligibility traces.

## Known partial confounds (§35)

$\eta_Q$ vs $\kappa$ (use the whole $P(C,t)$ trajectory); $\beta_P$ vs density (keep both behavioural and flow outputs); $\chi_C$ vs $\alpha$ (calibrate $\alpha$ on the all-independent control first); $\eta_C$ vs $\beta_C$ (fix $\eta_C=0.20$, vary $\beta_C$); $\eta_E$ vs exam frequency (report $E(t)$ with exam timing).
