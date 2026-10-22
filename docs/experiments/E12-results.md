# Motivation, public grades and AI: corrected V4 results

> **Audit erratum, 25 September 2026** ([[docs/experiments/V4-audit-2026-09-25|record]]). Four corrections. (a) The bolded headline below is an identity, not a finding: answer AI emits packets at `ai_accuracy` and grants no knowledge, while grades come only from packet bits and knowledge only from attempts, so any positive uptake *must* raise homework and widen the gap. The findings are the uptake, the substitution away from attempts and the peer propagation. (b) `tutor_ai0` is not a null-tutor control — `v4_public_ai.py` credits the tutor only when its hint strength is positive, so at strength 0 the action was invisible to credit assignment (0.5% of grade returns credited it, against 21.3% in `tutor_ai`) and students could not learn it was useless; that row should be read as "a useless tutor nobody can find out about". (c) `public_no_ai − motivation_only` moves five parameters at once and cannot attribute its effect; in particular `public_signal` biases the perceived value of copying upward by construction, because under the strictly-higher-grade rule the eligible pool always outscores the requester. (d) The early-attempt groups are labelled from `public_no_ai` and differenced against the other arms. Also, an ER graph is generated every replicate but used by no condition, so this study has no topology arm. The locked data stand. [[docs/experiments/E13-results|E13]] repairs the tutor credit, unpacks the bundle one parameter per rung — finding that `public_signal` accounts for essentially all of it — adds ER arms, and uses exogenous-trait subgroups.

24 September 2026 · A25 / E12r1 · 2,600 simulations · 26 conditions × 100 paired classrooms · 296 tests passing

**Students now seek high expected grades with low perceived effort. They do not see their true knowledge, current answer correctness or the AI's true effectiveness.** Homework grades become public after return, and source choice balances grades, relationship closeness and experienced availability. The corrected model includes no AI, answer-giving AI and tutoring AI.

## Main results: compare the same point in time

| Model | Final homework /100 | Same-time exam /100 | Homework–exam gap | True knowledge /100 |
|---|---:|---:|---:|---:|
| No AI | 71.73 | 69.09 | 2.64 | 69.25 |
| Answer AI | 86.38 | 59.01 | 27.37 | 59.24 |
| Tutor AI | 74.33 | 69.81 | 4.52 | 69.94 |

**Answer-giving AI creates a large separation between rewarded homework performance and unaided competence in this model.** Stronger effort avoidance makes the separation larger: answer-AI homework moves from 86.38 to 88.09, while the exam moves from 59.01 to 55.29. The student can improve the visible short-term outcome while reducing practice that would support later unaided work.

All headline homework and exam scores are measured at assignment 20. Previously, the E11 table put the average of homeworks 16–20 next to the final exam, which obscured the contemporaneous gap. Reconstructing assignment 20 in E11 gives homework 74.54 versus exam 73.47 with copying pressure. That comparison error and the missing public-grade/AI assumptions are separate issues.

![Matched grades and exams, knowledge trajectories, effort sensitivity and answer origins](../../runs/E12r1/derived/motivation-grades-ai.png)

Against the corrected no-AI case, answer AI changes final homework by +14.65 points (95% CI +13.40 to +15.94), the unaided exam by -10.08 points (95% CI -10.36 to -9.80), and the matched grade–exam gap by +24.73 points (95% CI +23.38 to +26.04). Tutor AI changes the exam by +0.72 points (95% CI +0.57 to +0.86). Tutor versus answer AI differs by +10.80 points (95% CI +10.53 to +11.08) on the unaided exam.

These are model counterfactuals under declared assumptions, not measured educational effects. Answer AI's default item accuracy is 90%; 80% and 100% cases are also reported. Tutor AI supplies a hint and requires a subsequent student attempt to produce learning or a new answer.

## Motivation: why easy grades can mislead

The central choice is expected grade improvement minus personally weighted effort cost, with the previously requested bad-grade pressure bias toward shortcuts. The main cases remove the old intrinsic learning reward and positive waiting bonus. Choosing to study must be supported by expected grades, uncertainty and experience; the policy receives no reward for secretly increasing the researcher's K variable.

Students differ in effort aversion. A three-tick attempt costs more effort than a one-tick AI answer. A tutor consultation takes two ticks and needs a further three-tick attempt; a peer request also faces delays, refusal and source availability. Preferences are probabilistic rather than perfect foresight. A student may conclude that copying works because a returned homework grade rewards it, while remaining unable to solve an unaided exam. No direct laziness penalty is applied to knowledge.

At effort settings 0, .15 and .5, answer-AI exam means are 61.12, 59.01 and 55.29. Corresponding no-AI means are 70.19, 69.09 and 66.75; tutor means are 70.96, 69.81 and 67.54. These values test effort preference within the model rather than labeling real students as lazy.

True AI accuracy and tutor strength are used only to generate outcomes. They cannot enter student choice scores. Students estimate AI value from private grade history. They see neither item correctness nor their latent knowledge while working. Grades arrive to everyone before the next homework, without using study time or adding competence. Separately delayed unaided exams update confidence.

## Public grades and relationship closeness

In the main rule, a peer source must have a strictly higher previous homework grade. A close, moderately higher-scoring classmate can be preferred over a distant top scorer. Equal scores are ineligible, and no peer copying is available before the first homework grades return. A relaxed control allows familiar sources below one's own grade as well. This exposes the ambiguity in "lower-scoring source" instead of silently conflating a lower-ranked alternative with a source below the requester.

All classmates' returned grades are visible. Friendship ties have stronger frozen contact weights; other classmates have weaker acquaintance weights. Source selection combines closeness, known grade and privately experienced availability. Closeness weights never change and the friendship graph is never rewired. A friends-only control removes weak acquaintance contacts, while a score-only control removes the closeness preference.

Known grades are evidence about performance, not direct access to competence. In the no-AI case, 32.43% of requests to a higher-graded source target someone whose current latent knowledge is no higher than the requester's. With answer AI, the corresponding proportion is 46.01%. These are classroom-averaged request-level diagnostics from hidden researcher state; students never observe that comparison. Sampling noise and previous assistance can make a higher grade an imperfect competence signal.

The motivation-only condition changes the decision objective while keeping old source selection. Public no-AI then changes the source-information/contact rules. This separates the change in motivation from the combined public-grade and relationship mechanism. The latter comparison does not separately identify every contribution of grade weighting, acquaintances and source filtering.

## AI use, practice and answer propagation

Over 20 homeworks, completed attempts average 24.73 per student without AI, 9.27 with answer AI and 24.04 with tutor AI. Students make 15.40 direct answer-AI consultations or 7.99 tutor consultations in the corresponding cases. Access begins at homework 2 and is voluntary, with at most one consultation per student per homework.

In the answer-AI condition, 51.32% of late submissions use a directly obtained AI answer; another 32.20% use an AI answer passed through a peer. Total peer-copied submissions are 37.28%. Thus direct AI uptake and AI-origin answer spread are different outcomes. Original AI item bits and packet identity are preserved through peer transfers.

In the tutor condition, 83.41% of received AI hints are consumed in a subsequent own attempt. Merely asking the tutor teaches nothing automatically. The resulting attempt applies the declared guidance rule; no free answer is supplied. A hint may be unused or replaced by later help.

Final within-class knowledge P90–P10 gaps are 21.80, 24.72 and 21.07 points for no AI, answer AI and tutor AI. These distributions should be distinguished from a difference between model-wide averages or a causal effect of an observed student's behavior.

One revealing sensitivity is near-perfect answer AI. At 100% item accuracy, late peer copying is only 6.45%, while direct AI answers account for 83.41% of submissions. Final homework is 97.00 and the unaided exam is 58.52. Looking only for copying between classmates would therefore miss much of the answer dependence. Strong AI rewards and the strict higher-grade rule's exclusion of tied sources both exist in this condition; this experiment does not separately identify their contributions to the shift.

## What exam feedback does and does not teach

Without exam feedback in the answer-AI condition, the final exam mean is 58.97, versus 59.01 with feedback. The paired change when removing feedback is -0.04 points (95% CI -0.15 to +0.08). Both conditions still take the same unaided exams for measurement and receive homework grades.

That interval includes zero: confidence feedback alone does not produce a clear exam-performance improvement here. Nor is the result simply persistent overconfidence: the answer-AI condition's late mean confidence bias is +0.43 points, with mean absolute error 4.14. Students can have roughly calibrated estimates of their ability and still choose the method that cheaply earns homework grades.

The current learner is short-sighted: exam feedback adjusts confidence, but does not assign a causal learning cost to each earlier strategy or explicitly optimize future exam grades. Therefore, continued shortcut use after poor exams is conditional on this credit-assignment limitation. It must not be claimed as proof that real students cannot recognize or correct a mistake. A model of learning which study strategy improves exams would be a distinct extension.

## All sensitivity conditions

| Condition | Final homework | Same-time exam | Gap | Late peer-copy % | Late direct-AI % | Knowledge P90–P10 |
|---|---:|---:|---:|---:|---:|---:|
| legacy | 74.98 | 73.24 | 1.75 | 18.67 | 0.00 | 18.08 |
| motivation_only | 72.78 | 70.75 | 2.03 | 25.41 | 0.00 | 20.16 |
| public_no_ai | 71.73 | 69.09 | 2.64 | 39.33 | 0.00 | 21.80 |
| answer_ai | 86.38 | 59.01 | 27.37 | 37.28 | 51.32 | 24.72 |
| tutor_ai | 74.33 | 69.81 | 4.52 | 39.49 | 0.00 | 21.07 |
| answer_ai80 | 76.42 | 59.83 | 16.59 | 44.21 | 40.33 | 25.63 |
| answer_ai100 | 97.00 | 58.52 | 38.48 | 6.45 | 83.41 | 24.37 |
| tutor_ai0 | 71.11 | 68.51 | 2.60 | 40.86 | 0.00 | 22.24 |
| tutor_ai50 | 77.43 | 70.94 | 6.49 | 38.67 | 0.00 | 20.43 |
| no_pressure | 72.75 | 70.87 | 1.88 | 30.67 | 0.00 | 19.35 |
| answer_no_pressure | 86.09 | 59.88 | 26.21 | 33.63 | 54.69 | 24.50 |
| tutor_no_pressure | 74.91 | 71.29 | 3.62 | 31.28 | 0.00 | 18.94 |
| public_relaxed | 72.11 | 69.50 | 2.61 | 35.75 | 0.00 | 21.85 |
| answer_relaxed | 85.63 | 58.73 | 26.90 | 50.84 | 40.61 | 24.55 |
| score_only | 72.32 | 69.02 | 3.30 | 39.85 | 0.00 | 22.07 |
| friends_only | 73.21 | 70.63 | 2.57 | 26.33 | 0.00 | 20.84 |
| H40_no_ai | 83.85 | 81.50 | 2.36 | 30.41 | 0.00 | 18.16 |
| H40_answer | 87.36 | 63.11 | 24.25 | 32.13 | 58.29 | 27.23 |
| H40_tutor | 85.33 | 82.02 | 3.30 | 30.60 | 0.00 | 17.43 |
| effort0_no_ai | 73.11 | 70.19 | 2.92 | 36.75 | 0.00 | 21.35 |
| effort0_answer | 84.94 | 61.12 | 23.82 | 39.89 | 44.15 | 24.39 |
| effort0_tutor | 75.40 | 70.96 | 4.44 | 37.60 | 0.00 | 20.23 |
| effort50_no_ai | 69.91 | 66.75 | 3.17 | 39.33 | 0.00 | 22.60 |
| effort50_answer | 88.09 | 55.29 | 32.80 | 25.23 | 69.43 | 24.10 |
| effort50_tutor | 71.39 | 67.54 | 3.84 | 38.47 | 0.00 | 22.04 |
| answer_no_exam_feedback | 86.51 | 58.97 | 27.54 | 37.62 | 51.73 | 24.36 |

Condition names encode the changes: `80/100` are answer accuracy percentages; tutor `0/50` are hint strengths; `no_pressure` removes the extra bad-grade copying incentive; `relaxed` allows lower-scoring peer sources; `effort0/50` changes effort aversion; `H40` doubles the course length. All conditions were specified before scientific outcomes were inspected. No preferred rate was selected because it widened the gap.

## Interpretation, validation and reproducibility

The encoded mechanisms are effort costs, grade-based reinforcement, public source information, copying pressure, AI capabilities and activity-specific learning. Emergent outcomes are the activity mix, voluntary uptake, shared answer provenance, confidence trajectories and resulting grade–knowledge separation under those mechanisms. A larger gap alone is not evidence of a new scientific phenomenon or accurate real-world magnitude.

Knowledge is a single monotone scalar; rates originate in chosen trajectories, not student-data calibration. Initial traits, social weights, target grade, AI quality and behavioral coefficients are assumptions. AI errors are independent item draws here; sanctions, plagiarism detection, correlated misconceptions, forgetting and multiple concepts are omitted. Confidence intervals resample 100 whole paired classrooms 2,000 times and are pointwise, not multiplicity-adjusted. The 30 students within a classroom are not independent experimental replicates.

All 296 tests pass. Universal delayed grades, higher-source eligibility, closeness tradeoffs, no hidden AI-quality access, time accounting, copied-packet identity, AI availability for isolates, no AI before introduction, no direct learning on AI receipt and legacy core parity were checked. Every student's event gains reconstruct knowledge change within 1e-12. All 1300 raw files were hash-verified. Independent reruns of no AI, answer AI and tutor AI reproduced every raw table.

The initial E12 run failed on an AI-log storage schema mismatch. The correction changed the data writer, not the engine, parameters or outcomes. All original sources and partial files are preserved; the entire study was restarted as E12r1 before aggregate results were inspected. [Deviation record](../../runs/E12r1/derived/E12-deviations.md). Earlier E9r1, E10 and E11 locked sources are intact.

- [Classroom outcomes](../../runs/E12r1/derived/classroom_results.csv), [student outcomes](../../runs/E12r1/derived/student_results.csv) and [trajectories](../../runs/E12r1/derived/trajectories.csv).
- [Condition estimates](../../runs/E12r1/derived/condition_estimates.csv), [paired effects](../../runs/E12r1/derived/paired_effects.csv) and [analysis metadata](../../runs/E12r1/derived/analysis.json).
- [Raw data locations and integrity hashes](../../runs/E12r1/derived/dataset_manifest.json).
- [Analysis data bundle](../../runs/E12r1/derived/motivation-ai-data.zip) and [source, tests, specification and lock](../../runs/E12r1/derived/motivation-ai-source.zip).

Raw logs remain in the project at `runs/E12r1`. Reproduce the analysis with `python -m classroom_swarm.e12 analyze --root runs/E12r1 --output <directory>`. A new simulation requires a new empty directory, `lock`, then `run --workers 4`. Existing completed runs are verified, not silently overwritten.
