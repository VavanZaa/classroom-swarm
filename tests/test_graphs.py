"""T14 (graph generation) and T16 (degree-preserving null). docs/04, docs/09 graphs.py."""
import collections

import pytest

from classroom_swarm.config import Params
from classroom_swarm.graphs import (
    generate_er, generate_graph, generate_sbm, generate_ws, rewire_degree_preserving,
    sbm_probabilities, sbm_sizes, shuffle_edge_weights, with_edge_weights,
)


def _check_canonical(g):
    assert len(g.edges) == len(set(g.edges))
    assert all(u < v for u, v in g.edges)
    assert list(g.edges) == sorted(g.edges)
    for i, nb in enumerate(g.neighbors):
        assert list(nb) == sorted(nb) and i not in nb
    from_edges = collections.defaultdict(set)
    for u, v in g.edges:
        from_edges[u].add(v)
        from_edges[v].add(u)
    assert all(set(g.neighbors[i]) == from_edges[i] for i in range(g.N))
    assert g.degree == tuple(len(nb) for nb in g.neighbors)
    for u, v in g.edges:
        assert g.has_edge(u, v) and g.has_edge(v, u)
    assert len(g.weights) == len(g.edges)
    assert all(w > 0 for w in g.weights)
    assert all(len(g.neighbor_weights[i]) == len(g.neighbors[i]) for i in range(g.N))
    for edge, weight in zip(g.edges, g.weights):
        u, v = edge
        assert g.neighbor_weights[u][g.neighbors[u].index(v)] == weight
        assert g.neighbor_weights[v][g.neighbors[v].index(u)] == weight


@pytest.mark.parametrize("N,sizes", [(20, (7, 7, 6)), (30, (10, 10, 10)), (40, (14, 13, 13))])
def test_sbm_sizes(N, sizes):
    assert sbm_sizes(N) == sizes


@pytest.mark.parametrize("N,p_in,p_out", [(20, 0.7177, 0.1435), (30, 0.4615, 0.0923), (40, 0.3394, 0.0679)])
def test_sbm_probabilities_match_docs04_and_hit_mean_degree(N, p_in, p_out):
    sizes = sbm_sizes(N)
    got_in, got_out = sbm_probabilities(sizes, 6, 5)
    assert (got_in, got_out) == pytest.approx((p_in, p_out), abs=1e-4)
    assert got_in == pytest.approx(5 * got_out)
    expected_degree = sum(n * ((n - 1) * got_in + (N - n) * got_out) for n in sizes) / N
    assert expected_degree == pytest.approx(6.0, abs=1e-12)


def test_sbm_probabilities_reject_p_in_above_one():
    with pytest.raises(ValueError):
        sbm_probabilities((3, 3, 3), 6, 10)


def test_sbm_graph_structure():
    g = generate_sbm(30, 6, 5, seed=11)
    _check_canonical(g)
    assert g.family == "SBM" and g.N == 30
    assert sorted(collections.Counter(g.community).values()) == [10, 10, 10]


def test_ws_graph_structure_and_rules():
    g = generate_ws(30, 6, 0.1, seed=11)
    _check_canonical(g)
    assert len(g.edges) == 30 * 6 // 2  # rewiring keeps the edge count
    with pytest.raises(ValueError):
        generate_ws(30, 5, 0.1, seed=11)  # odd k (A14)
    with pytest.raises(ValueError):
        generate_ws(6, 6, 0.1, seed=11)   # k must be < N


def test_er_graph_structure():
    g = generate_er(30, 6, seed=11)
    _check_canonical(g)
    assert g.generator_params["p"] == pytest.approx(6 / 29)


@pytest.mark.parametrize("family", ["ER", "WS", "SBM"])
def test_generate_graph_is_deterministic_and_hash_is_stable(family):
    a = generate_graph(family, Params(), seed=7)
    b = generate_graph(family, Params(), seed=7)
    c = generate_graph(family, Params(), seed=8)
    assert a.edges == b.edges and a.edge_hash == b.edge_hash
    assert len(a.edge_hash) == 64 and all(ch in "0123456789abcdef" for ch in a.edge_hash)
    assert a.edge_hash != c.edge_hash
    assert a.weights == (1.0,) * len(a.edges)
    assert a.weight_hash == b.weight_hash
    assert len(a.weight_hash) == 64


def test_T26_explicit_weights_are_validated_and_hashed_separately():
    g = generate_er(12, 3, seed=7)
    values = tuple(1.0 + k / 10 for k in range(len(g.edges)))
    w = with_edge_weights(g, values)
    _check_canonical(w)
    assert w.edges == g.edges and w.edge_hash == g.edge_hash
    assert w.weights == values and w.weight_hash != g.weight_hash
    mapping = {edge: value for edge, value in zip(g.edges, values)}
    assert with_edge_weights(g, mapping) == w
    for bad in ((1.0,) * (len(g.edges) - 1), (0.0,) + values[1:], (float("inf"),) + values[1:]):
        with pytest.raises(ValueError):
            with_edge_weights(g, bad)
    with pytest.raises(ValueError):
        with_edge_weights(g, {**mapping, (0, g.N): 2.0})


def test_T26_weight_shuffle_preserves_topology_and_multiset():
    g = generate_er(20, 4, seed=8)
    weighted = with_edge_weights(g, tuple(float(k + 1) for k in range(len(g.edges))))
    a = shuffle_edge_weights(weighted, seed=99)
    b = shuffle_edge_weights(weighted, seed=99)
    assert a == b
    assert a.edges == weighted.edges and a.edge_hash == weighted.edge_hash
    assert sorted(a.weights) == sorted(weighted.weights)
    assert a.weights != weighted.weights
    assert a.generator_params["weight_null"] == "edge_shuffle"


def test_T26_degree_rewire_preserves_weight_multiset_even_on_a_tiny_graph():
    # With fewer than four nodes no swaps are possible, but a non-uniform weighted graph must still
    # pass through the null builder without losing or invalidating its weights.
    g = generate_er(3, 2, seed=1)
    weighted = with_edge_weights(g, (1.0, 2.0, 3.0))
    rewired, swaps = rewire_degree_preserving(weighted, seed=5)
    assert swaps == 0 and rewired.edges == weighted.edges
    assert sorted(rewired.weights) == sorted(weighted.weights)


def test_disconnected_graphs_are_kept_not_redrawn():
    # sparse ER makes isolates near-certain; the generator must return them as drawn
    summaries = [generate_er(30, 2, seed=s).summary() for s in range(10)]
    assert any(s["isolates"] > 0 for s in summaries)
    assert any(s["components"] > 1 for s in summaries)
    assert all({"mean_degree", "isolates", "components"} <= set(s) for s in summaries)


@pytest.mark.parametrize("family", ["ER", "WS", "SBM"])
def test_degree_preserving_rewiring(family):
    g = generate_graph(family, Params(), seed=3)
    r, swaps = rewire_degree_preserving(g, seed=5)
    _check_canonical(r)
    assert r.N == g.N and r.degree == g.degree          # every node id keeps its degree
    assert r.community == g.community                    # attributes stay on the same ids
    assert swaps > 0 and r.edges != g.edges
    r2, swaps2 = rewire_degree_preserving(g, seed=5)
    assert r2.edges == r.edges and swaps2 == swaps
