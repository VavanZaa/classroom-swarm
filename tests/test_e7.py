from __future__ import annotations

import math

import numpy as np
import pytest

from classroom_swarm import e7
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import TABLES
from classroom_swarm.rng import Draws, graph_seed
from classroom_swarm.storage import read_table
from classroom_swarm.v3 import V3Params, V3RunSpec, simulate_v3


def _small_params(**changes) -> V3Params:
    values = dict(H=5, M_H=4, M_E=6, F_E=5)
    values.update(changes)
    return V3Params(**values)


def test_e7_lock_and_frozen_plans() -> None:
    assert e7.verify_lock().startswith("9f1bbbd4")
    assert len(e7.structural_conditions()) == 12
    assert len(set(e7.STRUCTURAL_LABELS)) == 12
    assert len(e7.factorial_conditions()) == 128
    assert len(set(e7.FACTORIAL_LABELS)) == 128
    assert e7.bits_from_label("E7-F-1010101") == (1, 0, 1, 0, 1, 0, 1)


def test_ai_access_is_exact_independent_and_reproducible() -> None:
    first = e7.ai_access_mask(30, 0.25, 920107, 7)
    second = e7.ai_access_mask(30, 0.25, 920107, 7)
    other = e7.ai_access_mask(30, 0.25, 920107, 8)
    assert first.sum() == math.ceil(0.25 * 30)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, other)
    assert e7.ai_access_mask(30, 1.0, 1, 1).all()


def test_four_action_probabilities_are_symmetric_and_normalized() -> None:
    utilities = np.zeros((2, 4))
    feasible = [(0, 1, 2, 3), (0, 3)]
    argmax = e7.action_probabilities_e7(utilities, feasible, 0.12, "argmax", 0.1)
    softmax = e7.action_probabilities_e7(utilities, feasible, 0.12, "softmax", 0.1)
    assert np.allclose(argmax.sum(axis=1), 1.0)
    assert np.allclose(softmax.sum(axis=1), 1.0)
    assert np.allclose(argmax[0], [0.25] * 4)
    assert np.allclose(softmax[1], [0.5, 0.0, 0.0, 0.5])


def test_control_is_exact_frozen_v3_parity() -> None:
    p, seed, replicate = _small_params(), 123456, 2
    condition = e7.E7Condition("E7-test-control", p, e7.E7Intervention(enabled=False))
    got = e7._simulate_plan((condition,), replicate, seed)[0].log
    graph = generate_graph("SBM", p, graph_seed(seed, replicate, "SBM"))
    draws = Draws(seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
    expected = simulate_v3(V3RunSpec(condition.label, replicate, "SBM", 3, p, seed), graph, draws)
    assert got.tables == expected.tables
    assert got.manifest == expected.manifest


def test_ai_gives_perfect_grade_no_knowledge_and_declared_confidence_loss() -> None:
    p, seed, replicate = _small_params(epsilon=1.0), 777, 1
    graph = generate_graph("SBM", p, graph_seed(seed, replicate, "SBM"))
    draws = Draws(seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
    spec = V3RunSpec("E7-test-ai", replicate, "SBM", 3, p, seed)
    intervention = e7.E7Intervention(confidence_decrement=0.04)
    result = e7.simulate_e7(spec, graph, draws, intervention, np.ones(p.N, dtype=bool))
    decisions = e7.zip_rows(result.log.tables["decisions"])
    states = {(r["event_id"], r["student_id"]): r for r in e7.zip_rows(result.log.tables["state_snapshots"])}
    ai = [r for r in decisions if r["action"] == "A"]
    assert ai
    for row in ai:
        h, i = row["homework_index"], row["student_id"]
        before = states[("init" if h == 1 else f"h{h - 1}", i)]
        after = states[(f"h{h}", i)]
        assert row["grade"] == 1.0
        assert after["K"] == before["K"]
        assert after["C"] == max(0.0, before["C"] - 0.04)
    probabilities = {(r["homework_index"], r["student_id"]): r["P_A"] for r in result.ai_decisions}
    for row in decisions:
        total = row["P_S"] + row["P_D"] + row["P_C"] + probabilities[(row["homework_index"], row["student_id"])]
        assert total == pytest.approx(1.0)


def test_e7_sidecars_roundtrip_and_summary(tmp_path) -> None:
    p = _small_params(epsilon=1.0)
    condition = e7.E7Condition("E7-test-write", p, e7.E7Intervention())
    rep = e7.run_structural_replicate(1, 888, tmp_path, (condition,))
    tables = {name: read_table(rep, name) for name in TABLES}
    ai = e7.read_ai_table(rep, "ai_decisions")
    access = e7.read_ai_table(rep, "ai_access")
    assert len(access) == p.N
    assert len(ai) == p.N * p.H
    summaries = e7.run_summaries(tables, ai)
    assert len(summaries) == 1
    assert summaries[0]["experiment_id"] == condition.label
    assert summaries[0]["pA_available_late"] is not None


def test_factorial_product_contrast() -> None:
    rows = []
    for label in e7.FACTORIAL_LABELS:
        bits = e7.bits_from_label(label)
        rows.append({"experiment_id": label, "replicate": 1, "y": 3.0 * bits[0] - 2.0 * bits[1]})
    assert e7.factorial_effects(rows, "y", (0,)) == [3.0]
    assert e7.factorial_effects(rows, "y", (1,)) == [-2.0]
    assert e7.factorial_effects(rows, "y", (0, 1)) == [0.0]
