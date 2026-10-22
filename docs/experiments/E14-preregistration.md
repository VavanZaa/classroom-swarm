# E14: classroom setup and literature trends

Declared 2026-10-01 before treatment outcomes. Engine: A28, the separate declared-settings fork of A26. No empirical calibration, fitting, or parameter search. This is a directional comparison of a numerical homework/peer model with published experiments, not a replication of human effect sizes.

## Evidence and scope

| Study | Reported trend | What this model can compare |
|---|---|---|
| Krueger, Project STAR, [NBER WP6051](https://www.nber.org/papers/w6051) | Random assignment to small classes (13–17) versus regular classes (22–25) improved test outcomes. | N=15 versus 24, and exploratory N=45; peer channels only. Teacher attention and classroom management are absent. |
| Kimbrough, McGee and Shigeoka, [2017 working paper](https://docs.iza.org/dp10783.pdf), later JHR 2022 | In laboratory problem solving, peer teaching helped low performers; ability tracking removed much of that benefit. Groups had four students. | Two groups of four drawn from four low and four high starters: mixed versus homogeneous, teaching enabled versus disabled. |
| Duflo, Dupas and Kremer, [AER 2011 manuscript](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf) | Tracking in Kenyan schools benefited students across ability levels, with instruction adapting to the group. | Group composition can be varied. The teacher adaptation mechanism is absent, so this result is outside the present causal model. |
| Wu, Zhang and Wang, [AEJ Economic Policy 2023](https://www.aeaweb.org/articles?id=10.1257/pol.20200563), [accepted manuscript](https://www.aeaweb.org/content/file?id=15848) | Mixed seating alone had no detectable benefit; mixed seating plus rewards improved low performers' math. | High–low versus randomly paired desks without rewards. Rewards and changing friendships are absent. |
| Bastani et al., [PNAS 2025](https://www.pnas.org/doi/10.1073/pnas.2422633122) | Unrestricted AI improved assisted work but harmed subsequent unaided performance. Guardrailed tutoring avoided that harm without a detectable test benefit. | Answer AI, tutor AI and no AI over four episodes; final homework and unaided exam measured at the same time. Model hints are numerical, not actual GPT tutoring. |

Higher-peer-knowledge tests are mechanism probes motivated by the peer-teaching evidence, not a literal intervention from that study. The paper's whole-problem AI accuracy is also a different quantity from this model's per-item accuracy. An explicitly bundled 0.51 accuracy sensitivity is exploratory, not a fitted translation.

## Fixed scenarios

The four generated JSON files contain every active parameter, initial distribution, graph declaration and condition override. Their hashes and all engine, analysis, test and preregistration source hashes are saved in `runs/E14/preregistration-lock.json` before execution. Each output group receives a separate resolved runtime lock before its first simulation. Run 100 independent classroom replicates per condition, with predeclared semantic streams paired within each configuration. No retuning, exclusions, reruns selected for results, or stopping for significance.

1. **Class size:** six conditions: N=15,24,45, each with friend-only contacts or weak acquaintance access. ER expected friend degree remains six; acquaintance weight is respectively zero or 0.1. This holds mean friend opportunities constant rather than holding network density constant. Initial knowledge uses the default bounded distribution, mean 0.5, SD 0.1.
2. **Peer composition:** eight conditions. The first 15 of 30 students always start at knowledge 0.35. The other 15 start at 0.35,0.55,0.75. Compare current hint/copy choices, hints only, and a low/high no-peer identity control.
3. **Grouping:** six conditions. Four low starters (0.35) and four high starters (0.75) form two four-person cliques, mixed or homogeneous, with teaching on/off and copying disabled. Two additional 32-student conditions pair 16 low and 16 high starters randomly or across ability. Both use the same opportunities and no rewards. The random seating realization is fixed before outcomes; inference is conditional on these declared seating graphs.
4. **AI and spread:** thirteen conditions. Bounded knowledge distributions with underlying means 0.35,0.50,0.80 and SD 0.1 cross no AI, answer AI and tutor AI. Four homework episodes, exam after each, AI starts at episode one. Add low/middle answer AI with assumed accuracy 0.51 and no-AI SD 0.05/0.20 at mean 0.50.

Total: 33 conditions, 3,300 runs. Defaults otherwise retained; initial confidence and all benefit beliefs fixed at 0.5, independently of knowledge. Learning efficiency and effort-aversion distributions are held constant. Bounded distributions can have realized means/SD different from their underlying normal parameters; report both. Numeric episodes have no calibrated mapping to minutes or semesters.

## Measurement and comparisons

The primary measure is final unaided exam. Exogenous focal students are the fixed low starters in peer composition/grouping, and all students in class-size/AI comparisons. Additional whole-class estimates are descriptive. Ten primary comparisons are frozen in `PRIMARY` in the analysis script: small versus regular under each contact rule; high versus low peers under current and hint-only choices; mixed versus tracked with teaching; mixed teaching versus mixed solo; cross-ability versus random seating; middle answer versus none; middle tutor versus none; middle tutor versus answer.

Use replicate means as independent sampling units, paired differences within configurations, and 5,000 bootstrap resamples with seed 10011499. Report pointwise 95% intervals and Bonferroni-adjusted 99.5% intervals for the ten primary comparisons (nominal simultaneous 95%; percentile bootstrap is approximate). A positive/negative predicted direction matches only if its adjusted interval excludes zero in that direction; an opposite exclusion is contrary; otherwise inconclusive. For published nondetection, test the separate, predeclared simulation equivalence band ±1 normalized score percentage point. Nondetection in a human study does not itself establish equivalence.

Secondary measures: initial/final knowledge and spread, knowledge gain, final homework, final copying share, attempts, successful hints, request delivery success, and AI uses. Scores, shares and normalized spread differences use 100×scale; counts use per 100 student episodes, explicitly labeled. Secondary intervals are exploratory, without familywise adjustment. Mean request success is per-class conditional on requests, assigning zero to a class without requests; report it descriptively, not as a delivery probability pooled over students.

The final exam and final homework are from the same episode. No subgroup is defined by post-intervention behavior. N-changing scenarios preserve stream identities but cannot preserve identical classroom-sized random tensors/graphs, so their pairing does not imply identical individual shocks.

## Identities, auditing and limits

Copying/direct answer AI grant zero direct knowledge by construction; nonnegative practice gain and remaining-knowledge headroom are identities, not empirical discoveries. Tutor-assisted gains reflect an assumed hint learning rule. AI effects on exams and grades depend on uptake, substitution and relative capability and are not guaranteed signs.

With all social learning channels disabled, changed peers/networks must leave fixed focal students' knowledge, homework and exams exactly unchanged at every replicate. Test both controls. Audit all raw logs with `validate_declared_log`, verify raw file hashes and declaration/source hashes, and preserve the complete inventory. Source errors require a documented deviation and a separately named run; do not silently replace frozen outputs. Existing E9–E13 sources and locks remain untouched.

Agreement will establish compatibility with the chosen model assumptions, not validation of those assumptions. Disagreement is reported unchanged. In particular, teacher attention, adaptive instruction, teaching rewards, friendship changes and actual LLM conversations cannot emerge from mechanisms that are absent here.
