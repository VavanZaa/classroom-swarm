# V4.1/V4.2 results: adaptation without a learning breakthrough

> **Interpretation correction:** the user subsequently clarified that checking means universal receipt of the previous homework grade, and that poor grades increase interest in cheating. This E9 report concerns the earlier, mistaken optional-checking interpretation. Its locked data are preserved; use A24 / E11 for the corrected intended model.

24 September 2026 · E9r1 · 2,600 simulations · 26 conditions · 100 paired classrooms per condition

**Implemented and tested. Students now change activities during homework, share limited time, and respond to delayed assessments. The clearest result is behavioral substitution: less answer copying and better self-assessment do not automatically produce more knowledge.** No large withdrawal cascade, tipping point or new universal law was established.

## What was implemented

V4.1 permits attempts, requests for explanations or answers, checking, waiting and submission. Human help requires consent and time; a delivered explanation does not automatically generate learning. V4.2 adds private self-assessment and delayed exam feedback, with recalibration-only, constructive and withdrawal-capable response rules. The graph stays fixed. There are no assigned cheater/helper types, AI agents, forgetting or changing friendships in this experiment.

V1–V3 and E8 engines were preserved. The historical V3 path is tested for exact delegation. **245 tests pass**, including timing, non-overlap, packet identity, local information, feedback delays and raw-log reconstruction. All 2,600 final runs passed integrity checks. Analysis rehashed **2,200 raw/manifest files**, and an independent scientific rerun reproduced every raw table exactly.

An initial run found a one-ULP roundoff error in inactive knowledge. It was corrected without changing parameters, and every condition was rerun under a new source lock. The first logs remain at runs/E9; results here use runs/E9r1 only. The deviation is documented.

## Main results

| Model | Final knowledge /100 | Final unaided exam /100 | Late homework /100 | Answer-backed submissions | Self-assessment error /100 |
|---|---:|---:|---:|---:|---:|
| V3 historical reference | 74.52 | 74.58 | 82.65 | 38.87% | not applicable |
| V4.1: activities/time | 76.66 | 76.59 | 77.09 | 13.19% | 25.15 |
| V4.2: self-assessment only | 76.69 | 76.61 | 77.24 | 10.41% | 5.15 |
| V4.2: exam recalibration | 76.66 | 76.57 | 77.18 | 9.91% | 4.29 |
| Constructive exam response | 76.70 | 76.60 | 77.24 | 9.78% | 4.29 |
| Withdrawal-capable response | 76.69 | 76.60 | 77.19 | 9.87% | 4.31 |


Knowledge is a latent probability scaled to 100, not an observed percentage of students who mastered a curriculum. Late means the final five homeworks. Answer-backed means the final submitted packet came from answer transfer, even if the student also attempted or checked. It is not the fraction of students assigned a copying identity. Self-assessment error is mean absolute C minus K, using the absolute value for each student. V3's confidence variable has a different meaning, so its error is not compared.

The V3 row is a descriptive reference, not an isolated causal estimate: V4 changes the activity menu, time structure and learning opportunities together. V3's larger grade–exam gap cannot be credited to one V4 mechanism.

![Trajectories of knowledge, behavior and self-assessment](../../runs/E9r1/derived/v4-trajectories.png)

### 1. Behavior reorganized while knowledge stayed almost unchanged

V4.1 to V4.2 recalibration reduced answer-backed submissions from 13.19% to 9.91%. The paired difference was -3.280 points [95% CI -3.820, -2.740]. Final knowledge changed by +0.002 points [95% CI -0.039, +0.043].

Raw-event decomposition explains the cancellation. Compared with V4.1, V4.2 gained approximately 0.28 additional knowledge points through attempts, lost 0.26 points of checking-related learning, and lost 0.03 points of learning while explaining to others. The net difference was approximately zero. Students reallocated activity; they did not simply add more learning when they copied less.

The large improvement in calibration is partly expected by construction: V4.1 freezes self-assessment at its initial value. The more informative exam-only comparison is recalibration versus self-assessment without exam feedback: calibration error changed by -0.860 points [95% CI -0.954, -0.763], copying by -0.507 points [95% CI -0.787, -0.213], and knowledge by -0.035 points [95% CI -0.060, -0.009].

At 40 homeworks, V4.2 still copied less than its matched V4.1 control, but had -0.484 points [95% CI -0.524, -0.445] less knowledge. The decomposition again shows extra attempt learning offset by less checking and explaining. This is a small model-dependent tradeoff, not evidence that real assessment feedback harms learning.

### 2. Receiving help did not ensure using it

Only **37.4%** of delivered hints were consumed in a subsequent completed guided attempt before the homework ended (classroom-mean 95% CI 35.3–39.4%). Some students instead checked or submitted existing work, waited, sought other help, or ran out of time. This result comes from an explicitly exploratory analysis of actual receipt and attempt events; it is not inferred merely from requesting a hint.

Removing explanation requests increased answer-backed submissions by +1.293 points [95% CI +0.847, +1.773], but changed final knowledge by only +0.033 points [95% CI -0.005, +0.071]. More independent attempts and checking offset the missing explanation activity under these rules.

This **help-utilization bottleneck** is a useful new pattern expressed by V4: delivery, engagement and learning are different events. Its magnitude is sensitive to the model's scheduling and one-shot activity choices. It does not show that real peer explanation is ineffective.

### 3. Help was concentrated, but stable helper identities were weak

In the recalibration condition, the most-used 20% of students supplied 48.39% of successful late help. Yet degree-adjusted early/late helper persistence was only 0.119 (95% CI 0.079–0.158).

Freezing access beliefs reduced this persistence by -0.057, while barely changing copying or knowledge. Thus private experience modestly stabilizes helper activity in this model, without determining the class-wide copying rate.

These are descriptive helper statistics, not the stricter V3 root-source test. Unequal traffic can arise from finite event counts and unequal opportunities; this experiment does not establish strong source identities independent of all traits and opportunities. “Temporary concentration” is more defensible than “permanent brokers emerged.”

![Help success, concentration and descriptive persistence](../../runs/E9r1/derived/v4-help-network.png)

### 4. Time and checking dominated the tested knowledge changes

Relative to recalibration, the short deadline changed final knowledge by -3.464 points [95% CI -3.513, -3.419]; the long deadline changed it by +2.465 points [95% CI +2.419, +2.508]. Short deadlines also sharply reduced explanation requests. They did not produce more copied submissions here: less time restricts opportunities to obtain help as well as opportunities to practice.

Removing checking changed knowledge by -2.062 points [95% CI -2.137, -1.984], even though students attempted more. This is partly a direct consequence of the model: checking provides reliable correctness information and an explicit practice increment. The emergent part is the compensating activity allocation, which did not fully replace that loss. This condition removes checking information, time use and practice together; it cannot isolate their individual contributions.

Removing the helper's time cost increased knowledge by only +0.262 points [95% CI +0.233, +0.291]. Limited time matters, but the tested helper burden did not generate a major congestion crisis. The control is deliberately unrealistic: helpers can work and help concurrently.

![Paired counterfactual effects](../../runs/E9r1/derived/v4-counterfactuals.png)

### 5. The withdrawal-capable rule did not generate a withdrawal regime

About 67.3% of released assessments in that condition exceeded students' prior predictions. Average controllability rose from 0.50 to 0.547. Most students were underconfident as competence improved, so the same rule that permits discouragement also permitted recovery.

Constructive and withdrawal-capable responses changed final knowledge by only +0.043 points [95% CI +0.031, +0.054] and +0.037 points [95% CI +0.024, +0.050], respectively. We should not tune these coefficients until a dramatic collapse appears. These scenarios simply did not create the repeated unexpected failures needed for that aggregate pattern.

## How strong are the findings?

The five preregistered primary contrasts were assessed on five primary outcomes. All 25 pointwise intervals remained within their declared practical-effect boundaries: 1 point of knowledge, 3 points for exam/behavior and 2 points for calibration. This means the primary design found **small effects**, even where a pointwise interval excluded zero. Larger changes came from additional sensitivity conditions, particularly deadline and checking changes.

Initial benefit expectations remain important: answer-backed submissions ranged from 4.49% with a .25 prior to 18.75% with a .75 prior. Argmax choice produced 5.16% versus 9.91% with the baseline stochastic rule. There is no single empirically established copying forecast.

V4.2's late mixed-activity share was 82.69%. This verifies that the new activity system is being used; the mere ability to mix activities was designed in and is not itself a discovery. Incompletion was almost absent, which also limits conclusions about disengagement or deadline failure. Availability of dynamic rules does not guarantee meaningful stress or instability.

## What emergence can be claimed?

The best-supported new system-level observation is **compensation between learning activities**: changes in answer use and self-assessment can be absorbed by changes in attempts, checking and helping, leaving overall competence nearly unchanged. The raw-event decomposition verifies the cancellation.

A second useful observation is **delivered help without follow-through**. Making explanation available is insufficient when participation competes with other activities and time. A third is **concentrated but weakly persistent help traffic**, with modest stabilization from private source learning.

These are conditional patterns within this new model, not claims of uniqueness across the scientific literature. We found no evidence establishing bistability, hysteresis, phase transitions, large withdrawal cascades or strong permanent broker roles. No numerical outcome is calibrated to a real school.

## Assumptions that most limit interpretation

- Fixed standard-difficulty items, one latent skill, monotone learning and no forgetting. There is no demanding new-topic shock to generate persistent setbacks.
- Checking reveals the actual packet grade using an assumed reliable rubric and also grants practice. Real self-checking may be fallible; this assumption deserves its own future experiment.
- Initial self-assessment equals initial latent knowledge, then V4.1 holds it fixed. Much of the V4.1 calibration gap is a designed benchmark effect.
- Choices are short-horizon scores; explanations are numerical scaffolds, not simulated dialogue. Grade benefits use coarse episode-level credit assignment.
- Removing an action changes both opportunities and the feasible choice set. Those contrasts do not identify a single psychological cause.
- Most deadlines still allow at least one packet, and automatic deadline submission makes noncompletion uncommon.
- Feedback response rules are hypotheses. Their immediate direction is encoded; their aggregate magnitude and interactions are the outcomes.
- Pointwise 95% intervals describe Monte Carlo uncertainty across independent classrooms, not real-student uncertainty or familywise-confirmed discoveries. Supplemental gain decomposition and hint uptake were exploratory after primary outcome inspection.

## Full condition table

| Condition | Final knowledge /100 | Unaided exam /100 | Answer-backed % | Incomplete % |
|---|---:|---:|---:|---:|
| v3_reference | 74.52 | 74.58 | 38.87 | 0.000 |
| v41 | 76.66 | 76.59 | 13.19 | 0.013 |
| v42_no_feedback | 76.69 | 76.61 | 10.41 | 0.007 |
| v42_recalibrate | 76.66 | 76.57 | 9.91 | 0.000 |
| constructive | 76.70 | 76.60 | 9.78 | 0.000 |
| withdrawal | 76.69 | 76.60 | 9.87 | 0.000 |
| delay0 | 76.65 | 76.56 | 9.84 | 0.007 |
| delay4 | 76.68 | 76.59 | 10.31 | 0.007 |
| helper_time_free | 76.92 | 76.83 | 9.94 | 0.000 |
| frozen_access | 76.67 | 76.60 | 10.07 | 0.000 |
| no_hint | 76.69 | 76.66 | 11.20 | 0.000 |
| no_answer | 77.28 | 77.18 | 0.00 | 0.000 |
| no_check | 74.60 | 74.50 | 10.37 | 0.000 |
| misattribute0 | 76.66 | 76.59 | 9.91 | 0.000 |
| misattribute80 | 76.67 | 76.60 | 9.81 | 0.000 |
| prior25 | 76.11 | 76.03 | 4.49 | 0.000 |
| prior75 | 76.85 | 76.77 | 18.75 | 0.000 |
| learning_value0 | 75.50 | 75.41 | 12.20 | 0.000 |
| deadline8 | 73.19 | 73.04 | 9.28 | 0.040 |
| deadline16 | 79.12 | 79.13 | 9.09 | 0.000 |
| argmax_v41 | 76.48 | 76.36 | 5.99 | 0.000 |
| argmax_v42 | 77.35 | 77.23 | 5.16 | 0.000 |
| ER_v41 | 76.63 | 76.51 | 13.26 | 0.013 |
| ER_v42 | 76.60 | 76.52 | 9.97 | 0.007 |
| H40_v41 | 88.94 | 89.01 | 11.91 | 0.007 |
| H40_v42 | 88.46 | 88.61 | 6.81 | 0.000 |


## Data and reproduction

- [Classroom results](../../runs/E9r1/derived/classroom_results.csv): one row per simulation, all available outcomes.
- [Trajectories](../../runs/E9r1/derived/classroom_trajectories.csv): one row per simulation/homework.
- [Condition estimates](../../runs/E9r1/derived/condition_estimates.csv): means, SDs, estimable classroom counts and intervals.
- [Paired effects](../../runs/E9r1/derived/paired_effects.csv): matched classroom differences, including null results.
- [Exploratory mechanism data](../../runs/E9r1/derived/mechanism_classrooms.csv): learning decomposition and actual hint consumption.
- [Analysis metadata](../../runs/E9r1/derived/analysis.json) and [mechanism checks](../../runs/E9r1/derived/mechanism_checks.json).
- [Source and reproducibility bundle](../../runs/E9r1/derived/V4-source-and-reproducibility.zip): implementation, tests, specification, preregistration, deviation record and source lock.

Complete raw logs remain in `D:\3D Project\AI Student classroom Socio graph multiagent simulation\runs\E9r1` (approximately 816.5 MiB before adding derived outputs). The delivered tables are derived from these logs. The raw dataset is not duplicated inside the source bundle. [Dataset location and integrity manifest](../../runs/E9r1/derived/dataset_manifest.json) records its location and hashes.

Within the project environment, reproduce analysis with `python -m classroom_swarm.e9 analyze --root runs/E9r1 --output <directory>`. Re-running `run --root runs/E9r1` verifies completed shards; to conduct a new complete run, lock a new empty output directory first. Do not edit the locked model to improve the observed story.

The recommended next scientific step is to challenge the checking/learning and difficulty assumptions, not immediately add more psychological states. Keep this result as a transparent baseline, including its small effects and absent crises.
