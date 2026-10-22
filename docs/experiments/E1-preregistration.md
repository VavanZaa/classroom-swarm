---
type: experiment
id: E1
status: LOCKED
date: 2026-09-18
locked: 2026-09-18
run_ids: []
tags:
  - experiment
  - preregistration
---
# E1 · Preregistration: M0–M5 × R × topology (LOCKED)

Status moves DRAFT → LOCKED → RUN → REPORTED, or to VOID if a measurement turns out not to measure its question. **Locked 2026-09-18 after Vavan approved the draft, including every value marked PROPOSED in it.** At the lock, no Experiment 1 run and no analysis code existed. Any later change is a numbered deviation (§11).

## 0. Sequence (frozen by Vavan, 2026-09-18)
Reference calibration and tests (done) → **this preregistration, reviewed and locked** → analysis layer built to exactly §4–§7, unit-tested on constructed fixtures (never E1 output) → excluded smoke run (§9) → E1 run **once** with the seeds in §2.

E1 tests the frozen model and never recalibrates it. $\alpha=0.0584$ comes from the all-S calibration (`72bdb78`), which is not part of E1. Nothing in E1 may change a model parameter.

## 1. Questions (no directional hypotheses)
E1 estimates what each mechanism contributes. It does **not** require any mechanism to "work". $M2\approx M1$, or copying that doesn't expand in M1, are fully informative outcomes (blueprint §49).

1. What does **personal reinforcement** add over fixed tendencies? ($M1-M0$)
2. What does **explicit peer exposure** add beyond personal reinforcement? ($M2-M1$)
3. What do **confidence → strategy**, **exam → confidence** and **exam → effort** each add? ($M3-M2$, $M4-M3$, $M5-M4$)
4. What does **multi-hop routing** add, holding the mechanism fixed? ($R3-R1$)
5. How does **topology** change all of the above? (family contrasts)
6. Does the observable proxy $\Delta_{GK}^{last}$ track the latent decoupling $\Delta_{HK}$ across conditions? (validity check)

## 2. Design
- **Conditions:** stages M0–M5 × $R\in\{1,3\}$ × families {ER, WS, SBM} = 36 per replicate. Model ladder: [[docs/01-model-hierarchy]]. Schedule: [[docs/03-event-schedule]].
- **Replicates:** 1–200 → **7,200 runs**. The replicate count is fixed here and is not extended after seeing results (see §8).
- **Parameters:** exactly `Params()` defaults (docs/02). $N=30$, $H=20$, $F_E=5$, $M_H=10$, $M_E=30$, $K_0=0.5$, $\alpha=0.0584$, $p_C^0=0.10$, $q_0=K_0-\kappa=0.35$, $\eta_Q=0.20$, $\kappa=0.15$, $\chi_C=0.10$, $\eta_C=0.20$; $\beta_P=0.5$ from M2, $\beta_C=0.5$ from M3, $\eta_E=0.30$ and $\tau_E=0.70$ in M5; $\bar d=6$, $\omega=0.1$, $r=5$. No robustness axes in E1.
- **Pairing:** one graph per replicate × family, one shared `Draws(R_max=3)` per replicate (docs/05). The replicate is the statistical unit.
- **Seeds:** `experiment_id = "E1"`, **master seed 918001**. Smoke run: `experiment_id = "E1-smoke"`, master seed 918999. Bootstrap seed 918100. The calibration and test seed (20260918) is never reused.
- **Runner:** `run_replicate("E1", rep, 918001, Params(), runs/E1)` for rep = 1..200, with default `SimulationControls`, from one clean git commit. Every manifest records that commit, and a dirty tree voids the run.

## 3. Units and conventions
- $h=1..20$ homeworks. Exams $e=1..4$ follow homework $h_e\in\{5,10,15,20\}$.
- $K^{post}_i(h)$ = committed K after homework h (the snapshot of event `h<h>`).
- Grades: $G^H_{i,h}$ = `decisions.grade`; $G^E_{i,e}$ = the student's share of correct exam items.
- Everything is computed from the canonical raw tables (docs/07) by `derive`, never from in-simulation state.

## 4. Outcomes and definitions
**Confirmatory** (the per-run scalar used in contrasts is in bold):

| # | Outcome | Definition | Run-level scalar |
|---|---|---|---|
| O1 | Copying prevalence | $P(C,h)=\#\{a_i(h)=C\}/N$ (all students) | **pC_late** = mean over $h=16..20$; **pC_change** = pC_late − mean over $h=1..5$ |
| O2 | Copy success | $P(\text{succ}\mid C,h)$ = successes / C-choices | **succ_late** = Σ successes / Σ C-choices over $h=16..20$ (NA if no C-choice) |
| O3 | Knowledge | $\bar K(h)$, $\mathrm{Var}(K(h))$ (population variance over N) | **K_final** = $\bar K(20)$; VarK_final (secondary) |
| O4 | Latent decoupling | $\Delta_{HK}(h)=\frac1N\sum_i\,(G^H_{i,h}-K^{post}_i(h))$ | **dHK_late** = mean over $h=16..20$; dHK_mean over $h=1..20$ (secondary) |
| O5 | Observable decoupling, primary | $\Delta^{last}_{GK}(e)=\frac1N\sum_i\,(G^H_{i,h_e}-G^E_{i,e})$ (mean of paired individual differences) | **dGK_last** = mean over $e=1..4$; each $e$ also reported |
| O6 | Cascades (§38, size includes the root; fallback excluded) | per homework: $S_{max}(h)$ = largest cascade size, $L_{max}(h)$ = largest depth | **Smax_mean**, **Lmax_mean** = means over $h$ |
| O7 | Route concentration | $F_{ij}=\sum_h H^{(h)}_{ij}$ over the run, on directed edges. Eligible edges = both directions of every social edge ($2\lvert E\rvert$). Top $k=\lceil0.2\cdot2\lvert E\rvert\rceil$ by flow. $C_F$ = flow on top $k$ / total flow (NA if no flow) | **CF** |

**Secondary** (reported, same contrasts, not interpreted as confirmatory): VarK_final; dHK_mean; $\Delta^{block}_{GK}(e)=\frac1N\sum_i\big(\frac{1}{5}\sum_{h\in B_e}G^H_{i,h}-G^E_{i,e}\big)$ with $B_e=\{5e-4..5e\}$ (**dGK_block**; it measures the accumulated advantage over the interval and includes honest learning over time, so it's not interchangeable with O5); reach = mean over $h$ of the share of students holding a copied packet.

**Validity check (pre-registered):** Spearman correlation between condition-mean dGK_last and condition-mean dHK_late across the 36 conditions, plus the per-condition scatter. Interpretation threshold: see §6.

**Exploratory** (reported as exploratory, no confirmatory claims): node-level broker identities, cascade shapes, SBM community-specific or bridge phenomena (these need the block-preserving null, docs/04), used-edge variant of $C_F$, per-family detail beyond §5, anything not listed above.

### 4b. Implementation clarifications (added at the lock, before any analysis code or run; disclosed to Vavan)
These fix edge cases the definitions above leave open. They change no outcome, contrast or threshold.
1. **No cascades in a homework** (no student produced an answer, e.g. everyone chose C): $S_{max}(h)=L_{max}(h)=0$ and reach $=0$ for that homework.
2. **NA rules:** succ_late is NA if there's no C-choice in $h=16..20$. CF is NA if total flow is 0 or the graph has no edges. $Z^B_i$ is NA if $\sigma^{null}=0$. A contrast drops pairs with any NA (§5). A condition mean ignores NA runs, and their count is reported.
3. **Bootstrap:** one set of 10,000 resampled replicate-index vectors (seed 918100) is shared by every contrast and every condition-mean CI, so all intervals are computed on the same resamples.
4. **Convergence (§8)** is evaluated per condition (36) for each listed quantity. The running mean is taken over replicates in order 1..200. The criterion is $\max_{n=151..200}\lvert\bar x_n-\bar x_{200}\rvert<0.1\times$ the half-width of the 95% bootstrap CI of $\bar x_{200}$. E1 counts as converged only if every condition passes, and failures are listed.
5. **$E[P(C,20)]$** in §8 means $P(C,h{=}20)$ per run (O1 at the last homework), not pC_late.
6. **Broker paths:** every copied answer contributes one path (root … holder). Students at positions 1..len−2 are internal, so sub-paths of longer paths are counted as separate paths, as §39's count of "answer paths where $i$ is internal" implies.
7. **Null member draws (§7):** `Draws(null_seed(918001, rep, "SBM", ℓ), rep, N, M_H, M_E, R_max=3)`, and the null graph comes from `rewire_degree_preserving(graph, null_seed(918001, rep, "SBM", ℓ))`. The same integer seeds both, and they are distinct streams because stream codes differ inside `Draws`.

## 5. Contrasts and estimation
- **Paired difference per replicate**, then the mean over replicates, with a **95% percentile bootstrap CI** over replicates ($B=10{,}000$, seed 918100). If either run is NA, the pair is dropped, and the number of pairs used is reported.
- **Primary contrasts** (three):
  - **P1** $M1-M0$ at $R=3$, SBM: the strongest emergence test (no peer-imitation rule).
  - **P2** $R3-R1$ at M1, SBM: multi-hop contribution.
  - **P3** $M2-M1$ at $R=3$, SBM: peer-exposure increment.
- **Secondary contrasts:** every adjacent stage difference at each $R$ × family (30); $R3-R1$ for every stage × family (18); SBM − ER and WS − ER for every stage × $R$ (24).
- Every contrast is reported with its estimate, CI and $n$. No result is dropped for being null or inconvenient.

## 6. Interpretation rules (no direction prejudged)
For each contrast and outcome with smallest effect of interest $\delta$:
- **Difference detected:** the CI excludes 0. Magnitude is reported relative to $\delta$.
- **Negligible:** the CI lies entirely within $\pm\delta$.
- **Inconclusive:** anything else.

**$\delta$ values (approved by Vavan, 2026-09-18):** pC_late, pC_change 0.02; succ_late 0.05; K_final 0.01; dHK_late 0.01; dGK_last 0.02; Smax_mean 1.0 student; Lmax_mean 0.25 hops; CF 0.05; broker share (§7) 0.05. Secondary outcomes use the δ of their primary counterpart (VarK_final: none, reported descriptively; dHK_mean 0.01; dGK_block 0.02; reach 0.02).

**Validity check (approved):** $\Delta^{last}_{GK}$ counts as an adequate proxy if Spearman $\rho\ge0.8$ across conditions. Otherwise that is reported as a warning about the proxy, not as a failure of E1.

Reference for scale: the all-S calibration noise floor of single-classroom $\Delta_{GK}$ is SD 0.024–0.035 (`72bdb78`). The replicate means here have SE of about 0.002.

## 7. Broker analysis (confirmatory scope only: M0, M1, M2 at $R=3$, SBM)
- $B_i$ = number of answer paths across all 20 homeworks in which student $i$ is **internal** (path[1:-1] of every copied answer's provenance path, §39).
- **Null:** $L=200$ degree-preserving rewirings of the replicate's SBM graph (docs/04), with the same stage and parameters. **Approved:** null member $\ell$ also gets its own dynamics draws, `Draws(master = null_seed(918001, rep, "SBM", ℓ), replicate = rep, …)`, so the null samples both topology and stochastic traffic. The alternative (the observed draws shared by all null members) samples topology only and would understate $\sigma^{null}$.
- Per student: $B^{excess}_i$, $Z^B_i$ (`NA` when $\sigma^{null}=0$, kept), $p_i=(1+\#\{B^{null}_i\ge B_i\})/(L+1)$.
- **Run-level confirmatory scalar:** the broker share = fraction of students with $p_i\le0.05$. Contrasts $M1-M0$ and $M2-M1$ as in §5. M0's own share is reported as topology plus fixed-traffic brokerage.
- Cost: 120,000 extra runs, about 0.5 h serial (feasibility check, `72bdb78` session).

## 8. Monte Carlo adequacy (§43)
$n=200$ is fixed for E1. Reported: the Monte Carlo SE of every primary scalar, and running-mean curves over replicates for $E[P(C,20)]$, $E[\bar K(20)]$, the median of Smax_mean and its 95th percentile. **Adequacy criterion (approved):** over the last 50 replicates the running mean moves by less than 10% of the final CI half-width. If it doesn't, that is reported as "not converged", and a separate pre-registered E1b with more replicates is required. E1 is never silently extended.

## 9. Excluded smoke run
`E1-smoke`, master seed 918999, replicates 1–2, all 36 conditions, plus the broker null at $L=5$. Its only purpose is to catch storage, runtime and analysis-pipeline failures. Checks are limited to: every run completes, every table reads back with the docs/07 schema, every §4–§7 output is produced without an unexpected NA, and runtime. **Effect sizes and outcome values are not inspected.** Outputs are deleted after the check and never used to change anything.

## 10. Known confounds and circularity risks
- Cascade size and flow concentration can come from topology alone, so they're read against M0 at the same $R$ and the degree-preserving null (A3, A8).
- A single high-degree student isn't a broker (§39): only $Z$, excess and $p$ against the null count.
- Early-choice lock-in from $q_0$ is controlled by the $q_0$ robustness axis, which is **not** in E1. Any "persistent regime" claim from E1 must say so.
- $\eta_Q$ vs $\kappa$, $\beta_P$ vs density, $\eta_E$ vs exam frequency are partly confounded (§35). E1 varies none of them, so it can't separate them.
- dGK_block includes honest learning over time. Only O5 (dGK_last) is primary.
- All claims are of the form "under these mechanisms and network conditions" (§49).

## 11. Deviations
After the lock, any change is a numbered deviation with its date and reason. No parameter changes after seeing E1 output. If an analysis bug is found after the run: fix it, re-run the analysis only (not the simulation), and report both versions.

## 12. Lock
Locked 2026-09-18. The lock record is `docs/experiments/E1-lock.json`: the SHA-256 of this file as locked, committed together with it in the commit titled "docs: lock Experiment 1 preregistration". The E1 runner must refuse to start if this file's SHA-256 no longer matches the lock record.

## Result
Filled only after the run.
