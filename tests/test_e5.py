"""E5 locked-plan, integrity, controls, summaries and runner tests."""
from pathlib import Path

import numpy as np

from classroom_swarm import e5
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import TABLES
from classroom_swarm.rng import graph_seed
from classroom_swarm.storage import read_table
from classroom_swarm.v3 import V3Params


REPO = Path(__file__).resolve().parents[1]


def test_e5_lock_and_frozen_model_are_intact():
    assert e5.verify_lock(REPO) == "02c9fece032cd3a556b6c3e1b3e2b760c6d89bafbf0f243139cce3e4801ca94f"


def test_e5_plan_exactly_matches_the_locked_19_conditions():
    plan = e5.conditions()
    assert len(plan) == 19 and tuple(c.label for c in plan) == e5.CONDITION_LABELS
    by_label = {c.label: c for c in plan}
    assert by_label["E5-base"].params == V3Params()
    assert by_label["E5-copycost1"].params.copy_success_cost == 1
    assert by_label["E5-H40"].params.H == 40 and by_label["E5-N60"].params.N == 60
    assert by_label["E5-weighted"].weight_mode == "weighted"
    assert by_label["E5-weightshuffle"].weight_mode == "shuffled"


def test_e5_weight_construction_is_reproducible_and_shuffle_preserves_multiset():
    p = V3Params()
    graph = generate_graph("SBM", p, graph_seed(e5.MASTER_SEED, 1, "SBM"))
    weighted_a = e5.weighted_graph(graph, e5.MASTER_SEED, 1)
    weighted_b = e5.weighted_graph(graph, e5.MASTER_SEED, 1)
    shuffled = e5.condition_graph(next(c for c in e5.conditions() if c.label == "E5-weightshuffle"),
                                   1, e5.MASTER_SEED)
    assert weighted_a.weights == weighted_b.weights
    assert all(weight > 0 for weight in weighted_a.weights)
    assert sorted(weighted_a.weights) == sorted(shuffled.weights)
    assert weighted_a.edges == shuffled.edges == graph.edges


def test_e5_small_replicate_round_trip_and_summaries(tmp_path):
    p = V3Params(N=9, H=5, F_E=5, M_H=3, M_E=3, d_bar=2)
    plan = (e5.E5Condition("T-base", p), e5.E5Condition("T-seed0", p.__class__(
        **{**p.__dict__, "seed_fraction": 0.0})))
    rep_dir = e5.run_e5_replicate(1, e5.SMOKE_SEED, tmp_path, plan)
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    summaries = e5.run_summaries(tables)
    assert len(summaries) == 2 and {s["experiment_id"] for s in summaries} == {"T-base", "T-seed0"}
    assert all(s["N"] == 9 and s["H"] == 5 for s in summaries)
    assert all(set(e5.CONFIRMATORY) <= set(s) for s in summaries)


def test_e5_absolute_rules_use_locked_lower_ci_thresholds():
    labels = {label for _, label, _, _ in e5.ABSOLUTE_CRITERIA}
    summaries = []
    for replicate in range(1, 5):
        for label in labels:
            summaries.append({
                "experiment_id": label, "replicate": replicate, "pC_late": 0.50,
                "source_resid_persist": 0.50, "multihop_rate": 0.50, "cascade5_rate": 0.50,
            })
    boot = np.tile(np.arange(4), (20, 1))
    results = e5.absolute_tests(summaries, boot)
    assert len(results) == 7 and all(row["passed"] for row in results)
