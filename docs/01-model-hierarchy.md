---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 01 · Model hierarchy and experiment matrix

Current spec. It replaces blueprint §36 and the exam/ladder parts of §47 ([[docs/00-blueprint-v1]], amendments A1–A3, A5).

## Ladder (mechanisms only)

| Model | $\eta_Q$ | $\beta_P$ | $\beta_C$ | Exam → $C$ | Exam → $E$ | Question it answers |
|---|---|---|---|---|---|---|
| **M0** | 0 | 0 | 0 | no (probe) | no (probe) | What flow structure appears from fixed tendencies alone? |
| **M1** | 0.20 | 0 | 0 | no (probe) | no (probe) | Can personal success alone make copying expand? **(strongest emergence test)** |
| **M2** | 0.20 | 0.5 | 0 | no (probe) | no (probe) | What does peer exposure add? |
| **M3** | 0.20 | 0.5 | 0.5 | no (probe) | no (probe) | Does letting the existing belief $C$ drive decisions change the system? |
| **M4** | 0.20 | 0.5 | 0.5 | yes, $\eta_C$ | no ($\eta_E=0$) | Does exam feedback on confidence alter behaviour? |
| **M5** | 0.20 | 0.5 | 0.5 | yes, $\eta_C$ | yes, $\eta_E=0.30$, $\tau_E=0.70$ | Does effort remediation alter long-run knowledge and behaviour? |

The $\beta_P=\beta_C=0.5$ "on" values are the §32 reference values.

**Always on in every model (A1, A5):**
- learning ($\alpha$);
- homework → confidence update ($\eta_C=0.20$), so $M_i=C_i-K_i$ is always measurable;
- $X_i$ always computed (inert while $\beta_P=0$);
- an exam every $F_E=5$ homeworks. In M0–M3 it is a **diagnostic probe** that measures $G^E$ and changes nothing ($C,E,Q$ untouched), so $\Delta_{GK}$ exists from M0 on. In M4–M5 it is causal.

In M0, $Q$ stays at $q_0$ for every action, so choice probabilities stay at $p^0$ for the whole run.

## Crossed factors (A3, A4)

$$\text{model}\{M0..M5\}\times R\{1,3\}\times\text{topology}\{ER, WS, SBM\}\times\text{replicate}$$

- $R$ is **not** a model stage. The reference is $R=3$; $R=1$ is the no-multi-hop control.
- For each replicate × topology, **one graph** is drawn and every model × $R$ run uses it (paired design, common random numbers: [[docs/05-rng-and-reproducibility]]).
- A20 frozen contact weights are a crossed **network input condition**, not a behavioural model stage. Unity and weighted conditions must reuse the same topology and semantic draws; no weight may update during a run.
- The reference topology is SBM (§30 "community network").
- Replicates: about 200 during development. Final counts are chosen by convergence (§43).

## V3 is a separate model, not M6

A21 V3 does not extend the M0–M5 ladder and must not be labelled M6. Its choice, belief, sharing and heterogeneity equations are frozen in [[docs/10-v3-generative-model]]. V1/V2 and V3 may share a topology, contact weights and semantic draws for paired comparisons, but use distinct run labels and manifests. No V3 result is part of E1–E4.

## Which comparison measures what

| Comparison (same replicate, same graph) | Measures |
|---|---|
| $M1(R) - M0(R)$ | effect of personal reinforcement at fixed routing depth |
| $M_k(R{=}3) - M_k(R{=}1)$ | effect of multi-hop flow with the mechanism held constant |
| $M2-M1$, $M3-M2$, $M4-M3$, $M5-M4$ | the added mechanism, one at a time |
| cascade / flow statistic of $M_k$ at $R$ vs **$M0$ at the same $R$** | whether structure exceeds what topology plus fixed tendencies give |

Never use $M0(R{=}1)$ as the null for an $R{=}3$ result (A3).

## Reference parameters (V1/V2; V3 uses these as distribution means)

$N=30$, $H=20$, $F_E=5$, $M_H=10$, $M_E=30$, $K_0=C_0=0.5$, $E_0=1$, $\alpha=0.0584$, $p_C^0=0.10$, $\kappa=0.15$, $\chi_C=0.10$, $\eta_C=0.20$, $q_0=K_0-\kappa=0.35$. Graph: $\bar d=6$; SBM $r=5$; WS $\omega=0.1$.

## Robustness axes (one at a time around the reference)

| Axis | Values | Source |
|---|---|---|
| $q_0$ | $0,\;K_0-\kappa,\;K_0$ (**mandatory**) | A6 |
| $p_C^0$ | 0.01, 0.20 | §31 |
| $K_0$ | 0.4, 0.6 | §31 |
| $C_0-K_0$ | ±0.2 | §31 |
| $\chi_C$ | 0, 0.5, 1 | §32 |
| $\kappa$ | 0 | §32 |
| $N$ | 20, 40 | §29 |
| $F_E$ | 2, 10, no exams | §29 |
| $M_H$, $M_E$ | → 1000 (noiseless grades) | §29 |
| $\bar d$ | 4, 6, 8, 10 (even, for WS matching) | §30, A14 |
| $\omega$ (WS) | 0.05–0.3 | §30 |
| $r$ (SBM) | 2–10 | §30 |
| $\tau_E$ | 0.6, 0.8 (M5 only) | §32 |
| failed-copy fallback | variant where a failed copier learns as if independent | §18 |

$q_0$ is derived as $K_0-\kappa$ on every axis (unclipped). Only the $q_0$ axis sets it directly (A12).

Broker analysis, first scope (A15): M0, M1, M2 at $R=3$, SBM, reference parameters, $L=200$ rewirings.

Calibration and sensitivity sequencing: [[docs/06-validation-and-ablations]].
