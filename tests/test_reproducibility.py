"""T6 exact reproducibility, T7 non-invasive diagnostic exams, T8 common random numbers across variants.

docs/05, docs/06, docs/09 (one Draws per replicate for every stage, R and family).
"""
import json
from collections import Counter

import pytest

from classroom_swarm.config import Params, SimulationControls, Stage
from classroom_swarm.experiment import run_replicate
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

from conftest import MASTER_SEED, make_spec, run, snapshots_by_event, table


def test_T6_simulate_is_exactly_reproducible():
    spec = make_spec(Stage.M5, p_C0=0.2)
    a, _ = run(spec)
    b, _ = run(spec)
    assert a.tables == b.tables
    assert a.manifest == b.manifest


def test_T6_run_replicate_is_exactly_reproducible(tmp_path):
    base = Params(H=10)
    d1 = run_replicate("t6", 1, MASTER_SEED, base, tmp_path / "a", families=("SBM",), stages=(Stage.M0, Stage.M1))
    d2 = run_replicate("t6", 1, MASTER_SEED, base, tmp_path / "b", families=("SBM",), stages=(Stage.M0, Stage.M1))
    for name in TABLES:
        assert read_table(d1, name).equals(read_table(d2, name)), name
    assert json.loads((d1 / "manifest.json").read_text("utf-8")) == json.loads((d2 / "manifest.json").read_text("utf-8"))


def _homework_view(log):
    """Everything except exam events, keyed so exam insertion can't shift the comparison.

    Rows are compared as multisets (Counter), not sorted lists: rows mix None with str/int
    (e.g. answer_id of a failed request), which Python can't order. Same check, no weakening.
    """
    events = {e["event_id"]: e for e in table(log, "events")}
    snaps = {k: v for k, v in snapshots_by_event(log).items() if k[0] != "exam"}
    snaps = {k: {i: {c: s[c] for c in ("K", "C", "E", "Q_S", "Q_D", "Q_C", "X")} for i, s in v.items()}
             for k, v in snaps.items()}
    decisions = Counter(tuple(sorted((k, v) for k, v in d.items() if k != "event_id"))
                        for d in table(log, "decisions"))
    routing = Counter(tuple(sorted(r.items())) for r in table(log, "routing_events"))
    items = Counter((events[r["event_id"]]["homework_index"], r["student_id"], r["item"], r["correct"], r["mode"])
                    for r in table(log, "item_outcomes") if r["mode"] != "exam")
    return snaps, decisions, routing, items


@pytest.mark.parametrize("stage", [Stage.M0, Stage.M1, Stage.M2, Stage.M3])
def test_T7_diagnostic_exams_change_nothing(stage):
    with_probe, _ = run(make_spec(stage, p_C0=0.2, F_E=5))
    without, _ = run(make_spec(stage, p_C0=0.2, F_E=None))
    assert any(e["event_type"] == "exam" for e in table(with_probe, "events"))
    assert not any(e["event_type"] == "exam" for e in table(without, "events"))
    assert _homework_view(with_probe) == _homework_view(without)


def _first_homework(log):
    decisions = {d["student_id"]: d for d in table(log, "decisions") if d["homework_index"] == 1}
    requests = sorted((r["round"], r["requester_id"], r["target_id"], r["target_had_packet"])
                      for r in table(log, "routing_events") if r["homework_index"] == 1)
    return decisions, requests


def test_T8_stages_share_draws_before_they_diverge():
    # at h = 1 every stage has the same state, so the shared uniforms must give identical choices
    m0, _ = run(make_spec(Stage.M0, p_C0=0.2))
    m1, _ = run(make_spec(Stage.M1, p_C0=0.2))
    d0, r0 = _first_homework(m0)
    d1, r1 = _first_homework(m1)
    assert {i: d["action"] for i, d in d0.items()} == {i: d["action"] for i, d in d1.items()}
    assert {i: d["partner_id"] for i, d in d0.items()} == {i: d["partner_id"] for i, d in d1.items()}
    assert r0 == r1


def test_T8_R1_is_the_first_round_of_R3():
    one, _ = run(make_spec(Stage.M1, R=1, p_C0=0.2))
    three, _ = run(make_spec(Stage.M1, R=3, p_C0=0.2))
    d1, r1 = _first_homework(one)
    d3, r3 = _first_homework(three)
    assert {i: d["action"] for i, d in d1.items()} == {i: d["action"] for i, d in d3.items()}
    assert r1 == [r for r in r3 if r[0] == 1]


def test_T8_forced_identical_actions_give_identical_items_across_stages():
    forced = SimulationControls(force_action="S")
    m0, _ = run(make_spec(Stage.M0), controls=forced)
    m1, _ = run(make_spec(Stage.M1), controls=forced)
    key = lambda log: sorted((r["student_id"], r["item"], r["correct"], r["mode"]) for r in table(log, "item_outcomes"))
    assert key(m0) == key(m1)


def test_T5_partner_and_routing_ignore_knowledge():
    # K0 changes everyone's knowledge but (uniform q0 shift, beta_C inactive in M1) not the h = 1 choices
    low, _ = run(make_spec(Stage.M1, K0=0.4, p_C0=0.2))
    high, _ = run(make_spec(Stage.M1, K0=0.6, p_C0=0.2))
    dl, rl = _first_homework(low)
    dh, rh = _first_homework(high)
    assert {i: (d["action"], d["partner_id"]) for i, d in dl.items()} == \
           {i: (d["action"], d["partner_id"]) for i, d in dh.items()}
    assert rl == rh


def test_T8_replicate_shares_graph_and_draws(tmp_path):
    rep = run_replicate("t8", 1, MASTER_SEED, Params(H=5), tmp_path)
    manifest = json.loads((rep / "manifest.json").read_text("utf-8"))
    text = json.dumps(manifest)
    assert text.count("R_max") >= 1
    edges = read_table(rep, "graph_edges").to_pylist()
    by_run = {}
    for e in edges:
        by_run.setdefault(e["run_id"], set()).add((e["u"], e["v"]))
    run_ids = sorted(by_run)
    assert len(run_ids) == 36
    for family in ("ER", "WS", "SBM"):
        family_graphs = [by_run[r] for r in run_ids if f"/{family}/" in r]
        assert len(family_graphs) == 12 and all(g == family_graphs[0] for g in family_graphs)
    # same uniforms across families: at h = 1, students feasible in both graphs choose identically
    decisions = [d for d in read_table(rep, "decisions").to_pylist() if d["homework_index"] == 1]
    choice = {(d["run_id"], d["student_id"]): (d["action"], d["feasible_C"]) for d in decisions}
    er = "t8/rep0001/ER/R3/M1"
    sbm = "t8/rep0001/SBM/R3/M1"
    shared = [i for i in range(30) if choice[(er, i)][1] and choice[(sbm, i)][1]]
    assert shared and all(choice[(er, i)][0] == choice[(sbm, i)][0] for i in shared)
