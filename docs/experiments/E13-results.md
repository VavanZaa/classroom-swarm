# Corrected controls: what the A25 bundle was actually made of

25 September 2026 · A26 / V4.3-C / E13 · 4,400 simulations · 44 conditions × 100 paired classrooms · 333 tests passing

E13 repeats the A25 questions with two engine defects repaired, the five-parameter "public grades" step unpacked into one parameter per rung, subgroups moved onto an exogenous trait, and a smallest effect of interest fixed in advance. One post-hoc section and two post-hoc contrasts are marked as such where they appear; everything else was locked before the run. Design and analysis were locked in [[docs/experiments/E13-preregistration]] before any outcome was seen. A22–A25 sources, locks and results are byte-identical and remain historical records.

## Read these three statements before any number below

They follow from the encoded rules, were written into the lock before the run, and their **sign is not evidence about anything**.

1. Answer AI emits packets at `ai_accuracy` and grants no knowledge, while grades come only from packet bits and knowledge only from attempts. **Any positive uptake must raise homework grades and widen the homework–exam gap.** The measured magnitudes are +13.70 points of homework (95% CI +12.72 to +14.62) and +23.70 points of gap (+22.74 to +24.76). Those numbers describe how far the identity was pushed; they are not a discovery about AI and education.
2. `grade_response * grade_shortfall` is added directly to the answer and AI-answer scores, so removing it must reduce copying. It does, by 7.45 percentage points (−8.30 to −6.56).
3. Action-benefit beliefs move toward the observed grade at receipt, so an above-expectation grade must raise the credited action's benefit. That is the update rule, audited, not a result.

The informative content of this study is elsewhere: which rung of the bundle actually moved anything, what the repaired tutor control shows, and how much the conclusions depend on two assumptions nobody had tested.

Intervals are pointwise 95% bootstrap intervals over 100 paired whole classrooms (2,000 resamples, seed 924402), not adjusted for 92 metrics × 42 contrasts. δ = 1.0 point for score means and 2 percentage points for shares. An interval inside ±δ is reported as a pre-stated null, one excluding ±δ as an effect, anything else as inconclusive.

## Unpacking the five-parameter bundle

E12 moved `peer_rule`, `distant_weight`, `closeness_spread`, `grade_bias` and `public_signal` in a single step and reported the result as "the combined public-grade and relationship mechanism". Unpacked one rung at a time on the same graphs and the same draws:

| Rung adds | Δ unaided exam | Δ late peer copying | Verdict |
|---|---:|---:|---|
| removing the intrinsic learning bonus | −2.58 [−2.76, −2.42] | +7.17 [+6.54, +7.79] | effect |
| removing the waiting bonus | +0.11 [+0.01, +0.20] | −0.29 [−0.93, +0.35] | **null** |
| both (grade-and-effort motivation) | −2.41 [−2.55, −2.26] | +6.02 [+5.32, +6.69] | effect |
| weak acquaintance contacts | −0.09 [−0.20, +0.02] | +1.15 [+0.31, +1.95] | **null** |
| strictly-higher-grade eligibility | +0.19 [+0.09, +0.31] | −0.57 [−1.35, +0.18] | **null** |
| grade weighting in source choice | −0.02 [−0.14, +0.09] | +0.43 [−0.33, +1.15] | **null** |
| **blending public grades into the perceived value of copying** | **−1.79 [−1.92, −1.65]** | **+13.37 [+12.35, +14.35]** | **effect** |

**`public_signal` is the largest single contributor, but the ladder overstates how much of the total it carries.** Each rung is measured at its own position in the sequence, and `public_signal` was added last, so it absorbs whatever the earlier rungs set up. A post-hoc check (below) brackets the attribution: added first it carries +7.25 points of copying, removed last +13.37, against a +14.39 total. It is the only component that clears δ under both orderings, so the ranking is safe even though the share is not.

What the term does is blend the eligible pool's mean grade into what a student expects a copied answer to be worth. Under the strictly-higher rule that pool always scores above the requester, so the blend is biased upward by construction. E12's design could not separate any of this; this one separates it far enough to show that the eligibility rule and the blending are not independent.

Likewise, E12's "motivation" step was the learning bonus. Dropping the arbitrary waiting bonus on its own does nothing measurable.

The rungs sum exactly to the direct `legacy → public_no_ai` difference (−4.12 points of exam, +20.41 points of copying), but that is arithmetic — a telescoping sum of paired means — not evidence that the mechanisms are additive.

### Post-hoc: how path-dependent is that attribution?

Not preregistered. Added after the locked analysis was read, and reproducible with `scripts/e13_order_robustness.py` on the same 100 classrooms, graphs and draws. Each component is measured both when **added first** to `motivation_only` and when **removed last** from the finished `public_no_ai` model.

| Component | Exam, added first | Exam, removed last | Copying, added first | Copying, removed last |
|---|---:|---:|---:|---:|
| acquaintances | −0.09 [−0.20, +0.02] | −0.67 [−0.80, −0.55] | +1.15 [+0.32, +1.95] | +5.03 [+4.18, +5.91] |
| grade filter | **+0.40** [+0.28, +0.52] | **−0.29** [−0.42, −0.17] | **−2.35** [−3.21, −1.50] | **+1.51** [+0.61, +2.41] |
| grade weighting | −0.21 [−0.30, −0.12] | −0.19 [−0.30, −0.08] | +1.71 [+0.93, +2.51] | +0.43 [−0.33, +1.20] |
| `public_signal` | −0.74 [−0.84, −0.64] | −1.79 [−1.92, −1.65] | +7.25 [+6.44, +8.07] | +13.37 [+12.41, +14.33] |
| **sum of parts** | −0.63 | −2.94 | +7.77 | +20.33 |
| **actual total** | −1.71 | −1.71 | +14.39 | +14.39 |

Three things follow. **The components interact strongly and no ordering attributes the total**: added-first shares sum to about half the copying effect, removed-last shares to about 140% of it. **The eligibility filter changes sign with order** — added on its own it *reduces* copying by 2.35 points, because it shrinks the pool a student may ask with nothing to offset that; removed from the finished model it *increases* copying by 1.51, because in that model the filter is precisely what guarantees every eligible source outscores the requester and so feeds the upward bias in `public_signal`. The filter has no worthwhile independent effect and instead *creates* the bias the blending term exploits, which is the coupling the audit predicted, now measured. **`acquaintances` is a null added first and an effect removed last** (+5.03 copying), consistent with `friends_only` from the full model (−12.64 [−13.52, −11.75], which also drops the closeness spread); that layer matters only once grade-based source choice is on.

The preregistered ladder remains the primary analysis — it was fixed in advance and this check was not — but its per-rung numbers should be read as one path through an interacting system, not as separable contributions.

## The repaired tutor control

A25 labelled an AI-tutored attempt by the hint's *strength*, so the zero-strength tutor was invisible to credit assignment: 0.32% of returned grades credited it, its perceived value stayed frozen at the initial prior, and no `ai_guided` route was ever recorded. It was not a tutor with no effect; it was a tutor nobody could learn about. A26 labels by hint *source*.

| tutor arm | consults/student | returns crediting the tutor | perceived tutor value | `ai_guided` late | unaided exam |
|---|---:|---:|---:|---:|---:|
| `tutor_ai` (strength .25) | 7.98 | 19.20% | 56.14 | 16.92% | 69.97 |
| `tutor_ai0` (strength 0, repaired) | 7.30 | 12.88% | 51.83 | 10.53% | 68.44 |
| `tutor_ai0_uncredited` (A25 rule) | 6.91 | 0.32% | 49.82 | 0.00% | 68.63 |

With the control working, `tutor_ai0 − tutor_ai` is an effect: −1.53 exam points (−1.66 to −1.39) and −1.49 knowledge points. **A tutor that helps nobody is clearly worse than one that does.** Whether it is worse than *no* tutor is a weaker claim: the paired contrast `tutor_ai0 − public_no_ai` is −0.74 exam points (−0.86 to −0.63) and −0.71 knowledge points — pointing the right way, since consulting still costs two ticks, but lying inside ±δ and therefore a pre-stated null. That contrast was not preregistered; it is a post-hoc re-reading of the locked data, reported here because the stronger phrasing is not supported.

The direct size of the old defect, `tutor_ai0_uncredited − tutor_ai0`, is small in outcomes — +0.19 exam points (+0.08 to +0.30, a pre-stated null) and +1.20 homework points (+0.22 to +2.23, inconclusive) — but it changes what the row *means*, and that was the problem.

The repair also has a direction worth stating plainly, because it is the opposite of what one might assume. Crediting the zero-strength tutor makes students consult it **more**, not less (7.30 vs 6.91 per student), because the credit is split half with the attempt that follows, so the tutor inherits half the credit for an ordinary attempt and its perceived value rises above the initial prior. The model learns that "consult then attempt" scores about what attempting scores — which is true — not that the tutor is worthless.

Tutor AI's own benefit does not clear the bar. `tutor_ai − public_no_ai` is +0.79 exam points (+0.66 to +0.92) and +0.78 knowledge points: both intervals lie inside ±δ, so this is a **pre-stated null**, not the small positive effect E12 reported with the same numbers and no δ. A stronger tutor does clear it: `tutor_ai50 − tutor_ai` is +1.14 knowledge points (+1.06 to +1.22).

## The assumption that matters most had never been varied

Two score-function assumptions were exposed as parameters. One barely matters; the other dominates everything else in the study.

**Confidence blending** (`attempt` and `hint` benefits shrunk toward self-assessment, the shortcut actions not) moves the answer-AI exam by −0.82 (w=0) to +0.96 (w=1) — inconclusive at δ in both directions, and null on knowledge at w=0. The A25 conclusions survive this assumption.

**The benefit prior** does not. All five action beliefs start at each student's true initial knowledge, and no A25 condition varied it:

| prior | direct AI use, late | AI consults/student | unaided exam | Δ exam vs default |
|---|---:|---:|---:|---:|
| .25 | 16.93% | 7.18 | 63.73 | +4.56 [+4.29, +4.85] |
| K₀ (default ≈ .5) | 50.37% | 15.44 | 59.18 | — |
| .75 | 62.50% | 18.23 | 57.39 | −1.78 [−1.99, −1.59] |

Direct AI uptake moves from 17% to 63% across a prior range nobody had tested. On **uptake** that is the widest span of any lever here — 45.6 percentage points, against 43.3 for AI accuracy (.8 to 1) and 25.3 for effort aversion (0 to .5). On the **exam** it is a tie rather than a win: 6.34 points across the prior range against 6.05 across the effort range. The honest statement is that an untested assumption matters about as much as the parameter the study was built around, not more. Without AI the prior is nearly inert (68.17 to 70.82). **The A25 AI story is substantially a story about how quickly a student's belief in the shortcut overtakes a frozen belief in their own work, and the starting point of those beliefs was never varied.**

The mechanism is visible in the belief-channel audit. The share of returned grades that credit the student's own attempt at all:

| condition | attempt | hint | answer | AI answer | AI tutor | belief in attempting | belief in AI answers |
|---|---:|---:|---:|---:|---:|---:|---:|
| `legacy` | 78.08% | 6.73% | 21.92% | — | — | 67.38 | — |
| `public_no_ai` | 60.02% | 2.85% | 39.98% | — | — | 62.13 | — |
| `answer_ai` | **20.41%** | 3.34% | 40.47% | 39.12% | — | **53.42** | 76.98 |
| `prior75_answer` | 13.09% | 2.19% | 31.31% | 55.61% | — | 68.30 | 87.79 |

Once a student submits an AI answer, the attempt they may still have made that homework is not credited, so evidence about their own work stops arriving. Under answer AI only one grade return in five carries any information about attempting. Nothing in the model lets a student learn what they could now do unaided; the only route back is the 6% uniform exploration floor. That is a real limitation of this learner, not a finding about students.

## The hint-timing artefact is real and immaterial

A peer hint used to be requestable whenever six ticks remained, but service could be delayed up to three ticks, so hints could arrive with too little time left for the attempt they were for — while the AI tutor already reserved that time. A26 applies the same reservation to peer hints.

With the guard off, 12.37% of peer hints arrive unusable and students receive 0.19 more peer hints per student. With it on, 100% are usable. The effect on outcomes is a pre-stated null: exam −0.05 (−0.14 to +0.05), knowledge −0.03 (−0.09 to +0.04), copying +0.55 (−0.28 to +1.35). So E9's "limited hint uptake" was mildly contaminated as a *statistic* but the contamination did not reach the outcomes.

## Topology, at last

E12 generated an ER graph every replicate and used it in no condition. E13 runs the three main arms on both families. The answer-AI contrast replicates almost exactly — exam −10.00 (−10.26 to −9.73) on ER against −10.00 (−10.27 to −9.74) on SBM, knowledge −10.06 against −10.02 — while the homework and gap contrasts are somewhat larger on ER (+15.19 and +25.20, against +13.70 and +23.70). Tutor AI is a null on both families (+0.62 on ER, +0.79 on SBM). Community structure is not carrying these results.

## Subgroups that can be differenced

Contrasted subgroups are now the top and bottom thirds by the exogenous learning trait α, which is drawn before any behaviour and is identical in every condition of a replicate. E10 and E11 took their labels from one arm of the contrast, which imports that arm's noise into every subgroup difference.

The high-minus-low-α final knowledge gap is 8.22 points without AI, 8.51 with tutor AI and 4.33 with answer AI; `answer_ai − public_no_ai` on that gap is −3.89 (−4.28 to −3.50). Answer AI compresses the ability gap by lowering the top, not by raising the bottom. The behavioural early-attempt grouping gives a visibly different picture in the same runs (8.51, 7.08 and 7.51), which is why it is reported per condition under a `desc_` prefix and excluded from the paired-effect table in code.

## All conditions

| Condition | Homework at final exam | Same-time exam | Gap | Knowledge | Late peer-copy % | Late direct-AI % | K P90–P10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| legacy | 74.31 | 73.30 | 1.01 | 73.44 | 18.17 | 0.00 | 17.60 |
| drop_learning_bonus | 71.74 | 70.72 | 1.02 | 70.81 | 25.34 | 0.00 | 19.48 |
| drop_wait_bonus | 74.44 | 73.41 | 1.03 | 73.55 | 17.87 | 0.00 | 17.87 |
| motivation_only | 72.41 | 70.89 | 1.52 | 70.98 | 24.19 | 0.00 | 19.36 |
| acquaintances | 71.96 | 70.80 | 1.16 | 70.84 | 25.34 | 0.00 | 19.82 |
| plus_grade_filter | 72.75 | 71.00 | 1.75 | 71.06 | 24.77 | 0.00 | 19.63 |
| plus_grade_weighting | 73.00 | 70.97 | 2.02 | 71.05 | 25.21 | 0.00 | 19.63 |
| public_no_ai | 72.01 | 69.18 | 2.83 | 69.25 | 38.57 | 0.00 | 21.19 |
| answer_ai | 85.71 | 59.18 | 26.54 | 59.23 | 38.08 | 50.37 | 23.94 |
| tutor_ai | 73.63 | 69.97 | 3.66 | 70.03 | 39.48 | 0.00 | 20.53 |
| answer_ai80 | 76.22 | 59.99 | 16.23 | 59.97 | 45.09 | 39.87 | 24.66 |
| answer_ai100 | 96.56 | 58.70 | 37.87 | 58.71 | 6.68 | 83.17 | 23.54 |
| tutor_ai0 | 71.10 | 68.44 | 2.66 | 68.54 | 41.19 | 0.00 | 21.75 |
| tutor_ai0_uncredited | 72.30 | 68.63 | 3.67 | 68.70 | 40.91 | 0.00 | 21.68 |
| tutor_ai50 | 77.32 | 71.06 | 6.26 | 71.17 | 38.54 | 0.00 | 19.95 |
| no_pressure | 72.54 | 70.91 | 1.62 | 71.01 | 31.12 | 0.00 | 18.99 |
| answer_no_pressure | 86.77 | 60.07 | 26.70 | 60.12 | 34.11 | 53.82 | 24.40 |
| tutor_no_pressure | 74.88 | 71.36 | 3.52 | 71.44 | 31.66 | 0.00 | 18.43 |
| public_relaxed | 71.50 | 69.59 | 1.91 | 69.64 | 36.57 | 0.00 | 21.60 |
| answer_relaxed | 86.01 | 58.72 | 27.29 | 58.79 | 50.11 | 41.27 | 24.46 |
| score_only | 71.23 | 69.06 | 2.16 | 69.10 | 39.85 | 0.00 | 21.50 |
| friends_only | 72.59 | 70.58 | 2.01 | 70.72 | 25.93 | 0.00 | 20.26 |
| confidence0_no_ai | 71.26 | 68.89 | 2.38 | 68.99 | 40.50 | 0.00 | 21.72 |
| confidence0_answer | 87.10 | 58.36 | 28.74 | 58.39 | 38.09 | 52.57 | 23.79 |
| confidence100_no_ai | 72.02 | 69.38 | 2.64 | 69.48 | 37.47 | 0.00 | 20.90 |
| confidence100_answer | 85.40 | 60.13 | 25.26 | 60.17 | 36.59 | 49.69 | 23.59 |
| prior25_no_ai | 71.01 | 68.17 | 2.84 | 68.24 | 37.67 | 0.00 | 22.17 |
| prior75_no_ai | 72.97 | 70.82 | 2.15 | 70.84 | 38.21 | 0.00 | 18.97 |
| prior25_answer | 77.68 | 63.73 | 13.95 | 63.79 | 45.45 | 16.93 | 28.62 |
| prior75_answer | 87.39 | 57.39 | 30.00 | 57.45 | 30.36 | 62.50 | 24.05 |
| hint_guard_off_no_ai | 71.96 | 69.13 | 2.83 | 69.22 | 39.12 | 0.00 | 21.29 |
| effort0_no_ai | 72.57 | 70.26 | 2.31 | 70.28 | 36.41 | 0.00 | 21.10 |
| effort0_answer | 85.19 | 61.44 | 23.75 | 61.39 | 40.69 | 43.69 | 24.21 |
| effort0_tutor | 75.40 | 70.95 | 4.44 | 71.06 | 38.45 | 0.00 | 20.11 |
| effort50_no_ai | 69.29 | 66.90 | 2.39 | 66.99 | 39.33 | 0.00 | 22.08 |
| effort50_answer | 87.71 | 55.39 | 32.32 | 55.45 | 25.57 | 68.99 | 23.35 |
| effort50_tutor | 70.84 | 67.63 | 3.21 | 67.70 | 37.97 | 0.00 | 21.27 |
| H40_no_ai | 82.85 | 81.46 | 1.39 | 81.49 | 30.19 | 0.00 | 17.92 |
| H40_answer | 88.26 | 63.34 | 24.93 | 63.28 | 32.25 | 58.49 | 26.88 |
| H40_tutor | 84.33 | 82.17 | 2.16 | 82.18 | 30.05 | 0.00 | 17.36 |
| ER_no_ai | 70.96 | 69.30 | 1.66 | 69.33 | 38.79 | 0.00 | 21.19 |
| ER_answer | 86.15 | 59.29 | 26.86 | 59.27 | 37.22 | 51.39 | 23.98 |
| ER_tutor | 74.79 | 69.91 | 4.88 | 70.01 | 39.83 | 0.00 | 20.45 |
| answer_no_exam_feedback | 86.47 | 59.05 | 27.43 | 59.12 | 37.59 | 52.21 | 23.94 |

Where AI answers are submitted, most submitted work is AI-origin even when direct use is not: in `answer_ai`, 50.37% of late submissions are directly obtained from the AI, 32.43% are AI answers forwarded by a peer, and 82.79% carry AI-origin item bits. Near-perfect AI inverts the mix — 83.17% direct and 6.68% peer copying — so looking only at classmate-to-classmate copying would miss most of the dependence. That reproduces E12's finding on a corrected engine.

## Limits

A26 repairs controls, identification and reporting. It adds no mechanism, calibrates nothing, and does not make any earlier result wrong in its own terms. Knowledge is a single monotone scalar; every rate and coefficient comes from a chosen trajectory, not student data. Forgetting, sanctions, plagiarism detection, correlated AI errors and multiple concepts are all absent. AI item errors are independent draws. Effect intervals are pointwise over 100 classrooms and are not multiplicity-adjusted; the 30 students inside a classroom are not independent replicates. A cleaner ladder identifies which encoded rule moved an outcome — it cannot turn an encoded rule into an empirical finding.

## Reproducibility

333 tests pass, including 37 for A26. Under its legacy flags the corrected engine reproduces A25 on every shared raw table across two seeds, three AI modes and both motivation settings, and the score dictionaries match over 1,200 random states. Every student's knowledge change reconstructs from `attempt` and `help_hint` event gains within 1e-12. All 1,400 raw shard files were hash-verified at analysis. `legacy`, `public_no_ai`, `answer_ai`, `tutor_ai` and `tutor_ai0` were independently re-simulated and reproduced every raw table exactly. A regression test forbids any benefit channel that is written and never read.

Of 110 classroom metrics, 92 are differenced across conditions and 18 behavioural-subgroup metrics are reported per condition only; the analysis code enforces that split rather than leaving it to the writer.

- [Classroom outcomes](../../runs/E13/derived/classroom_results.csv), [student outcomes](../../runs/E13/derived/student_results.csv), [trajectories](../../runs/E13/derived/trajectories.csv)
- [Condition estimates](../../runs/E13/derived/condition_estimates.csv), [paired effects](../../runs/E13/derived/paired_effects.csv), [analysis metadata](../../runs/E13/derived/analysis.json)
- [Raw data locations and integrity hashes](../../runs/E13/derived/dataset_manifest.json)
- Post-hoc ladder robustness: `scripts/e13_order_robustness.py` (re-simulates, reads nothing from `runs/E13`)

Raw logs are in `runs/E13`. Reproduce the analysis with `python -m classroom_swarm.e13 analyze --root runs/E13 --output <directory>`. A new study needs a new empty directory, then `lock`, then `run --workers 6`. Completed runs are verified, never silently overwritten.
