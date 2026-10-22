"""Parquet storage of the canonical tables (docs/07, docs/09 storage.py). No scientific calculation.

One table set per replicate: each Parquet file concatenates all runs of the replicate, told apart by
`run_id`, plus one manifest.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from .records import COLUMNS, TABLES, RunLog

SCHEMA_VERSION = "3"

_S, _I, _F, _B = pa.string(), pa.int64(), pa.float64(), pa.bool_()
_TYPES: dict[str, dict[str, pa.DataType]] = {
    "graph_nodes": {"run_id": _S, "student_id": _I, "community_id": _I, "degree": _I},
    "graph_edges": {"run_id": _S, "u": _I, "v": _I, "weight": _F},
    "agent_traits": {"run_id": _S, "student_id": _I, "K0": _F, "alpha": _F, "kappa": _F},
    "events": {"run_id": _S, "event_id": _S, "seq": _I, "event_type": _S, "homework_index": _I,
               "exam_index": _I, "diagnostic_only": _B, "exam_updates_confidence": _B, "exam_updates_effort": _B},
    "state_snapshots": {"run_id": _S, "event_id": _S, "student_id": _I, "K": _F, "C": _F, "E": _F,
                        "Q_S": _F, "Q_D": _F, "Q_C": _F, "X": _F},
    "tie_snapshots": {"run_id": _S, "event_id": _S, "observer_id": _I, "target_id": _I, "A": _F},
    "decisions": {"run_id": _S, "event_id": _S, "homework_index": _I, "student_id": _I, "feasible_S": _B,
                  "feasible_D": _B, "feasible_C": _B, "P_S": _F, "P_D": _F, "P_C": _F, "action": _S,
                  "partner_id": _I, "grade": _F, "reward": _F, "cost": _I, "copy_success": _B,
                  "answer_id": _S, "root_id": _I, "depth": _I},
    "v3_decisions": {"run_id": _S, "event_id": _S, "homework_index": _I, "student_id": _I,
                     "decision_mode": _S, "seeded": _B, "explored": _B, "expected_access": _F},
    "routing_events": {"run_id": _S, "homework_index": _I, "round": _I, "requester_id": _I, "target_id": _I,
                       "target_had_packet": _B, "transfer_success": _B, "answer_id": _S, "root_id": _I,
                       "sender_depth": _I, "receiver_depth": _I},
    "sharing_events": {"run_id": _S, "homework_index": _I, "round": _I, "requester_id": _I,
                       "target_id": _I, "target_had_packet": _B, "share_probability": _F,
                       "sharing_draw": _F, "willing": _B, "capacity_available": _B, "share_granted": _B},
    "item_outcomes": {"run_id": _S, "event_id": _S, "student_id": _I, "item": _I, "correct": _B, "mode": _S,
                      "answer_id": _S, "root_id": _I},
}
_NULLABLE = {
    "graph_nodes": {"community_id"},
    "events": {"homework_index", "exam_index", "diagnostic_only", "exam_updates_confidence", "exam_updates_effort"},
    "decisions": {"partner_id", "copy_success"},
    "routing_events": {"answer_id", "root_id", "sender_depth", "receiver_depth"},
    "item_outcomes": {"answer_id", "root_id"},
    "sharing_events": {"share_probability", "sharing_draw", "willing", "capacity_available"},
}

ARROW_SCHEMAS: dict[str, pa.Schema] = {
    name: pa.schema([pa.field(c, _TYPES[name][c], nullable=c in _NULLABLE.get(name, set())) for c in COLUMNS[name]])
    for name in TABLES
}


def write_replicate(rep_dir: Path, logs: Sequence[RunLog], shared_manifest: dict) -> list[Path]:
    """Concatenate the runs; write one Parquet file per canonical table plus manifest.json."""
    rep_dir = Path(rep_dir)
    rep_dir.mkdir(parents=True, exist_ok=True)
    run_ids = [log.run_id for log in logs]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("duplicate run_id in one replicate")
    written = []
    for name in TABLES:
        columns = {c: [v for log in logs for v in log.tables[name][c]] for c in COLUMNS[name]}
        table = pa.table(columns, schema=ARROW_SCHEMAS[name])  # raises if a value breaks the schema
        path = rep_dir / f"{name}.parquet"
        pq.write_table(table, path)
        written.append(path)
    manifest = {"schema_version": SCHEMA_VERSION, **shared_manifest, "runs": [log.manifest for log in logs]}
    path = rep_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    written.append(path)
    return written


def to_arrow(log: RunLog, name: str) -> pa.Table:
    """One in-memory run table as a typed Arrow table (for derive.* without a disk round trip)."""
    return pa.table(log.tables[name], schema=ARROW_SCHEMAS[name])


def read_table(rep_dir: Path, name: str) -> pa.Table:
    if name not in TABLES:
        raise ValueError(f"unknown table {name!r}")
    path = Path(rep_dir) / f"{name}.parquet"
    if not path.exists() and name in {"agent_traits", "tie_snapshots", "v3_decisions", "sharing_events"}:
        return pa.Table.from_batches([], schema=ARROW_SCHEMAS[name])
    if name == "graph_edges":
        table = pq.read_table(path)
        if "weight" not in table.column_names:  # schema-v1 compatibility: historical edges were all unity
            table = table.append_column("weight", pa.array([1.0] * len(table), type=_F))
        return table.select(COLUMNS[name]).cast(ARROW_SCHEMAS[name])
    return pq.read_table(path, schema=ARROW_SCHEMAS[name])
