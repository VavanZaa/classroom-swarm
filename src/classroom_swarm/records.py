"""Canonical in-memory run records (docs/07, docs/09 records.py). No scientific logic here.

The engine emits rows through `append_row`, which rejects any row whose columns differ from the
frozen schema, so the log structure can't drift from docs/07.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TABLES = ("graph_nodes", "graph_edges", "agent_traits", "events", "state_snapshots", "tie_snapshots",
          "decisions", "v3_decisions", "routing_events", "sharing_events", "item_outcomes")

COLUMNS: dict[str, tuple[str, ...]] = {
    "graph_nodes": ("run_id", "student_id", "community_id", "degree"),
    "graph_edges": ("run_id", "u", "v", "weight"),
    "agent_traits": ("run_id", "student_id", "K0", "alpha", "kappa"),
    "events": ("run_id", "event_id", "seq", "event_type", "homework_index", "exam_index",
               "diagnostic_only", "exam_updates_confidence", "exam_updates_effort"),
    "state_snapshots": ("run_id", "event_id", "student_id", "K", "C", "E", "Q_S", "Q_D", "Q_C", "X"),
    "tie_snapshots": ("run_id", "event_id", "observer_id", "target_id", "A"),
    "decisions": ("run_id", "event_id", "homework_index", "student_id", "feasible_S", "feasible_D",
                  "feasible_C", "P_S", "P_D", "P_C", "action", "partner_id", "grade", "reward", "cost",
                  "copy_success", "answer_id", "root_id", "depth"),
    "v3_decisions": ("run_id", "event_id", "homework_index", "student_id", "decision_mode", "seeded",
                     "explored", "expected_access"),
    "routing_events": ("run_id", "homework_index", "round", "requester_id", "target_id", "target_had_packet",
                       "transfer_success", "answer_id", "root_id", "sender_depth", "receiver_depth"),
    "sharing_events": ("run_id", "homework_index", "round", "requester_id", "target_id", "target_had_packet",
                       "share_probability", "sharing_draw", "willing", "capacity_available", "share_granted"),
    "item_outcomes": ("run_id", "event_id", "student_id", "item", "correct", "mode", "answer_id", "root_id"),
}


def empty_tables() -> dict[str, dict[str, list]]:
    return {name: {column: [] for column in COLUMNS[name]} for name in TABLES}


def append_row(tables: dict[str, dict[str, list]], name: str, **row) -> None:
    expected = COLUMNS[name]
    if set(row) != set(expected):
        missing, extra = set(expected) - set(row), set(row) - set(expected)
        raise ValueError(f"{name}: row columns differ from docs/07 (missing {sorted(missing)}, extra {sorted(extra)})")
    columns = tables[name]
    for column in expected:
        columns[column].append(row[column])


@dataclass
class RunLog:
    run_id: str
    manifest: dict                                   # docs/07 entry for this run
    tables: dict[str, dict[str, list]] = field(default_factory=empty_tables)
    test_tally: dict | None = None
