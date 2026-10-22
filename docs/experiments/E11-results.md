# Corrected model: previous-homework grades and cheating

> **Audit erratum, 25 September 2026** ([[docs/experiments/V4-audit-2026-09-25|record]]). The headline increase in copying is the encoded rule, not a discovery. `v4_grades.py` adds `grade_response * grade_shortfall` directly to the answer score, and the primary contrast is that coefficient against zero, so a rise in copying is entailed; only its magnitude is informative. The same applies to the audited `B_answer` movements after above- and below-target copied grades, which follow from the update rule. `docs/13` states this; this report's summary did not. Also, the early-attempt groups are labelled from the `reference` arm and then differenced against the other arms, so `group_gap_*` contrasts carry a regression-to-the-mean term. [[docs/experiments/E13-results|E13]] names such identities in its lock before the run and uses exogenous-trait subgroups.

> **Comparison and scope clarification:** the table below reports late homework averages (16–20) alongside the final exam, so those two columns are not a same-time grade gap. Reconstructing assignment 20 only gives 74.54 homework versus 73.47 exam in the copying-pressure condition (75.25 versus 74.72 without pressure). The user's further corrections—public grades, relationship-sensitive source choice, AI, and grade-versus-effort motivation—are implemented separately in A25/E12. E11 did not model those additions.

24 September 2026 · V4.2-G / A24 · E11 · 1,300 simulations · 100 paired classrooms × 13 conditions · 276 passing tests

**The user's intended rule is now implemented: every student receives the previous homework grade automatically. A bad grade increases interest in cheating; a good copied grade can reinforce copying. Receiving a grade is not studying and adds no knowledge.** The earlier E9/E10 optional-checking interpretation was mistaken. Those records are preserved, but their checking conclusions do not describe this corrected mechanism.

## The feedback loop

- Finish homework → grade returned to everyone before the next homework, without spending homework time.
- Below-target grade → pressure to obtain a better grade → greater attraction of requesting an answer to copy.
- Good copied grade → copying's expected grade benefit usually increases → copying can become attractive again.
- Copying replaces opportunities to attempt or explain → less learning → subsequent grades can disappoint again.
- A sufficiently good grade clears the immediate bad-grade pressure. Students may change approach; copying is never compulsory.

The provisional target is 75/100. Bad-grade pressure adds `response × max(.75 − previous_grade, 0)` only to the answer-request score, with response=.4 by default. Attempts and explanation requests receive no extra bad-grade bonus. Independent attempts, guided attempts and explaining to peers still produce knowledge. Grade receipt and copied answers produce none directly.

Action-benefit beliefs update from the returned grade of the submitted route. Copied final work credits the answer action; independent work credits attempting; a guided attempt splits credit between attempting and requesting an explanation. Confidence also responds, with reduced attribution for assisted work. Separately delayed unaided exams can recalibrate confidence. The signed grade-minus-target value is a satisfaction proxy, not a validated happiness measurement or an additional hidden reward.

## What happened

Both the reference and proposed model receive universal grades and learn from them. Their only primary difference is whether bad grades add copying pressure. Compared with the no-pressure reference:

- Late copied submissions increase from **11.45% to 17.73%**: +6.29 points (95% CI +5.71 to +6.85).
- Final knowledge falls from **74.63 to 73.41**: -1.22 points (95% CI -1.29 to -1.16).
- Late homework grades fall from **73.97 to 73.11**: -0.86 points (95% CI -1.11 to -0.59).
- The within-class final P90–P10 knowledge gap increases from **16.29 to 17.68**: +1.39 points (95% CI +1.07 to +1.72).

![Corrected grade feedback results](../../runs/E11/derived/grade-feedback.png)

The population-level result is an unintended consequence of grade-seeking: more copying does not improve average homework grades in these settings, and knowledge grows more slowly. This is consistent with a reinforcing dependency mechanism, but it is not proof of an irreversible trap, a real-world effect size or a scientifically unique phenomenon.

## Behavior and the two different reactions

Students make 14.21 answer requests across 20 homeworks, compared with 8.20 without bad-grade pressure. Completed attempts fall from 32.79 to 30.93; received explanations fall from 3.48 to 2.94. A request is not necessarily successful: peer availability, willingness and existing answers still constrain actual copying.

After a below-target grade, an answer request occurs on 54.56% of next homeworks; after an at/above-target grade, 33.60%. These are classroom-averaged conditional associations, affected by who receives each grade, rather than randomized comparisons between good and bad grades. The paired pressure-versus-no-pressure comparison above is the experimental contrast.

After an above-target copied grade, B_answer increases in 99.93% of feedback events, averaging the proportions within each classroom. This verifies the intended reward channel. However, only 20.87% of next homeworks after a good copied grade are also submitted as copies. Reinforcement does not create a permanent cheating type.

There are two standards of success: the grade target and the expected benefit of copying. Only 41.34% of below-target copied grades decrease B_answer. A grade can disappoint relative to 75/100 yet exceed a student's previously low expectation for copying, thereby reinforcing it. That distinction is explicitly encoded by the expectation update; the observed frequency depends on the evolving histories.

## Knowledge gaps and limits of the emergence claim

The overall student spread widens relative to the no-pressure reference. But early high- and low-attempt groups do not become more separated: their final gap decreases from 1.24 to 0.33 points. These groups are fixed using each reference classroom's first five homeworks; they are observational, tied ranks and initial traits can matter, and they are not assigned student types.

Both variants still narrow their initial knowledge spread of 24.14 points. There is no demonstrated permanent low-knowledge class or collapse. At 40 homeworks, knowledge is still increasing, and copying remains higher under pressure (13.15% versus 8.77%). The model permits improvement and switching.

The individual tendencies—bad grades increasing answer-request attraction and successful copied grades reinforcing expected benefit—are assumptions supplied by the user, not discoveries. Their joint classroom consequences, including lost practice, constrained delivery, lower average grades and differences in spread, are simulation outputs. A fuller causal decomposition of the feedback cycle would require additional interventions; these results establish the total effect of the declared copying-pressure rule.

## All conditions

| Condition | Knowledge /100 | Unaided exam /100 | Late homework /100 | Late copied work | K P90–P10 |
|---|---:|---:|---:|---:|---:|
| Grades + reinforcement; no copying pressure | 74.63 | 74.72 | 73.97 | 11.45% | 16.29 |
| Grades + reinforcement + copying pressure (.4) | 73.41 | 73.47 | 73.11 | 17.73% | 17.68 |
| Weaker copying pressure (.2) | 74.13 | 74.22 | 73.64 | 14.07% | 16.71 |
| Stronger copying pressure (.8) | 71.50 | 71.61 | 71.65 | 25.71% | 20.17 |
| No action-benefit reinforcement | 72.51 | 72.63 | 71.80 | 14.96% | 17.21 |
| Answer requests unavailable | 75.84 | 75.91 | 74.96 | 0.00% | 15.67 |
| Explanation requests unavailable | 72.90 | 73.05 | 72.27 | 21.43% | 18.26 |
| No assisted-grade self-assessment update | 73.42 | 73.51 | 73.13 | 18.13% | 17.64 |
| Stronger assisted-grade self-assessment update | 73.32 | 73.44 | 72.94 | 17.80% | 17.82 |
| 40 homeworks: no copying pressure | 86.50 | 86.51 | 86.29 | 8.77% | 12.32 |
| 40 homeworks: copying pressure | 85.57 | 85.55 | 85.60 | 13.15% | 13.80 |
| ER network: no copying pressure | 74.64 | 74.76 | 74.03 | 10.74% | 16.13 |
| ER network: copying pressure | 73.39 | 73.53 | 72.98 | 17.87% | 17.75 |

We report both weaker and stronger pressure without selecting a preferred rate to maximize the gap. All non-reference ablations compare with the proposed model; response-strength variants compare with the no-pressure reference, and H40/ER compare with their matched references. Removing action-benefit reinforcement affects every action, so it is not a pure test of the copying-reward channel alone.

## Timing, validation and reproducibility

All students receive one grade for every homework, including missing work. Homework h's grade arrives at h+1; the final homework is returned at a terminal boundary with no extra work. There is no same-homework grade leak, no optional checking event, no study-time charge for receiving a grade and no direct competence update. End-of-homework snapshots precede receipt of that homework's grade; final feedback is separately logged.

All 276 tests pass, including universal delivery, exact reinforcement equations, no first-homework effect, no checking, missing-work grades, local information, no overlapping time use, and no pressure effect when answer requests are unavailable. Every one of 1100 raw files was hash-verified. Every student's event gains reconstruct total knowledge change within 1e-12. Independent reruns of reference and pressure conditions match every raw table. The E9, E10 and E11 source locks remain intact.

This is a phenomenological experiment implementing the user's hypothesis, not an assertion that every real student cheats after a bad grade. The 75-point target and all reaction strengths are assumptions. Alpha comes from a chosen trajectory, not educational calibration. Confidence intervals use 2,000 resamples of 100 whole paired classrooms; they are pointwise, not multiplicity-adjusted. Rate/target sensitivity is not exhausted, and knowledge remains a single monotone scalar.

- [Classroom results](../../runs/E11/derived/classroom_results.csv), [student results](../../runs/E11/derived/student_results.csv) and [trajectories](../../runs/E11/derived/trajectories.csv).
- [Condition estimates](../../runs/E11/derived/condition_estimates.csv), [paired effects](../../runs/E11/derived/paired_effects.csv) and [analysis metadata](../../runs/E11/derived/analysis.json).
- [Raw dataset locations and hashes](../../runs/E11/derived/dataset_manifest.json).
- [Analysis data bundle](../../runs/E11/derived/grade-feedback-data.zip) and [source, tests and locked specification](../../runs/E11/derived/grade-feedback-source.zip).

Raw logs remain at the project's `runs/E11`. Reproduce the analysis with `python -m classroom_swarm.e11 analyze --root runs/E11 --output <directory>`. New simulations require a new empty directory and `lock` followed by `run --workers 4`; existing completed runs are verified rather than overwritten.
