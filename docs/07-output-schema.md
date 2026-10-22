---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 07 · Output schema

Canonical outputs are **raw event tables only** (A10, A17). Every derived quantity is computed from them and stored under `derived/`, never treated as truth. Obsidian, Plotly and PyVista read these tables and never define them.

## Rules
1. **No stored paths.** Each self-generated answer set has an `answer_id`. A copier accepts only its first packet, so `routing_events` holds exactly one parent link per copied answer, and the full provenance path is reconstructed from it. A stored `path` could disagree with the log; a reconstructed one can't.
2. **One state convention.** `state_snapshots` holds the **committed post-event state**, with event 0 as the initial state. The pre-state of event $t$ is the snapshot of event $t-1$. There are no `_pre`/`_post` column pairs.
3. **Derived ≠ canonical.** $H^{(h)}$, $H^{cum}$, cascade sizes and depths, brokerage $B_i$, $Z^B$, $C_F$, $\Delta_{GK}$ and flow centralities live under `derived/` and are recomputed from the raw tables (test T13).
4. Every table carries `run_id`, so tables from many runs can be concatenated.
5. **`answer_id` is unique only within a run.** The key for any answer is the composite **`(run_id, answer_id)`**. A replicate's tables hold 36 runs, so a bare `h3-s7` exists up to 36 times. Never join on `answer_id` alone.
6. **`event_id` format:** `init` for event 0, `h<homework>` for homework events (e.g. `h3`), `e<exam>` for exam events (e.g. `e1`). It is unique within a run, and the key across runs is `(run_id, event_id)`. Tables that carry only `event_id` (e.g. `item_outcomes`) can therefore be mapped back to their homework without a join. Added 2026-09-18 because `derive.grades_from_items(item_outcomes)` needs it.

## Canonical tables

| Table | Fields |
|---|---|
| `manifest.json` | `schema_version`, `run_id`, `git_commit` when available, model/stage, replicate, master seed, `rng_scheme`, stream codes, bit generator, `R_max`, package versions, raw/effective parameters, controls, graph family and parameters, topology `edge_hash`, A20 `weight_hash`, $R$, and `q0_mode`; V3 records `model_version="V3"` and individual-$q_0$ mode |
| `graph_nodes` | `run_id`, `student_id`, `community_id` (nullable), `degree` |
| `graph_edges` | `run_id`, `u`, `v` (with $u<v$), `weight` (positive finite fixed contact weight; 1.0 for historical V1/V2 graphs) |
| `events` | `run_id`, `event_id`, `seq`, `event_type` (`init`, `homework`, `exam`), `homework_index`, `exam_index` (nullable), `diagnostic_only`, `exam_updates_confidence`, `exam_updates_effort` |
| `state_snapshots` | `run_id`, `event_id`, `student_id`, `K`, `C`, `E`, `Q_S`, `Q_D`, `Q_C`, `X` (committed post-event; event 0 = initial) |
| `decisions` | `run_id`, `event_id`, `homework_index`, `student_id`, `feasible_S`, `feasible_D`, `feasible_C`, `P_S`, `P_D`, `P_C`, `action` (S, D or C; one column, because with isolate masking the sampled action is always the executed one), `partner_id` (nullable), `grade`, `reward`, `cost`, `copy_success` (nullable; C only), `answer_id`, `root_id`, `depth` |
| `routing_events` | `run_id`, `homework_index`, `round`, `requester_id`, `target_id`, `target_had_packet`, `transfer_success`, `answer_id` (nullable), `root_id` (nullable), `sender_depth`, `receiver_depth` |
| `item_outcomes` | `run_id`, `event_id`, `student_id`, `item`, `correct`, `mode` (`S`, `D`, `copied`, `fallback`, `exam`), `answer_id` (nullable), `root_id` (nullable) |

`answer_id` = `h{h}-s{i}`, one per self-generated answer set (S, D or fallback). A copier's `decisions.answer_id` is the one it received. Exam items have no `answer_id`. `transfer_success` equals `target_had_packet` while the share probability is 1 (§33), but both are kept for the later sharing-probability extension.

`read_table()` remains backward compatible with schema-v1 `graph_edges.parquet`: absence of the A20 `weight` column is interpreted as `weight = 1.0`, which is exactly the historical model.

## V3 canonical additions (schema v3 from A21, 2026-09-20)

The shared tables remain canonical for every model. V3 adds four raw tables; legacy runs write them empty.

| Table | Fields |
|---|---|
| `agent_traits` | `run_id`, `student_id`, `K0`, `alpha`, `kappa` |
| `tie_snapshots` | `run_id`, `event_id`, `observer_id`, `target_id`, `A` for every directed social tie |
| `v3_decisions` | `run_id`, `event_id`, `homework_index`, `student_id`, `decision_mode`, `seeded`, `explored`, `expected_access` |
| `sharing_events` | `run_id`, `homework_index`, `round`, `requester_id`, `target_id`, `target_had_packet`, `share_probability`, `sharing_draw`, `willing`, `capacity_available`, `share_granted` |

`sharing_events` distinguishes availability, willingness and capacity. `routing_events.transfer_success` remains the causal flow truth. `tie_snapshots` records committed post-event beliefs; its initial rows are at `event_id=init`.

## Format and layout (schema v3 from A21, 2026-09-20)
- **Format: Parquet from day one**, written with `pyarrow` (no pandas dependency for writing).
- **Granularity: one set of tables per replicate.** Each replicate's files hold all its runs (6 models × 2 $R$ × 3 topologies = 36), told apart by `run_id`. That's about 1,600 files for a 200-replicate dev grid instead of about 58k. A replicate is also the unit of parallel work, so writes never collide.

```
runs/<experiment_id>/                 (excluded from git and from Obsidian)
  rep0001/
    manifest.json                     shared fields + one entry per run_id
    graph_nodes.parquet   graph_edges.parquet   agent_traits.parquet   tie_snapshots.parquet
    events.parquet        state_snapshots.parquet   decisions.parquet   v3_decisions.parquet
    routing_events.parquet   sharing_events.parquet   item_outcomes.parquet
  rep0002/ …
  derived/                            everything computed from the raw tables
```

`run_id` = `<experiment_id>/rep<replicate:04d>/<family>/R<R>/<model>`, e.g. `dev01/rep0001/SBM/R3/M1`.
