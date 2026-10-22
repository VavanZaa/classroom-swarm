"""T1 bounds, T2 provenance, T11 isolate masking, T12 M0 behaviour, T15 snapshots. docs/03, docs/07."""
import math

import numpy as np
import pytest

from classroom_swarm.config import Stage, resolve_params
from classroom_swarm.engine import strategy_probabilities

from conftest import graph_from_edges, make_spec, ordered_snapshots, run, table

CASES = [(stage, R) for stage in Stage for R in (1, 3)]


@pytest.fixture(scope="module")
def logs():
    return {(stage, R): run(make_spec(stage, R=R, p_C0=0.2)) for stage, R in CASES}


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c[0].name}-R{c[1]}")
def test_T1_bounds(logs, case):
    log, _ = logs[case]
    for s in table(log, "state_snapshots"):
        assert 0.0 <= s["K"] <= 1.0 and 0.0 <= s["C"] <= 1.0 and s["E"] >= 1.0
    for d in table(log, "decisions"):
        assert 0.0 <= d["grade"] <= 1.0
        probs = (d["P_S"], d["P_D"], d["P_C"])
        assert all(0.0 <= p <= 1.0 for p in probs) and math.isclose(sum(probs), 1.0, abs_tol=1e-12)
        assert d["action"] in ("S", "D", "C")


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c[0].name}-R{c[1]}")
def test_T2_T3_provenance_from_raw_tables(logs, case):
    log, graph = logs[case]
    R = case[1]
    decisions = {(d["homework_index"], d["student_id"]): d for d in table(log, "decisions")}
    transfers = {}
    for ev in table(log, "routing_events"):
        if ev["transfer_success"]:
            assert (ev["homework_index"], ev["requester_id"]) not in transfers  # first packet only
            transfers[(ev["homework_index"], ev["requester_id"])] = ev
    n_copied = 0
    for (h, i), d in decisions.items():
        if d["action"] != "C" or not d["copy_success"]:  # S, D and failed copiers answer themselves
            assert (d["root_id"], d["depth"], d["answer_id"]) == (i, 0, f"h{h}-s{i}")
            continue
        n_copied += 1
        cur, hops, rounds = i, 0, []
        while decisions[(h, cur)]["action"] == "C":
            t = transfers[(h, cur)]
            assert graph.has_edge(t["requester_id"], t["target_id"])
            assert t["answer_id"] == d["answer_id"] and t["root_id"] == d["root_id"]
            assert t["receiver_depth"] == t["sender_depth"] + 1
            rounds.append(t["round"])
            cur, hops = t["target_id"], hops + 1
        root = decisions[(h, cur)]
        assert root["action"] in ("S", "D")
        assert (d["root_id"], d["answer_id"], d["depth"]) == (cur, f"h{h}-s{cur}", hops)
        assert rounds == sorted(rounds, reverse=True) and len(set(rounds)) == len(rounds)  # one hop per round
        assert d["depth"] <= R
    assert n_copied > 0, "run produced no copies; the provenance test would be vacuous"


def _isolate_graph():
    edges = [(i, i + 1) for i in range(25)] + [(0, 25), (3, 17), (8, 21)]
    return graph_from_edges(30, edges)  # students 26..29 are isolated


@pytest.mark.parametrize("stage", [Stage.M2, Stage.M5])
def test_T11_isolates_can_only_choose_S(stage):
    spec = make_spec(stage, family="ER", p_C0=0.2)
    log, graph = run(spec, graph=_isolate_graph())
    q0 = resolve_params(stage, spec.params).q0
    isolated = {i for i in range(30) if graph.degree[i] == 0}
    assert isolated == {26, 27, 28, 29}
    assert {n["student_id"] for n in table(log, "graph_nodes") if n["degree"] == 0} == isolated
    for d in table(log, "decisions"):
        if d["student_id"] in isolated:
            assert (d["feasible_S"], d["feasible_D"], d["feasible_C"]) == (True, False, False)
            assert (d["P_S"], d["P_D"], d["P_C"]) == (1.0, 0.0, 0.0)
            assert d["action"] == "S" and d["partner_id"] is None
        else:
            assert d["feasible_D"] and d["feasible_C"]
    for s in table(log, "state_snapshots"):
        if s["student_id"] in isolated:
            assert s["X"] == 0.0 and s["Q_D"] == q0 and s["Q_C"] == q0


def test_T12_M0_fixed_tendencies():
    counts = {"S": 0, "D": 0, "C": 0}
    for rep in range(1, 11):
        spec = make_spec(Stage.M0, replicate=rep)
        log, graph = run(spec)
        q0 = resolve_params(Stage.M0, spec.params).q0
        for s in table(log, "state_snapshots"):
            assert (s["Q_S"], s["Q_D"], s["Q_C"]) == (q0, q0, q0)
        for d in table(log, "decisions"):
            if d["feasible_C"]:
                assert d["P_C"] == pytest.approx(0.10, abs=1e-12)
                counts[d["action"]] += 1
    n = sum(counts.values())
    assert n >= 5000
    for action, p in (("C", 0.10), ("S", 0.45), ("D", 0.45)):
        se = math.sqrt(p * (1 - p) / n)
        assert abs(counts[action] / n - p) <= 4 * se, (action, counts, n)


@pytest.mark.parametrize("stage", list(Stage))
def test_T15_snapshots_and_events(stage):
    spec = make_spec(stage, p_C0=0.2)
    log, graph = run(spec)
    ep = resolve_params(stage, spec.params)
    seq = ordered_snapshots(log)

    init_event, init = seq[0]
    assert init_event["event_type"] == "init" and init_event["seq"] == 0
    assert all(len(snap) == spec.params.N for _, snap in seq)  # every event snapshots every student
    for s in init.values():
        assert (s["K"], s["C"], s["E"], s["X"]) == (ep.K0, ep.C0, 1.0, 0.0)
        assert (s["Q_S"], s["Q_D"], s["Q_C"]) == (ep.q0, ep.q0, ep.q0)

    homeworks = [e for e, _ in seq if e["event_type"] == "homework"]
    exams = [e for e, _ in seq if e["event_type"] == "exam"]
    assert [e["homework_index"] for e in homeworks] == list(range(1, spec.params.H + 1))
    assert [(e["homework_index"], e["exam_index"]) for e in exams] == [(5, 1), (10, 2), (15, 3), (20, 4)]
    for e in exams:
        assert e["diagnostic_only"] == (stage <= Stage.M3)
        assert e["exam_updates_confidence"] == (stage >= Stage.M4)
        assert e["exam_updates_effort"] == (stage >= Stage.M5)

    decisions = {}
    for d in table(log, "decisions"):
        decisions.setdefault(d["homework_index"], []).append(d)
    feasible = np.array([deg > 0 for deg in graph.degree])
    for (prev_event, prev), (event, cur) in zip(seq, seq[1:]):
        if event["event_type"] == "homework":
            # the pre-state of this homework is exactly the previous committed snapshot
            ids = sorted(prev)
            Q = np.array([[prev[i]["Q_S"], prev[i]["Q_D"], prev[i]["Q_C"]] for i in ids])
            C = np.array([prev[i]["C"] for i in ids])
            X = np.array([prev[i]["X"] for i in ids])
            P = strategy_probabilities(Q, C, X, feasible[ids], ep)
            logged = {d["student_id"]: (d["P_S"], d["P_D"], d["P_C"]) for d in decisions[event["homework_index"]]}
            np.testing.assert_allclose([logged[i] for i in ids], P, rtol=0, atol=1e-12)
        elif stage <= Stage.M3:
            assert cur == {i: {**s, "event_id": cur[i]["event_id"]} for i, s in prev.items()}  # probe: no change
