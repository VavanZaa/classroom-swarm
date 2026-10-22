---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 06 · Validation, nulls and ablations

## A. Automated tests, required before any scientific run (§44 + amendments)

The four easiest to get subtly wrong are **bold**: isolate masking (T11), synchronous propagation (T3), CRN reproducibility across variants (T8), and reconstruction from raw logs (T13).

| # | Test |
|---|---|
| T1 | Bounds every event: $0\le K,C,G\le1$; $E\ge1$ |
| T2 | Provenance: following `routing_events` parent links from any copied answer ends at its root, the root produced that `answer_id` itself, and every hop is an edge of $A$ |
| **T3** | **Synchronous propagation:** a packet received in round $r$ is never sent in round $r$; transfers in a round use only holders at the round start; depth ≤ $R$; with $R=1$, depth ≤ 1 |
| T4 | Each request targets a not-yet-queried neighbour; a copier stops asking after its first packet; transfer ⇔ target had a packet at round start |
| T5 | No student-side use of another student's $K$: routing and partner choice receive only ids and uniforms (checked structurally) |
| T6 | Same seed + config + graph + code gives identical outputs |
| T7 | **A1:** M0–M3 with and without diagnostic exams give identical trajectories and identical non-exam tables |
| **T8** | **CRN across variants:** runs in one replicate share the graph hash and identical $U$ tensors; $U^{routing}$ for $R=1$ equals row 0 of $R=3$; with forced identical actions, M0 and M1 give identical item outcomes |
| T9 | $b_C$: with $Q$ uniform, $C=0.5$, $X=0$, $P(C)=p_C^0$ exactly; a uniform $q_0$ shift leaves $P$ unchanged; $q_0=K_0-\kappa$ unclipped (may be negative) |
| T10 | Calibration identity: all-S with $E=1$ gives $K_T=1-(1-K_0)(1-\alpha)^T$ exactly ($K$ is deterministic under S) |
| **T11** | **Isolate masking:** $\deg=0$ ⇒ `feasible_D = feasible_C = false`, $P(S)=1$, action always S, $X=0$, $Q^D$ and $Q^C$ never change |
| T12 | M0 ($\eta_Q=0$): $Q$ never changes; action frequencies over many replicates match $p^0$ among feasible students |
| **T13** | **Reconstruction:** every homework grade equals the mean of that student's `item_outcomes`; copied item outcomes equal the source `answer_id`'s outcomes exactly; cascades and $H^{(h)}$ rebuilt from `routing_events` match an independent in-simulation tally kept only for the test |
| T14 | Graphs: SBM sizes and $p_{in}/p_{out}$ as in docs/04; WS rejects odd $k$ or $k\ge N$; the edge-list hash is stable across runs |
| T15 | Snapshots: event 0 is the initial state; each event's pre-state is the previous committed snapshot; probe exams leave the snapshot unchanged |
| T16 | Degree-preserving null keeps every node's degree and node ids |

**Equation conformance (docs/03).** Exact hand-computed values on tiny hand-built graphs with fixed uniforms. Directional checks ("K went up") don't count.

| # | Test |
|---|---|
| T17 | Independent learning: $K^+=K+\alpha E(1-K)$ (e.g. 0.5 → 0.55 at $\alpha=0.1$), clipped at 1; items are thresholded at the **post-learning** $K^+$ |
| T18 | Discussion: uses frozen pre-homework $K_i, K_j$; $\Delta K=\alpha E(1-K_i)[1+(K_j-K_i)_+]$; answer probability $\max(K_i^+,K_j)$; multiplier 1 with a weaker partner; clipping at 1 |
| T19 | Successful copy: items equal the source's exactly (no new randomness); $K^+=K+\chi_C\alpha E(1-K)$ (e.g. 0.5 → 0.51 at $\chi_C=0.2$); cost 0 |
| T20 | Failed copy: fallback items thresholded at the pre-homework $K$; $\Delta K=0$; cost 1; no transfer, no flow edge, no cascade membership; own `answer_id`, `root_id = i`, `depth = 0` |
| T21 | Reward $R=G-\kappa c$; only the chosen $Q_a$ updates, $Q_a+\eta_Q(R-Q_a)$; the other two are unchanged |
| T22 | $C'=C+\eta_C(G-C)$; $X'$ = distinct incoming requesters / degree; the student's own outgoing requests don't count |
| T23 | Exams: M0–M3 change nothing; M4 updates $C$ only; M5 updates $C$ and $E'=1+\eta_E(\tau_E-G^E)_+$; a good exam resets $E$ to 1; the next homework's learning uses the new $E$ |
| T24 | Frozen pre-state: a student discussing with a partner who learns in the same homework sees the partner's **pre-homework** $K$; nothing is committed before the homework is resolved |
| T25 | V2 exposure: `exposure="copying"` measures the share of neighbours choosing C in the previous homework; default `"requests"` preserves V1; isolates get 0 |
| **T26** | **Frozen weighted graph (A20):** weights are positive, finite, symmetric and immutable; uniform weights reproduce legacy outputs exactly; weighted partner/request choices use the same semantic uniforms and sorted candidate ids; weights never affect strategy probabilities or $X$ directly; weight shuffle preserves topology and the global weight multiset |
| **T27** | **V3 no-prevalence policy:** no V3 choice function accepts $X$ or neighbour-copy prevalence; homework 1 uses only the declared seed; later exploration is uniform over feasible actions and the seed is off |
| T28 | V3 traits follow the approved transforms, are reproducible and graph-independent; an explicit permutation moves complete trait bundles without changing their multiset |
| T29 | $A_{ij}$ starts at $A_0$ on directed social ties, changes only after $i$ directly requests $j$, and follows $A'=A+\eta_A(Y-A)$ exactly |
| T30 | V3 target selection maps the routing uniform through weights proportional to $w_{ij}A_{ij}$; discussion continues to use $w_{ij}$ only |
| **T31** | **Endogenous sharing:** the logit reciprocity equation is exact; non-holders cannot share; simultaneous transfers are synchronous; willingness and per-homework capacity are separately logged and enforced |
| T32 | Individual $K_0$, $\alpha$ and $\kappa$ drive the corresponding learning and reward equations; there are no role/type fields |
| T33 | Optional social learning is zero in baseline and, when positive, applies the same weighted-neighbour reward update to S, D and C |
| T34 | V3 is exactly reproducible; V1/V2 legacy tables and decisions remain unchanged by the added streams and V3 code |

## B. Calibration order (§41, on the new ladder)
1. All-S, $\eta_E=0$: confirm $\alpha$ (T10). 2. Measurement noise from $M_H$, $M_E$. 3. Discussion on. 4. Copying on with adaptation frozen (M0, both $R$). 5. Reinforcement (M1). 6. Peer exposure (M2). 7. Confidence → decisions (M3). 8. Exam → confidence (M4). 9. Exam → effort (M5).

Never calibrate everything at once. $\eta_C$, $\tau_E$ and $\alpha$ stay fixed after calibration.

## C. Nulls
- **Cascades** (size $S_s$, depth $L_s$, §38): compare $M_k$ against **M0 at the same $R$**, same replicate (A3).
- **Route concentration** $C_F$ (§40): against M0 at the same $R$ ($\eta_Q=0$) and against the degree-preserving ensemble.
- **Weighted contact condition (A20):** compare against (i) the same topology with every weight set to 1 and (ii) the same topology with weights shuffled across edges. A claim that a broker exceeds the weighted input structure requires a strength-aware null; the simple shuffle is not sufficient because it does not preserve each node's strength.
- **Brokers** (§39, A8, A15): run the same model on the $L$ degree-preserving rewired graphs and report all three:
  - $Z_i^B=(B_i-\mu_i^{null})/\sigma_i^{null}$, or `NA` when $\sigma_i^{null}=0$ (the case is kept, not dropped);
  - $B_i^{excess}=B_i-\mu_i^{null}$;
  - the one-sided permutation $p_i=\dfrac{1+\#\{B_i^{null}\ge B_i^{obs}\}}{L+1}$.

  All-zero nulls with $B_i^{obs}>0$ are potentially the most informative cases, not errors. First scope: **M0, M1, M2; $R=3$; SBM; reference parameters; $L=200$**. M0 measures the brokerage produced by topology plus stochastic traffic alone. $L=500$–1000 only for final claims. Claims about *community bridges* need the degree- and block-preserving null first ([[docs/04-network-generation]]).

## D. Robustness
Axes in [[docs/01-model-hierarchy]]. The $q_0$ axis is mandatory (A6). If persistent regimes change drastically across $q_0$, initialisation is driving the "emergence". $\eta_Q=0$ does **not** test this.

## E. Sensitivity (§42)
Structural ablation first. Then one-factor screening (fix or remove parameters with negligible effect on all key outputs). Then global analysis on the survivors: LHS + PRCC where monotone, Sobol where strongly nonlinear. First vector: $[\eta_Q,\kappa,\beta_P,\beta_C,\chi_C,\eta_E]$.

## F. Monte Carlo (§43)
About 200 replicates during development. Final counts come from convergence of $E[P(C,T)]$, $E[\bar K(T)]$, median max cascade size and upper-tail cascade statistics, not from a round number.

## G. Failure criteria (§45): reduce the model, don't add variables
The result exists only in a narrow parameter range; removing one arbitrary parameter reverses most conclusions; topology has no measurable effect; $Q$ adds nothing over M0; confidence adds nothing beyond $Q$; widely different parameters give the same macro output with no distinguishing observable; or the "emergent" phenomenon follows trivially from one imposed equation.

## H. Claims (§49)
Say "under these mechanisms and network conditions, X emerged". Never say "real classrooms behave this way". Spread under $\beta_P=0$ and spread only with $\beta_P>0$ are both informative results.
