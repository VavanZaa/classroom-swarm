---
type: research-proposal
updated: 2026-10-10
status: proposed-not-implemented
tags:
  - classroom
  - research
  - mechanisms
  - validation
---
# Classroom mechanisms research and implementation options

**Implement a small skill curriculum, improve teachers' forecasts from observations, and add feasible group preparation before adding a more elaborate decision engine.** Then extend voluntary peer practice and make helper learning depend on what the helper actually practices. These changes address the failed pathways found in A32, while allowing benefits, null effects and harms to arise in different settings.

This is a research and design assessment, not an approved specification, implementation or new experiment. Human calibration remains deferred. The proposed parameters below are hypotheses to declare and examine; none is a field estimate. All earlier sources and results must remain intact. The numerical evidence comes from the [A32 assessment](reports/A32-paper-trend-assessment-2026-10-07.md), its [lesson-pathway audit](reports/E22-lesson-pathway-audit.json), and the frozen E22/E22b comparisons.

## 1 Problems that need different mechanisms

| Observed model failure | Candidate explanation from equations and saved actions | What an extension must distinguish |
|---|---|---|
| Tracking helps lower starters but harms higher starters. | Harder lessons reduce teacher correctness and student processing; competence does not represent mastering a new advanced skill. | Useful new content, prerequisites, teacher content accuracy and student readiness. |
| Teacher rewards raise participation but select no coaching. | The planner starts participation at .7, increases it heuristically for followup, and initializes predicted format familiarity at zero. Its forecasts differ from students' access-cost decisions. | Observed attendance response, accumulated preparation, diminishing returns and combinations of actions. |
| One voluntary peer session has an uncertain effect. | Few useful sessions occur; the simulation lacks the lab's shared puzzle and explanatory interaction. | Availability, willingness, joint work and later independent understanding. |
| Helper rewards also improve upper helpers' outcomes. | Explanation grants helper consolidation and can stimulate ordinary helping as well as contracts. | Practicing something new versus repeating mastered content, and displaced own study. |
| Smaller classes help only after a tenfold assumed guidance-cost reduction. | Guidance allocation crosses a sharp choice threshold; otherwise teacher capacity is unused. | Allocation under realistic costs, imperfect information and congestion. |

These explanations are supported model diagnoses, not experimentally identified human causes. Existing topics, attention/effort gates, fatigue, finite teacher time, helper contracts, concept/form preparation and exam participation already exist. Reimplementing those features under new names would not close the remaining gaps.

## 2 What the research supports

| Primary research | Relevant evidence or method | Limit on its use here |
|---|---|---|
| [Duflo, Dupas and Kremer, tracking](https://www.aeaweb.org/articles?id=10.1257/aer.101.5.1739) | Instructional targeting is central to the interpretation of benefits to both starting groups. | Does not establish that tracking benefits every population or that a higher lesson difficulty always increases learning. |
| [Corbett and Anderson, knowledge tracing](https://link.springer.com/article/10.1007/BF01099821) | Estimates mastery of individual procedural rules and selects exercises from those estimates. | An observation and instructional method, not a universal physical law of student learning. Publisher preview consulted. |
| [Kalyuga and colleagues, expertise reversal](https://www.tandfonline.com/doi/abs/10.1207/S15326985EP3801_4) | The usefulness of instructional assistance depends on prior expertise. | Does not supply one optimal difficulty, a universal curve, or numerical coefficients for our population. Publisher abstract consulted. |
| [Koedinger and colleagues, assistance dilemma](https://pact.cs.cmu.edu/pubs/Koedinger%2C%20Pavlik%2C%20McLaren%20%26%20Aleven%20CogSci08.pdf) | Immediate assisted performance and robust subsequent learning are different objectives; assistance choices involve tradeoffs. | More help or less help is not uniformly better. |
| [Glewwe, Ilias and Kremer, Kenyan teacher incentives](https://www.aeaweb.org/articles?id=10.1257/app.2.3.205) | Reward-linked results and participation increased; test preparation increased without corresponding unrelated-exam gains. | Requires the actual participation denominator, reward design and assessment relationship; does not identify the optimal simulated policy. |
| [Muralidharan and Sundararaman, Indian teacher performance pay](https://econweb.ucsd.edu/~kamurali/papers/Published%20Articles/Publisher%20Formatted%20Versions/Teacher%20Performance%20Pay%20%28JPE%202011%29.pdf) | Learning improved in rewarded subjects and also in unrewarded science/social studies. | A contrasting context: an incentive mechanism hardwired to produce only test familiarity would exclude this evidence. |
| [Rafferty and colleagues, teaching through POMDP planning](https://cocosci.princeton.edu/tom/papers/FasterTeachPOMDPPlanning.pdf) | Planning can consider uncertain knowledge and the future consequences of teaching actions. | Demonstrated in concept-learning tasks; a full classroom planner needs additional assumptions and computation. |
| [Kimbrough, McGee and Shigeoka, peer teaching lab](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) | Participants worked on a shared Sudoku puzzle with communication during one ten-minute practice block. | Twenty repeated scheduled blocks do not reproduce that exposure. A shared task encourages interaction without guaranteeing useful teaching. |
| [Smith and colleagues, peer discussion](https://web.mit.edu/jrankin/www/MIST/Peer_Discussion_Smith.pdf) | Later individual concept questions improve after discussion; the evidence also supports learning in groups without an initially correct respondent. | Does not mean every incorrect discussion is productive or that the correct answer must be revealed before learning. |
| [Fiorella and Mayer, learning by teaching](https://doi.org/10.1016/j.cedpsych.2014.01.001) | Preparing to teach and actually explaining can affect subsequent comprehension. | The studied video-teaching task is not a paid peer contract; helper gains depend on activity and outcome. Publisher abstract consulted. |
| [Kornell, Hays and Bjork, unsuccessful retrieval](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/Kornell_Hays_Bjork_2009_JEP-LMC.pdf) | Unsuccessful attempts followed by feedback can improve subsequent learning. | Wrong answers or effort alone are insufficient justification for automatic knowledge credit. |
| [Wu, Zhang and Wang, seating and helper incentives](https://www.aeaweb.org/content/file?id=15848) | Distinguishes seating from rewards based on a partner's improvement, and examines both partners. | A small upper-helper effect is not a rule that forbids helper learning; the relationship outcomes need additional state. |
| [Wilson and colleagues, the 85 percent rule](https://www.nature.com/articles/s41467-019-12552-4) | Derives an optimal error rate for particular classification-learning assumptions. | Does not establish an 85% target for all classroom skills, students or teaching activities. |
| [Reckase, multidimensional item response theory](https://link.springer.com/book/10.1007/978-0-387-89976-3) | Describes item/person measurement with multiple latent dimensions. | A measurement framework, not an activity-dependent learning process. Publisher overview consulted. |

The proposed causal structures below are our inferences from this evidence and the code audit. The studies motivate mechanisms; they do not determine our transition probabilities, time costs or utility weights.

## 3 Comparison and weighting

Ratings use 1–5, where 5 is better. The assessment weights are **causal fit 35%, architecture fit 25%, auditability 20%, implementation simplicity 10%, and directness of evidence 10%**. Causal fit means addressing our diagnosed gap, not evidence of a known treatment effect. These are explicit engineering judgments, not estimated probabilities or model learning/reward coefficients. Related options are often complements rather than substitutes.

| Option | Causal | Architecture | Audit | Simple | Evidence | Weighted / 5 | Decision and principal tradeoff |
|---|---:|---:|---:|---:|---:|---:|---|
| Teacher forecasts from released observations | 5 | 5 | 5 | 4 | 3 | 4.70 | First repair. High compatibility; observing private barriers remains difficult. |
| Small skill curriculum with prerequisites | 5 | 4 | 4 | 2 | 4 | 4.15 | Preferred learning structure. More changes than a scalar patch, but represents advanced learning. |
| Class/group preparation with real resource costs | 4 | 5 | 4 | 3 | 4 | 4.15 | First teacher extension. Must account for reach, feedback and pupil effort. |
| Helper learning conditional on practiced skill | 4 | 5 | 4 | 4 | 3 | 4.15 | Add alongside the curriculum. Cannot assume advanced helpers always gain zero. |
| Shared reasoning and voluntary explanation | 4 | 4 | 4 | 2 | 4 | 3.80 | Next peer extension. Requires numerical task rules, not merely a conversation label. |
| Scalar difficulty and novelty patch | 3 | 5 | 4 | 5 | 2 | 3.80 | Cheap diagnostic alternative. Curve choice could manufacture the desired tracking sign. |
| Item-response measurement alone | 2 | 4 | 5 | 3 | 4 | 3.40 | Useful measurement companion; cannot supply a missing learning mechanism. |
| Always target 85% success | 2 | 5 | 3 | 5 | 2 | 3.25 | Conditional benchmark only; evidence does not justify a universal default. |
| Full belief-state planning engine | 4 | 3 | 3 | 1 | 3 | 3.15 | Defer; start with a bounded comparison of feasible action sequences. |

Equal weights leave the forecast repair first, but move group preparation/helper refinement above the curriculum and tie measurement with shared reasoning. Thus the scores do not establish a uniquely optimal order. Curriculum is an enabling dependency; measurement serves a different purpose. Numerical agreement in scores also does not make options scientifically equivalent. The companion source manifest records ratings and both calculations.

## 4 Learning and instructional targeting alternatives

**Preferred: a small component curriculum.** Start with a declared set of perhaps three to five skills per domain, with tagged items and explicit prerequisites. That size is a proposed prototype, not a research estimate. Keep each student's true component competence separate from the teacher's estimate. Existing topic arrays provide a starting point, but item generation, learning, targeting and assessment need a new optional branch.

A lesson should specify the skill it teaches, required prerequisites, explanatory accuracy and opportunities to practice. An advanced student can then learn an unmastered advanced skill; an introductory lesson can have little remaining value. Teacher subject competence determines content accuracy separately from learner readiness. Teachers can still give incorrect explanations; students can fail to attend, engage or understand. No advanced-content bonus is granted merely because the difficulty number is higher.

Initial component competence must remain configurable: means, spreads, bounds, correlations between skills and relationships with effort/access traits. A higher overall mean alone does not specify which prerequisites a class possesses. Composition experiments should reassign the same declared students and retain global IDs, rather than redraw a new population for each arm.

Use a common, frozen assessment bank and skill weights across the treatment arms. Otherwise changing test weights could create a tracking benefit through measurement alone. A knowledge-tracing observer can estimate component mastery from released item responses, with declared guessing/slip assumptions. An assisted response must have a different observation model from an unaided response; copying a correct answer cannot establish mastery. This adapts the component-estimation idea in [Corbett and Anderson](https://link.springer.com/article/10.1007/BF01099821); it does not require adopting their entire learning law.

**Cheaper alternative: retain scalar competence.** Decouple teacher accuracy from pupil challenge, and add a declared novelty/readiness response to lesson difficulty. This can isolate whether the existing difficulty penalty causes the reversal. It is less suitable as the final structure because one scalar still mixes achievement, content level and learning need. Compare several response shapes and include flat/zero novelty controls; do not choose a shape solely because it makes higher starters benefit.

**Measurement alternative: item-response curves.** These can distinguish easier/harder questions and ceiling effects. They improve how we observe learning, but a measurement curve cannot make an advanced lesson teach a new skill. It should accompany an explicit learning model; [Reckase](https://link.springer.com/book/10.1007/978-0-387-89976-3) provides the measurement framework. A fixed 85% success target can be a policy sensitivity, conditional on its assumptions, rather than a curriculum rule. [Wilson and colleagues](https://www.nature.com/articles/s41467-019-12552-4) concern a specific classification-learning setup.

Do not increase the general learning rate to repair tracking. It also changes AI, peer and teacher comparisons without identifying the content pathway.

## 5 Teacher choice and incentives alternatives

**First repair: consistent forecasts with persistent observed state.** Current actual participation compares perceived score times stakes with access costs after followup. The teacher should predict that same decision through beliefs about confidence and barriers, updating only from released participation and assessment evidence. The teacher cannot read private student costs or hidden competence. If uncertainty over barriers produces a participation probability, use that distribution explicitly. A logistic student choice rule would be a separate behavioral change and would need to agree with the forecasting model.

Persist estimated format familiarity instead of restarting it at zero for every plan. Distinguish conceptual progress from familiar-form success in observations; one composite score is insufficient to identify both. Track which exam or common access barrier followup addresses. An event-specific reminder may affect one exam; transport/access support may affect several. Neither scope should be selected simply to force an unrelated-exam null.

**Add a feasible group preparation action.** Teachers can prepare reusable examples, lead group revision, or coach a familiar test format. Charge material preparation once, class delivery by actual clock time, and feedback/individual attention according to reach and group size. Every pupil still spends time and chooses effort; material receipt alone grants no competence. Reuse existing concept/form states rather than adding another generic learning bonus.

This permits one group session to compete with several followups. It does not automatically favor small classes: broadcast explanation can scale well, while diagnosis and feedback become congested. Record group reach, student engagement and teacher effort to explain any size effect. Kenya's increased preparation sessions motivate the action, but do not establish that simulated teachers must choose it. [Glewwe, Ilias and Kremer](https://www.aeaweb.org/articles?id=10.1257/app.2.3.205).

**Compare bounded planning alternatives.** Evaluate greedy appointments against a fixed mixed policy and a two- or three-action sequence search. Sequence forecasts must update participation, preparation and expected student activity, include saturation, and use the same evaluator as realized rewards. The existing `planning_horizon` scales projections/discounting; it is not already a search over joint sequences. Merely increasing it is insufficient.

Full partially observable planning is a later alternative. [Rafferty and colleagues](https://cocosci.princeton.edu/tom/papers/FasterTeachPOMDPPlanning.pdf) justify considering uncertainty and future consequences, but do not provide a validated classroom transition model. Reinforcement learning would add training distributions, exploration and policy-selection risks; a transparent bounded planner is easier to diagnose first.

Keep transferable conceptual teaching and exam-format practice as distinct options. [Muralidharan and Sundararaman](https://econweb.ucsd.edu/~kamurali/papers/Published%20Articles/Publisher%20Formatted%20Versions/Teacher%20Performance%20Pay%20%28JPE%202011%29.pdf) found positive unrewarded-subject spillovers in India. Therefore neither zero transfer nor pure test coaching should be a universal consequence of incentives. School-level shared rewards, ranking and multiple teachers also require a separately specified school scope; the current single-class teacher contract cannot represent every field contract exactly.

## 6 Peer practice and helper reward alternatives

**Preferred peer mechanism: a shared task with explicit reasoning operations.** Give participants private partial strategies or evidence, a common work product, and actions to attempt, explain, question, compare and revise. A numerical puzzle or finite rule system is sufficient. Correctness must follow the task's rules; combining fragments may solve something no participant initially solved alone. Partial knowledge is a proposed implementation of constructive reasoning, not a mechanism uniquely identified by [Smith and colleagues](https://web.mit.edu/jrankin/www/MIST/Peer_Discussion_Smith.pdf).

Separate explanation quality, recipient teachback and later independent performance. When feedback is available, charge and record it. It is not required that all learning waits for an externally revealed answer: students may reason successfully from available evidence. Conversely, incorrect claims with no useful reasoning or repair earn no automatic gain. Failed retrieval followed by corrective information is a separate productive learning opportunity, consistent with [Kornell, Hays and Bjork](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/Kornell_Hays_Bjork_2009_JEP-LMC.pdf). Diagnostic exams continue to measure only.

For the lab comparison, retain a single shared practice block, voluntary speaking/helping, equal-time solo practice, and the published assessment/incentive sequence. Public baseline ranks must derive from released pretest results, not current hidden competence. This is an explicit observation-protocol addition within a frozen contact arrangement. The [Kimbrough lab paper](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) does not justify forcing a session for every student or setting willingness until a positive effect appears.

**Refine helper learning rather than disabling it.** Credit the helper for retrieval, preparation and constructive explanation of the relevant skill. A mastered introductory skill has limited remaining gain; teaching a less-mastered advanced skill may help. Charge explanation effort and the own study it displaces. Equal-time solo retrieval, preparing to teach, actual explanation and verbatim repetition are useful controls. [Fiorella and Mayer](https://doi.org/10.1016/j.cedpsych.2014.01.001) motivate this distinction, not a guaranteed gain for every helper.

The upper-helper effect in [Wu, Zhang and Wang](https://www.aeaweb.org/content/file?id=15848) must remain an outcome to compare. Turning helper learning off only in that study would encode the target result. Observed partner improvement may reflect prior attainment, ceiling effects, participation or measurement noise; preserve those components separately in reward calculations.

Static reciprocity or a declared prosocial preference is a compatible optional utility hypothesis, but cannot replace the missing task. Friendship formation or endogenous contact weights would change the current static-graph boundary and need a separate model. Language-model dialogue is also a broader alternative requiring reproducible dialogue assessment and policy controls; it is unnecessary for the first numerical mechanisms.

## 7 Compatibility conditions and options to exclude

All recommended mechanisms are compatible **as independently enabled branches in a new model identity**, not edits to frozen A32. Disabled branches must reproduce A32 exactly on shared raw tables. Preserve stable global IDs across regrouping, semantic random streams, synchronous updates, actual time budgets and raw reconstruction of every learning event. Expand logs when state changes, rather than deriving unobserved events from final scores.

| Proposed shortcut | Assessment |
|---|---|
| Increase every learning multiplier or reward until paper signs match | Exclude as a mechanism solution. It changes several pathways and can amplify current helper mismatch. Declared sensitivity analysis remains useful. |
| Give teachers/student policies hidden true knowledge or future outcomes | Incompatible with the information boundary. An oracle can be a labeled upper-bound comparator only. |
| Give knowledge for attendance, payments, copied answers or elapsed time | Incompatible with the approved activity/effort model. |
| Force positive tracking, zero upper-helper gain, or zero unrelated learning | Exclude as evidence. An encoded constraint is an identity, not a reproduced finding. |
| Automatically rewire friendships from successful help | Defer to a separate model boundary; conflicts with frozen exogenous contact weights. |
| Add forgetting and misconceptions immediately | Plausible later extension, but not the first repair of content allocation or forecasts; requires new persistence and error-state assumptions. |
| Use a larger time budget as the whole teacher solution | Retain as a diagnostic only. More unused time does not repair a policy that chooses no useful instruction. |

## 8 Implementation sequence and validation design

1. **Teacher forecast repair:** persistent released-evidence beliefs, consistent participation forecasts and marginal returns. Compare with frozen A32 under identical cohorts and costs; do not retune guidance cost first.
2. **Small curriculum and common assessment bank:** separate content accuracy, prerequisites and learning need. Include flat scalar and fixed-curriculum controls. Refine helper saturation/opportunity costs on the same component state.
3. **Group preparation and bounded planning:** cross each action/policy addition separately before combining them. Reusable material preparation and teacher/student time must reconcile.
4. **Shared peer task:** optional explanation and teachback with observed ranks; compare single-block mixed/tracked/solo practice at equal exposure.

Before runs, declare every distribution, curriculum, observation error, productivity assumption, action duration, utility coefficient, intervention and analysis. Small grids should span plausible alternative mechanisms, including zero/flat controls, rather than search arbitrarily for matching signs. Identify by algebra any contrasts whose direction is encoded. Select settings using explicitly labeled development criteria, retain every candidate and failure, then freeze the selection before fresh-seed comparisons.

Rerun the seven E22 study families to check whether previously supported directions survive. For tracking, report both starting groups and actual skill exposure. For teacher incentives, separate cohort contribution, participation, participant scores, potential scores, concepts, forms and teacher actions. For rewarded help, report both partners, ordinary versus contracted sessions and displaced study. For AI, retain assisted/unaided outcomes and source-specific learning; keep common lesson, practice and review phases explicit. For class size, report guidance counts and congestion, not only final achievement. Peer composition still needs own ability crossed with peer mean/spread under controlled focal students; adding dialogue does not complete that comparison.

Use India as a contrasting incentive consistency check, not a blind holdout: its findings were consulted in this proposal. Fresh seeds test repeatability under chosen assumptions, not external human validity. A future genuinely withheld study or human process data is needed for stronger validation. Neither computational tests nor directional agreement alone justify human effect-size or policy claims.

**Done:** literature review, alternatives, compatibility assessment and recommended sequence. **Waiting:** no required user input for this proposal. **Next:** turn the chosen first modules into a separately reviewed specification and diagnostic design; no engine or setup has changed in this research task.
