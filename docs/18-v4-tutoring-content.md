# A29: tutoring activity, content, helper learning and observed quality

Authorized by the user's 2026-10-01 request. Separate engine/settings/configuration
forks preserve all A22–A28 source locks. Defaults are uncalibrated assumptions.
Teacher capacity, adaptive instruction, helper rewards and future-exam utility are
outside this amendment. No universal sign or empirical validation is promised.

`TutoringParams`, `simulate_tutoring`, `validate_tutoring_log` and
`python -m classroom_swarm.tutoring_config template|validate|run` are the interface.
Every old parameter remains declarable. New initial distributions are teaching
skill (N values), directed source quality (N*N values) and task difficulty (items
values). All support A28's bounded distribution types. Task difficulty is drawn
afresh each homework from the declared specification, shared across students.

The three explicit activity protocols are:

* `legacy_hint`: delegate to the unchanged A28 engine, with byte-identical shared
  raw tables and old manifest. Extra declarations are inactive.
* `joint_practice`: a successful hint request becomes a committed guided practice
  session, occupying requester and helper for `guided_practice_ticks`, after the
  usual request time. The requester practices during explanation and produces its
  own packet. There is no unconsumed peer hint. Optional AI tutoring remains A28.
* `shared_practice`: schedule a practice block at tick zero every homework, with
  each student attempting the same content while optionally explaining to peers.
  Each learner samples a contact using frozen closeness and private quality beliefs;
  explanations are simultaneous. Outside this block the old homework policy runs,
  with optional peer hints disabled to avoid double-counting the intervention.
  Disabling `allow_hint` means scheduled independent practice of equal duration.
  This explicitly changes task structure, not a coefficient fitted to an outcome.

For item difficulty d, competence k implies item retrieval probability
clip(k+.5-d,0,1). Retrieval and explanation draws use independent semantic streams.
An explanation is correct only if the helper retrieves it and successfully
explains it (declared teaching skill). Its learner contribution also requires a
previously unresolved item and readiness clip(1-max(0,d-k)/band,0,1). This minimal
item-content model permits complementary knowledge at equal aggregate K, but is
not persistent topic mastery or a model of Sudoku strategy.

Guided practice uses the old base practice fraction alpha/attempt_learning_divisor,
multiplied by 1+content_learning_multiplier*mean(usable novel content). Correct
content can assist current performance without being copied. Helper retrieval and
explanation earn alpha/helper_learning_divisor*mean(correct novel explanation),
only for an actual completed activity. Shared helpers average their completed
explanation opportunities rather than obtaining unbounded rewards per group member.
Simultaneous learning commits from a frozen pre-completion state; base and helper
fractions combine multiplicatively against remaining headroom. Time and learning
fractions are separately declared, as in A28; duration sensitivity is mandatory.

Directed private quality beliefs update only after an explanation the learner
personally receives, using the correctness fraction on items with observed
worksheet checks. `quality_check_probability` is an explicit observable feedback
channel; zero disables all quality updates. No latent K or true K increment enters
policy. Availability remains separate and updates only on delivered requests.
The graph/closeness never update. Grades/exams retain the previous information
boundary. Content and quality diagnostics are researcher outputs.

Encoded identities: learning is nonnegative and bounded; wrong/unready explanations
have no direct content bonus; copying grants no direct K; observed checks never
grant K; zero communication isolates unchanged students from changed peers. These
constraints are not discoveries. Stronger peers can improve conditional content
quality, but uptake, time costs, helper displacement, task difficulty and copying
can reverse total effects. Scheduled positive guidance at equal base practice
partly encodes a benefit; the grouping contrast still changes who helps whom.

Streams: A28 1–119 unchanged; task difficulty 120, source-quality initialization
121, teaching skill 122, item retrieval 123, explanation success 124, observed
checks 125. Streams are indexed by seed, replicate, homework, start tick, student,
item. Source retrieval uses provider index; item content is common across arms.
New logs: `tutoring_content`, `quality_feedback`, `initial_quality`,
`task_content`, `learning_components`. Existing events/packets/request/feedback
schemas remain available. A dedicated validator audits occupied intervals,
packet lineage, bounded learning and observable quality updates.

E16 must freeze sources/configurations before inspecting outcomes. Run all declared
comparisons and ablations, then a separate untouched seed set. Repairs need a new
run identity and explicit explanation; no sign-only coefficient tuning. The lab
comparison is a directional mechanism probe, not an effect-size replication.
