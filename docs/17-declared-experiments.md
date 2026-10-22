# A28: declare an experiment before running it

2026-10-01. User request: all initial distributions, model parameters and numerical assumptions should be declared before an experiment. This extension uses a separate `v4_declared.py` engine, distribution declarations and a JSON experiment runner. Historical sources and locks remain unchanged. The reference configuration reproduces A27/A26 raw tables.

## Configuration interface

The JSON has `schema_version`, `experiment_id`, `seed`, `replicates`, `params`, `initial`, `network`, `conditions`, `contrasts`, `stated_identities` and `notes`. `params` accepts every active inherited model parameter plus newly exposed numerical coefficients and durations. `initial` accepts knowledge, learning efficiency, effort aversion, confidence, perceived control, five separate action-benefit beliefs and two directed access-belief distributions. Network parameters include ER/WS/SBM topology, degree, rewiring, community ratio, explicit community sizes and frozen friendship-weight distributions. Each condition may override `params`, `initial` and `network`. Unknown fields and invalid declarations are rejected before simulation.

Initialization supports `constant`, `normal`, `truncated_normal`, `lognormal`, `uniform`, `choice` (with weights) and `values` (exact values in student-id order). Knowledge, confidence, control and benefits must stay in [0,1]; access beliefs must be strictly positive and at most 1; learning efficiency must be positive and effort aversion nonnegative. Unbounded distributions are rejected for bounded states; use truncated normal. Lognormal `mean` is arithmetic mean and `log_sd` is standard deviation in log space. Initial confidence and benefit beliefs can explicitly use `from_knowledge`. Other traits are independent unless exact values or knowledge links are declared.

JSON uses one authoritative declaration for initialization: legacy scalar aliases `K0`, `K0_sd`, `alpha`, `kappa`, `alpha_log_sd`, `kappa_log_sd` and `benefit_prior` belong in `initial` as distribution declarations, not in `params`. Python callers can still use these compatibility fields on `DeclaredParams`; explicit `initial` declarations override their defaults. Per-run manifests retain those internal compatibility fields for engine validation, but the resolved lock and actual initial-state tables are authoritative for the distributions used.

`grade_shortfall` (0 to 1) and `grade_satisfaction` (-1 to 1) can also be initialized explicitly. Initial access `values` lists have `N*N` entries in row-major requester/provider order; self entries are ignored during interaction. Exact friendship-weight lists follow the graph's sorted canonical edge order and must fit every replicate. Friendship weights are frozen, then multiplied by the existing closeness variation; set `closeness_spread=0` to use exactly the declared weight distribution.

| Distribution kind | Required fields | Interpretation |
|---|---|---|
| `constant` | `value` | Everyone receives one value |
| `normal` | `mean`, `std` | Unbounded normal, accepted only for states whose support permits it (or zero spread) |
| `truncated_normal` | `mean`, `std`, `low`, `high` | Normal conditioned to lie within the bounds |
| `lognormal` | `mean`, exactly one of `std` or `log_sd` | Arithmetic mean and standard deviation, or log-space spread; a zero mean requires zero spread and gives zero effort only |
| `uniform` | `low`, `high` | Equal probability across a range |
| `choice` | `values`, optional `weights` | Draw from listed values, with optional probability weights |
| `values` | `values` | Exact values; no sampling |
| `from_knowledge` | none | Confidence or a benefit belief equals that student's sampled knowledge |

Changing knowledge therefore also changes default confidence and default benefit priors; declare them independently to remove that coupling. Truncated-normal location and spread are the *underlying* normal's parameters, not exact sample moments. All means/rates are assumptions, not calibration.

## Workflow

1. Generate a complete editable default file with `python -m classroom_swarm.experiment_config template --output configs/my_experiment.json`.
2. Edit the file; declare conditions and any contrasts. Validate and inspect fully resolved settings with `python -m classroom_swarm.experiment_config validate configs/my_experiment.json`.
3. Run with `python -m classroom_swarm.experiment_config run configs/my_experiment.json --output runs/my_experiment`.

The runner validates every condition before starting, refuses an existing output directory, and writes a resolved `lock.json` with source hashes, declared contrasts/identities, seeds, software versions and all defaults *before* executing simulations. Per-replicate outputs contain raw Parquet tables, a manifest, actual initial state and hashes; a CSV inventory reports completion. Graphs and semantic randomness are paired across conditions when the declarations match. Graphs remain static throughout a run. Configuration changes never silently edit previous experiments.

The editable files `configs/experiment-defaults.json` and `configs/high-knowledge-class.json` demonstrate a complete declaration and a high-starting-knowledge class compared under no AI, answer AI and tutor AI. They declare 100 replicates; only temporary small verification runs have been executed as part of implementing this feature.

## Numerical coefficients newly exposed

All earlier active controls remain in `params`. The additional settings cover:

- `peer_request_ticks`, `peer_hint_ticks`, `peer_answer_ticks`, `request_timeout_ticks`, `wait_ticks`, `submit_ticks`: time spent requesting/helping, how long to retry, waiting and submitting. A final wait can be shortened to the remaining time; other activities must fit completely.
- `max_ai_uses`: consultations allowed per student per homework (0 disables consultation).
- `effort_time_scale`: denominator translating ticks into effort cost; separate from the homework deadline.
- `attempt_learning_divisor`, `helper_learning_divisor`: scale knowledge gain from own attempts and explaining.
- `hint_learning_multiplier`, `hint_performance_multiplier`: scale a hint's lasting learning effect and its immediate answer-performance effect.
- `perceived_hint_boost`, `hint_learning_value_multiplier`: students' presumed hint benefit and optional intrinsic learning bonus.
- `peer_hint_base`, `peer_hint_knowledge_weight`: actual peer-hint strength as base plus weight times provider knowledge; their sum cannot exceed 1.
- `reciprocity_reference`: access-belief level treated as neutral in the helping decision.
- `peer_attempt_credit`, `tutor_attempt_credit`: share of assisted-grade reinforcement credited to own work; the complement goes to the peer hint or tutor.
- `submit_value`: score used for submission.

Distribution changes and these coefficients do not create new information channels: students still cannot read current errors or others' hidden knowledge. A provider's knowledge only determines the effectiveness of a hint after selection.

## Scope and constraints

The declaration covers numerical assumptions in the present model: task and exam sizes/schedules, durations, feedback, choice, learning, helping, source choice, AI, population and network. Structural meanings stay explicit: item outcomes are binary; knowledge is bounded to [0,1]; activities have integer tick durations; an assignment starts with no packet, hint, pending request or returned grade; feedback costs no practice time; copied answers grant no learning. These are model rules, not unexplained tunable constants. `allow_check` must remain false. The current semantic tensor extent limits an episode to 32 ticks. A different mechanism requires a separately documented engine change.

Contrasts declare `kind` as `single_parameter` or `bundled`; the runner verifies the number of differing resolved settings. Bundled contrasts must include a reason and cannot identify their separate components. Each contrast also declares `identity` or `not_identity`; an identity needs an explanation and is recorded before the run. The runner produces raw data, not automated empirical claims or significance tests.
