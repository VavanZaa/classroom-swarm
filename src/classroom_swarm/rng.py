"""Semantic, pre-generated randomness with stable stream codes (docs/05, docs/09 rng.py).

Every tensor is keyed by what it means (stream, homework or exam), never by consumption order:
`default_rng(SeedSequence([master_seed, replicate, stream_code, h_or_e]))`. Stream codes are fixed
integers, so adding a stream can never shift an existing one.
"""
from __future__ import annotations

import math
from typing import Protocol, Sequence

import numpy as np

RNG_SCHEME = "v1"
BIT_GENERATOR = "PCG64"
STREAM_CODE = {"graph": 1, "strategy": 2, "partner": 3, "item": 4, "routing": 5, "exam": 6, "null": 7,
               "exploration": 8, "traits": 9, "sharing": 10}
FAMILY_CODE = {"ER": 1, "WS": 2, "SBM": 3}


class DrawProvider(Protocol):
    """What simulate() needs from a source of uniforms (docs/09)."""

    R_max: int

    def strategy(self, h: int) -> np.ndarray: ...
    def partner(self, h: int) -> np.ndarray: ...
    def item(self, h: int) -> np.ndarray: ...
    def routing(self, h: int) -> np.ndarray: ...
    def exam(self, e: int) -> np.ndarray: ...
    def exploration(self, h: int) -> np.ndarray: ...
    def traits(self) -> np.ndarray: ...
    def sharing(self, h: int) -> np.ndarray: ...


def _check_seed_parts(master_seed: int, replicate: int) -> None:
    for name, value in (("master_seed", master_seed), ("replicate", replicate)):
        if not isinstance(value, (int, np.integer)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")


def _rng(master_seed: int, replicate: int, code: int, *key: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(entropy=[master_seed, replicate, code, *key]))


def _int_seed(master_seed: int, replicate: int, code: int, *key: int) -> int:
    ss = np.random.SeedSequence(entropy=[master_seed, replicate, code, *key])
    return int(ss.generate_state(1, dtype=np.uint32)[0])


class Draws:
    """Semantic uniforms for one replicate, shared by all its paired runs (every stage, R and family)."""

    def __init__(self, master_seed: int, replicate: int, N: int, M_H: int, M_E: int, R_max: int):
        _check_seed_parts(master_seed, replicate)
        for name, value in (("N", N), ("M_H", M_H), ("M_E", M_E), ("R_max", R_max)):
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be an integer >= 1")
        self.master_seed, self.replicate = int(master_seed), int(replicate)
        self.N, self.M_H, self.M_E, self.R_max = N, M_H, M_E, R_max
        self._cache: dict[tuple[str, int], np.ndarray] = {}

    def _tensor(self, stream: str, index: int, shape: tuple[int, ...]) -> np.ndarray:
        if not isinstance(index, (int, np.integer)) or index < 1:
            raise ValueError(f"{stream} index must be a 1-based integer, got {index!r}")
        key = (stream, int(index))
        if key not in self._cache:
            arr = _rng(self.master_seed, self.replicate, STREAM_CODE[stream], int(index)).random(shape)
            arr.setflags(write=False)
            self._cache[key] = arr
        return self._cache[key]

    def strategy(self, h: int) -> np.ndarray:
        return self._tensor("strategy", h, (self.N,))

    def partner(self, h: int) -> np.ndarray:
        return self._tensor("partner", h, (self.N,))

    def item(self, h: int) -> np.ndarray:
        return self._tensor("item", h, (self.M_H, self.N))

    def routing(self, h: int) -> np.ndarray:
        return self._tensor("routing", h, (self.R_max, self.N))  # a run with R uses rows [:R]

    def exam(self, e: int) -> np.ndarray:
        return self._tensor("exam", e, (self.M_E, self.N))

    def exploration(self, h: int) -> np.ndarray:
        return self._tensor("exploration", h, (self.N,))

    def traits(self) -> np.ndarray:
        key = ("traits", 0)
        if key not in self._cache:
            arr = _rng(self.master_seed, self.replicate, STREAM_CODE["traits"]).standard_normal((3, self.N))
            arr.setflags(write=False)
            self._cache[key] = arr
        return self._cache[key]

    def sharing(self, h: int) -> np.ndarray:
        return self._tensor("sharing", h, (self.R_max, self.N))


def graph_seed(master_seed: int, replicate: int, family: str) -> int:
    _check_seed_parts(master_seed, replicate)
    return _int_seed(master_seed, replicate, STREAM_CODE["graph"], FAMILY_CODE[family])


def null_seed(master_seed: int, replicate: int, family: str, ell: int) -> int:
    _check_seed_parts(master_seed, replicate)
    if not isinstance(ell, int) or ell < 0:
        raise ValueError("ell must be a non-negative integer")
    return _int_seed(master_seed, replicate, STREAM_CODE["null"], FAMILY_CODE[family], ell)


def pick(sorted_candidates: Sequence[int], u: float) -> int:
    """Map one uniform onto an already-sorted candidate list: candidates[floor(u * len)]."""
    if len(sorted_candidates) == 0:
        raise ValueError("pick() needs at least one candidate")
    if not 0.0 <= u < 1.0:
        raise ValueError(f"uniform must be in [0, 1), got {u!r}")
    return sorted_candidates[math.floor(u * len(sorted_candidates))]


def weighted_pick(sorted_candidates: Sequence[int], weights: Sequence[float], u: float) -> int:
    """Map one uniform through positive candidate weights aligned with sorted candidate ids (A20).

    Equal weights delegate to `pick`, making the historical unweighted mapping exact, including at
    floating-point boundaries.
    """
    if len(sorted_candidates) == 0:
        raise ValueError("weighted_pick() needs at least one candidate")
    if len(weights) != len(sorted_candidates):
        raise ValueError("weights must align one-for-one with candidates")
    if not 0.0 <= u < 1.0:
        raise ValueError(f"uniform must be in [0, 1), got {u!r}")
    values = [float(w) for w in weights]
    if any(not math.isfinite(w) or w <= 0.0 for w in values):
        raise ValueError("candidate weights must be positive finite numbers")
    if all(w == values[0] for w in values[1:]):
        return pick(sorted_candidates, u)
    target, cumulative = u * sum(values), 0.0
    for candidate, weight in zip(sorted_candidates, values):
        cumulative += weight
        if target < cumulative:
            return candidate
    return sorted_candidates[-1]  # rounding guard; u is strictly below 1
