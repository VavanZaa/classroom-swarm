"""T8 (draw part): semantic, pre-generated uniforms with stable stream codes. docs/05, docs/09 rng.py."""
import inspect

import numpy as np
import pytest

from classroom_swarm.rng import FAMILY_CODE, RNG_SCHEME, STREAM_CODE, Draws, graph_seed, null_seed, pick, weighted_pick

MASTER, REP, N, M_H, M_E = 20260918, 3, 30, 10, 30


def _expected(code, key, shape):
    ss = np.random.SeedSequence(entropy=[MASTER, REP, code, key])
    return np.random.default_rng(ss).random(shape)


def test_scheme_constants_are_stable():
    assert RNG_SCHEME == "v1"
    assert STREAM_CODE == {"graph": 1, "strategy": 2, "partner": 3, "item": 4, "routing": 5, "exam": 6,
                           "null": 7, "exploration": 8, "traits": 9, "sharing": 10}
    assert FAMILY_CODE == {"ER": 1, "WS": 2, "SBM": 3}


def test_tensors_follow_the_documented_derivation():
    d = Draws(MASTER, REP, N, M_H, M_E, R_max=3)
    for h in (1, 2, 20):
        np.testing.assert_array_equal(d.strategy(h), _expected(2, h, (N,)))
        np.testing.assert_array_equal(d.partner(h), _expected(3, h, (N,)))
        np.testing.assert_array_equal(d.item(h), _expected(4, h, (M_H, N)))
        np.testing.assert_array_equal(d.routing(h), _expected(5, h, (3, N)))
        np.testing.assert_array_equal(d.exploration(h), _expected(8, h, (N,)))
        np.testing.assert_array_equal(d.sharing(h), _expected(10, h, (3, N)))
    for e in (1, 4):
        np.testing.assert_array_equal(d.exam(e), _expected(6, e, (M_E, N)))
    expected_traits = np.random.default_rng(np.random.SeedSequence(entropy=[MASTER, REP, 9])).standard_normal((3, N))
    np.testing.assert_array_equal(d.traits(), expected_traits)


def test_shapes_and_range():
    d = Draws(MASTER, REP, N, M_H, M_E, R_max=5)
    assert d.strategy(1).shape == (N,) and d.partner(1).shape == (N,)
    assert d.item(1).shape == (M_H, N) and d.routing(1).shape == (5, N) and d.exam(1).shape == (M_E, N)
    for arr in (d.strategy(1), d.item(1), d.routing(1), d.exam(1), d.exploration(1), d.sharing(1)):
        assert arr.min() >= 0.0 and arr.max() < 1.0
    assert d.traits().shape == (3, N) and np.isfinite(d.traits()).all()


def test_routing_rows_are_paired_across_R_max():
    one = Draws(MASTER, REP, N, M_H, M_E, R_max=1)
    three = Draws(MASTER, REP, N, M_H, M_E, R_max=3)
    for h in (1, 7):
        np.testing.assert_array_equal(one.routing(h), three.routing(h)[:1])


def test_draws_are_deterministic_and_streams_distinct():
    a = Draws(MASTER, REP, N, M_H, M_E, R_max=3)
    b = Draws(MASTER, REP, N, M_H, M_E, R_max=3)
    np.testing.assert_array_equal(a.item(5), b.item(5))
    assert not np.array_equal(a.strategy(5), a.partner(5))
    assert not np.array_equal(a.strategy(5), a.strategy(6))
    other_rep = Draws(MASTER, REP + 1, N, M_H, M_E, R_max=3)
    assert not np.array_equal(a.strategy(5), other_rep.strategy(5))


def test_draws_are_shared_across_graph_families():
    # one Draws per replicate for every family is intentional (docs/05, docs/09)
    assert "family" not in inspect.signature(Draws).parameters


def test_graph_and_null_seeds():
    assert graph_seed(MASTER, REP, "SBM") == graph_seed(MASTER, REP, "SBM")
    assert len({graph_seed(MASTER, REP, f) for f in ("ER", "WS", "SBM")}) == 3
    assert graph_seed(MASTER, REP, "SBM") != graph_seed(MASTER, REP + 1, "SBM")
    assert len({null_seed(MASTER, REP, "SBM", ell) for ell in range(50)}) == 50
    assert isinstance(graph_seed(MASTER, REP, "ER"), int)


def test_pick_maps_uniform_onto_sorted_candidates():
    assert pick([2, 5, 9], 0.0) == 2
    assert pick([2, 5, 9], 0.34) == 5
    assert pick([2, 5, 9], 0.999999) == 9
    assert pick([4], 0.5) == 4
    with pytest.raises(ValueError):
        pick([], 0.5)


def test_T26_weighted_pick_uses_cumulative_weights_and_uniform_is_legacy_exact():
    candidates = [2, 5, 9]
    assert weighted_pick(candidates, [8.0, 1.0, 1.0], 0.0) == 2
    assert weighted_pick(candidates, [8.0, 1.0, 1.0], 0.79) == 2
    assert weighted_pick(candidates, [8.0, 1.0, 1.0], 0.80) == 5
    assert weighted_pick(candidates, [8.0, 1.0, 1.0], 0.95) == 9
    for u in (0.0, 0.1, 0.34, 0.66, 0.999999):
        assert weighted_pick(candidates, [1.0, 1.0, 1.0], u) == pick(candidates, u)
    with pytest.raises(ValueError):
        weighted_pick([], [], 0.5)
    with pytest.raises(ValueError):
        weighted_pick([1, 2], [1.0], 0.5)
    with pytest.raises(ValueError):
        weighted_pick([1, 2], [1.0, 0.0], 0.5)
