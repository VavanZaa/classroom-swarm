"""Static classroom graphs (docs/04, docs/09 graphs.py).

Wrappers around NetworkX generators: our code owns parameters, canonical form, reproducibility and
validation, not the generation algorithms. Graphs are never redrawn (disconnected graphs and
isolated students are kept).
"""
from __future__ import annotations

import bisect
import hashlib
import math
import random
from dataclasses import dataclass
from typing import Mapping, Sequence

import networkx as nx

from .config import FAMILIES, Params


@dataclass(frozen=True, eq=True)
class Graph:
    family: str
    N: int
    generator_params: Mapping[str, float | int | str]
    seed: int
    edges: tuple[tuple[int, int], ...]        # sorted, u < v
    neighbors: tuple[tuple[int, ...], ...]    # sorted ascending per node
    community: tuple[int, ...] | None         # SBM only
    weights: tuple[float, ...] | None = None  # A20: positive, aligned with edges; None -> all 1

    __hash__ = None  # generator_params is a mapping; graphs are compared, not hashed

    def __post_init__(self) -> None:
        weights = (1.0,) * len(self.edges) if self.weights is None else tuple(float(w) for w in self.weights)
        if len(weights) != len(self.edges):
            raise ValueError("weights must have exactly one value per canonical edge")
        if any(not math.isfinite(w) or w <= 0.0 for w in weights):
            raise ValueError("edge weights must be positive finite numbers")
        object.__setattr__(self, "weights", weights)

    @property
    def degree(self) -> tuple[int, ...]:
        return tuple(len(nb) for nb in self.neighbors)

    @property
    def edge_hash(self) -> str:
        """SHA-256 of the canonical edge list, one 'u v' line per edge."""
        text = "".join(f"{u} {v}\n" for u, v in self.edges)
        return hashlib.sha256(text.encode("ascii")).hexdigest()

    @property
    def weight_hash(self) -> str:
        """SHA-256 of canonical topology plus exact binary-float text for every aligned weight."""
        text = "".join(f"{u} {v} {float(w).hex()}\n" for (u, v), w in zip(self.edges, self.weights))
        return hashlib.sha256(text.encode("ascii")).hexdigest()

    @property
    def neighbor_weights(self) -> tuple[tuple[float, ...], ...]:
        """Weights aligned with each node's sorted `neighbors` tuple (A20)."""
        by_edge = {edge: weight for edge, weight in zip(self.edges, self.weights)}
        return tuple(tuple(by_edge[(min(i, j), max(i, j))] for j in nb)
                     for i, nb in enumerate(self.neighbors))

    @property
    def strength(self) -> tuple[float, ...]:
        return tuple(sum(row) for row in self.neighbor_weights)

    def has_edge(self, u: int, v: int) -> bool:
        nb = self.neighbors[u]
        k = bisect.bisect_left(nb, v)
        return k < len(nb) and nb[k] == v

    def summary(self) -> dict:
        degrees = self.degree
        seen, components = [False] * self.N, 0
        for start in range(self.N):
            if seen[start]:
                continue
            components += 1
            stack, seen[start] = [start], True
            while stack:
                for w in self.neighbors[stack.pop()]:
                    if not seen[w]:
                        seen[w] = True
                        stack.append(w)
        return {
            "mean_degree": (2 * len(self.edges) / self.N) if self.N else 0.0,
            "mean_strength": (sum(self.strength) / self.N) if self.N else 0.0,
            "isolates": sum(1 for d in degrees if d == 0),
            "components": components,
        }


def _from_edges(family: str, N: int, generator_params: Mapping[str, float | int | str], seed: int,
                edge_iter, community: Sequence[int] | None = None,
                weights: Sequence[float] | None = None) -> Graph:
    edges = sorted({(min(u, v), max(u, v)) for u, v in edge_iter if u != v})
    if weights is not None and len(weights) != len(edges):
        raise ValueError("weights must align with the canonical edge list")
    nbrs: list[list[int]] = [[] for _ in range(N)]
    for u, v in edges:
        nbrs[u].append(v)
        nbrs[v].append(u)
    return Graph(family=family, N=N, generator_params=dict(generator_params), seed=int(seed),
                 edges=tuple((int(u), int(v)) for u, v in edges),
                 neighbors=tuple(tuple(sorted(int(x) for x in nb)) for nb in nbrs),
                 community=None if community is None else tuple(int(c) for c in community),
                 weights=None if weights is None else tuple(float(w) for w in weights))


def with_edge_weights(graph: Graph,
                      weights: Mapping[tuple[int, int], float] | Sequence[float]) -> Graph:
    """Return the same frozen topology with explicit A20 contact weights.

    A sequence is aligned with `graph.edges`. A mapping must cover exactly those canonical edges.
    """
    if isinstance(weights, Mapping):
        canonical: dict[tuple[int, int], float] = {}
        for edge, weight in weights.items():
            if not isinstance(edge, tuple) or len(edge) != 2:
                raise ValueError("weight mapping keys must be (u, v) edge tuples")
            u, v = edge
            if not isinstance(u, int) or not isinstance(v, int) or u == v:
                raise ValueError("weight mapping keys must be distinct integer node ids")
            key = (min(u, v), max(u, v))
            if key in canonical:
                raise ValueError(f"duplicate undirected weight for edge {key}")
            canonical[key] = weight
        if set(canonical) != set(graph.edges):
            raise ValueError("weight mapping must cover exactly the graph's canonical edges")
        values = tuple(canonical[edge] for edge in graph.edges)
    else:
        values = tuple(weights)
    return Graph(graph.family, graph.N, dict(graph.generator_params), graph.seed, graph.edges,
                 graph.neighbors, graph.community, values)


def shuffle_edge_weights(graph: Graph, seed: int) -> Graph:
    """A20 null: fixed topology, deterministic permutation of the global edge-weight multiset."""
    values = list(graph.weights)
    random.Random(seed).shuffle(values)
    params = dict(graph.generator_params)
    params.update({"weight_null": "edge_shuffle", "weight_null_seed": int(seed)})
    return Graph(graph.family, graph.N, params, graph.seed, graph.edges, graph.neighbors,
                 graph.community, tuple(values))


def sbm_sizes(N: int, blocks: int = 3) -> tuple[int, ...]:
    """Near-equal block sizes at every N (A13): 7/7/6, 10/10/10, 14/13/13."""
    if not isinstance(N, int) or not isinstance(blocks, int) or blocks < 1 or N < blocks:
        raise ValueError("need integers with N >= blocks >= 1")
    return tuple(N // blocks + (1 if g < N % blocks else 0) for g in range(blocks))


def sbm_probabilities(sizes: Sequence[int], d_bar: float, r: float) -> tuple[float, float]:
    """(p_in, p_out) hitting mean degree d_bar with p_in / p_out = r (A13)."""
    if d_bar <= 0 or r <= 0 or len(sizes) < 1 or min(sizes) < 1:
        raise ValueError("need d_bar > 0, r > 0 and positive block sizes")
    N = sum(sizes)
    w = sum(n * (n - 1) for n in sizes) / N
    b = N - 1 - w
    denominator = r * w + b
    if denominator <= 0:
        raise ValueError("block structure admits no edges")
    p_out = d_bar / denominator
    p_in = r * p_out
    if p_in > 1.0 or p_out > 1.0:
        raise ValueError(f"p_in = {p_in:.4f} > 1: d_bar {d_bar} with r {r} is infeasible for sizes {tuple(sizes)}")
    return p_in, p_out


def generate_er(N: int, d_bar: float, seed: int) -> Graph:
    if N < 2:
        raise ValueError("ER needs N >= 2")
    p = d_bar / (N - 1)
    if not 0.0 < p <= 1.0:
        raise ValueError(f"d_bar {d_bar} gives edge probability {p} outside (0, 1]")
    G = nx.gnp_random_graph(N, p, seed=seed)
    return _from_edges("ER", N, {"d_bar": d_bar, "p": p}, seed, G.edges())


def generate_ws(N: int, d_bar: int, omega: float, seed: int) -> Graph:
    if not isinstance(d_bar, int) or d_bar < 2 or d_bar % 2 != 0:
        raise ValueError("WS needs an even integer k = d_bar >= 2 (A14)")
    if d_bar >= N:
        raise ValueError("WS needs k = d_bar < N")
    if not 0.0 <= omega <= 1.0:
        raise ValueError("omega must be in [0, 1]")
    G = nx.watts_strogatz_graph(N, d_bar, omega, seed=seed)
    return _from_edges("WS", N, {"d_bar": d_bar, "k": d_bar, "omega": omega}, seed, G.edges())


def generate_sbm(N: int, d_bar: float, r: float, seed: int) -> Graph:
    sizes = sbm_sizes(N)
    p_in, p_out = sbm_probabilities(sizes, d_bar, r)
    P = [[p_in if a == b else p_out for b in range(len(sizes))] for a in range(len(sizes))]
    G = nx.stochastic_block_model(list(sizes), P, seed=seed)
    community = [G.nodes[i]["block"] for i in range(N)]
    return _from_edges("SBM", N, {"d_bar": d_bar, "r": r, "p_in": p_in, "p_out": p_out}, seed,
                       G.edges(), community)


def generate_graph(family: str, params: Params, seed: int) -> Graph:
    if family not in FAMILIES:
        raise ValueError(f"family must be one of {FAMILIES}")
    if family == "ER":
        return generate_er(params.N, params.d_bar, seed)
    if family == "WS":
        return generate_ws(params.N, params.d_bar, params.omega, seed)
    return generate_sbm(params.N, params.d_bar, params.sbm_ratio, seed)


def rewire_degree_preserving(graph: Graph, seed: int, nswap_factor: int = 10,
                             max_tries_factor: int = 100) -> tuple[Graph, int]:
    """Degree-preserving null (A8): double-edge swaps, connectivity not imposed.

    Returns (rewired graph, swaps actually performed). Node ids, degrees and community labels are
    unchanged. If the swap budget runs out early, the partial result is returned with its true count.
    """
    G = nx.Graph()
    G.add_nodes_from(range(graph.N))
    G.add_edges_from(graph.edges)
    nswap = nswap_factor * len(graph.edges)
    swaps = 0
    rng = random.Random(seed)
    if graph.N >= 4 and len(graph.edges) >= 2:
        for _ in range(nswap):
            try:
                nx.double_edge_swap(G, nswap=1, max_tries=max_tries_factor, seed=rng)
            except nx.NetworkXAlgorithmError:
                break  # budget exhausted: keep the partial rewiring, report the true count
            swaps += 1
    params = dict(graph.generator_params)
    params.update({"null_nswap_target": nswap, "null_swaps": swaps})
    new_edges = sorted((min(u, v), max(u, v)) for u, v in G.edges())
    weights = list(graph.weights)
    if len(set(weights)) > 1:
        rng.shuffle(weights)  # preserve the global multiset; this is not a strength-preserving null
    return _from_edges(graph.family, graph.N, params, seed, new_edges, graph.community, weights), swaps
