"""Locked E5 plan: prevalence-free V3 emergence experiment.

The authoritative design is docs/experiments/E5-preregistration.md. This module contains only the
machine-readable plan, integrity guards, experiment-level controls and derived E5 summaries.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

import networkx
import numpy as np
import pyarrow
import pyarrow as pa

from .analysis import bootstrap_indices, spearman
from .derive import cascade_extremes, exam_gaps, homework_trajectories, route_concentration
from .experiment import _git_state
from .graphs import Graph, generate_graph, shuffle_edge_weights, with_edge_weights
from .records import RunLog
from .rng import BIT_GENERATOR, FAMILY_CODE, RNG_SCHEME, STREAM_CODE, Draws, graph_seed, null_seed
from .storage import write_replicate
from .v3 import V3Controls, V3Params, V3RunSpec, simulate_v3

EXPERIMENT_ID = "E5"
SMOKE_ID = "E5-smoke"
MASTER_SEED = 920005
SMOKE_SEED = 920995
BOOT_SEED = 920500
BOOT_B = 10_000
REPLICATES = tuple(range(1, 401))
SMOKE_REPLICATES = (1, 2)
PREREG = "docs/experiments/E5-preregistration.md"
LOCK = "docs/experiments/E5-lock.json"
MODEL_LOCK = "docs/V3-model-lock.json"
WEIGHT_STREAM_CODE = 11
WEIGHT_LOG_SD = 0.5
REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class E5Condition:
    label: str
    params: V3Params = V3Params()
    family: str = "SBM"
    R: int = 3
    weight_mode: str = "unity"
    trait_shuffle: bool = False


def conditions() -> tuple[E5Condition, ...]:
    p = V3Params()
    return (
        E5Condition("E5-base", p),
        E5Condition("E5-seed0", replace(p, seed_fraction=0.0)),
        E5Condition("E5-seed05", replace(p, seed_fraction=0.05)),
        E5Condition("E5-seed20", replace(p, seed_fraction=0.20)),
        E5Condition("E5-eps0", replace(p, epsilon=0.0)),
        E5Condition("E5-etaA0", replace(p, eta_A=0.0)),
        E5Condition("E5-etaQ0", replace(p, eta_Q=0.0)),
        E5Condition("E5-copycost1", replace(p, copy_success_cost=1)),
        E5Condition("E5-traitshuffle", p, trait_shuffle=True),
        E5Condition("E5-unlimited", replace(p, share_capacity=p.N)),
        E5Condition("E5-share1", replace(p, share_p0=1.0)),
        E5Condition("E5-social010", replace(p, eta_social=0.10)),
        E5Condition("E5-weighted", p, weight_mode="weighted"),
        E5Condition("E5-weightshuffle", p, weight_mode="shuffled"),
        E5Condition("E5-ER", p, family="ER"),
        E5Condition("E5-WS", p, family="WS"),
        E5Condition("E5-R1", p, R=1),
        E5Condition("E5-H40", replace(p, H=40)),
        E5Condition("E5-N60", replace(p, N=60)),
    )


CONDITION_LABELS = tuple(c.label for c in conditions())

CONFIRMATORY = (
    "pC_late", "pC_change", "pC_postseed", "succ_late", "K_final", "dHK_late", "dGK_last",
    "Smax_mean", "Lmax_mean", "reach", "CF", "belief_sd_final", "source_top20", "source_gini",
    "source_resid_persist", "multihop_rate", "cascade5_rate", "capacity_denial_rate", "share_refusal_rate",
)
DELTA = {
    "pC_late": 0.02, "pC_change": 0.02, "pC_postseed": 0.02, "succ_late": 0.05,
    "K_final": 0.01, "dHK_late": 0.01, "dGK_last": 0.02, "Smax_mean": 1.0,
    "Lmax_mean": 0.25, "reach": 0.02, "CF": 0.05, "belief_sd_final": 0.02,
    "source_top20": 0.05, "source_gini": 0.05, "source_resid_persist": 0.10,
    "multihop_rate": 0.05, "cascade5_rate": 0.05, "capacity_denial_rate": 0.05,
    "share_refusal_rate": 0.05,
}


def verify_lock(repo: Path) -> str:
    repo = Path(repo)
    lock = json.loads((repo / LOCK).read_text(encoding="utf-8"))
    digest = hashlib.sha256((repo / PREREG).read_bytes()).hexdigest()
    if digest != lock["sha256"]:
        raise RuntimeError(f"E5 preregistration SHA-256 {digest} != lock {lock['sha256']}")
    model = json.loads((repo / MODEL_LOCK).read_text(encoding="utf-8"))
    for path_key, hash_key in (("specification", "specification_sha256"),
                               ("engine", "engine_sha256"), ("tests", "tests_sha256")):
        actual = hashlib.sha256((repo / model[path_key]).read_bytes()).hexdigest()
        if actual != model[hash_key]:
            raise RuntimeError(f"frozen V3 file changed: {model[path_key]}")
    if lock["model_commit"] != model["git_commit"]:
        raise RuntimeError("E5 and V3 model locks name different commits")
    return digest


def _base_graph(condition: E5Condition, replicate: int, master_seed: int) -> Graph:
    p = condition.params
    return generate_graph(condition.family, p, graph_seed(master_seed, replicate, condition.family))


def weighted_graph(graph: Graph, master_seed: int, replicate: int) -> Graph:
    """E5 locked independent mean-one lognormal edge weights on canonical edges."""
    ss = np.random.SeedSequence([master_seed, replicate, WEIGHT_STREAM_CODE,
                                 FAMILY_CODE[graph.family], graph.N])
    z = np.random.default_rng(ss).standard_normal(len(graph.edges))
    weights = np.exp(WEIGHT_LOG_SD * z - 0.5 * WEIGHT_LOG_SD ** 2)
    return with_edge_weights(graph, weights)


def condition_graph(condition: E5Condition, replicate: int, master_seed: int,
                    cache: dict[tuple, Graph] | None = None) -> Graph:
    p = condition.params
    key = (condition.family, p.N, p.d_bar, p.omega, p.sbm_ratio)
    if cache is not None and key in cache:
        base = cache[key]
    else:
        base = _base_graph(condition, replicate, master_seed)
        if cache is not None:
            cache[key] = base
    if condition.weight_mode == "unity":
        return base
    weighted = weighted_graph(base, master_seed, replicate)
    if condition.weight_mode == "weighted":
        return weighted
    if condition.weight_mode == "shuffled":
        return shuffle_edge_weights(weighted, null_seed(master_seed, replicate, condition.family, 501))
    raise ValueError(f"unknown E5 weight mode {condition.weight_mode!r}")


def condition_controls(condition: E5Condition, replicate: int, master_seed: int) -> V3Controls:
    if not condition.trait_shuffle:
        return V3Controls()
    seed = null_seed(master_seed, replicate, condition.family, 502)
    perm = tuple(int(x) for x in np.random.default_rng(seed).permutation(condition.params.N))
    return V3Controls(trait_permutation=perm)


def run_e5_replicate(replicate: int, master_seed: int, out_root: Path,
                     plan: Sequence[E5Condition] | None = None) -> Path:
    plan = tuple(conditions() if plan is None else plan)
    if len({c.label for c in plan}) != len(plan):
        raise ValueError("E5 condition labels must be unique")
    graph_cache: dict[tuple, Graph] = {}
    draws_cache: dict[tuple[int, int, int], Draws] = {}
    logs: list[RunLog] = []
    for c in plan:
        p = c.params
        p.validate()
        draw_key = (p.N, p.M_H, p.M_E)
        draws = draws_cache.setdefault(draw_key, Draws(master_seed, replicate, p.N, p.M_H, p.M_E, R_max=3))
        graph = condition_graph(c, replicate, master_seed, graph_cache)
        controls = condition_controls(c, replicate, master_seed)
        spec = V3RunSpec(c.label, replicate, c.family, c.R, p, master_seed)
        logs.append(simulate_v3(spec, graph, draws, controls=controls))
    shared = {
        "experiment_id": EXPERIMENT_ID if master_seed == MASTER_SEED else SMOKE_ID,
        "model_version": "V3", "replicate": replicate, "master_seed": master_seed,
        "rng_scheme": RNG_SCHEME, "bit_generator": BIT_GENERATOR, "stream_codes": dict(STREAM_CODE),
        "e5_weight_stream_code": WEIGHT_STREAM_CODE, "family_codes": dict(FAMILY_CODE), "R_max": 3,
        "preregistration_sha256": hashlib.sha256((REPO / PREREG).read_bytes()).hexdigest(),
        "v3_model_commit": json.loads((REPO / MODEL_LOCK).read_text(encoding="utf-8"))["git_commit"],
        "conditions": [asdict(c) for c in plan],
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "networkx": networkx.__version__, "pyarrow": pyarrow.__version__},
    }
    shared.update(_git_state())
    rep_dir = Path(out_root) / f"rep{replicate:04d}"
    write_replicate(rep_dir, logs, shared)
    return rep_dir


def _mean(values) -> float | None:
    values = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return sum(values) / len(values) if values else None


def _gini(counts: Sequence[int]) -> float | None:
    x = np.asarray(counts, float)
    total = float(x.sum())
    if total == 0:
        return None
    return float(np.abs(x[:, None] - x[None, :]).sum() / (2 * len(x) * total))


def _residuals(counts: np.ndarray, degree: np.ndarray) -> np.ndarray:
    X = np.column_stack((np.ones(len(degree)), degree))
    return counts - X @ np.linalg.lstsq(X, counts, rcond=None)[0]


def run_summaries(tables: Mapping[str, pa.Table]) -> list[dict]:
    """Locked E5 per-run outcomes reconstructed only from canonical raw tables."""
    traj = homework_trajectories(tables["decisions"], tables["state_snapshots"])
    gaps = exam_gaps(tables["decisions"], tables["item_outcomes"], tables["events"])
    casc = cascade_extremes(tables["decisions"])
    cf = route_concentration(tables["routing_events"], tables["graph_edges"])
    by_run: dict[str, dict[int, dict]] = defaultdict(dict)
    for (run_id, h), row in traj.items():
        by_run[run_id][h] = row
    decisions: dict[str, list[dict]] = defaultdict(list)
    for row in tables["decisions"].to_pylist():
        decisions[row["run_id"]].append(row)
    ties: dict[str, list[dict]] = defaultdict(list)
    for row in tables["tie_snapshots"].to_pylist():
        ties[row["run_id"]].append(row)
    sharing: dict[str, list[dict]] = defaultdict(list)
    for row in tables["sharing_events"].to_pylist():
        sharing[row["run_id"]].append(row)
    degrees: dict[str, dict[int, int]] = defaultdict(dict)
    for row in tables["graph_nodes"].to_pylist():
        degrees[row["run_id"]][row["student_id"]] = row["degree"]
    exams: dict[str, dict[int, dict]] = defaultdict(dict)
    for (run_id, e), row in gaps.items():
        exams[run_id][e] = row

    out = []
    for run_id in sorted(by_run):
        rows, drows = by_run[run_id], decisions[run_id]
        hs, N = sorted(rows), len(degrees[run_id])
        H, late_start = hs[-1], hs[-1] - 4
        early = [rows[h] for h in hs if 1 <= h <= 5]
        postseed = [rows[h] for h in hs if 2 <= h <= 5]
        late = [rows[h] for h in hs if late_start <= h <= H]
        n_c = sum(r["n_C"] for r in late)
        pC_late, pC_early = _mean(r["pC"] for r in late), _mean(r["pC"] for r in early)
        copied = [r for r in drows if r["action"] == "C" and r["copy_success"]]
        late_copied = [r for r in copied if late_start <= r["homework_index"] <= H]
        root_late = Counter(r["root_id"] for r in late_copied)
        root_counts = np.array([root_late[i] for i in range(N)], float)
        k = math.ceil(0.2 * N)
        source_top20 = (sum(sorted(root_counts, reverse=True)[:k]) / root_counts.sum()
                        if root_counts.sum() else None)
        midpoint = H // 2
        root_first = Counter(r["root_id"] for r in copied if 2 <= r["homework_index"] <= midpoint)
        root_second = Counter(r["root_id"] for r in copied if midpoint < r["homework_index"] <= H)
        degree = np.array([degrees[run_id][i] for i in range(N)], float)
        residual_first = _residuals(np.array([root_first[i] for i in range(N)], float), degree)
        residual_second = _residuals(np.array([root_second[i] for i in range(N)], float), degree)
        persistence = spearman(residual_first, residual_second)
        if not math.isfinite(persistence):
            persistence = None
        multihop = [any(r["homework_index"] == h and r["depth"] >= 2 for r in late_copied)
                    for h in range(late_start, H + 1)]
        cascade5 = []
        for h in range(late_start, H + 1):
            roots = Counter(r["root_id"] for r in late_copied if r["homework_index"] == h)
            cascade5.append(max(roots.values(), default=0) >= 5)
        final_ties = [r["A"] for r in ties[run_id] if r["event_id"] == f"h{H}"]
        late_shares = [r for r in sharing[run_id] if late_start <= r["homework_index"] <= H]
        willing = [r for r in late_shares if r["target_had_packet"] and r["willing"]]
        available = [r for r in late_shares if r["target_had_packet"]]
        run_exams = exams.get(run_id, {})
        identity = run_id.split("/")
        summary = {
            "run_id": run_id, "experiment_id": identity[0], "replicate": int(identity[1][3:]),
            "family": identity[2], "R": int(identity[3][1:]), "stage": identity[4], "N": N, "H": H,
            "pC_late": pC_late,
            "pC_change": None if pC_late is None or pC_early is None else pC_late - pC_early,
            "pC_postseed": _mean(r["pC"] for r in postseed),
            "succ_late": sum(r["n_succ"] for r in late) / n_c if n_c else None,
            "K_final": rows[H]["K_mean"], "dHK_late": _mean(r["dHK"] for r in late),
            "dGK_last": _mean(run_exams[e]["dGK_last"] for e in sorted(run_exams)),
            "Smax_mean": _mean(casc[(run_id, h)][0] for h in hs),
            "Lmax_mean": _mean(casc[(run_id, h)][1] for h in hs),
            "reach": _mean(rows[h]["reach"] for h in hs), "CF": cf.get(run_id),
            "belief_sd_final": float(np.std(final_ties, ddof=0)) if final_ties else None,
            "source_top20": source_top20, "source_gini": _gini(root_counts),
            "source_resid_persist": persistence,
            "multihop_rate": float(np.mean(multihop)), "cascade5_rate": float(np.mean(cascade5)),
            "capacity_denial_rate": (sum(not r["share_granted"] for r in willing) / len(willing)
                                     if willing else None),
            "share_refusal_rate": (sum(not r["willing"] for r in available) / len(available)
                                   if available else None),
        }
        out.append(summary)
    return out


def mean_ci(summaries: Sequence[Mapping], label: str, outcome: str, boot: np.ndarray) -> dict:
    rows = sorted((s for s in summaries if s["experiment_id"] == label), key=lambda s: s["replicate"])
    if boot.shape[1] != len(rows):
        raise ValueError("bootstrap matrix does not match E5 replicate count")
    values = np.array([np.nan if s.get(outcome) is None else s[outcome] for s in rows], float)
    with np.errstate(invalid="ignore"):
        estimates = np.nanmean(values[boot], axis=1)
    finite = estimates[np.isfinite(estimates)]
    lo, hi = np.percentile(finite, [2.5, 97.5]) if len(finite) else (np.nan, np.nan)
    return {"condition": label, "outcome": outcome, "n": int(np.isfinite(values).sum()),
            "estimate": float(np.nanmean(values)) if np.isfinite(values).any() else None,
            "lo": float(lo), "hi": float(hi)}


ABSOLUTE_CRITERIA = (
    ("baseline_persistence", "E5-base", "pC_late", 0.04),
    ("seed_free_entry", "E5-seed0", "pC_late", 0.04),
    ("seed_only_persistence", "E5-eps0", "pC_late", 0.02),
    ("cost_independent_persistence", "E5-copycost1", "pC_late", 0.04),
    ("persistent_source_roles", "E5-base", "source_resid_persist", 0.20),
    ("multihop_routing", "E5-base", "multihop_rate", 0.10),
    ("large_repeated_root_events", "E5-base", "cascade5_rate", 0.10),
)


def absolute_tests(summaries: Sequence[Mapping], boot: np.ndarray) -> list[dict]:
    out = []
    for name, label, outcome, threshold in ABSOLUTE_CRITERIA:
        result = mean_ci(summaries, label, outcome, boot)
        result.update(name=name, threshold=threshold,
                      passed=bool(math.isfinite(result["lo"]) and result["lo"] > threshold))
        out.append(result)
    return out
