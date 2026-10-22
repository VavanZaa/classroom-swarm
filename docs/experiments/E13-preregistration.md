---
type: experiment
status: locked
updated: 2026-09-25
tags:
  - experiment
---
# E13 · A26 corrected controls and identified contrasts

**Locked 2026-09-25, before any E13 outcome was observed.** Status: **exploratory**. This is a re-run of the A25 questions under repaired controls and an identified design; it is not a confirmatory test of a pre-existing hypothesis, and it calibrates nothing.

Motivated by the read-only audit in [[docs/experiments/V4-audit-2026-09-25]]. The amendment is [[docs/15-v4-corrected-controls]]. A22–A25 sources, locks and results are untouched and remain historical records.

## Design

Master seed **924401**, bootstrap seed **924402**, 2,000 paired whole-classroom resamples, pointwise 95% intervals. **100 paired classrooms × 44 conditions = 4,400 runs.** `N=30`, `H=20` (40 in the `H40` arms), `T=12` ticks, `M_H=10`, `M_E=30`, exams every 5 homeworks. One graph per replicate per family, reused by every condition in that replicate; common random numbers throughout, so every contrast is paired on the same graph, the same traits and the same semantic draws.

Reference topology SBM, with ER arms for no AI, answer AI and tutor AI. Every parameter is an assumption from a chosen trajectory. No student data exists for this model.

## The contrast ladder

E12's single step from `motivation_only` to `public_no_ai` moved five parameters together and could not attribute its effect. E13 replaces it with one parameter per rung, each rung a primary contrast against the rung below:

| Rung | What it adds |
|---|---|
| `legacy` | A24-like baseline: legacy routing, intrinsic learning bonus, waiting bonus |
| `drop_learning_bonus` | removes the intrinsic learning reward only |
| `drop_wait_bonus` | removes the waiting bonus only |
| `motivation_only` | removes both: grade-and-effort motivation |
| `acquaintances` | weak non-friend contacts and closeness spread |
| `plus_grade_filter` | strictly-higher-grade eligibility for answer sources |
| `plus_grade_weighting` | grade weighting in source selection |
| `public_no_ai` | blending the eligible pool's public grades into the perceived value of copying |

The ladder is additive by construction. It identifies which rung moved an outcome; it does not estimate interactions between rungs and does not claim the effects sum.

**Primary contrasts (12), fixed here:** the seven ladder rungs; `answer_ai − public_no_ai`; `tutor_ai − public_no_ai`; `tutor_ai − answer_ai`; `tutor_ai0 − tutor_ai`; and `tutor_ai0_uncredited − tutor_ai0`. Thirty secondary contrasts cover AI capability, copying pressure, source rules, the confidence weight, the benefit prior, the hint deadline guard, effort aversion, course length, topology and exam feedback. All are listed in `lock.json` and in `e13.py`; all are reported whatever they show.

`tutor_ai0` is the null-tutor control that A25 could not provide, because A25 credited the tutor only when its hint strength was positive. `tutor_ai0_uncredited` reproduces that defect deliberately, so its size is measured rather than asserted.

## Stated identities — reported, never claimed as findings

These follow from the encoded rules. Their **sign is not evidence about anything**; only their magnitude, and the behaviour around them, is informative.

1. Answer AI emits packets at `ai_accuracy` and grants no knowledge; grades come only from packet bits and knowledge only from attempts. **Any positive uptake must raise homework grades and widen the homework–exam gap.** The scientific content of the AI arms is uptake, substitution away from attempts, and peer propagation of AI answers — not the gap.
2. `grade_response * grade_shortfall` is added directly to the answer and AI-answer scores, so `no_pressure` must show less copying.
3. `B` moves toward an observed grade at receipt, so an above-expectation grade must raise the credited action's benefit.

The results document must carry these three statements before any number derived from them.

## Smallest effect of interest and how intervals are read

δ = **1.0 point** on the 0–100 scale for mean homework, exam and knowledge outcomes, and **2 percentage points** for route and uptake shares. Boundary reading, as in E4 onwards: an interval lying entirely inside ±δ is reported as a pre-stated null; an interval excluding both +δ and −δ is reported as an effect exceeding the smallest effect of interest; anything else is reported as inconclusive at this replicate count. Intervals are pointwise and not multiplicity-adjusted across 92 metrics × 42 contrasts; the 30 students inside a classroom are not independent replicates.

## Subgroups

Contrasted subgroups are the top and bottom thirds of each classroom by the **exogenous learning trait α**, drawn before any behaviour and identical across every condition of a replicate. Behavioural early-attempt thirds are computed **inside each condition**, reported under a `desc_` prefix, and **excluded from the paired-effect table in code** — a group defined by one arm's realised behaviour cannot be differenced against another arm without importing that arm's noise. E10 and E11 took their labels from one arm of the contrast; this experiment does not.

## Audit requirements

Every raw table is written to Parquet, hashed and re-verified at analysis. Every student's knowledge change must reconstruct from `attempt` and `help_hint` event gains within 1e-12. `legacy`, `public_no_ai`, `answer_ai`, `tutor_ai` and `tutor_ai0` are independently re-simulated at analysis time and must reproduce every raw table exactly. `validate_corrected_log` additionally requires: universal grade delivery at h+1 with no within-homework leak and no knowledge change; strict higher-grade eligibility where `peer_rule='higher'`; no checking action; AI use only from homework 2 and at most once per student per homework; no knowledge on AI receipt; **no peer hint received with fewer than three ticks remaining while the guard is on**; and **every AI-tutored attempt credited to the tutor when `tutor_credit_by_source` is set**. A regression test forbids any benefit channel that is written and never read — the defect A22 carried in `B_check`.

Under its legacy flags the A26 engine must reproduce A25 on every shared raw table; this is tested across two seeds, three AI modes and both motivation settings, and the score dictionaries are compared over 1,200 random states.

## What would count against the A25 story

- The ladder attributing most of the `public_no_ai − motivation_only` movement to the contact set or the eligibility filter rather than to public grade information.
- `tutor_ai0 − tutor_ai` showing no difference, which would mean tutor uptake is insensitive to whether the tutor helps.
- `confidence0_*` or `prior25/75_*` moving the AI contrasts by more than δ, which would make the AI conclusions an artefact of the score-blending or the K₀-anchored prior rather than of grade-and-effort motivation.
- `hint_guard_off_no_ai` differing from `public_no_ai`, which would mean E9's "limited hint uptake" was partly an arrival-timing artefact.

## Deviations

Numbered, dated and recorded in `docs/experiments/E13-deviations.md` if any occur. `lock.json` is never replaced; a corrected study gets a new run identifier. Locked sources are never edited to improve an outcome.
