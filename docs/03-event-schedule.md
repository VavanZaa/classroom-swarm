---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 03 · Event schedule

This document is the V1/V2 schedule. V3 has its own A21 schedule and equations in [[docs/10-v3-generative-model]]; it does not modify the steps below.

Frozen spec. This is blueprint §27–28 ([[docs/00-blueprint-v1]]) with amendments A1, A5, A6, A11 and A12 applied. The random-number tensor used by each random step is in brackets; see [[docs/05-rng-and-reproducibility]].

## Model stages

- **M0** = fixed strategy tendencies ($\eta_Q=0$, $\beta_P=0$, $\beta_C=0$)
- **M1** = M0 + personal strategy reinforcement ($\eta_Q>0$)
- **M2** = M1 + peer-exposure effect ($\beta_P>0$)
- **M3** = M2 + confidence affects strategy ($\beta_C>0$)
- **M4** = M3 + exam updates confidence
- **M5** = M4 + exam changes effort ($\eta_E>0$)

**$R$ is not a model stage.** It is crossed independently, $R\in\{1,3\}$, for every model. In **M0–M3 the exam every $F_E$ homeworks is a diagnostic probe only**: it records $G^E$ and changes no state. M4 makes the exam → confidence update causal; M5 adds exam → effort. Parameter values per stage: [[docs/01-model-hierarchy]].

## Initialise (per run)
Load the replicate's graph ([[docs/04-network-generation]]). For every $i$: $K=K_0$, $C=K_0$ (+ offset if on that axis), $E=1$, $\alpha_i=\alpha$, $Q^S=Q^D=Q^C=q_0$ with $q_0=K_0-\kappa$ unless the $q_0$ axis overrides it (A12, unclipped), and $X=0$. Compute $b_C$. Feasibility: S is always feasible; D and C are feasible iff $\deg(i)>0$. Write snapshot event 0.

## Homework $h = 1..H$

1. **Snapshot.** Freeze $K, C, E, Q, X$ as $K^0, C^0, E^0, Q^0, X^0$. Clear packets, queried sets and incoming requesters. Every decision and learning step below reads the snapshot.
2. **Choose strategy** [$U^{strategy}_{h,i}$]:
   - $U^S=Q^{0,S}+\beta_C(C^0-0.5)$
   - $U^D=Q^{0,D}$
   - $U^C=b_C+Q^{0,C}+\beta_P X^0$
   - **If $\deg(i)=0$: $U^D=U^C=-\infty$, so $P(S)=1$ (A11).**
   - $P=\text{softmax}$ (temperature 1). The action is the inverse-CDF of $U^{strategy}_{h,i}$ over the order (S, D, C). The uniform is drawn for every student, isolates included, so the pairing is unaffected.
3. **Independent / discussion learning and answer creation.** Every self-generated answer set gets `answer_id` = (h, i) with root $=i$, path $=[i]$.
   - **S:** $K^+=\text{clip}(K^0+\alpha E^0(1-K^0))$. Item $q$ is correct iff $U^{item}_{h,i,q}<K^+$.
   - **D** (only feasible when $\deg(i)>0$): sort $N_i$ by student id and map $U^{partner}_{h,i}$ to the cumulative normalized fixed contact weights $w_{ij}/\sum_{k\in N_i}w_{ik}$ (A20). Uniform weights recover the original index rule exactly. Selection uses topology and exogenous contact opportunity only, never another student's $K$. $K^+=\text{clip}(K^0_i+\alpha E^0(1-K^0_i)[1+(K^0_j-K^0_i)_+])$. Item correct iff $U^{item}_{h,i,q}<\max(K^+,K^0_j)$.
   - **C:** no packet yet.
4. **Routing, rounds $r=1..R$** [$U^{routing}_{h,r,i}$]:
   - `holders` = students holding a packet at the start of the round.
   - Each unresolved copier takes the sorted candidates $N_i\setminus\mathcal Q_i$ (and skips if that's empty) and maps $U^{routing}_{h,r,i}$ to their cumulative normalized fixed contact weights (A20). Uniform weights recover the original index rule exactly. It adds $j$ to $\mathcal Q_i$, logs the request $i\to j$ and adds $i$ to $j$'s incoming requesters. If $j\in$ holders, a transfer $j\to i$ is scheduled.
   - At the end of the round all transfers commit **simultaneously**. The receiver gets the sender's answers and `answer_id` unchanged, with depth = sender depth + 1.
   - A packet received in round $r$ can be passed on from round $r+1$. A copier accepts only its first packet.
5. **Grades:**
   - S/D: $G^H$ = mean of item outcomes.
   - Successful copier: item outcomes are **inherited exactly** from the packet (no new item randomness), and $G^H$ is their mean. $K^+=\text{clip}(K^0+\chi_C\alpha E^0(1-K^0))$.
   - Failed copier: item correct iff $U^{item}_{h,i,q}<K^0$ (same tensor, own `answer_id`, mode `fallback`). $G^H$ is the mean, and $K^+=K^0$ (no learning).
6. **Confidence (all models):** $C'=\text{clip}(C^0+\eta_C(G^H-C^0))$.
7. **Reward:** $R^H=G^H-\kappa c$, with $c=1$ for S, D and failed C, and $c=0$ for successful C.
8. **Q update (chosen action only):** $Q^{a}\leftarrow Q^{0,a}+\eta_Q(R^H-Q^{0,a})$. The other two actions keep their values.
9. **Peer exposure:** with `exposure="requests"` (V1, default): $X'_i=|\text{distinct incoming requesters}|/\deg(i)$, and 0 if $\deg(i)=0$. Requests to non-holders count; the student's own requests don't. With `exposure="copying"` (V2, A19): $X'_i=|\{j\in N_i: a_j=C\}|/\deg(i)$ for this homework's actions, 0 if $\deg(i)=0$; the student's own action never counts.
10. **Commit** $K,C,Q,X$ and write the snapshot for this event ([[docs/07-output-schema]]).

## Exam, if $h \bmod F_E = 0$ (after commit) [$U^{exam}_{e,i,q}$]

$Y_i=\#\{q<M_E: U^{exam}_{e,i,q}<K_i\}$ (Binomial($M_E,K_i$) in distribution) and $G^E_i=Y_i/M_E$. Then:

| Model | Effect of the exam |
|---|---|
| M0–M3 | **none**: probe only (`diagnostic_only = true`) |
| M4 | $C\leftarrow\text{clip}(C+\eta_C(G^E-C))$ |
| M5 | as M4, plus $E\leftarrow 1+\eta_E(\tau_E-G^E)_+$ |

No exam ever touches $Q$ (§33). Each exam is its own event and gets its own post-event snapshot.

## Invariants
Tests T1–T24 in [[docs/06-validation-and-ablations]]. T17–T24 check each step above with exact values.
