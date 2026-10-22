---
type: specification
updated: 2026-10-07
status: implemented-A32
---
# A32: effortful learning and study protocols

The user approved implementing the design in `docs/22-proposed-effort-learning-incentives.md`. This specification identifies the implemented separate A32 fork. The proposal and all A22–A31 engines, experiments and locks remain historical evidence. Defaults below are numerical hypotheses, not estimated human effects. Human calibration and field-study fitting remain deferred.

## Interface and compatibility

`simulate_effort(p, graph, draws, condition, initial, teacher, mechanisms, extensions)` lives in `v4_effort_learning.py`. `effort_settings.py`, `effort_runtime.py`, `effort_validation.py` and `effort_config.py` supply declarations, physics, audits and execution. `extensions` has four independently enabled branches: `learning_process`, `teacher_work`, `helper_contract`, `test_preparation`; `student_ids` declares stable global nonnegative integer identities. Every branch defaults off. All four off delegates directly to A31, preserving every manifest and raw table exactly, including A31's own A30 fallback.

Active A32 uses stable student draws and separate protocol assessments. These common infrastructure changes are part of the version comparison. With `learning_process=false`, legacy completed-attempt/helper learning and post-learning response mapping remain explicit controls; the effort-gate replacement applies when it is enabled. Partial teacher work and new concept/format activities have their declared dose mechanics. Do not attribute a combined A31-to-A32 difference to one new mechanism.

An enabled helper contract requires scarce helper time and joint practice. `teacher_work` requires an enabled teacher and replaces A31 workload/incentive branches; simultaneous declarations are rejected. A31 topic transfer and private checked peer observations remain available. A32 does not change the social graph or use the derived answer-flow graph as state.

JSON schema 2 accepts all existing declared parameters, initial distributions, network, teacher and A31 mechanisms plus `extensions`. Strict unknown-field, dimension, probability, resource, form and share validation precedes execution. Conditions may override declared fields; the resolver freezes every default, realized identity list, exam design, form transfer/state and checkpoint schedule before a run. Exact initial lists can encode a correlated cohort; unsupported correlation keywords are rejected. To reassign a cohort between sections, keep global IDs and remap exact initial lists and pair assignments together.

```
.venv\Scripts\python.exe -m classroom_swarm.effort_config template --output configs/my-A32.json
.venv\Scripts\python.exe -m classroom_swarm.effort_config validate configs/my-A32.json
.venv\Scripts\python.exe -m classroom_swarm.effort_config run configs/my-A32.json --output runs/my-A32-r1
```

Existing output directories are rejected. Each run freezes specification, all engine sources, tests, resolved settings, software and semantic stream codes before simulation, then saves all raw tables and per-file hashes. Scientific comparisons still require a separately frozen plan and contrasts. A32 functional diagnostics are mechanism checks and cannot establish external validation.

## Learning, task performance and costs

Student traits have independent declared distributions: learning efficiency/effort aversion from existing initial declarations, plus attention, distraction probability, fatigue sensitivity, initial fatigue, future-test utility and helper reward preference. Cognitive effort is chosen from a declared grid `[0, .5, 1]`. The policy uses private confidence, benefit/access/quality beliefs and released grades; physics alone reads latent knowledge. A teacher cannot read student fatigue, latent knowledge or unreleased item outcomes to plan.

For an attended activity, distraction is a Bernoulli shock, then

`attention_probability = clip(attention + attention_effort_weight*effort - fatigue_sensitivity*fatigue - distraction, 0, 1)`.

Attention and processing use distinct private draws. Processing probability is `correct_content_quality * readiness`, applied once. Dose is `effort * duration/reference_ticks * attentive * processed`. Fraction learned is `1 - (1 - min(1, alpha/source_divisor)) ** (source_multiplier*dose*concept_share)`, with explicit zero-dose and full-efficiency limits. The default reference is three ticks, attempt divisor three and helper divisor six. Efficiency changes productive-dose conversion; it is not removed or increased to amplify AI effects.

Independent study has explicitly available corrective materials (default quality .8), or self-generated reasoning (default .1). Material access and corrective feedback are separate switches. With both useful channels zero, an attempt has no learning even if time was spent. Received score feedback alone changes beliefs, never competence. AI tutor receipt alone has no learning; its content is used during a later effortful attempt. Copied peer/AI answers grant no direct learning. Teacher and helper explanations can fail due to incorrect content, prerequisites, attention or processing. Already mastered competence has zero remaining gain.

Attempt item responses use knowledge captured at activity start, effort and assistance; the resulting learning cannot improve the same packet retrospectively. Supported performance is `K + assistance*(1-K)`. Execution is `effort + (1-effort)*assistance`, and response probability is `guess + execution*(supported-guess)`. Default guessing is zero; unaided zero-effort solving gives zero performance. Actual assistance may carry some performance at zero cognitive effort, without giving learning. Feedback/material processing occurs after response generation within the same recorded activity, with no second unpriced learning opportunity.

Study utility prices expected performance, explicit future-test value, marginal helper reward, cognitive cost and fatigue cost. Predicted unaided performance rises with effort. Listening forecasts the forthcoming practice opportunity; a positive cost or failure can still yield no learning. Costs are paid at start even if learning fails. Default operational effort .1 is additional to cognitive effort; cognitive effort ticks are multiplied by declared activity costs and effort aversion and divided by the existing effort time scale (12). Default costs are attempt/helper/revision/format 1, guided .75, listening .15, coaching .2, answer copying .1 and tutor receipt .2. All productive costs must be positive; zero individual effort aversion is allowed. Student fatigue rises .01 per effort tick, recovers .5 between homeworks and can recover during rest; rest grants no knowledge. Teacher fatigue remains a separate A31 state when that older workload branch is used.

Raw `effort_choices`, `student_costs`, `student_fatigue`, `material_exposure` and `learning_doses` show predicted choices, paid effort, probabilities/draws, dose, concept/form partition, conversion fraction and multiple zero-gain flags. Attendance is separately recorded, including absent students. Topic gains link to their causative dose event IDs and reconstruct from bounded residual multiplication and declared topic transfer. No background tick or automatic homework increment is added.

In simultaneous shared practice, a student who also explains partitions effort between their own problem and explanation (declared `shared_explanation_share`, default .5). A provider serving several recipients divides the explanation dose among them; total conceptual effort cannot grow with the number of listeners. Joint contract sessions reserve a single helper and recipient. This accounting is part of A32 and leaves historical shared-practice semantics available in the all-off comparator.

## Teacher work and contract

Default work periods are two before-class ticks, the existing student classroom timetable, and two after-class ticks, under one total teacher budget of eight. Mandatory administration and one preparation tick occur before class. Three curricular instruction ticks are protected. Previous homework grading uses available before-class time; remaining grading can occur after class, with grades returned the next day. Teacher actions never overlap. After-class availability is part of the resource declaration, not extra time added after seeing outcomes.

Nominal mandatory work and protected lessons must fit. Validation rejects an infeasible setup unless `allow_instruction_crowdout=true` declares the stress case. Grading cannot displace a protected commitment in the ordinary protocol; remaining grading becomes backlog. Default minimum lesson segment is one tick, and shorter declared protected lessons carry their actual dose.

Topic preparation stock starts at zero, increases by `1-(1-rate)^ticks` on its remaining gap, and is reusable. Default rate .2, skill bonus .3 and decay zero are hypotheses. Preparation changes explanation skill through `min(1, teacher_skill + bonus*stock)`; it never changes student knowledge directly. Benefit zero gives a tax-only control at the same resources. Administration has no such product.

The teacher chooses discretionary guidance/explanation/coaching/follow-up from observed topic estimates, announced exams, declared uptake and productivity beliefs. Default horizon two homeworks, expected opportunities two, expected engagement .7, gain belief .02, format belief .1, belief update rate zero, intrinsic weight .2, linear cost .001 and quadratic cost .002 are hypotheses. Guidance forecasts a later study opportunity and records zero immediate concept gain. Actual guidance changes the subsequent attempt preference/confidence and grants no knowledge by itself. Coaching partitions concept/form dose; follow-up reduces exam access cost at a time cost without learning. A productivity update, if enabled, uses released eligible score improvement over frozen observed baseline; it is an observational belief update, not identification of causal productivity.

One `RewardContract` evaluator serves forecasts and realized payments. Default strength/power/cap/discount one, level rather than gain, eligible-cohort denominator, missing-zero rule, exam weight one/homework zero and one-homework payment delay. Eligible forms can restrict payments. Missing scores remain `None` in observations; a missing-zero rule assigns zero contribution to the contract. Gain mode compares with frozen pre-intervention observed assessment. Forecasts integrate participation uncertainty using the same missing/denominator rules, including exact Poisson-binomial integration for an observed denominator. Delayed amounts remain in backlog at the finite horizon.

`baseline_scores` can declare observed baselines by form; homework gain contracts require such a baseline. Exam baselines otherwise come from a pre-intervention unaided assessment. Forecasts sum every eligible announced form using observed topic estimates, topic transfer and format transfer, rather than projecting an active-topic gain onto an unrelated test. Only administered exam scores enter the teacher observer. For mixed-topic designs, that composite score is an explicitly logged proxy for represented topics; it is not an additional invisible topic test. Format effects can therefore bias a teacher's competence estimate, a declared observation-model limitation.

Teacher records include the work schedule, preparation, resource totals, forecasts, frozen observed baselines, contract evidence/payments and observation/payment backlogs. Teacher identity remains outside student outcomes. This is one teacher and one class, not a multi-teacher school tournament.

## Student-helper contract

Pairs are explicitly declared and frozen; no automatic sorting on hidden knowledge occurs. Pair members are disjoint and may be assigned independently of the graph as an announced seating intervention. Baseline observed scores can be supplied; otherwise pre-intervention unaided assessment freezes them. The declaration fixes eligible form, checkpoint dates, top fraction (.1), monetary prize (1), certificate value (0), preference distribution (1), delay (1), discount (1), winning prior (.1), progress belief (.03), session duration (three ticks), offer ticks (default tick three), helper cost multiplier (1) and recipient acceptance (1).

At a checkpoint, recipients rank by observed unaided score improvement over baseline. Quota is `q * recipient_count`: full positions are `floor(quota)`, plus a separate Bernoulli boundary position for the fractional part. Ties use an independent seeded lottery. Missing recipients cannot win. Payments/certificates arrive after released checkpoint evidence plus declared delay, with no knowledge, skill or friendship change.

Helping decisions use baseline/checkpoint progress and a released cutoff, with a declared marginal progress-to-winning belief. Prize and certificate utility enter the expected marginal benefit of explaining; zero values and an unrelated placebo remove it. The helper's own predicted study value, real time and effort cost oppose helping. An explicit offer may be unavailable or refused; accepted sessions reserve both students, allow separate helper/recipient effort choices, then generate explanation content and learning. High cost, disengagement or bad explanations may eliminate gains. Private access requests remain available separately. Assigned-session offers/acceptances/end records, displaced time, helper gains, recipient uptake and payments are reported separately.

The implementation represents the reward/learning protocol. Friendship/personality changes and verbal dialogue are not represented.

## Test preparation and participation

Format familiarity is separate from conceptual topic knowledge and teacher preparation. Default forms are familiar, novel, unrelated and core, with identity format transfer, zero initial familiarity and no decay. Declared revision, format practice and coaching take actual time/effort. Default format practice and coaching allocate .2 of dose to concepts and .8 to format; revision allocates one to concepts and zero to format. Shares above one are rejected. Format rate .1 and practice duration three ticks are hypotheses.

Exam designs declare name, form, topic weights, difficulty, format loading, stakes and access cost. Default familiar/novel forms test topic zero; unrelated tests topic one if it exists; core balances topics. With only one topic, an unrelated name cannot represent unrelated content, and this limitation must be disclosed. Familiar loading is .5; other default loadings are zero. Item core probability is `clip(weighted_K + .5 - difficulty, 0, 1)`, then `core + (1-core)*loading*F_form`. Concept and form transfer are separate matrices. Zero concept share with zero novel-form transfer gives an encoded zero direct novel/core effect; it is not an empirical discovery.

Exams measure without teaching. Student participation defaults mandatory; the optional decision compares private predicted score times stated stakes with access/effort cost. Teacher follow-up reduces that cost (default .2) without competence gain. The same semantic potential item draws are saved for participants and nonparticipants. Reports keep participation rate, participant-only score, eligible-cohort zero contribution, potential score and underlying competence separate. Nonparticipants receive neither a fake zero observed score nor assessment feedback.

## Semantic randomness and validation boundary

Fixed codes: initial 140, new traits 141, attention 142, distraction 143, processing 144, effort 145 (reserved), exam 146, participation 147 (reserved for a stochastic extension; current participation is deterministic), baseline 148, helper boundary 149, tie 150, acceptance 151, choices/targets/request acceptance/priority 152–155, task/AI items 156–157, retrieval/explanation/checks 158–160, teacher attendance 161, observation coverage/noise 162–163, peer error 164. Keys include master seed, replicate, global student ID and scheduled date/tick/item; no failed gate shifts later draws. Task difficulty and teacher content are classroom-level opportunities. Teacher observation and peer-check error are also keyed to stable IDs. Exact lists refer to declared slot order; IDs do not reorder user-supplied lists silently.

Acceptance tests cover all-off parity, no dose/no gain, failure with costs, pre-learning response, score-only feedback, attention/absence, stable identities, effort-dependent choice, teacher conservation/preparation/protection, delayed consistent contracts, helper offers/refusal/zero/placebo/high cost, format/core separation and unchanged potential tests under participation changes. Raw validation reconstructs learning, topic/format state, time, teacher resources and assessment/payments and rejects deliberate corruptions. Scientific trend direction is never a unit-test requirement.

Functional results and limitations are reported separately in `docs/experiments/A32-functional-results.md`. Further study-specific comparisons must retain E21's contrary cases, distinguish infrastructure, resources and uptake, and use new frozen protocols. No larger AI effect or universal incentive benefit is promised.
