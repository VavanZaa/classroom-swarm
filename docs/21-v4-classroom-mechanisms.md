---
type: model-specification
updated: 2026-10-06
---
# A31 — Teacher incentives, workload, persistent topics and peer observations

The user authorized these four extensions and explicitly deferred human calibration. This is a separate A30 fork, not a rewrite of the frozen engines or E18/E19. All four feature branches are independently enabled in `mechanisms`; defaults disable them and delegate to A30 with byte-identical raw tables/manifests. Numerical rates remain declared hypotheses. No desired study sign is an implementation requirement.

## Interface and scope

`simulate_mechanisms(params, graph, draws, condition, initial, teacher, mechanisms)` retains A30 activities, copying/AI provenance, private student beliefs, separate teacher identity, fixed graph, time reservations and grading queues. Enabled features require joint/shared practice. Teacher incentives/workload require an enabled teacher; topic/peer features can run without teaching. `mechanism_config` extends the teacher JSON declaration with four nested setting objects and condition overrides. Resolve and validate every setting, topic shape/schedule and network before execution. Save resolved settings, initial topics, sources and streams before outcomes.

This version adds numerical teaching decisions and skill states. It does not add language dialogue, forgetting, misconception acquisition, relationships, coordinated multiple teachers, student financial rewards or a human time/test-scale conversion.

## Teacher incentives

The teacher chooses discretionary teaching effort and broadcast difficulty from observed assessment estimates, own declared skill/knowledge and a declared learning-productivity belief. Candidate targets are a fixed difficulty grid plus the observed class mean. Candidate effort is every feasible integer teaching budget after mandatory work. Existing action priorities and recipient allocation remain declared separately.

For each candidate, replay `plan_teacher` using that budget/target. Predicted content usefulness uses teacher-known estimates in the same correctness/novelty/readiness geometry, not true student competence. Predicted score gain is `belief_gain_rate × useful_fraction × learning_multiplier × (1-estimate)`. Guidance has a separate declared anticipated gain; it grants no direct competence. Clip predictions to [0,1]. Expected utility is intrinsic predicted mean gain plus `reward_strength × mean(after^reward_power - before^reward_power)`, minus linear teaching-tick cost and quadratic normalized effort cost. Fatigue can increase the linear effort cost. Ties prefer less effort, then targets closest to the observed mean, then lower difficulty. Zero effort is feasible. Every candidate, estimate vector, utility and selected plan are logged.

Reward power below/at/above one represents concave/linear/convex score rewards. Actual reward is calculated from assessment signals received by the teacher and paid after a declared homework delay; missing signals receive no fictitious score/payment. Payouts are financial logs, not student learning increments. This initial teacher uses a known contract/productivity belief rather than learning a reward-response model from payments. Incentives may alter effort and targeting; improved scores are not guaranteed.

The [Duflo–Dupas–Kremer tracking paper](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf) motivates representing reward curvature, effort and teaching level together. Its actual reward/effort process is not identified by this simulator. [Glewwe–Ilias–Kremer](https://www.nber.org/papers/w9671) also motivates caution about incentives and measured tests. This fork does not yet represent test-specific cramming distinct from general skill.

## Workload and fatigue

Keep A30's shared teacher budget and actual grading-feedback completion times. Additional workload declares per-homework admin bursts, preparation ticks and topic-switch preparation. These mandatory arrivals enter the admin backlog, so unfinished work persists and can delay appointments/grading. Log each arrival component and the ordinary queue accounting. Closing H+1 adds no new admin/preparation.

Fatigue is bounded [0,1]. At each homework start recover the declared fraction of prior fatigue. Actual mandatory work then adds `fatigue_per_tick × workload_ticks`; teaching quality becomes `base_skill × (1-quality_loss × fatigue_after_workload)`. Actual teaching ticks add fatigue before the next homework. Skill is constant within that homework. This is an explicit workload proxy, not a medical/occupational model. Admin, preparation, grading and teaching consume one budget; fatigue does not create additional time. Disabling fatigue coefficients preserves the duration mechanism. Recovery does not alter student knowledge.

## Persistent topics

Each student has a bounded competence vector, one element per named topic. Initial topic values can be declared as an N×T matrix; otherwise declared topic offsets are added to scalar initial knowledge and clipped, with realized moments saved. Homework has one declared active topic, covering its items; a schedule of length H is explicit or the topics cycle. Student decisions retain pooled confidence/benefit beliefs; retrieval, explanation usefulness and learning use the active topic's competence. Teacher estimates are separate per topic, updated only by released observed scores.

At a completion tick, compose A30 practice/content/helper/teacher learning fractions synchronously on the active topic. Apply that same composed fraction to other topics only through the declared transfer matrix: `K_target += (1-K_target) × fraction × transfer[active,target]`. Diagonal entries are one; default transfer is identity. No exposure and zero cross-transfer leave unrelated competence unchanged. Record before/after/fraction for every affected topic. Official student K is the arithmetic mean across topics, with active competence recorded separately; events and activity component rows refer to active-topic competence.

Homework grades concern its active topic. Measurement-only exams balance items across topics, record every item topic/probability/outcome and topic score, and publish the all-item mean as the exam score. Teacher observers receive topic-specific exam scores after the ordinary release delay. Exams grant no learning. Aggregate K is a mean over topics whereas an exam with indivisible item counts uses its realized item weights; both are declared, not silently equated.

Optional helper consolidation adds a declared learning fraction for completed explanatory activity based on the provider's correct-content fraction, independently of recipient novelty. It respects existing explanation time and can operate with legacy helper-novelty learning disabled. Zero consolidation recovers the old helper rule. This is a numerical explanation proxy, not natural-language quality.

## Peer observations

Direct recipients privately observe checked explanation items. Existing check coverage is multiplied by declared additional coverage. True correctness is hidden from policy; observed bits are generated with declared sensitivity/specificity using a new semantic stream. Save true checked correctness for research separately from the received signal. Queue signals for a declared tick delay, including across homeworks. Update a source-quality belief only when the signal arrives; absent checks cause no update. Signals arriving after H remain an explicit backlog.

Quality can be topic-specific or pooled. Source selection and perceived guided-practice usefulness read the currently available quality belief, retaining A29's declared targeting/update rates. No third-party/global reputation, current hidden competence or future signal is available. Graph contacts stay static. Perfect immediate signals and pooled beliefs recover the old quality-update rule within the declared active model; all features off recover A30 exactly.

## Streams, raw evidence and required checks

Historical streams remain unchanged. Stream 134 generates peer-observation error, indexed by seed/replicate/homework/start/recipient/item. Topic scheduling/initial offsets, workload and incentive enumeration are deterministic declarations. Exams retain their semantic uniforms with explicit topic assignment.

Add raw initial/current topic states, topic learning, exam items/topic scores, peer signals/arrivals/backlogs, teacher runtime settings/workload arrivals/fatigue, incentive candidates/choices and reward records. Reconstruct competence, time, observed beliefs and teacher policy from these records. Never book payment or guidance as direct learning. Required tests cover disabled parity, topic isolation/transfer, measurement-neutral exams, bounded initial declarations, helper consolidation with knowledgeable recipients, signal coverage/noise/delay/backlog, quality read by choices, feasible incentive decisions, no hidden-state policy input, delayed payment, workload conservation, topic-switch preparation, fatigue/recovery, static graphs, serialization and corruption detection.

Functional diagnostics compare switches and single-setting controls on paired semantic draws. They report signs and uncertainty without tuning or human calibration. Reward arithmetic, nonnegative topic learning/transfer, capacity limits and fatigue quality penalties are encoded identities; net exam/group effects are outcomes.

Progress: mechanism interface and equations declared; no input pending. Next: implementation, tests, frozen diagnostics and source/raw audits.
