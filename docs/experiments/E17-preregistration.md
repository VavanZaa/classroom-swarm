# E17: tutoring assumption robustness and protocol diagnostics

Declared 2026-10-06 before outcomes. This experiment uses existing A29 controls for backlog F01 and F11, existing voluntary/scheduled modes to probe F02, and new analysis for F12. It does not implement noisy/delayed checks, persistent topics, teacher instruction or helper rewards. Historical source locks and runs remain unchanged.

The target is the Sudoku peer-teaching pattern in [Kimbrough, McGee and Shigeoka's author manuscript](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf): mixed-group teaching benefits low starters, tracking weakens those benefits, high starters benefit less, and tracking reduces teaching frequency. One common task opportunity with optional conversation differs from guaranteed explanation receipt. Numerical guided sessions are only a proxy for teaching statements. The model exam score is not the human solving-time measurement.

## Design

Eight students: four fixed initial knowledge .35, four .75. Same mixed and tracked groups of four as E16; no copying or AI. A third arm is independent practice on the mixed graph, with hint access disabled. Initial confidence/action-benefit priors .5, static contacts, paired semantic randomness, inherited uncalibrated learning rates and task difficulty uniform [0,1]. All settings are saved before execution.

Fourteen variants, each with mixed, tracked and solo arms:

1. Reference A29: skill 1, check coverage 1, 20 episodes, 3-tick scheduled practice.
2. Skill .75.
3. Skill .5.
4. Heterogeneous skill uniform [.5,1]. Distribution-family/support changes form a declared bundle.
5. Check coverage .25.
6. No checks, coverage 0.
7. Frozen quality beliefs, update rate 0.
8. No quality-based targeting, target weight 0. Quality can still affect perceived packet value; this is not a full quality-channel removal.
9. Uniform quality prior .2.
10. Uniform quality prior .8.
11. Five-tick scheduled practice.
12. Voluntary joint practice, 20 episodes.
13. Single-episode scheduled practice, final exam after episode 1.
14. Single-episode voluntary joint practice, final exam after episode 1.

Each parameter contrast uses its matched reference. The single-episode contrast changes H and exam frequency jointly to obtain a final exam: it cannot identify their separate effects. The last variant is compared against single-episode scheduled practice for the protocol change and against 20-episode voluntary practice for the schedule bundle. These are coarse schedule probes, not exact human protocol replication: no public baseline ranks, payment objective, persistent strategy mastery or initial competence-changing assessment is added. No learning coefficients are fitted or tuned to the desired signs.

20 development replicates at seed 10061701; 60 untouched confirmation replicates at seed 10061791. The 42 conditions, seeds, source hashes, analysis and tests are locked together before any outcomes. Total 3,360 runs. Confirmation is opened only after a written development review. Additional seeds test model repeatability, not external human validation.

## Outcomes and comparisons

Exogenous groups: low indices 0–3, high 4–7 and all 0–7. Report final unaided exam, competence gain, same-time homework, practice/content/helper gains, completed guided sessions per student per episode, usable/correct explanations, helping events, quality updates and occupied practice/help time. Competence and feedback truth remain analysis-only information.

For every variant compare mixed–tracked, mixed–solo and tracked–solo. Compare each changed setting against its matched reference in all three arms. Include high-minus-low differences in the mixed–tracked and mixed–solo effects. Both measured exam and latent gain are required for an outcome-direction match; report uncertainty and mismatches. A positive mean with an interval spanning zero is uncertain, not an established benefit.

Paired replicate bootstrap: 3,000 resamples, pointwise 95% Monte Carlo intervals for all outcomes. A simultaneous 95% family uses Bonferroni over nine prespecified low-group exam comparisons: three arm contrasts in reference, single scheduled and single voluntary. Other intervals are exploratory. No equivalence threshold is inferred from human statistical nondetection, and no conversion to human SD or solving time is performed.

## Encoded identities and implementation checks

Scheduled practice guarantees an explanation opportunity when enabled and a contact exists. Mixed and tracked guided-session frequencies are therefore equal by construction; this fails to explain endogenous teaching frequency. Equal base scheduled practice plus nonnegative content/helper additions partly encodes a practice advantage. Knowledge only increases, incorrect content grants no direct bonus, and diagnostic exams do not directly change competence. These are assumptions, not discovered human mechanisms.

No checks or zero update rate must produce zero quality changes. Disabled hints must produce no tutoring content or content/helper learning. Initial knowledge, trait draws and semantic streams are shared across paired arms. Raw logs, completion hashes, source hashes, run identities and time/gain accounting are audited before analysis. Frozen E16 sources must remain byte-identical. Defects require a new corrected run identity; scientific mismatches require a stated mechanism hypothesis, not post-outcome coefficient searches. Keep all contrary results.

## Development review and adjustment rule

Before opening confirmation, record whether identities and audits pass, which patterns agree/disagree, and whether the cause is a software defect, protocol mismatch or unsupported assumption. All predeclared arms remain in confirmation regardless of their signs. A single practice episode and voluntary dialogue are predeclared design adjustments grounded in the human protocol, not selected winning configurations. A new engine mechanism, if warranted, needs a separate specification, tests and lock; it must not replace these results.
