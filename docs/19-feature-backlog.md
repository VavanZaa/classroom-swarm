---
type: feature-backlog
updated: 2026-10-10
tags:
  - features
  - classroom
  - validation
---
# Classroom simulation feature backlog

**A34 / bounded-parameter follow-up (2026-10-10):** the audit corrections are [implemented separately](26-v4-policy-repair.md) and assessed in [E25/E26/E27](reports/Plausible-parameter-study-assessment-2026-10-10-reviewed.md). Returned-grade benefits, expected hint service, effective initial-state dependencies and complete policy/curriculum validation are repaired. Unpaid studies no longer inherit teacher rewards; STAR can use the existing individual explanation action under its existing budget. Fitting requires actual teacher/helper activity, uses shared bounded preferences and caps teacher gain beliefs to the physical productivity ceiling. All 731 tests pass; 5,652 saved classrooms, 11,304 hashes and over 5.38 million private benefit/service inputs were audited. Sixteen untouched cohorts match 15 selected mean patterns, with 13 simultaneous matches. Two equivalence checks remain uncertain; single-session lab tracking remains unresolved. AI tutor assisted-practice improvement is smaller than answer AI, opposite the paper's ordering; test tool/content/usage accuracy assumptions before adding a direct AI effect. After-class teacher coaching, full lab/composition protocols and human calibration remain gaps. The fitted values are conditional hypotheses with declared units, bounds and uncertainty, not calibrated human parameters. All frozen sources/results and failed searches remain preserved.

**Priority correction (2026-10-10):** the user requested a deep check and configuration of existing features before more additions. The [existing-mechanism audit](reports/Existing-mechanism-audit-2026-10-10.md) finds disconnected productive-policy benefit beliefs, discarded hint-service probability, effective-initial-state dependency and validator-completeness gaps. Fifteen new audit tests (694 total), 268 fresh configuration-only classrooms and 39 saved E23 history checks passed. Faster observation updates can alter tracking without a new mechanism; other settings remain inactive under the checked policies. Repair/simplify these existing pathways and clarify teacher forecast/disutility units before implementing further planning, peer actions or AI-effect adjustments. The [minimal classroom](../configs/A33-minimal-classroom.json) and [observer sensitivity](../configs/A33-observation-sensitivity.json) examples are validated and smoke-tested; all scientific defaults/sources remain preserved. Human calibration remains deferred.

**A33 update (2026-10-10):** the promising numerical design is [implemented](25-v4-promising-mechanisms.md), with [1,908 audited E23 classrooms](experiments/E23-promising-mechanisms-results.md), 679 passing tests and all prior evidence preserved. Curriculum/prerequisites, observed teacher forecasts, time-accounted group preparation and shared reasoning are available. The [mechanism assessment](reports/A33-mechanism-assessment-2026-10-10.md) records improved higher-starter tracking, a lower-starter tracking reversal, default preparation failure and preserved AI/reward directions. No outcome-driven fitting or human calibration occurred. Remaining gaps include conceptual mastery forecasts between tests, differentiated instruction, bounded planning, observed lab ranks/teachback and full composition protocols.

The remaining gaps from the [study comparison and assumption review](reports/Classroom-study-comparison-and-assumption-review-2026-10-01.md) are recorded here as features, experiment controls and completion checks. The goal is to represent the interventions and learning processes more faithfully, then test whether their predicted patterns agree with the studies. Agreement is an outcome to assess, not an implementation requirement.

**Status:** A32 implements effort-dependent performance and productive learning gates, student fatigue/costs, teacher work/preparation/protected instruction, helper observed-progress rewards, concept/form preparation and exam participation. Its 60 new tests bring the suite to 631 passing tests; all 150 fixed functional classrooms and 11,076 saved hashes passed audit. [Specification](23-v4-effort-learning.md), [functional report](experiments/A32-functional-results.md) and editable `configs/A32-effort-learning-example.json` are available. E22/E22b completed 2,016 study-comparison classrooms; their assessment records both matches and failures. Human calibration remains deferred. A31 adds configurable teacher incentives/effort, preparation/admin bursts/fatigue, persistent topics/transfer/helper consolidation, and noisy/delayed private peer observations. E20 completed 576 functional diagnostics. E21 completed 3,864 study-informed comparisons across seven paper families, thirteen exact historical replays and 571 passing tests; some earlier conclusions are sensitive to the added mechanisms. A30 provides the separate teacher, observed teaching/guidance and finite budget; E18/E19 study-specific class-size/tracking fits remain preserved. A29 provides shared practice and item content; A28 allows declared settings/distributions. **Human calibration is deferred at the user's request.** Other additions remain planned unless described as available. Historical engines and runs remain preserved.

## Feature priorities and study coverage

**A32 study assessment completed:** [E22/E22b paper-trend assessment](reports/A32-paper-trend-assessment-2026-10-07.md) reports all 2,016 audited classrooms and preserved earlier results. F04 supports answer-AI harm and tutor mitigation under three fixed setups, with residual tutor harm. F05 exposes threshold-sensitive guidance, a higher-starter tracking reversal, and followup crowding out test coaching. F06 supports rewarded help but also upper-helper gains. F02's single voluntary block remains uncertain; F07 is still only a partial peer-mean probe. The duplicated exam-cost setup is corrected transparently in a separate run; no engine was changed to force study signs. Computational checks pass; full human validity remains unestablished.

These A32 priorities now have partial A33 implementations: component content, released-evidence participation forecasts, feasible classwide preparation and numerical shared reasoning. E23 shows that implemented mechanisms do not guarantee matching directions. Observed concept estimates can lag actual mastery and stall lower classes; the default teacher policy still favors access followup; the full lab's ranks, task and optional explanation protocol remain gaps.

**Research and options assessment (2026-10-10):** [content, teacher and peer mechanism alternatives](24-proposed-content-teacher-peer-mechanisms.md) compares nine options using explicit engineering weights and fourteen primary research sources. Its promising numerical branches are now implemented in the separate A33 fork and assessed in E23. Scalar patches, measurement-only changes and full planning have different purposes and tradeoffs; full planning, observed lab ranks and richer explanation/teachback remain deferred. The preserved proposal and all frozen A32 results remain unchanged.

**A32 review followed by implementation:** [effort, effective learning, teacher work, helper rewards and test preparation](22-proposed-effort-learning-incentives.md) specified the approved changes, now implemented in the separate [A32 fork](23-v4-effort-learning.md). A read-only E21 audit found guaranteed base gains on all 7,219 bare completed AI-case attempts. Answer AI already reduces practice time by 42.41% and new knowledge by 40.10%; the small total knowledge increment limits the exam difference. The proposal replaces guaranteed attempt credit with productive learning dose, separates attendance from engagement, charges cognitive effort, reviews teacher time/productivity forecasts, and defines observed-progress helper contracts plus conceptual/format preparation and exam participation. No larger AI effect is imposed.

| ID | Feature | Current gap | Priority |
|---|---|---|---|
| F01 | Realistic explanations and feedback | A33 adds effortful complementary-fragment reasoning; language quality, teachback and richer observation protocols remain missing. | Numerical channel available; E23 assessed |
| F02 | Study-matched tutoring protocols | A33 permits shared reasoning without extra scheduled sessions; public ranks and the full single-block task/incentive protocol remain absent. | First; single-block result unresolved |
| F03 | Persistent topic knowledge and helper consolidation | A33 adds component mastery, prerequisites and common tagged tests; curriculum stalls expose lagged concept beliefs and rigid class targeting. | Available; belief/time allocation next |
| F04 | Future-test motivation and worked-example learning | A32 implements effort-dependent work, productive gates, materials and future-test stakes; A31 remains the guaranteed-credit comparator. | Available; E22/E22b assessed |
| F05 | Teacher capacity and instructional targeting | A33 adds observed participation/format state and feasible group coaching. Default effort choices and both-group tracking still fail; bounded planning/differentiation remain absent. | Available; E23 assessed |
| F06 | Helper rewards and helping costs | A33 uses active-skill headroom and constructive explanations with A32 rewards/costs; upper partners still gain and unrewarded helper effort can be zero. | Available; E23 assessed |
| F07 | Controlled peer composition and correlated initial traits | Whole-class spread changes mix own ability with peer composition. | First for composition studies |
| F08 | Forgetting, misconceptions and error repair | Knowledge only increases; incorrect explanations cannot create misconceptions. | Later |
| F09 | Learning from retrieval assessments | Exams measure competence without a retrieval-learning mechanism. | Later, separate assessment mode |
| F10 | Participation and relationship development | A32 has attention/processing and exam participation; friendship/personality changes remain absent. | Relationships later |
| F11 | Exposure, duration and practice opportunity costs | A32 implements effective dose from time, effort and successful processing; human dose calibration is absent. | Numerical accounting available |
| F12 | Protocol and mechanism validation reports | E23 compares exact-cohort A32/A33 and prespecified ablations, separate development/fresh results, activity paths and family intervals; human validity remains unestablished. | Required throughout |

The peer-teaching lab principally motivates F01–F03 and F11; the AI study motivates F04. STAR class size and Kenyan tracking require F05. Rewarded seating requires F06, with F10 needed to examine friendship outcomes. University peer-composition comparisons require F07. The learning studies inform F03, F08 and F09 as mechanism hypotheses rather than fitted coefficients. F12 applies to every comparison. These connections come from the existing review; they do not assert that the studies identified every proposed mechanism.

## Experiments completed against this backlog

[E17](experiments/E17-results.md) completed 3,360 simulations using existing A29 controls for F01/F11, scheduled versus voluntary and single-episode probes for F02, and low/high subgroup, teaching-activity and raw-gain analysis for F12. Eleven of fourteen declared variants had both positive low-starter outcome means; six had all four pointwise intervals above zero. These correlated sensitivity conditions are not independent validations. The complete study pattern was not reproduced: weaker delivery can reverse the teaching benefit, single-block effects remain uncertain, and guaranteed sessions cannot explain endogenous teaching frequency.

The E17 protocol adjustments were declared before outcomes; no engine coefficients were fitted. F01's skill/coverage benchmarking is complete for that design. A31 subsequently adds noisy/delayed checks and persistent topics. F02 public ranks, optional dialogue and explanatory choice remain unimplemented.

[E20](experiments/E20-mechanism-results.md) checks the four A31 channels in 24 fixed setups across six development and 18 fresh replicates, with no outcome-driven selection or tuning. All 576 saved-log/hash audits passed. Grading automation restored teaching time; fatigue reduced quality; explicit transfer improved outcomes; private peer-feedback effects were small under scheduled shared practice. Every null, contrary and uncertain contrast is retained. These are implementation and sensitivity results with assumed rates, not human calibration or field-study replication.

[E21](experiments/E21-study-mechanism-results.md) completed 3,864 audited classrooms across 24 fresh paired replicates without engine changes or outcome-driven fitting. Three of eleven main exam-contrast changes exclude zero under simultaneous intervals: the smaller-class benefit weakens to an uncertain opposite mean, answer-AI harm shrinks, and tutor-versus-answer advantage shrinks. Tracking becomes sensitive to teacher capacity and peer access; a positive exam contrast with no delivered instruction cannot reproduce a teacher-adaptation explanation. Repeated shared practice retains positive lower-starter effects, while the single voluntary session remains uncertain. Seating-only mismatch remains; isolated peer-mean directions with/without copying persist. The new teacher-reward probe raises general scores but lacks the study's distinguishing test-preparation and unrelated-assessment channels. Thirteen exact historical replays and all source checks preserve previous evidence. Full profiles, protocol bridges, time/learning/quality measures and uncertainty remain in the report.

## Tutoring realism and content

### F01 — Realistic explanations and observed feedback

**Available in A31:** coverage, sensitivity/specificity, fixed tick delay, private arrival-based quality updates, topic-specific or pooled quality, and raw true/observed/received/backlogged evidence. Perfect immediate signals match the reference quality rule; absent checks cause no update; delayed evidence cannot affect earlier choices. E20 reports all controls. Configurable delay distributions, third-party observations and language-quality assessments remain separate future work.

Keep the existing ability to declare heterogeneous teaching skill and partial check coverage. Add explicit observation error and feedback delay, so students can receive incomplete, mistaken or late evidence about a source. A private quality belief must update only when its owner actually receives a signal; it must never read the helper's current true competence or the explanation's hidden correctness directly.

Declare skill distributions, check coverage, signal sensitivity/specificity, delay distribution, quality priors and update rates. Save explanation delivery, true item outcome for analysis, observed signal, arrival time and the recipient's belief update as distinct records.

**Completion checks:** perfect immediate feedback reproduces the declared reference behavior; absent checks create no quality updates; delayed checks cannot affect earlier choices. Run fixed-protocol contrasts for skill, coverage, error, delay and quality learning separately, including frozen quality beliefs. Report adverse or inconclusive exam and helper effects as well as exposure and source-selection changes. Existing skill/coverage controls need these benchmarks, not another implementation of the same settings.

### F02 — Optional dialogue and study-matched tutoring protocols

Add separately declared protocol modes for optional asking, offering, accepting, explaining and ending an interaction. Scheduled shared practice remains an explicit comparator. Represent public baseline ranks as observed assessment information, with timing and visibility stated; ranks must not expose current hidden knowledge.

Declare interaction permissions, group size, episode sequence, contact access, rank visibility, task/practice/evaluation schedule and interaction time costs. Record requests, refusals, teaching frequency, participation and time spent by each role. A lab-matched preset should follow the study's individual sequence; the number of experimental sessions across treatment cells must not become repeated learning episodes per participant.

**Completion checks:** students can refuse or receive no explanation, interactions fit the available time, and no permitted interaction is silently counted as learning. Compare mixed, tracked and independent conditions under the same content and resource budget. Evaluate teaching frequency and helper outcomes alongside low-starter gains. Do not call guaranteed exposure a reproduction of voluntary teaching.

### F03 — Persistent topics and learning from explanatory activity

**Available in A31:** persistent per-student topic competence, explicit schedules/item mappings, declared initial values/offsets and transfer matrices, topic-based retrieval, measurement-only topic exams, and helper consolidation independent of recipient novelty. Tests include knowledgeable recipients and zero-transfer controls. E20 reports isolated topics, transfer, preparation, consolidation and combined-module removals. One active topic per homework and pooled student confidence/benefit beliefs remain simplifying assumptions; dialogue and human explanation measures are still absent.

Add topic or strategy competence that persists between tasks, with item-to-topic mappings and explicitly defined transfer. Retrieval success should depend on that state and task difficulty. Separate a helper's own retrieval, explanation effort and elaboration from the recipient's initial lack of knowledge; recipient novelty can affect learner gains without being the only reason a helper learns.

Declare topic count, initial topic distributions, task mappings, retrieval and learning rules, transfer coefficients, explanation effort/quality and helper consolidation rates. Record topic exposure, retrieval, explanatory activity, feedback and subsequent unaided performance. Numerical explanation-quality measures must be named as model proxies, not human language assessments.

**Completion checks:** prior topic learning affects later relevant tasks; unrelated-topic transfer occurs only through the declared rule. Compare equal-time solo retrieval, preparation and explanation, including zero helper-consolidation and zero transfer controls. Test whether helper learning persists when the recipient already knows the material. Learning-by-teaching research motivates the channel but does not supply its numerical rate.

### F11 — Exposure and duration

Add an explicit account of usable practice opportunities during a session. Separate elapsed time, active retrieval attempts, explanation time, repetitions and idle/waiting time. Longer sessions may offer additional practice and displace other activities; neither benefit nor harm should be imposed simply by a duration label.

Declare tick-to-time interpretation when justified, session duration, attempt/explanation costs, practice density and saturation rules. Record completed attempts and time allocation by role.

**Completion checks:** learning changes only through declared exposure and learning rules; total time is conserved, overlapping commitments are rejected and unfinished practice earns no completed-attempt gain. Compare equal-duration/different-content and equal-content/different-duration conditions. The current three-versus-five-tick result is an opportunity-cost diagnostic, not evidence of an optimal human lesson length.

## Motivation and classroom interventions

### F04 — Future assessments and studied answers

**Implemented in A32:** source-attributed productive dose; attendance, attention, effort and processing; self-study materials/reasoning; cognitive costs and fatigue; effort-dependent task performance; future-test stakes and existing explicit AI opportunity limits. A study-specific lecture/practice/review sequence still needs a separately frozen experiment. The learning-efficiency coefficient remains a conversion parameter. No teacher or attempt grants competence automatically, and score-only feedback is not corrective content. The functional controls are complete; new study comparisons remain next.

Add a separately specified expected future-test objective using a student's own observed learning history and beliefs. Distinguish pure answer substitution from reading a worked example and from active self-explanation. Learning from a viewed answer should require the declared study activity and its time cost, rather than being granted automatically to every copied submission.

Declare homework/test weights, planning horizon, perceived learning priors, effort costs, example-study time and learning rates. Record answer provenance, study activity, anticipated benefit and subsequent unaided performance.

**Completion checks:** zero future-test weight recovers the homework objective; pure copying remains a separate limiting case; zero example-learning rate adds no competence. Vary motivation and example learning independently. Reassess both assisted homework and unaided tests, including tutor-versus-no-AI, to reveal how much agreement with the AI study depends on answer substitution assumptions.

### F05 — Teacher capacity and instructional targeting

**Revision implemented in A32:** separate student timetables and teacher work periods under one explicit total resource declaration; protected curricular instruction and infeasible-design checks; partial-lesson dose; reusable preparation with a quality benefit; forecasts of guidance through later study; common predicted/actual contract rules and delayed observed productivity updates. The A31 engine and E21 evidence are preserved.

**Available in A30:** the [teacher specification](20-v4-teacher-role.md) and [functional diagnostic results](experiments/A30-teacher-functional-results.md) implement a separate teacher outside student outcomes; fixed/adaptive instruction, individual explanation/corrective feedback/guidance; delayed/partial/noisy assessment observations; declared attendance; grading/admin/appointment budgets; actual feedback completion timing; and raw queues, time and learning logs. The historical [A29 assessment](reports/Teacher-role-implementation-assessment-2026-10-06.md) identified the missing role and remains preserved. A30 has 60 dedicated passing tests and 72 audited functional runs. Automated grading freed guidance time, while its net learning effect was not uniformly positive. These checks establish implementation behavior, not a field-study match.

**Study comparisons completed:** [E18](experiments/E18-teacher-study-results.md) and [E19](experiments/E19-teacher-study-results.md) completed 5,048 audited classrooms without engine changes. E19's stronger guidance plus longer common student session yields a positive smaller-class contrast; a lower initial knowledge mean with retained teacher-content multiplier 2 yields positive tracking means in both starting halves. The upper-half exam interval remains uncertain and tracking missed its development confidence gate. Teacher-disabled, zero-support-calendar, fixed-curriculum and peer-access controls are reported alongside every rejected setup. Equal guidance time still depends on appointment fragmentation, so it is not an exact null. These are disclosed fits to known study directions; they do not validate the full field mechanism.

**Available in A31:** an observed-only teacher selects feasible discretionary effort and targets under concave/linear/convex rewards, intrinsic motivation and effort costs. Received-score payments have declared timing and no direct learning effect. Preparation/topic switches/admin bursts, fatigue/recovery and skill loss extend the shared budget and grading queues. E20 audits choices, workloads, actual release times and all four combined-module removals. E21 completes separately declared study comparisons: incentives remove the individual guidance behind the earlier class-size advantage, and preparation prevents lessons under the original three-tick tracking budget. A six-tick control restores teaching but leaves higher-starter exam gains uncertain; peer access under the original budget reverses the lower-starter effect. These separate contexts do not establish a full resource-by-peer interaction. The policy is myopic and uses assumed productivity; strategic test preparation, long-horizon payment response and coordinated teachers remain outside the engine. Human calibration is deferred; no conversion of ticks/knowledge to human minutes/test scales is established. Review effort choice and discrete lesson feasibility under a new declared model/run identity, preserving these failures.

Declare class size, total teacher time, service cost/capacity, allocation policy, assessment visibility, curriculum difficulty and fixed/adaptive targets. Record waiting, attention received, chosen instructional content and students' practice exposure.

**Completion checks:** attention never exceeds capacity, zero teacher intervention recovers the specified control, and adaptation uses information available at that time. Class-size contrasts must state whether total resources or resources per student are held fixed. Tracking contrasts should separate peer composition from instructional adaptation. Compare both controls rather than encoding a universal small-class or tracking advantage.

### F06 — Helper rewards and helping costs

**Implemented in A32:** baseline observed eligibility and fixed pairs; unaided partner progress; top-fraction tournament with disclosed quota/tie lotteries; delayed money/certificate utility; expected-reward helping choices; recipient refusal and cognitive uptake; helper burden and displaced own study; the configuration needed for a seating × reward factorial, and completed placebo/zero/high-cost/refusal controls. Payment itself supplies no knowledge. Full study-specific seating comparisons remain next.

Add reward rules tied to observable partner progress, with explicit helping costs and payment or recognition timing. Keep seating, permission to help and rewards as separate interventions. A source-quality belief is not a financial incentive, and rearranging peers alone is not the rewarded-seating treatment.

Declare reward form/value, eligibility, baseline/outcome assessment, progress rule, visibility, payment delay, effort/time cost and reward preference distributions. Record offered/accepted help, helper burden, observed progress, eligibility and actual reward.

**Completion checks:** no reward is issued without its declared observed trigger; zero reward removes the incentive channel; helper time cannot be spent twice. Compare control, seating alone, rewards alone and their combination with the interaction explicitly analyzed. Report low- and high-starter learning, helper outcomes and participation. Friendship outcomes require F10 rather than being inferred from successful help.

## Population and learning extensions

### F07 — Isolated peer mean/spread and correlated initial traits

Extend experiment declarations to keep focal students' own initial state fixed while varying their peers' mean and SD independently. Check feasible bounded distributions and report realized moments; requested parameters do not guarantee identical realized samples. Preserve declared teacher resources and contact rules so their changes do not become hidden composition treatments.

Add optional declared joint distributions or correlations for initial competence, confidence, effort preferences and learning efficiency. Independence remains an explicit comparator. Correlations are hypotheses unless estimated from suitable data.

**Completion checks:** focal states remain identical across paired arms; impossible moment requests are rejected or use an explicitly documented approximation; realized means, SDs and correlations are audited. Analyze exogenous low, middle and high groups and peer mean–spread interactions. Do not describe a whole-class variance change as an isolated contextual peer effect, or convert numerical competence to GPA/IQ without evidence.

### F08 — Forgetting, misconceptions and correcting errors

Add separately controllable retention decay, topic-specific misconception states and corrective learning. Wrong content may be ignored, adopted or corrected according to declared exposure and feedback rules. Forgetting and misconception acquisition are distinct processes.

Declare decay rates/distributions, misconception susceptibility, error persistence, correction effectiveness and feedback timing. Record acquisition, retention loss, incorrect belief adoption and correction separately from ordinary learning gains.

**Completion checks:** disabling these mechanisms recovers the specified monotone-learning control; all competence states remain bounded. Incorrect content cannot create a misconception without exposure, and correction cannot occur before its evidence arrives. Run retention and error-repair contrasts independently; do not assume every wrong explanation causes lasting harm.

### F09 — Retrieval learning during assessments

Create a learning-assessment mode distinct from the historical diagnostic exam. Repeated retrieval and feedback may change topic competence only under this declared mode. A measurement-only exam remains state-neutral.

Declare assessment purpose, retrieval-learning rate, feedback content/timing, test repetition and topic coverage. Record pre-assessment competence, retrieval, learning events and later delayed performance.

**Completion checks:** measurement-only exams leave state unchanged; zero retrieval-learning rate recovers that competence behavior; correctness feedback is separate from retrieval effort. Compare equal-time restudy and retrieval when the protocol supports it. Preserve every historical exam convention.

### F10 — Participation and relationship development

Add optional participation/engagement dynamics and, in a separately specified model, relationship development from experienced interactions. Avoid treating engagement, competence and friendship as the same state. The historical contact graph and closeness remain frozen.

Declare participation priors, response to experienced costs/outcomes, withdrawal/re-entry rules and relationship update rules. Specify whether relationships change only partner preferences or also access: graph rewiring would require a further explicit model amendment. Record invitations, attendance, refusals and privately experienced relationship changes.

**Completion checks:** disabled updates preserve baseline behavior; agents cannot update relationships from unobserved third-party outcomes. Audit participation and relationship changes separately from learning and reward receipt. This extension is needed to investigate friendship formation, not to manufacture it whenever a reward is paid.

## Experiment declaration and validation

### F12 — Compare protocols, mechanisms and outcomes

Every feature must expose its numerical settings and initial distributions before execution, validate them, save resolved values and lock configuration, semantic random streams and source hashes. An experiment setup summary should show the protocol, treatment differences, information available to each role and time/resource budget. A32 declarations are accepted by schema 2; remaining prospective controls are requirements rather than accepted keys until separately implemented.

Add a study-comparison report that records the human sample/intervention/measurement, model counterpart, missing mechanisms and prediction status. Compare teaching frequency, explanation quality proxies, helper outcomes, time allocation, unaided gain and exogenous subgroup effects in addition to final signs. Distinguish model percentage points, human standardized effects and percentile ranks; do not silently convert them.

**Available for teacher studies:** the [E19 comparison and assumption report](experiments/E19-teacher-study-results.md) includes primary sources, exact selected adjustments, failed development gates, fresh uncertainty, raw time/content metrics, paired mechanism contrasts and the [preserved E18 incomplete match](experiments/E18-teacher-study-results.md). It supplies numerical repeatability evidence after known-direction fitting. Independent human calibration and held-out protocol testing remain uncompleted.

**Available across study families:** the [E21 mechanism comparison report](experiments/E21-study-mechanism-results.md) preserves earlier estimates, fresh features-off results, separate legacy-to-joint-practice bridges and matched A31 effects. It reports eleven main paired exam changes with simultaneous intervals, every secondary profile, active-topic/all-topic exams, knowledge and homework outcomes, teacher effort/budget/content, helper activity and private observed quality. Thirteen exact original-seed replays check continuity. Directional agreement without its proposed activity pathway is explicitly insufficient; teacher rewards cannot substitute for student helper rewards or targeted test preparation.

**Completion checks:** contrasts change one declared factor or acknowledge an inseparable bundle; encoded signs are listed as identities. Raw events must reconstruct all reported measures. Fresh random seeds test simulation repeatability, while independent human studies or participant data test generalization. Hold out human evidence from mechanism design where possible; retain null, opposite and inconclusive outcomes with uncertainty. Revise a model under a new identity and reevaluate rather than repeatedly tune until a desired sign appears.

## Next implementation and study sequence

1. The approved A32 mechanisms and functional controls are complete. Run separately frozen study-specific comparisons, retaining E21 failures and separating resources, learning, helper rewards, test forms and participation. Human calibration remains deferred.
2. Add F02 general optional dialogue/rank protocols and study-specific lecture/practice/review schedules. Extend F03 beyond its numerical consolidation proxy only under explicit activity/content rules.
3. Extend F07 controlled cohort/composition comparisons and prospective joint-distribution declarations. Exact lists and stable global IDs already allow fixed correlated cohorts. Student forecasting currently uses declared learning beliefs; learning those productivity beliefs from one's own history remains a separate extension.
4. Run the seating × student-helper-reward factorial using A32, with exogenous eligibility, zero/placebo rewards, high costs and uptake controls. Teacher rewards cannot substitute for this intervention.
5. Add F08–F10 retention, misconceptions, deliberate assessment learning and relationship development under their own declared identities. Exam participation is already implemented in A32.

For each scientific revision, preserve historical locks and freeze the model, protocols, contrasts and analyses before outcomes. Passing implementation checks means the declared mechanism works; agreement with human trends remains a separate result.

Progress: approved A32 fork implemented; 631 tests and 150 saved-data diagnostics passed; historical sources preserved; editable example validated and unrun. Waiting: none. Next: study-specific comparisons with explicit assumptions, retaining failures. Human calibration remains deferred.
