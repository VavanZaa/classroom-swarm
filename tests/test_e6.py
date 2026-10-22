"""Locked E6 plan, variant parity, strict role metric and factorial-effect tests."""
from pathlib import Path

import numpy as np

from classroom_swarm import e6
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import TABLES
from classroom_swarm.rng import Draws, graph_seed
from classroom_swarm.storage import read_table
from classroom_swarm.v3 import V3Params, V3RunSpec, simulate_v3
from classroom_swarm.v3_variants import E6Variant, _choice_probabilities, simulate_variant


REPO = Path(__file__).resolve().parents[1]


def test_e6_lock_and_frozen_v3_are_intact():
    assert e6.verify_lock(REPO) == "f6aa7ac964c3ba276ff572721960e98694cfe7dd6fd7e9e9772c8ad5848d3800"


def test_e6_locked_condition_counts_and_factor_endpoints():
    structural, factorial = e6.structural_conditions(), e6.factorial_conditions()
    assert len(structural) == 14 and len(factorial) == 256
    assert tuple(c.label for c in structural) == e6.STRUCTURAL_LABELS
    assert tuple(c.label for c in factorial) == e6.FACTORIAL_LABELS
    low, high = factorial[0], factorial[-1]
    assert e6.bits_from_label(low.label) == (0,) * 8 and e6.bits_from_label(high.label) == (1,) * 8
    assert (low.params.copy_success_cost, low.params.eta_Q, low.params.epsilon, low.params.seed_fraction,
            low.params.share_p0, low.params.eta_A, low.params.eta_social, low.R) == (0, 0, 0, 0, .6, 0, 0, 1)
    assert (high.params.copy_success_cost, high.params.eta_Q, high.params.epsilon, high.params.seed_fraction,
            high.params.share_p0, high.params.eta_A, high.params.eta_social, high.R) == (1, .4, .12, .2, 1, .4, .1, 3)
    for condition in structural + factorial:
        condition.params.validate()


def test_e6_variant_default_has_exact_frozen_v3_tables():
    p = V3Params(N=9, H=5, F_E=5, M_H=3, M_E=3, d_bar=2)
    spec = V3RunSpec("e6parity", 1, "SBM", 3, p, e6.SMOKE_SEED)
    graph = generate_graph("SBM", p, graph_seed(e6.SMOKE_SEED, 1, "SBM"))
    frozen = simulate_v3(spec, graph, Draws(e6.SMOKE_SEED, 1, p.N, p.M_H, p.M_E, 3))
    variant = simulate_variant(spec, graph, Draws(e6.SMOKE_SEED, 1, p.N, p.M_H, p.M_E, 3), E6Variant())
    assert frozen.tables == variant.tables


def test_e6_softmax_probabilities_are_symmetric_and_normalized():
    U = np.array([[1.0, 2.0, 3.0], [5.0, 0.0, 0.0]])
    P = _choice_probabilities(U, np.array([True, False]), 0.06, E6Variant("softmax", 0.25))
    np.testing.assert_allclose(P.sum(axis=1), 1.0)
    assert P[0, 2] > P[0, 1] > P[0, 0] > 0
    np.testing.assert_array_equal(P[1], [1.0, 0.0, 0.0])


def test_e6_small_structural_round_trip_has_strict_source_metric(tmp_path):
    p = V3Params(N=9, H=6, F_E=3, M_H=3, M_E=3, d_bar=2)
    plan = (e6.E6Condition("E6-S-test", p),)
    rep_dir = e6.run_structural_replicate(1, e6.SMOKE_SEED, tmp_path, plan)
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    summaries = e6.run_summaries(tables)
    assert len(summaries) == 1 and "source_resid_persist_strict" in summaries[0]
    null = e6.source_null(tables, summaries[0]["run_id"], 1, permutations=9)
    assert set(null) == {"run_id", "replicate", "rho", "p", "significant"}


def test_e6_factorial_effect_uses_product_code_contrast():
    rows = []
    for replicate in (1, 2):
        for condition in e6.factorial_conditions():
            bits = e6.bits_from_label(condition.label)
            value = 2 * bits[0] + 3 * bits[1] + 5 * ((1 if bits[0] else -1) * (1 if bits[1] else -1))
            rows.append({"experiment_id": condition.label, "replicate": replicate, "y": value})
    np.testing.assert_allclose(e6.factorial_effects(rows, "y", (0,)), [2, 2])
    np.testing.assert_allclose(e6.factorial_effects(rows, "y", (1,)), [3, 3])
    np.testing.assert_allclose(e6.factorial_effects(rows, "y", (0, 1)), [10, 10])
