"""A21 V3 generative-model equations and invariants (docs/10, T27-T34)."""
import inspect
import json
import math
from statistics import NormalDist

import numpy as np
import pytest

from classroom_swarm.engine import Packet
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import TABLES
from classroom_swarm.rng import Draws, graph_seed
from classroom_swarm.storage import read_table
from classroom_swarm.v3 import (
    V3Controls, V3Params, V3RunSpec, action_probabilities, expected_access, initial_traits,
    route_v3, run_v3_replicate, seed_probabilities, share_probability, simulate_v3, social_update, update_beliefs,
)

from conftest import MASTER_SEED, FixedDraws, graph_from_edges, table

SRC = Packet("h1-s0", 0, 0, (True, False))


def _small_params(**overrides):
    values = dict(N=4, H=2, F_E=None, M_H=2, M_E=2, d_bar=2)
    values.update(overrides)
    return V3Params(**values)


def test_v3_params_validate_approved_defaults():
    p = V3Params()
    p.validate()
    assert (p.seed_fraction, p.epsilon, p.A0, p.eta_A) == (0.10, 0.06, 0.50, 0.20)
    assert (p.share_p0, p.share_reciprocity, p.share_capacity) == (0.80, 2.0, 2)
    assert (p.K0_sd, p.alpha_log_sd, p.kappa_log_sd, p.eta_social) == (0.10, 0.25, 0.25, 0.0)
    assert p.copy_success_cost == 0
    assert "beta_P" not in vars(p) and "exposure" not in vars(p)
    for changes in (dict(epsilon=-0.1), dict(A0=1.0), dict(share_capacity=0), dict(eta_social=1.1),
                    dict(copy_success_cost=2), dict(copy_success_cost=0.5)):
        with pytest.raises(ValueError):
            _small_params(**changes).validate()


def test_T27_no_prevalence_policy_and_action_neutral_exploration():
    assert "X" not in inspect.signature(action_probabilities).parameters
    assert "prevalence" not in inspect.signature(action_probabilities).parameters
    feasible = np.array([True, False])
    seed = seed_probabilities(feasible, 0.10)
    np.testing.assert_allclose(seed, [[0.45, 0.45, 0.10], [1.0, 0.0, 0.0]], atol=0, rtol=0)
    Q = np.array([[1.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    P = action_probabilities(Q, np.array([0.5, 0.0]), np.array([0.15, 0.15]), feasible,
                             epsilon=0.06, A0=0.5)
    np.testing.assert_allclose(P, [[0.96, 0.02, 0.02], [1.0, 0.0, 0.0]], atol=1e-12)


def test_T28_traits_follow_approved_transforms_and_shuffle_bundles():
    p = _small_params(N=3, K0=0.5, K0_sd=0.1, alpha=0.2, alpha_log_sd=0.25,
                      kappa=0.3, kappa_log_sd=0.25)
    z = np.array([[0.0, 1.0, -1.0], [0.0, 1.0, -1.0], [0.0, 1.0, -1.0]])
    draws = FixedDraws(3, 2, 2, 1, traits=z)
    traits = initial_traits(p, draws)
    normal = NormalDist()
    lo, hi = normal.cdf((0.0 - p.K0) / p.K0_sd), normal.cdf((1.0 - p.K0) / p.K0_sd)
    expected_K = [p.K0 + p.K0_sd * normal.inv_cdf(lo + normal.cdf(v) * (hi - lo)) for v in z[0]]
    np.testing.assert_allclose(traits.K0, expected_K)
    np.testing.assert_allclose(traits.alpha, p.alpha * np.exp(0.25 * z[1] - 0.5 * 0.25 ** 2))
    np.testing.assert_allclose(traits.kappa, p.kappa * np.exp(0.25 * z[2] - 0.5 * 0.25 ** 2))
    shuffled = initial_traits(p, draws, V3Controls(trait_permutation=(2, 0, 1)))
    np.testing.assert_allclose(shuffled.K0, traits.K0[[2, 0, 1]])
    bundles = sorted(zip(traits.K0, traits.alpha, traits.kappa))
    assert sorted(zip(shuffled.K0, shuffled.alpha, shuffled.kappa)) == bundles
    boundary = initial_traits(_small_params(N=3, K0=0.0, K0_sd=0.1), draws)
    assert np.isfinite(boundary.K0).all() and ((boundary.K0 > 0.0) & (boundary.K0 < 1.0)).all()


def test_T29_beliefs_update_only_the_requesters_direct_tie():
    A = np.full((3, 3), np.nan)
    A[0, 1] = A[1, 0] = A[1, 2] = A[2, 1] = 0.5
    got = update_beliefs(A, [(0, 1, True), (2, 1, False)], eta_A=0.2)
    assert got[0, 1] == pytest.approx(0.6)
    assert got[2, 1] == pytest.approx(0.4)
    assert got[1, 0] == 0.5 and got[1, 2] == 0.5
    assert np.isnan(got[0, 2])


def test_T30_expected_access_and_learned_target_selection():
    neighbors = ((1, 2), (0,), (0,))
    weights = ((1.0, 1.0), (1.0,), (1.0,))
    A = np.full((3, 3), np.nan)
    A[0, 1], A[0, 2], A[1, 0], A[2, 0] = 0.9, 0.1, 0.5, 0.5
    # Selection weights are .9/.1, so expected reliability is .9*.9 + .1*.1 = .82.
    np.testing.assert_allclose(expected_access(neighbors, weights, A), [0.82, 0.5, 0.5])
    result = route_v3(neighbors, weights, A, {1: SRC, 2: SRC}, [0],
                      np.array([[0.5, 0.0, 0.0]]), np.zeros((1, 3)),
                      share_p0=0.8, share_reciprocity=2.0, A0=0.5, capacity=2)
    assert result.requests == [(1, 0, 1, True, True)]


def test_T31_sharing_reciprocity_and_capacity_are_separate():
    assert share_probability(0.8, 2.0, 0.5, 0.5) == pytest.approx(0.8)
    assert share_probability(0.8, 2.0, 0.9, 0.5) > 0.8
    assert share_probability(0.8, 2.0, 0.1, 0.5) < 0.8
    neighbors = ((1, 2, 3), (0,), (0,), (0,))
    weights = ((1.0, 1.0, 1.0), (1.0,), (1.0,), (1.0,))
    A = np.full((4, 4), np.nan)
    for i in (1, 2, 3):
        A[0, i] = A[i, 0] = 0.5
    result = route_v3(neighbors, weights, A, {0: SRC}, [1, 2, 3],
                      np.zeros((1, 4)), np.array([[0.9, 0.1, 0.2, 0.3]]),
                      share_p0=0.8, share_reciprocity=2.0, A0=0.5, capacity=2)
    assert set(result.received) == {1, 2}
    by_requester = {e["requester_id"]: e for e in result.sharing_events}
    assert by_requester[1]["share_granted"] and by_requester[2]["share_granted"]
    assert by_requester[3]["willing"] and not by_requester[3]["capacity_available"]
    assert not by_requester[3]["share_granted"]


def test_T31_v3_routing_remains_synchronous_across_hops():
    neighbors = ((1,), (0, 2), (1, 3), (2,))
    weights = tuple((1.0,) * len(nb) for nb in neighbors)
    A = np.full((4, 4), np.nan)
    for i, nb in enumerate(neighbors):
        for j in nb:
            A[i, j] = 0.5
    routing = np.array([[0.0, 0.0, 0.9, 0.0], [0.0, 0.0, 0.0, 0.0]])
    result = route_v3(neighbors, weights, A, {0: SRC}, [1, 2, 3], routing, np.zeros_like(routing),
                      share_p0=1.0, share_reciprocity=0.0, A0=0.5, capacity=3)
    assert result.received[1][2] == 1
    assert result.received[2][2] == 2
    assert result.received[2][0].depth == 2
    assert (1, 2, 3, False, False) in result.requests
    assert (2, 2, 1, True, True) in result.requests  # relay only after 1 received in round 1


def test_T33_social_learning_is_symmetric_across_action_labels():
    Q = np.zeros((4, 3))
    neighbors = ((1, 2, 3), (0,), (0,), (0,))
    weights = ((1.0, 1.0, 1.0), (1.0,), (1.0,), (1.0,))
    got = social_update(Q, ["S", "S", "D", "C"], np.array([0.0, 0.8, 0.8, 0.8]),
                        neighbors, weights, eta_social=0.5)
    np.testing.assert_allclose(got[0], [0.4, 0.4, 0.4])
    np.testing.assert_array_equal(social_update(Q, ["S"] * 4, np.ones(4), neighbors, weights, 0.0), Q)


def test_T32_T34_v3_simulation_is_reproducible_and_has_no_prevalence_state():
    p = _small_params(H=4)
    spec = V3RunSpec("v3test", 1, "ER", 2, p, MASTER_SEED)
    graph = graph_from_edges(4, [(0, 1), (0, 2), (1, 2), (2, 3)])
    draws = Draws(MASTER_SEED, 1, p.N, p.M_H, p.M_E, R_max=2)
    a = simulate_v3(spec, graph, draws)
    b = simulate_v3(spec, graph, Draws(MASTER_SEED, 1, p.N, p.M_H, p.M_E, R_max=2))
    assert a.tables == b.tables and a.manifest == b.manifest
    assert table(a, "agent_traits") and table(a, "tie_snapshots") and table(a, "v3_decisions")
    assert all(s["X"] == 0.0 for s in table(a, "state_snapshots"))
    for d in table(a, "v3_decisions"):
        if d["homework_index"] == 1:
            assert d["decision_mode"] in ("seed", "initial_honest")
        else:
            assert not d["seeded"] and d["decision_mode"] in ("explore", "exploit")
    traits = table(a, "agent_traits")
    assert len({round(t["K0"], 12) for t in traits}) > 1
    assert all(set(t) == {"run_id", "student_id", "K0", "alpha", "kappa"} for t in traits)


def test_T29_T31_simulation_commits_direct_beliefs_after_capacity_outcomes():
    p = _small_params(H=1)
    spec = V3RunSpec("v3exact", 1, "ER", 1, p, MASTER_SEED)
    graph = graph_from_edges(4, [(0, 1), (0, 2), (0, 3)])
    draws = FixedDraws(4, 2, 2, 1, strategy={1: [0.2, 0.95, 0.95, 0.95]},
                       routing={1: [[0.0] * 4]}, sharing={1: [[0.9, 0.1, 0.2, 0.3]]})
    log = simulate_v3(spec, graph, draws)
    shares = {r["requester_id"]: r for r in table(log, "sharing_events")}
    assert shares[1]["share_granted"] and shares[2]["share_granted"]
    assert shares[3]["willing"] and not shares[3]["capacity_available"]
    ties = {(r["observer_id"], r["target_id"]): r["A"] for r in table(log, "tie_snapshots")
            if r["event_id"] == "h1"}
    assert ties[(1, 0)] == pytest.approx(0.6)
    assert ties[(2, 0)] == pytest.approx(0.6)
    assert ties[(3, 0)] == pytest.approx(0.4)
    assert ties[(0, 1)] == ties[(0, 2)] == ties[(0, 3)] == 0.5


def test_T32_equal_cost_control_removes_successful_copy_cost_advantage():
    graph = graph_from_edges(4, [(0, 1), (0, 2), (0, 3)])
    draws = FixedDraws(4, 2, 2, 1, strategy={1: [0.2, 0.95, 0.95, 0.95]},
                       routing={1: [[0.0] * 4]}, sharing={1: [[0.9, 0.1, 0.2, 0.3]]})
    base = _small_params(H=1, copy_success_cost=0)
    equal = _small_params(H=1, copy_success_cost=1)
    base_log = simulate_v3(V3RunSpec("cost0", 1, "ER", 1, base, MASTER_SEED), graph, draws)
    equal_log = simulate_v3(V3RunSpec("cost1", 1, "ER", 1, equal, MASTER_SEED), graph, draws)
    base_rows = {r["student_id"]: r for r in table(base_log, "decisions")}
    equal_rows = {r["student_id"]: r for r in table(equal_log, "decisions")}
    traits = {r["student_id"]: r for r in table(equal_log, "agent_traits")}
    for student in (1, 2):
        assert base_rows[student]["copy_success"] and equal_rows[student]["copy_success"]
        assert (base_rows[student]["cost"], equal_rows[student]["cost"]) == (0, 1)
        assert equal_rows[student]["reward"] == pytest.approx(
            base_rows[student]["reward"] - traits[student]["kappa"])


def test_T34_traits_share_draws_across_graph_families():
    p = _small_params(N=12)
    draws = Draws(MASTER_SEED, 2, p.N, p.M_H, p.M_E, R_max=1)
    np.testing.assert_array_equal(initial_traits(p, draws).K0, initial_traits(p, draws).K0)
    er = generate_graph("ER", p, graph_seed(MASTER_SEED, 2, "ER"))
    sbm = generate_graph("SBM", p, graph_seed(MASTER_SEED, 2, "SBM"))
    assert er.edges != sbm.edges  # traits are independent of these different graph draws


def test_T34_v3_runner_writes_schema_v3_reproducibly(tmp_path):
    p = V3Params(N=12, H=2, F_E=None, M_H=2, M_E=2, d_bar=2)
    a = run_v3_replicate("v3smoke", 1, MASTER_SEED, p, tmp_path / "a", families=("ER",), R=2)
    b = run_v3_replicate("v3smoke", 1, MASTER_SEED, p, tmp_path / "b", families=("ER",), R=2)
    for name in TABLES:
        assert read_table(a, name).equals(read_table(b, name)), name
    manifest = json.loads((a / "manifest.json").read_text("utf-8"))
    assert manifest["schema_version"] == "3" and manifest["model_version"] == "V3"
