"""T13: grades, flows, cascades and provenance rebuilt from the raw tables on disk. Also pins the
docs/07 table columns and the Parquet round trip.

Pipeline under test: simulate -> write_replicate -> read_table -> derive.*. Every answer join uses the
composite key (run_id, answer_id) (docs/07 rule 5). test_tally format (T13 only):
  {"H": {(h, source, receiver): count}, "grades": {(h, student): grade}}
"""
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from classroom_swarm.config import Stage
from classroom_swarm.derive import cascades, flow_counts, grades_from_items, provenance_paths
from classroom_swarm.records import COLUMNS, TABLES
from classroom_swarm.storage import read_table, write_replicate

from conftest import make_spec, run

DOCS07_COLUMNS = {
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


def test_columns_match_docs07():
    assert TABLES == tuple(DOCS07_COLUMNS)
    assert {k: tuple(v) for k, v in COLUMNS.items()} == DOCS07_COLUMNS


@pytest.fixture(scope="module")
def stored(tmp_path_factory):
    logs, graphs = [], {}
    for stage in (Stage.M1, Stage.M2):  # two runs in one table set, so the composite key matters
        log, graph = run(make_spec(stage, R=3, p_C0=0.2), test_tally=True)
        logs.append(log)
        graphs[log.run_id] = graph
    rep_dir = tmp_path_factory.mktemp("rep")
    write_replicate(rep_dir, logs, {"experiment_id": "test"})
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    return logs, graphs, rep_dir, tables


def test_parquet_round_trip(stored):
    logs, _, rep_dir, tables = stored
    for name in TABLES:
        assert tuple(tables[name].column_names) == DOCS07_COLUMNS[name]
        expected = {c: [v for log in logs for v in log.tables[name][c]] for c in DOCS07_COLUMNS[name]}
        assert tables[name].to_pydict() == expected, name
    manifest_text = (rep_dir / "manifest.json").read_text("utf-8")
    json.loads(manifest_text)
    assert all(log.run_id in manifest_text for log in logs)


def test_A20_schema_v1_graph_edges_read_as_unity_weights(tmp_path):
    legacy = pa.table({"run_id": ["old/run"], "u": [0], "v": [1]},
                      schema=pa.schema([pa.field("run_id", pa.string(), nullable=False),
                                        pa.field("u", pa.int64(), nullable=False),
                                        pa.field("v", pa.int64(), nullable=False)]))
    pq.write_table(legacy, tmp_path / "graph_edges.parquet")
    got = read_table(tmp_path, "graph_edges")
    assert got.to_pylist() == [{"run_id": "old/run", "u": 0, "v": 1, "weight": 1.0}]


def test_T13_grades_from_items(stored):
    logs, _, _, tables = stored
    rebuilt = grades_from_items(tables["item_outcomes"])
    for log in logs:
        for (h, i), grade in log.test_tally["grades"].items():
            assert rebuilt[(log.run_id, h, i)] == pytest.approx(grade, abs=1e-12)
    for d in tables["decisions"].to_pylist():
        assert rebuilt[(d["run_id"], d["homework_index"], d["student_id"])] == pytest.approx(d["grade"], abs=1e-12)


def test_T13_copied_items_equal_the_source_answer(stored):
    _, _, _, tables = stored
    produced, copied = {}, {}
    for r in tables["item_outcomes"].to_pylist():
        key = (r["run_id"], r["answer_id"])  # composite key
        if r["mode"] in ("S", "D"):
            produced.setdefault(key, {})[r["item"]] = r["correct"]
        elif r["mode"] == "copied":
            copied.setdefault((key, r["student_id"]), {})[r["item"]] = r["correct"]
    assert copied, "no copied answers; the test would be vacuous"
    for (key, _student), items in copied.items():
        assert items == produced[key]


def test_T13_flows_match_the_independent_tally(stored):
    logs, _, _, tables = stored
    rebuilt = flow_counts(tables["routing_events"])
    for log in logs:
        mine = {k[1:]: v for k, v in rebuilt.items() if k[0] == log.run_id}
        assert mine == log.test_tally["H"]
        assert sum(mine.values()) > 0


def test_T13_provenance_and_cascades(stored):
    _, graphs, _, tables = stored
    decisions = tables["decisions"].to_pylist()
    paths = provenance_paths(tables["routing_events"], tables["decisions"])
    for d in decisions:
        path = paths[(d["run_id"], d["homework_index"], d["student_id"])]
        assert path[0] == d["root_id"] and path[-1] == d["student_id"]
        assert len(path) - 1 == d["depth"]
        g = graphs[d["run_id"]]
        assert all(g.has_edge(u, v) for u, v in zip(path, path[1:]))

    expected = {}
    for d in decisions:
        if d["action"] == "C" and not d["copy_success"]:
            continue  # §38: a failed copier holds no packet, so its fallback answer is in no cascade
        key = (d["run_id"], d["homework_index"], d["root_id"])
        size, depth = expected.get(key, (0, 0))
        expected[key] = (size + 1, max(depth, d["depth"]))
    got = {(c["run_id"], c["h"], c["root"]): (c["size"], c["max_depth"]) for c in cascades(tables["decisions"])}
    assert got == expected
