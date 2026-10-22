---
type: diagnostic-results
updated: 2026-10-06
---
# A30 teacher implementation and functional checks

The separate teacher role is implemented and passes its functional checks. A teacher now has a distinct identity, explicit instruction/explanation/corrective-feedback/guidance actions, decisions based on released assessment observations, and a finite budget shared with administration and grading. The teacher never enters student counts, graph nodes, student trait distributions, homework outcomes or exams. This addresses the structural gap in the [historical A29 teacher assessment](../reports/Teacher-role-implementation-assessment-2026-10-06.md).

The [A30 specification](../20-v4-teacher-role.md) defines the new rules and limitations. The [diagnostic plan](A30-teacher-functional-plan.md), complete [JSON declaration](../../configs/A30-teacher-diagnostic.json), engine, tests and [diagnostic script](../../scripts/a30_teacher_diagnostic.py) were locked before diagnostic outcomes in `runs/A30-teacher-functional-r1/diagnostic-lock.json`. Sources were unchanged throughout the diagnostic. No coefficients were adjusted after viewing these results.

## What changed

- Teacher decisions use delayed/partial/noisy observed scores and declared priors. They do not receive current true student competence or current hidden errors. Assisted homework has a configurable observation weight; zero weight prevents copied or assisted grades from becoming competence evidence.
- Whole-class instruction is charged once; individual appointments are charged separately. Student participation, occupied time, completed teaching and unserved requests are recorded. Appointment content must be correct, novel and accessible to grant teacher learning. Teaching provides no homework answer packet.
- Guidance changes confidence and a declared encouragement bonus that is actually read by subsequent independent-practice choices. It grants no direct competence. These numerical channels are assumptions, not calibrated psychological effects.
- Positive-cost grading uses real capacity. Unfinished submissions stay queued, and feedback/public grades become available at the grading completion tick. Earlier choices cannot use them. Fully automated grading returns grades at tick zero and frees teacher time while preserving grade accuracy.
- Shared practice begins after the teacher phase; a displaced session is logged and earns no practice gain. A final grading day returns what fits and preserves the remaining workload queues.
- Disabled teachers reproduce every historical A29 raw table and manifest exactly. All historical engine files and the inspected source locks were preserved.

## Verification

The complete test suite passed: **496 tests**, including **60 new teacher tests**. Checks cover identity exclusion, disabled parity, broadcast and individual capacity, actual grade/observation timing, absent and noisy information, adaptive decisions, usable content, refused appointments, guidance affecting choices, peer/AI interactions, short and long clocks, shared-practice displacement, strict declarations, reproducibility and detection of corrupted raw records.

The declared diagnostic completed **72 simulations**: nine conditions over eight paired seeds, with six students and six homeworks per simulation. Every saved raw table was re-read, its hash verified and its time/information/learning audit replayed. The script verified **226 source entries across nine historical locks**, including E16, E17 and the previous teacher audit. No source hash differed. Raw output and reconstructable summaries are under `runs/A30-teacher-functional-r1/probes` and `runs/A30-teacher-functional-r1/summary.json`.

## Diagnostic outcomes

Values below are averages across eight simulated classrooms. Knowledge and unaided exam scores are on the model's 0–100 scale. Appointments include broadcasts and individual guidance, so one broadcast can reach six students. Ungraded submissions are counted after the closing grading day.

| Condition | Final knowledge | Final unaided exam | Teacher appointments | Completed guidance | Ungraded submissions |
|---|---:|---:|---:|---:|---:|
| No teacher | 53.77 | 53.88 | 0 | 0 | 0 |
| Fixed teacher, manual grading | 54.11 | 54.17 | 10 | 9 | 0 |
| Fixed teacher, automated grading | 53.83 | 54.08 | 30 | 24 | 0 |
| Adaptive teacher, automated grading | 53.86 | 54.10 | 30 | 24 | 0 |
| Zero teaching skill, automated grading | 51.54 | 51.75 | 30 | 24 | 0 |
| Guidance only, encouragement active | 56.31 | 56.52 | 36 | 36 | 0 |
| Guidance only, time cost with zero encouragement | 52.26 | 52.67 | 36 | 36 | 0 |
| Reduced teacher budget, manual grading | 53.90 | 53.79 | 1 | 0 | 17 |
| Adaptive teacher with no observed assessments | 53.67 | 54.08 | 30 | 24 | 0 |

Automation reduced teacher grading from 30 ticks to zero over the six homeworks and increased completed guidance from 9 to 24 and whole-class lessons from 1 to 6. This confirms the resource-transfer mechanism. Its final knowledge was about 0.28 model points below the manual condition: the additional lessons also displaced voluntary practice. More teacher time therefore did not imply a universal net learning benefit in this setup.

Teacher content contributed 0.46 model knowledge points per student in the manual condition and 2.53 in the automated fixed-instruction condition. These are raw sums of the explicitly encoded teacher-learning component, not estimates of the net treatment effect; displaced practice and changed feedback also affect the final outcome. Zero teaching skill produced exactly zero teacher content gain, as required by the rule, and lower final scores despite occupying teaching time.

The isolated encouragement setting increased final knowledge by about 4.05 model points and exam scores by 3.85 relative to equal-time guidance with zero encouragement. This shows that guidance is read and can alter subsequent practice. It does not establish that real guidance has this magnitude or mechanism. Fixed versus adaptive instruction differed little here; the small descriptive difference cannot establish an advantage for adaptive teaching. The overloaded condition retained 17 ungraded submissions after its closing day rather than silently discarding the work.

## What these checks establish

The teacher role now functions through distinct actions, recorded information and conserved resources. Net outcomes retain adverse and weak differences, which is appropriate for a causal simulation. Eight simulated seeds are functional probes, not independent human evidence; these results do **not** establish reproduction of a class-size, tracking or AI-assisted-teacher study.

The main assumptions still needing study-specific assessment are the fixed/adaptive content rule, scalar competence and readiness, encouragement/confidence response, attendance, action order, grading cost and the shared-practice phase convention. Multiple teachers, topic-specific error repair, actual dialogue/counselling, teacher training and field-calibrated workloads remain separate extensions.

For a new editable setup, use [A30-teacher-example.json](../../configs/A30-teacher-example.json). It enables an adaptive teacher and automated grading with a fresh seed; it has **not** been run. Validate or run it with `python -m classroom_swarm.teacher_config validate CONFIG` and `python -m classroom_swarm.teacher_config run CONFIG --output NEW_DIRECTORY`. Existing A29 configurations remain usable through the historical runner; teacher declarations use the new runner.

Progress: teacher fix, full regression suite and functional diagnostic completed; no input pending. Next: declare a study-matched teacher-capacity or tracking comparison, including whether resources are fixed per class or per student, and assess its outcomes without sign tuning.
