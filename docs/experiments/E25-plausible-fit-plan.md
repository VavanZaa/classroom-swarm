# E25: plausible parameter fitting after the existing-mechanism audit

Declared 2026-10-10, before this experiment's outcomes. The user authorizes audit corrections, multi-study comparison, fitting and supported interaction repairs, while requiring meaningful parameters. E24 failures and A32/A33 source locks remain immutable. E25 applies A34 policy repairs; it does not silently refit the frozen studies.

## Parameter meanings and admissibility

All knowledge/probability/quality variables use a bounded 0–1 scale. One tick is a model scheduling unit; three ticks define one reference learning dose. This is not a verified conversion to classroom minutes. Utility is normalized to one expected homework/test point on that 0–1 scale. Teacher costs and prizes are utility quantities, not salary dollars. Initial knowledge distributions are latent assumptions, not the human pretest score distribution. Study sample sizes below are representative protocol settings, not full replications of the original populations.

| Tunable quantity | Meaning and units | Bounds | Reason and evidence status |
|---|---|---:|---|
| Tracking observation update | Fraction of newly released score used in an observer update | 0.5–1 | Existing partial-to-full updating; avoids non-updating or overreaction. Unknown empirical rate. |
| Tracking mastery threshold | Prerequisite criterion on 0–1 scale | 0.6–0.8 | Exploratory performance criteria. One existing setting controls both lesson eligibility and physical uptake; the coupled effect is explicitly bundled and cannot identify these parts. No paper-estimated threshold. |
| Teacher linear cost | Utility cost per additional work tick | 0.0001–0.002 | Strictly positive, near prior audited sensitivities. Unknown empirical coefficient; schedules must remain budget feasible. |
| Teacher convex cost | Extra utility penalty on squared resulting within-class work fraction | 0.0005–0.004 | Positive sensitivity around the existing 0.002. Preserves the current formula; not interpreted as the marginal derivative of total work disutility. No empirical calibration. |
| Teacher intrinsic weight | Utility per projected average student score gain | 0.1–1 | Nonzero intrinsic concern, at most homework-scale value. Shared across studies, never a treatment effect multiplier. Unmeasured. |
| Teacher gain belief | Expected fraction of available knowledge headroom learned per productive reference dose | 0.01–0.04 | Half to twice the prior 0.02; preserves diminishing headroom. A subjective productivity hypothesis, not the physical learning rate. |
| Helper intrinsic value | Utility bonus per unit helper effort | 0.01–0.04 | Small nonzero preference near 0.02. Excludes E24's 0.1 probe that changed virtually all helping effort. Applies to ordinary and rewarded help. Unmeasured. |
| Helper cost multiplier | Helper effort cost relative to ordinary productive work | 0.75–1.5 | Modest cost difference, strictly positive. Same meaning and setting across peer studies and treatments. Unmeasured. |
| Kenyan incentive exam access cost | Utility cost per exam relative to its declared stakes | 0.25–0.4 | Only this study's participation setup; reference 0.35 is the preserved E23 low-access sensitivity, with heterogeneous initial confidence from knowledge. An assumption about attendance barriers, not a measured attendance rate. |
| Corrective material quality | Probability of usable corrective content for independent practice | 0.6–1 | Moderately useful to reliable content, same across all studies and AI arms. Unknown empirical quality; cannot become a treatment-specific score bonus. |

Shared teacher/helper/material quantities are optimized jointly over five cases. Class sizes, group assignment, initial knowledge means/SDs, physical alpha, teacher skills, time budgets, AI capacity, prize/contract strength, transfer matrix, curriculum levels, study duration and exam item counts are fixed. Initial ability, learning efficiency and time-scale assumptions still need human data; the optimizer cannot establish that they are correct. Weak identification and boundary solutions must be reported.

Hard admissibility: at least 20% of dose events productive, at least 60% of enrolled unrewarded students take the familiar incentive exam, some teacher guidance is used for the class-size account, and some rewarded test preparation is used for the incentive account. These are declared plausibility/pathway screens, not empirical estimates. All original budget, no-background-learning, hidden-information and raw reconstruction checks are required. Infeasible candidates are retained and cannot beat feasible ones under the objective. If no selection candidate is feasible, preserve that result and report failure rather than asserting a fit.

## Studies, outcomes and fixed protocols

[STAR](https://www.nber.org/papers/w6051) compared small classes (13–17) with regular classes (22–25), finding higher standardized achievement in small classes. Use fixed representative 15/24 sections of the same 120 students, identical per-teacher resources; no class-size multiplier on learning.

[Duflo, Dupas and Kremer](https://www.aeaweb.org/articles?id=10.1257/aer.101.5.1739) found tracking benefits consistent with teachers adapting instruction to ability. Use the same fixed students in mixed/tracked groups and observed prerequisite lesson choice. Lower and higher starter exam directions both matter.

[Bastani and colleagues](https://www.pnas.org/doi/10.1073/pnas.2422633122) report better assisted practice but worse subsequent unaided performance with unrestricted GPT Base; tutor guardrails mitigate the harm. Both assisted homework and unaided exams are fit targets, so the optimizer cannot manufacture the exam sign by simply making AI unusable.

[Wu, Zhang and Wang](https://www.aeaweb.org/content/file?id=15848) motivate across-rank seating and explicit helper incentives. Fit lower-starter reward benefit and modest upper-starter change, with exogenous observed-baseline ranks and fixed assigned pairs. Random vs cross-rank seating is also checked.

[Glewwe, Ilias and Kremer](https://www.aeaweb.org/articles?id=10.1257/app.2.3.205) report linked test gains, exam participation and test preparation increases, without broad unrelated test improvements. Fit familiar-test gain and participation with test preparation actually delivered, and modest novel-score/knowledge changes. Unrelated zero-transfer nulls are structural identities and excluded from loss. Teacher attendance and compulsory instruction cannot respond to incentives here; their invariance is an identity, not reproduced field evidence. After-class preparation is not yet a discretionary action: a separately documented protocol/design gap.

Single/repeated [peer learning laboratory](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) and the partial [composition probe](https://leuven.economists.nl/pdf/ability_final.pdf) are untouched secondary checks. The repeated model is not the single-session protocol. Composition is incomplete and has no unconditional directional fit target.

## Loss, algorithm, selection and fresh pool

The first 2 cohorts (draw IDs 51000–51001) are training, 4 different cohorts (52000–52003) are candidate selection, and 16 untouched cohorts (53000–53015) are fresh evaluation. All cohort definitions, bounds, targets and code are locked before outcomes. Semantic global-student draws preserve paired arms. Changed population sizes/assignments cannot be optimized.

Use bounded `rand/1/bin` differential evolution: 8 population members, 2 generations after initialization, mutation 0.7, crossover 0.8, fixed optimizer seed. This is a finite exploratory search of 24 shared parameter vectors, not a claim of global convergence in 10 dimensions. Training targets are directional hinge loss (0.1 model percentage-point positive/negative margin, participation 1 pp) and near-zero bands (AI and upper seating 0.2 pp; teacher novel/knowledge 0.5 pp). Margins/bands are declared model-resolution tolerances, not human effect-size or equivalence estimates. Average target losses within studies, then average studies, adding 0.02 times mean squared normalized distance from reference. This discourages unnecessary movement but does not identify true parameters.

Select the best three feasible training candidates plus the reference on the four selection cohorts; choose the lowest admissible objective and freeze selection before fresh runs. No fresh outcome may alter candidates, bounds, source or loss. Fresh profiles: frozen A33 default, A34 default correction, selected A34 settings; all primary and secondary studies, preserving contrary results and previous-study regressions. Two-sided paired bootstrap intervals across classroom cohorts, 20,000 resamples; 15-target Bonferroni intervals for primary family. Near-zero agreement is supported only when the family interval lies within the declared band, not merely because zero lies in it. Secondary tests are exploratory.

Save every candidate's resolved job, complete raw tables and independent live/reloaded checks. E25 uses lossless compressed JSON for the same raw table records to avoid hundreds of thousands of small files; no aggregation replaces raw logs. Record source hashes, failure history, all objectives, selections and final effects.

A search improvement with actual intended activity is evidence of conditional parameter sensitivity. An absent/disconnected causal pathway is a design deficiency. A contrary result in this limited search does not prove no plausible parameter can work. Interactions are added only with a documented deficiency; preserve a failed model version before any subsequent design run. Successful trend selection uses published outcomes and is internal simulated-cohort robustness, not independent external validation.

## Why not direct backpropagation

The engine uses hard thresholds, discrete effort/action argmax, Boolean attention/content gates and variable schedules in NumPy. Direct pathwise derivatives through the existing complete simulation are unavailable. [SciPy's official differential-evolution documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html) describes bounded stochastic population search without gradients. E25 implements that small algorithm with existing NumPy dependencies. Score-function gradients or a differentiable surrogate could be a later design, but would require separate variance/control and simulator-fidelity validation; they are not needed for this audit follow-up.
