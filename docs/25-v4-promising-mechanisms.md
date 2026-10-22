---
type: specification
updated: 2026-10-10
status: implemented-A33
---
# A33 content targeting and observed teacher choices

The user authorized implementing the promising designs in docs/24 and running and analyzing comparisons. A33 is a separate optional fork of A32. Frozen sources and all past results remain unchanged. This specification declares numerical hypotheses, not human estimates; calibration remains deferred. No acceptance test requires a paper's treatment-effect sign.

## Interface and boundary

`simulate_promising(..., extensions=None, design=None)` adds a strict `design` declaration with four independent branches: curriculum, teacher_forecast, group_preparation and shared_reasoning. All off delegates directly to A32 with exact manifests/raw tables. Active branches require A32 productive learning. Teacher forecasts/group preparation require enabled teacher work; groups also require test preparation and improved forecasts. A new schema-3 CLI in `promising_config.py` supplies template, validation, preflight, source locking and execution.

Use `.venv\Scripts\python.exe -m classroom_swarm.promising_config template --output configs/my-A33.json`, followed by `validate configs/my-A33.json` or `run configs/my-A33.json --output runs/my-A33-r1`. Existing output identities are rejected. Every default, source and semantic stream is frozen before execution. `configs/A33-promising-example.json` is a configurable fresh-seeded example, separate from scientific locked declarations.

Curriculum expands each original domain into three configurable skills (foundation, application, advanced). Existing topic arrays carry actual skill competence. Offsets [.25,0,-.25] initialize each domain from its declared population; a bounded centering shift preserves every student's domain mean exactly. An explicit N by expanded-skill matrix overrides this projection and supports arbitrary realized correlations. Domain schedules/assessment weights and cross-domain transfer expand consistently; transfer connects matching levels, not prerequisites. A prerequisite does not grant free transfer.

Prerequisites default [-1,0,1], observed advancement threshold .7, physical readiness width .3. Readiness is `clip((K_prerequisite - (threshold-width))/width,0,1)`; foundations need no prerequisite. The teacher selects the highest level whose prerequisite class estimate reaches the declared threshold, using released per-skill pretests and subsequently administered tagged assessments. A fixed skill or an explicit H-entry level schedule is an independent control. Teachers do not read true competence, current student confidence, fatigue or unreleased answers. Every selected skill and the full observed estimate vector is logged.

Pre-intervention skill tests default to 30 items per skill, with declared coverage/noise; they measure without teaching. They are an additional protocol assumption, not an invisible observation or a recreation of a specific field pretest. Subject accuracy is separate from pupil difficulty: teacher knowledge and teaching skill determine correctness in the new curriculum branch; the old difficulty penalty is a declared control. Student attention/effort/prerequisites still gate learning. Existing efficiency and source multipliers remain unchanged. Competence is updated only for the active skill and explicitly declared transfers; residual mastery limits helper gains for the skill actually practiced.

Homework practices one tagged skill per block. A common frozen assessment bank samples skill tags from expanded domain weights using a separate semantic stream; the same bank is used in both treatment arms. Responses depend on that skill, not the class's lesson choice. Topic means and initial overall competence remain comparable, but the observation/assessment structure differs from A32 and is part of the bundled version comparison.

## Teacher forecasts and group preparation

Teachers persist an expected format state from their own delivered coaching and declared expected engagement, not actual private student processing. Formatted scores are adjusted using that expected state before updating competence estimates. Released participation observations update a confidence-proxy bias; the forecast probability is the normal CDF of announced stakes times estimated confidence minus announced access costs/followup. Uncertainty defaults .15, update rate .2, initial bias 0. The actual student threshold is unchanged. This is an imperfect, observable-data forecasting model, not knowledge of a private student's decision. Predictions, observations, updates and release dates are logged separately.

Group coaching is a new scope of the existing coaching action. Default delivery two ticks plus one feedback tick per up to 30 pupils; all durations/capacities are configurable. The full duration consumes teacher time and reserves each attendee; conceptual/format dose uses delivery time only. Reusable preparation is already paid in A32 before-class work. A group is available only if coaching is an allowed action, preparation exists and its whole time fits. It competes with individual appointments through the same reward contract, intrinsic weight and effort costs. Individual coaching, guidance and followup remain possible; no action is forced. Student listening/effort costs include the full reserved interval.

Planning remains transparent greedy marginal allocation, with updated observed beliefs and saturation within the planned portfolio. Full POMDP/RL planning is deferred. The sequence-search alternative is not claimed implemented. Followup remains a declared common access intervention in this first fork; event-specific reminders are deferred, so unrelated participation can change.

## Shared reasoning

Optional guided/shared sessions can combine two private fragments per item. Fragment probabilities are the square root of active competence; completing both fragments has the corresponding single-person competence probability. A union can yield a solution after an effort-dependent reasoning check even when neither participant initially has both fragments. Explanation correctness combines valid provider explanations and constructive solutions, never a flat group bonus. Existing requests, willingness, refusals, occupied time and quality checks remain in force; no extra session is scheduled. Fractional effort and fragmented evidence use private semantic draws. This is a numerical shared-task proxy, not a language/Sudoku implementation. Copying and payments still grant no competence.

## Randomness and evidence

New codes 170 skill pretest, 171 assessment tags, 172 private fragments, 173 reasoning; they do not shift A32 streams. Stable global IDs follow students across reassignment. Task/exam item tags are common opportunities. New tables record curriculum projection/pretest/choice/readiness, forecast releases, teacher belief updates, format expectations and shared reasoning. Existing raw reconstruction remains mandatory, with tagged test and group delivery checks added.

Functional gates precede study comparisons: exact disabled parity; stable reassignment; no prerequisite/no gain; teacher information isolation; no payment/assessment learning; persistence and saturation; group time/dose conservation; fragment union and zero reasoning; strict dimensions/types/unknown fields; corruption detection. Every experiment locks sources, settings, seeds, comparisons and identities before outcomes. Development and fresh-seed cohorts are reported separately; no outcome-driven fitting occurs in the first comparison.

Done: separate implementation, interface, strict declarations and functional tests. Waiting: E23 execution. Next: the separately frozen E23 default/ablation/study-protocol comparisons; outcomes are reported separately rather than changing this specification.
