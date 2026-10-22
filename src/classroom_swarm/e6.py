"""Locked E6 structural robustness and full-factorial sensitivity plan."""
from __future__ import annotations

import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
from typing import Mapping, Sequence

import networkx as nx
import numpy as np
import pyarrow
import pyarrow as pa

from . import e5
from .analysis import spearman
from .experiment import _git_state
from .graphs import Graph, generate_graph
from .records import RunLog
from .rng import BIT_GENERATOR, FAMILY_CODE, RNG_SCHEME, STREAM_CODE, Draws, graph_seed
from .storage import write_replicate
from .v3 import V3Params, V3RunSpec, simulate_v3
from .v3_variants import E6Variant, simulate_variant

EXPERIMENT_ID = "E6"
STRUCTURAL_SEED = 920006
FACTORIAL_SEED = 920007
SMOKE_SEED = 920994
BOOT_SEED = 920600
SOURCE_NULL_SEED = 920601
BOOT_B = 10_000
SOURCE_NULL_B = 999
STRUCTURAL_REPLICATES = tuple(range(1, 401))
FACTORIAL_REPLICATES = tuple(range(1, 101))
SMOKE_REPLICATES = (1, 2)
PREREG = "docs/experiments/E6-preregistration.md"
LOCK = "docs/experiments/E6-lock.json"
MODEL_LOCK = "docs/V3-model-lock.json"
REPO = Path(__file__).resolve().parents[2]
FACTOR_NAMES = ("copy_cost", "eta_Q", "epsilon", "seed", "share_p0", "eta_A", "eta_social", "R")
PRIMARY = ("pC_late", "succ_late", "K_final", "source_resid_persist_strict", "multihop_rate")
DELTA = {**e5.DELTA, "source_resid_persist_strict": 0.10}


@dataclass(frozen=True)
class E6Condition:
    label: str
    params: V3Params = V3Params()
    R: int = 3
    variant: E6Variant | None = None


def structural_conditions() -> tuple[E6Condition, ...]:
    p = V3Params()
    return (
        E6Condition("E6-S-base", p),
        E6Condition("E6-S-homogeneous", replace(p, K0_sd=0.0, alpha_log_sd=0.0, kappa_log_sd=0.0)),
        E6Condition("E6-S-softmax010", p, variant=E6Variant("softmax", 0.10)),
        E6Condition("E6-S-softmax025", p, variant=E6Variant("softmax", 0.25)),
        E6Condition("E6-S-knowledgeReward", p, variant=E6Variant(reward_rule="knowledge_cost")),
        E6Condition("E6-S-noCostReward", p, variant=E6Variant(reward_rule="grade_no_cost")),
        E6Condition("E6-S-noAccessUtility", p, variant=E6Variant(access_utility=False)),
        E6Condition("E6-S-equalCost", replace(p, copy_success_cost=1)),
        E6Condition("E6-S-N15", replace(p, N=15)),
        E6Condition("E6-S-N120", replace(p, N=120)),
        E6Condition("E6-S-H10", replace(p, H=10)),
        E6Condition("E6-S-H80", replace(p, H=80)),
        E6Condition("E6-S-d2", replace(p, d_bar=2)),
        E6Condition("E6-S-d10", replace(p, d_bar=10)),
    )


STRUCTURAL_LABELS = tuple(c.label for c in structural_conditions())


def factorial_conditions() -> tuple[E6Condition, ...]:
    p = V3Params()
    out = []
    for bits in product((0, 1), repeat=8):
        params = replace(
            p, copy_success_cost=bits[0], eta_Q=0.40 if bits[1] else 0.0,
            epsilon=0.12 if bits[2] else 0.0, seed_fraction=0.20 if bits[3] else 0.0,
            share_p0=1.0 if bits[4] else 0.60, eta_A=0.40 if bits[5] else 0.0,
            eta_social=0.10 if bits[6] else 0.0,
        )
        out.append(E6Condition("E6-F-" + "".join(map(str, bits)), params, R=3 if bits[7] else 1))
    return tuple(out)


FACTORIAL_LABELS = tuple(c.label for c in factorial_conditions())


def bits_from_label(label: str) -> tuple[int, ...]:
    prefix = "E6-F-"
    if not label.startswith(prefix) or len(label) != len(prefix) + 8 or set(label[len(prefix):]) - {"0", "1"}:
        raise ValueError(f"invalid E6 factorial label {label!r}")
    return tuple(int(bit) for bit in label[len(prefix):])


def verify_lock(repo: Path = REPO) -> str:
    repo = Path(repo)
    lock = json.loads((repo / LOCK).read_text(encoding="utf-8"))
    digest = hashlib.sha256((repo / PREREG).read_bytes()).hexdigest()
    if digest != lock["sha256"]:
        raise RuntimeError(f"E6 preregistration SHA-256 {digest} != lock {lock['sha256']}")
    e5.verify_lock(repo)
    return digest


def _shared(block: str, replicate: int, master_seed: int, plan: Sequence[E6Condition]) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID, "block": block, "model_version": "V3/E6-variants",
        "replicate": replicate, "master_seed": master_seed, "rng_scheme": RNG_SCHEME,
        "bit_generator": BIT_GENERATOR, "stream_codes": dict(STREAM_CODE), "family_codes": dict(FAMILY_CODE),
        "R_max": 3, "preregistration_sha256": hashlib.sha256((REPO / PREREG).read_bytes()).hexdigest(),
        "v3_model_commit": json.loads((REPO / MODEL_LOCK).read_text(encoding="utf-8"))["git_commit"],
        "conditions": [{"label": c.label, "params": asdict(c.params), "R": c.R,
                        "variant": None if c.variant is None else asdict(c.variant)} for c in plan],
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "networkx": nx.__version__, "pyarrow": pyarrow.__version__}, **_git_state(),
    }


def _simulate_plan(plan: Sequence[E6Condition], replicate: int, master_seed: int) -> list[RunLog]:
    graphs: dict[tuple, Graph] = {}
    draws: dict[tuple[int, int, int], Draws] = {}
    logs = []
    for condition in plan:
        p = condition.params
        p.validate()
        graph_key = (p.N, p.d_bar, p.omega, p.sbm_ratio)
        if graph_key not in graphs:
            graphs[graph_key] = generate_graph("SBM", p, graph_seed(master_seed, replicate, "SBM"))
        graph = graphs[graph_key]
        draw_key = (p.N, p.M_H, p.M_E)
        if draw_key not in draws:
            draws[draw_key] = Draws(master_seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
        source = draws[draw_key]
        spec = V3RunSpec(condition.label, replicate, "SBM", condition.R, p, master_seed)
        log = simulate_v3(spec, graph, source) if condition.variant is None else simulate_variant(
            spec, graph, source, condition.variant)
        logs.append(log)
    return logs


def run_structural_replicate(replicate: int, master_seed: int, out_root: Path,
                             plan: Sequence[E6Condition] | None = None) -> Path:
    plan = tuple(structural_conditions() if plan is None else plan)
    rep_dir = Path(out_root) / f"rep{replicate:04d}"
    write_replicate(rep_dir, _simulate_plan(plan, replicate, master_seed),
                    _shared("structural", replicate, master_seed, plan))
    return rep_dir


def run_factorial_replicate(replicate: int, master_seed: int, out_root: Path,
                            shard_size: int = 16, *, resume: bool = False) -> list[Path]:
    plan = factorial_conditions()
    if shard_size < 1 or 256 % shard_size:
        raise ValueError("factorial shard_size must be a positive divisor of 256")
    paths = []
    for start in range(0, len(plan), shard_size):
        shard = plan[start:start + shard_size]
        shard_dir = Path(out_root) / f"rep{replicate:04d}" / f"shard{start // shard_size:02d}"
        if shard_dir.exists():
            if not resume:
                raise FileExistsError(f"refusing to overwrite existing factorial shard {shard_dir}")
            paths.append(shard_dir)
            continue
        write_replicate(shard_dir, _simulate_plan(shard, replicate, master_seed),
                        _shared("factorial", replicate, master_seed, shard))
        paths.append(shard_dir)
    return paths


def _strict_details(tables: Mapping[str, pa.Table], run_id: str) -> tuple[float | None, np.ndarray, np.ndarray]:
    nodes = sorted((r for r in tables["graph_nodes"].to_pylist() if r["run_id"] == run_id),
                   key=lambda r: r["student_id"])
    N = len(nodes)
    edges = [(r["u"], r["v"]) for r in tables["graph_edges"].to_pylist() if r["run_id"] == run_id]
    graph = nx.Graph()
    graph.add_nodes_from(range(N))
    graph.add_edges_from(edges)
    between = nx.betweenness_centrality(graph, normalized=True)
    traits = {r["student_id"]: r for r in tables["agent_traits"].to_pylist() if r["run_id"] == run_id}
    decisions = [r for r in tables["decisions"].to_pylist() if r["run_id"] == run_id]
    H = max(r["homework_index"] for r in decisions)
    midpoint = H // 2

    def counts(lo: int, hi: int) -> tuple[np.ndarray, np.ndarray]:
        roots, holders = Counter(), Counter()
        for row in decisions:
            h, student = row["homework_index"], row["student_id"]
            if not lo <= h <= hi:
                continue
            if row["action"] in {"S", "D"}:
                holders[student] += 1
            if row["action"] == "C" and row["copy_success"]:
                roots[row["root_id"]] += 1
        return np.array([roots[i] for i in range(N)], float), np.array([holders[i] for i in range(N)], float)

    first, hold_first = counts(2, midpoint)
    second, hold_second = counts(midpoint + 1, H)
    fixed = []
    for row in nodes:
        i, community = row["student_id"], row["community_id"]
        trait = traits[i]
        fixed.append([1.0, row["degree"], between[i], float(community == 0), float(community == 1),
                      trait["K0"], math.log(trait["alpha"]), math.log(trait["kappa"])])
    X = np.asarray(fixed, float)

    def residual(y: np.ndarray, holding: np.ndarray) -> np.ndarray:
        design = np.column_stack((X, holding))
        return y - design @ np.linalg.lstsq(design, y, rcond=None)[0]

    r_first, r_second = residual(first, hold_first), residual(second, hold_second)
    rho = spearman(r_first, r_second)
    return (float(rho) if math.isfinite(rho) else None), r_first, r_second


def run_summaries(tables: Mapping[str, pa.Table]) -> list[dict]:
    summaries = e5.run_summaries(tables)
    for summary in summaries:
        rho, _, _ = _strict_details(tables, summary["run_id"])
        summary["source_resid_persist_strict"] = rho
    return summaries


def source_null(tables: Mapping[str, pa.Table], run_id: str, replicate: int,
                permutations: int = SOURCE_NULL_B) -> dict:
    observed, first, second = _strict_details(tables, run_id)
    if observed is None:
        return {"run_id": run_id, "replicate": replicate, "rho": None, "p": None, "significant": None}
    rng = np.random.default_rng(np.random.SeedSequence([SOURCE_NULL_SEED, replicate]))
    exceed = 0
    for _ in range(permutations):
        rho = spearman(first, second[rng.permutation(len(second))])
        exceed += int(math.isfinite(rho) and rho >= observed)
    p_value = (1 + exceed) / (permutations + 1)
    return {"run_id": run_id, "replicate": replicate, "rho": observed,
            "p": p_value, "significant": p_value <= 0.05}


def factorial_effects(summaries: Sequence[Mapping], outcome: str, order: Sequence[int]) -> list[float]:
    """One within-replicate product-code effect per replicate for selected factor indices."""
    by_rep: dict[int, list[Mapping]] = defaultdict(list)
    for row in summaries:
        by_rep[row["replicate"]].append(row)
    effects = []
    for replicate in sorted(by_rep):
        positive, negative = [], []
        for row in by_rep[replicate]:
            bits = bits_from_label(row["experiment_id"])
            sign = math.prod(1 if bits[index] else -1 for index in order)
            value = row.get(outcome)
            if value is not None:
                (positive if sign > 0 else negative).append(float(value))
        effects.append(float(np.mean(positive) - np.mean(negative)) if positive and negative else float("nan"))
    return effects
