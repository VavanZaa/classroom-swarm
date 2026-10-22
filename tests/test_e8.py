from __future__ import annotations

import numpy as np
import pytest

from classroom_swarm import e8
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import TABLES
from classroom_swarm.rng import Draws, graph_seed
from classroom_swarm.storage import read_table
from classroom_swarm.v3 import V3Params, V3RunSpec, simulate_v3


def _small_params(**changes) -> V3Params:
    values = dict(H=5, M_H=20, M_E=10, F_E=5)
    values.update(changes)
    return V3Params(**values)


def test_e8_lock_and_exact_condition_plans() -> None:
    assert e8.verify_lock().startswith("0dab0171")
    assert len(e8.primary_conditions()) == 3
    assert len(set(e8.PRIMARY_LABELS)) == 3
    assert len(e8.surface_conditions()) == 37
    assert len(set(e8.SURFACE_LABELS)) == 37
    assert len(e8.robustness_conditions()) == 144
    assert len(set(e8.ROBUSTNESS_LABELS)) == 144
    assert e8.parse_robustness_label("E8-C-T-12101") == ("T", 1, 2, 1, 0, 1)


def test_both_ai_regimes_have_universal_equal_feasibility() -> None:
    unrestricted = e8.primary_conditions()[1]
    controlled = e8.primary_conditions()[2]
    assert unrestricted.policy.enabled and controlled.policy.enabled
    assert unrestricted.policy.kind == "unrestricted"
    assert controlled.policy.kind == "controlled"
    assert unrestricted.policy.universal_access
    assert controlled.policy.universal_access
    probabilities = e8.action_probabilities_e8(
        np.zeros((2, 4)), [(0, 1, 2, 3), (0, 3)], 0.12, "argmax", 0.10
    )
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    assert np.allclose(probabilities[0], [0.25] * 4)
    assert np.allclose(probabilities[1], [0.5, 0.0, 0.0, 0.5])


def test_no_ai_control_has_exact_frozen_v3_parity() -> None:
    p, seed, replicate = _small_params(), 456789, 2
    condition = e8.E8Condition("E8-test-none", p, "SBM", False, e8.E8Policy(enabled=False, kind="none"))
    got = e8._simulate_plan((condition,), replicate, seed)[0].log
    graph = generate_graph("SBM", p, graph_seed(seed, replicate, "SBM"))
    draws = Draws(seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
    expected = simulate_v3(V3RunSpec(condition.label, replicate, "SBM", 3, p, seed), graph, draws)
    assert got.tables == expected.tables
    assert got.manifest == expected.manifest


def test_unrestricted_ai_uses_declared_accuracy_learning_and_normal_confidence() -> None:
    p, seed, replicate = _small_params(epsilon=1.0), 8181, 1
    graph = generate_graph("SBM", p, graph_seed(seed, replicate, "SBM"))
    draws = Draws(seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
    spec = V3RunSpec("E8-test-U", replicate, "SBM", 3, p, seed)
    policy = e8.E8Policy(kind="unrestricted", unrestricted_accuracy=1.0,
                         unrestricted_learning=0.10, ai_cost=0)
    result = e8.simulate_e8(spec, graph, draws, policy)
    decisions = e8.zip_rows(result.log.tables["decisions"])
    traits = {r["student_id"]: r for r in e8.zip_rows(result.log.tables["agent_traits"])}
    ai_rows = {(r["homework_index"], r["student_id"]): r for r in result.ai_decisions}
    used = [r for r in decisions if r["action"] == "A"]
    assert used
    assert all(r["grade"] == 1.0 and r["cost"] == 0 for r in used)
    for row in used:
        side = ai_rows[(row["homework_index"], row["student_id"])]
        expected = side["K_before"] + 0.10 * traits[row["student_id"]]["alpha"] * (1 - side["K_before"])
        assert side["K_after"] == pytest.approx(expected)
        assert side["correct_probability"] == 1.0
        expected_c = side["confidence_before"] + p.eta_C * (row["grade"] - side["confidence_before"])
        assert side["confidence_after"] == pytest.approx(expected_c)


def test_controlled_ai_requires_effort_and_separates_scaffold_from_learning() -> None:
    p, seed, replicate = _small_params(epsilon=1.0), 9191, 1
    graph = generate_graph("SBM", p, graph_seed(seed, replicate, "SBM"))
    draws = Draws(seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
    spec = V3RunSpec("E8-test-T", replicate, "SBM", 3, p, seed)
    policy = e8.E8Policy(kind="controlled", tutor_learning=1.0,
                         scaffold_strength=0.25, ai_cost=1)
    result = e8.simulate_e8(spec, graph, draws, policy)
    decisions = e8.zip_rows(result.log.tables["decisions"])
    traits = {r["student_id"]: r for r in e8.zip_rows(result.log.tables["agent_traits"])}
    ai_rows = {(r["homework_index"], r["student_id"]): r for r in result.ai_decisions}
    used = [r for r in decisions if r["action"] == "A"]
    assert used
    assert all(r["cost"] == 1 for r in used)
    assert any(r["grade"] < 1.0 for r in used)
    for row in used:
        side = ai_rows[(row["homework_index"], row["student_id"])]
        expected_k = side["K_before"] + traits[row["student_id"]]["alpha"] * (1 - side["K_before"])
        expected_p = expected_k + 0.25 * (1 - expected_k)
        assert side["K_after"] == pytest.approx(expected_k)
        assert side["correct_probability"] == pytest.approx(expected_p)
        assert side["learning_increment"] == pytest.approx(expected_k - side["K_before"])


def test_e8_sidecar_roundtrip_and_outputs(tmp_path) -> None:
    p = _small_params(epsilon=1.0)
    plan = (
        e8.E8Condition("E8-test-none", p, "SBM", False, e8.E8Policy(enabled=False, kind="none")),
        e8.E8Condition("E8-test-controlled", p, "SBM", False, e8.E8Policy(kind="controlled")),
    )
    rep = e8.run_block_replicate("test", 1, 7171, tmp_path, plan)
    tables = {name: read_table(rep, name) for name in TABLES}
    ai = e8.read_ai_table(rep)
    summaries, trajectories = e8.run_outputs(tables, ai)
    assert len(summaries) == 2
    assert len(trajectories) == 2 * p.H
    controlled = [r for r in ai.to_pylist() if r["run_id"].startswith("E8-test-controlled/")]
    assert controlled and all(r["accessible"] for r in controlled)
    assert all(r["available"] == (r["homework_index"] >= 2) for r in controlled)
    assert {r["experiment_id"] for r in summaries} == {"E8-test-none", "E8-test-controlled"}
