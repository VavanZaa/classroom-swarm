# Learning activities and the knowledge gap

> **Audit erratum, 25 September 2026** ([[docs/experiments/V4-audit-2026-09-25|record]]). Two defects affect how this report should be read. (a) `B_check` is written on every homework by the benefit update but is read by no score in `v4.py`; because credit is normalised across activities, the inert channel absorbed 31.8% of the benefit-update mass in this reference run, so the beliefs that *do* drive choice moved about a third slower than they otherwise would — and at different rates across these conditions (19.09 checks in `reference`, 18.48 in `check0`, 0 in `no_check`). The `no_check` comparison below therefore mixes a belief-update-rate difference into what is described as time reallocation. (b) The early-attempt groups are labelled from the `reference` arm and then differenced against the other arms, so every `group_gap_*` contrast carries a regression-to-the-mean term; common random numbers keep it small here, but the near-zero group-gap change should not be read as a clean null. Separately, `align_check_value` is an experimenter-imposed belief revision: nothing in the model can learn that checking stopped teaching, so `check0` and `check0_unaligned` bracket "knows instantly" and "never finds out" with no learner in between. The locked data stand; a regression test now forbids write-only belief channels, and [[docs/experiments/E13-results|E13]] uses exogenous-trait subgroups.

> **Interpretation correction:** the user subsequently clarified that checking means universal receipt of the previous homework grade, and that poor grades increase interest in cheating. This E10 report concerns the earlier, mistaken optional-checking interpretation. Its locked data are preserved; use A24 / E11 for the corrected intended model.

24 September 2026 · V4.2-L / A23 · E10 · 1,000 simulations · 100 independent paired classrooms × 10 conditions

**Implemented and tested: score inspection now informs beliefs without automatically adding competence. This widens the overall final knowledge spread modestly, but does not establish a stronger, persistent split between students' learning behaviors.** The original V4.1/V4.2 engines and E9 results are preserved.

## What changed

Originally a two-tick check revealed an answer packet's exact score and also gained knowledge at half the rate of a three-tick independent attempt. The new default gives this **score-only check** no direct knowledge increment. It still takes time, supplies information, updates confidence and affects later choices. Students learn when they actually attempt work or explain to peers; a hint boosts a subsequent attempt. Copying retains zero direct learning. No copying penalty, assigned student type, larger general learning rate or target gap was added.

The check's expected intrinsic learning value changes consistently; its information value remains. A separate condition keeps the original choice values to isolate this change. Checking-learning strengths of 0%, 10%, 25% and 100% of the original are all reported, without choosing a winning value after inspecting outcomes. The zero default describes score inspection; it does **not** claim that effortful checking, error correction or self-explanation cannot teach.

## Main findings

The class mean falls from **76.51 to 72.19**. The within-class 90th–10th percentile gap rises from **15.12 to 16.83**: +1.71 points (95% CI +1.48 to +1.93). This is about an 11% wider final spread relative to the original rule, not a claim of real-world accuracy.

**Both models still compress the initial spread**, which averages 24.43 points. Learning remains monotone and proportional to remaining headroom, `(1-K)`. Given comparable learning exposure and rates, lower knowledge leaves more room to gain and students approach the same ceiling. The intervention reduces this convergence rather than producing divergence from the initial classroom.

![Learning trajectories, within-class spread, learning decomposition and early activity groups](../../runs/E10/derived/learning-gap.png)

## Do different activity patterns now create a clearer lasting gap?

Not convincingly in this test. We fixed the top and bottom thirds of each reference classroom using **completed attempts in the first five homeworks**, then followed the same students across paired conditions. Their final knowledge gap is 1.78 points originally and 1.72 with score-only checking. The paired change is -0.07 points (95% CI -0.20 to +0.05). Their initial gap was already 0.83 points; these are not randomly assigned strategies.

After homework 5, the high-minus-low attempt-rate difference is just 0.008 attempts per homework originally and 0.002 with score-only checking. Early behavior predicts little sustained difference in later attempt frequency. Integer attempt counts also tie frequently: on average 1.69 of the two group boundaries are tied; student ID resolves ties. These groups are a limited descriptive diagnostic, not distinct stable student types or a causal estimate of an activity's benefit.

The high-attempt group gains 0.89 points more over the full course, but 0.82 points less after homework 5. This is compatible with catch-up and regression toward typical activity rates; it is not evidence of a self-reinforcing learning divide.

## Behavioral responses and mechanisms

Removing automatic check learning reduces that contribution from 6.44 to zero knowledge points. Own-attempt gains rise from 19.20 to 21.19; explanation gains rise from 0.93 to 1.06. Lower K increases learning headroom as well as changing behavior, so this decomposition must not all be attributed to additional attempts.

Completed attempts increase only from 28.36 to 28.82 per student across 20 homeworks. Checks decrease from 19.09 to 18.48. Students continue checking frequently for its modeled informational value. Late copied submissions increase from 9.77% to 10.77%; both defaults complete all homework. Knowledge and behavioral change are therefore not interchangeable.

When checking is entirely unavailable, mean knowledge is 74.49, versus 72.19 with score-only checking available. Attempts increase to 32.74. Within this model, a useful information-seeking activity can consume time that would otherwise produce competence. This is a counterfactual model result, not a recommendation to stop checking real work.

## All conditions

| Condition | Mean knowledge /100 | P90–P10 gap | Early-group final gap | Late copied submissions |
|---|---:|---:|---:|---:|
| Original (100% check learning) | 76.51 | 15.12 | 1.78 | 9.77% |
| 25% check learning | 73.30 | 16.52 | 1.72 | 10.53% |
| 10% check learning | 72.65 | 16.67 | 1.72 | 10.60% |
| Score-only check (0%) | 72.19 | 16.83 | 1.72 | 10.77% |
| 0%, original choice values | 72.07 | 16.94 | 1.88 | 10.47% |
| Checking unavailable | 74.49 | 16.02 | 0.65 | 10.49% |
| 40 homeworks: original | 88.28 | 10.80 | 0.94 | 6.88% |
| 40 homeworks: score-only | 84.33 | 13.06 | 1.06 | 7.56% |
| ER network: original | 76.49 | 15.17 | 1.77 | 9.89% |
| ER network: score-only | 72.17 | 16.98 | 1.62 | 10.43% |

The wider overall spread persists on ER networks (+1.82 points (95% CI +1.54 to +2.09)) and at 40 homeworks (+2.26 points (95% CI +2.06 to +2.45)). Nevertheless, the absolute spread is smaller at 40 than at 20 homeworks. More time alone does not generate persistent divergence.

## What is encoded, what emerges, and what to change next

An attempt teaching more than passive score inspection is **encoded**, so this difference is not a discovered phenomenon. The observed activity substitution, continued checking, weak persistence of early attempt differences, and partial compensation are responses produced by the coupled decision and learning system. This study does not establish a scientifically unique form of emergence.

The next useful target is **persistence and learning content**, rather than another increase in activity multipliers. Candidate mechanisms are habit reinforcement from privately observed effort and outcomes, and separate concept skills with prerequisite difficulty and transfer tests. These could let repeated practice build useful capability while repeated answer access preserves grades without equivalent unaided performance. They require separate evidence, ablations and an explicit design; neither is implemented here. They should also permit recovery, strategy switching and null results.

For now, V4.2-L is a clearer operational distinction between information and competence. It succeeds in widening overall spread modestly, but **does not yet achieve a robust knowledge divide associated with persistent activity styles**. We retained that result rather than tuning until a larger divide appeared.

## Evidence and limitations

[Karpicke and Blunt (2011)](https://pubmed.ncbi.nlm.nih.gov/21252317/) found benefits of retrieval practice on conceptual assessments relative to elaborative concept-mapping study. This motivates distinguishing reconstructive activity from receipt of information, but does not supply the model's numerical learning rates or prove that every attempt is effective.

[Smith and colleagues (2009)](https://pubmed.ncbi.nlm.nih.gov/19119232/) found improvement on related concept questions after peer discussion. This supports retaining a route from discussion to learning, not treating all assistance as copying. These studies do not validate the simulated gap or the score-only zero-learning assumption.

All rates remain assumptions; alpha comes from a chosen trajectory, not educational data. This is an exploratory extension motivated by E9 results, with the E10 design and source hashes fixed before its runs. Uncertainty intervals resample 100 whole paired classrooms, 2,000 times; they are pointwise, not multiplicity-adjusted. Thirty students per classroom are not treated as independent experimental replicates. Initial skills, heterogeneous rates and choices confound activity-group comparisons. One scalar K cannot represent separate concepts, misconceptions, forgetting or transfer.

## Verification and reproducibility

261 tests pass, including exact historical parity at original checking strength, information updates without automatic competence, activity-time accounting and event-level learning equations. All 1000 raw data files were hash-verified. Every student's accumulated event gains reconstruct total knowledge change within 1e-12. Independent reruns of the reference and score-only condition reproduced every raw table. All E9 locked source hashes remain unchanged.

- [All classroom outcomes](../../runs/E10/derived/classroom_results.csv)
- [All student outcomes and fixed early-group labels](../../runs/E10/derived/student_results.csv)
- [Trajectories](../../runs/E10/derived/trajectories.csv)
- [Condition estimates](../../runs/E10/derived/condition_estimates.csv) and [paired effects](../../runs/E10/derived/paired_effects.csv)
- [Analysis metadata](../../runs/E10/derived/analysis.json) and [raw dataset locations and hashes](../../runs/E10/derived/dataset_manifest.json)
- [Analysis data bundle](../../runs/E10/derived/learning-gap-data.zip)
- [Source, tests, specification and run lock](../../runs/E10/derived/learning-gap-source.zip)

Raw logs stay in the project at `runs/E10`. Reproduce with `python -m classroom_swarm.e10 analyze --root runs/E10 --output <directory>`. For a new simulation, use `lock` on a new empty directory, then `run --workers 4`. An existing completed run is verified rather than overwritten. E9 remains the historical baseline.
