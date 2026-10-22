---
type: experiment-results
id: E1
status: REPORTED
date: 2026-09-18
tags:
  - experiment
  - results
---
# E1 · Results: M0–M5 × R × topology

Results of the preregistered Experiment 1 ([[docs/experiments/E1-preregistration]], locked 2026-09-18, commit `d9bbb6b`). The locked file is not edited. This report and its deviation list are the record.

## Run record
| | |
|---|---|
| Runs | 7,200 (200 replicates × 36 conditions), all completed. Broker null: $L=200$ for M0–M2 at $R=3$, SBM |
| Code | commit `4e73e4d` (clean tree), preregistration SHA-256 `28fd52ca…6914` verified at start |
| Seeds | master 918001, bootstrap 918100 |
| Runtime | 39.3 min serial; raw output 90.6 MB in `runs/E1/` (git-ignored) |
| Derived outputs (SHA-256) | `contrasts.parquet` 2d835572…b938 · `run_summaries.parquet` ed01ea65…5b16 · `broker_scores.parquet` a66eb1f5…fa4c · `broker_null_B.parquet` d82f8680…cd63 · `convergence.parquet` 96cbc6e6…7b18 · `proxy_check.json` bc622734…8587 · `e1_report.json` e814009e…0488 |

## Deviations
**D1 · §8 convergence check VOID (measurement defect, found after the run).** The locked rule requires the running mean over the last 50 replicates to move by less than 10% of the final 95% CI half-width. Both quantities shrink as $1/\sqrt{n}$, so their ratio doesn't depend on $n$. On synthetic iid $N(0,1)$ data the rule passed in **0/200 datasets at n = 200, 800 and 3,200**. It cannot certify convergence, and the preregistered remedy (an E1b with more replicates) could never pass either. The computed result (57/144 checks passed) is therefore reported but **not interpreted**. The criterion was proposed by Claude and not tested on synthetic data before the lock. That is the same class of error as a measurement operator that doesn't measure its estimand.
*Monte Carlo precision, exploratory:* the bootstrap CIs already carry the replicate-level uncertainty. For the primary contrasts, every confirmatory CI half-width is at most 23.2% of its δ (largest: succ_late in P2, 0.012 against δ 0.05), and 26 of 27 are below 10%. So no interpretation label is sensitive to Monte Carlo noise at this precision. A valid adequacy criterion for future experiments needs Vavan's decision.

No other deviations. Parameters, seeds, conditions and analyses ran as locked.

## Primary contrasts (§5), confirmatory outcomes
Estimate [95% CI] and label (§6). "Below δ" means the CI excludes 0 but lies inside ±δ: a real but practically negligible difference.

| Outcome (δ) | **P1** M1 − M0, R3 SBM | **P2** R3 − R1, M1 SBM | **P3** M2 − M1, R3 SBM |
|---|---|---|---|
| pC_late (0.02) | −0.0063 [−0.0074, −0.0051] detected, below δ | +0.0004 [+0.0002, +0.0006] detected, below δ | +0.0009 [+0.0006, +0.0013] detected, below δ |
| pC_change (0.02) | −0.0063 [−0.0076, −0.0051] detected, below δ | +0.0004 [+0.0002, +0.0006] detected, below δ | +0.0001 [−0.0003, +0.0006] negligible |
| succ_late (0.05) | +0.0003 [+0.0000, +0.0008] negligible | **+0.0872 [+0.0758, +0.0990] detected, above δ** | +0.0000 [+0.0000, +0.0000] negligible |
| K_final (0.01) | +0.0005 [+0.0004, +0.0006] detected, below δ | +0.0001 [+0.0001, +0.0002] detected, below δ | −0.0002 [−0.0002, −0.0001] detected, below δ |
| dHK_late (0.01) | +0.0000 [−0.0002, +0.0003] negligible | +0.0001 [−0.0001, +0.0003] negligible | −0.0001 [−0.0001, +0.0000] negligible |
| dGK_last (0.02) | −0.0001 [−0.0003, +0.0002] negligible | +0.0000 [−0.0003, +0.0003] negligible | −0.0000 [−0.0001, +0.0001] negligible |
| Smax_mean (1.0) | −0.0155 [−0.0207, −0.0105] detected, below δ | +0.0503 [+0.0437, +0.0570] detected, below δ | +0.0050 [+0.0028, +0.0075] detected, below δ |
| Lmax_mean (0.25) | −0.0075 [−0.0108, −0.0043] detected, below δ | +0.0203 [+0.0160, +0.0248] detected, below δ | +0.0015 [+0.0003, +0.0030] detected, below δ |
| CF (0.05) | +0.0231 [+0.0193, +0.0269] detected, below δ | **−0.0539 [−0.0589, −0.0489] detected, straddles δ** | −0.0044 [−0.0057, −0.0032] detected, below δ |

## Broker analysis (§7), confirmatory scope
| | Estimate [95% CI] | Label (δ 0.05) |
|---|---|---|
| Broker share M1 − M0 | −0.0015 [−0.0028, −0.0003] | detected, below δ |
| Broker share M2 − M1 | +0.0002 [+0.0000, +0.0005] | negligible |

The mean broker share (students with $p_i\le0.05$) is **0.0143 (M0), 0.0128 (M1), 0.0130 (M2)**, all below the nominal 0.05 expected by chance under the null. Observed brokerage never exceeds what the degree-preserving null produces. **No emergent brokers.**

## Validity check (§4, §6)
Spearman ρ between condition means of dGK_last and dHK_late across 36 conditions = **0.587 < 0.8, so by the locked rule $\Delta^{last}_{GK}$ is not an adequate proxy.** This is reported as a warning about the proxy, not a failure of E1. Context: both measures are close to zero in every condition (dHK_late 0.0014–0.0021, dGK_last 0.0005–0.0014, against δ of 0.01 and 0.02), so the check had almost no between-condition signal to track. The warning stands, but E1 can't show whether the proxy would track real decoupling.

## Secondary contrasts (§5): 72 contrasts × 13 outcomes
Of all 977 contrast rows, 415 are "detected" and **38 reach or cross δ. All 38 are the multi-hop effect ($R3-R1$):** copy success above δ in all 18 stage × family cells (plus P2), and route concentration straddling δ in all 18 (plus P2). **No stage contrast and no topology contrast reaches δ anywhere.** Full table: `runs/E1/derived/contrasts.parquet`.

## Condition means (descriptive), SBM
| Condition | pC_late | succ_late | K_final | dHK_late | dGK_last | Smax_mean | Lmax_mean | CF |
|---|---|---|---|---|---|---|---|---|
| M0/R1 | 0.1005 | 0.9026 | 0.8328 | 0.0014 | 0.0006 | 2.072 | 0.955 | 0.827 |
| M0/R3 | 0.1005 | 0.9997 | 0.8330 | 0.0016 | 0.0007 | 2.126 | 0.977 | 0.773 |
| M1/R1 | 0.0939 | 0.9128 | 0.8334 | 0.0015 | 0.0006 | 2.060 | 0.949 | 0.850 |
| M1/R3 | 0.0943 | 1.0000 | 0.8335 | 0.0016 | 0.0006 | 2.111 | 0.969 | 0.796 |
| M2/R3 | 0.0952 | 1.0000 | 0.8334 | 0.0016 | 0.0006 | 2.116 | 0.971 | 0.792 |
| M3/R3 | 0.0889 | 1.0000 | 0.8339 | 0.0015 | 0.0007 | 2.100 | 0.965 | 0.809 |
| M4/R3 | 0.0887 | 1.0000 | 0.8339 | 0.0015 | 0.0007 | 2.098 | 0.964 | 0.810 |
| M5/R3 | 0.0886 | 1.0000 | 0.8357 | 0.0016 | 0.0006 | 2.098 | 0.964 | 0.810 |

## Answers to the preregistered questions
Under these mechanisms and network conditions, at the reference parameters:
1. **Personal reinforcement (M1 − M0)** did **not** make copying expand. It slightly *reduced* copying (−0.6 percentage points), with every effect below δ.
2. **Peer exposure (M2 − M1)** added practically nothing: every outcome was negligible or below δ.
3. **Confidence → strategy (M3 − M2)** slightly reduced copying (−0.6 points). **Exam → confidence (M4)** and **exam → effort (M5)** changed only knowledge, slightly (M5: +0.0017). All below δ.
4. **Multi-hop routing (R3 − R1)** is the only mechanism with effects at or above δ: copy success rose from about 0.91 to about 1.00 (+0.087), and flow spread over more edges (CF −0.054). Cascades grew only below δ (largest cascade about 2.1 students, depth about 1).
5. **Topology (SBM, WS vs ER)** had no effect reaching δ.
6. **Proxy validity:** ρ = 0.59, not adequate by the locked rule, in a setting with almost no decoupling to detect.

**Overall: at the reference parameters, V1 produced none of the phenomena of blueprint §1.** Copying stayed at about the seeded 10%. There were no meaningful cascades, no brokers beyond the topological null, no persistent routes beyond what M0 produces, and no grade–knowledge decoupling. This is an informative null outcome in the sense of §49.

## Post hoc observations (exploratory, not tested)
These are hypotheses for Vavan's review, not findings.
- **Why copying didn't expand:** $Q^C$ is updated only when C is chosen (about 10% of the time), while $Q^S$ and $Q^D$ are updated often and rise as learning raises honest grades. The honest options' values may keep pace with or outgrow copying's, despite copying's cost advantage.
- **Why there's no decoupling:** students are homogeneous ($K_0$ and $\alpha$ identical), so a copied answer comes from a source whose knowledge is close to the copier's own. Copying at about 10% with $\chi_C=0.1$ opens only a small gap.
- **Blueprint §45:** at the reference parameters, "Q-reinforcement adds nothing beyond fixed random behavior" and "network topology has no measurable effect" both hold (effects below δ). Under §45 that points to model reduction or revision, not adding variables. What to do next is Vavan's decision.
