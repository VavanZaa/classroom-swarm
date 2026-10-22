"""Run summaries, paired contrasts, interpretation, validity, convergence and broker scores.

Implements docs/experiments/E1-preregistration.md §4-§8 and §4b. Pure functions over derived
quantities; nothing here simulates or reads files.
"""
from __future__ import annotations

import math
import warnings
from collections import defaultdict
from typing import Mapping, Sequence

import numpy as np
import pyarrow as pa

from .derive import cascade_extremes, exam_gaps, homework_trajectories, route_concentration

SCALARS = ("pC_late", "pC_change", "succ_late", "K_final", "VarK_final", "dHK_late", "dHK_mean",
           "dGK_last", "dGK_block", "Smax_mean", "Lmax_mean", "reach", "CF", "P_C_last", "tipped")
TIPPING_LEVEL = 0.5  # a classroom "tipped" if its late copying rate exceeds this (E4)


def parse_run_id(run_id: str) -> dict:
    experiment_id, rep, family, R, stage = run_id.split("/")
    return {"experiment_id": experiment_id, "replicate": int(rep[3:]), "family": family, "R": int(R[1:]),
            "stage": stage}


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def run_summaries(tables: Mapping[str, pa.Table], early: tuple[int, int] = (1, 5),
                  late: tuple[int, int] = (16, 20)) -> list[dict]:
    """One dict per run: run identity plus every E1 scalar (§4). Missing values are None."""
    traj = homework_trajectories(tables["decisions"], tables["state_snapshots"])
    gaps = exam_gaps(tables["decisions"], tables["item_outcomes"], tables["events"])
    casc = cascade_extremes(tables["decisions"])
    cf = route_concentration(tables["routing_events"], tables["graph_edges"])
    by_run: dict[str, dict[int, dict]] = defaultdict(dict)
    for (run_id, h), row in traj.items():
        by_run[run_id][h] = row
    exams_by_run: dict[str, dict[int, dict]] = defaultdict(dict)
    for (run_id, e), row in gaps.items():
        exams_by_run[run_id][e] = row

    out = []
    for run_id in sorted(by_run):
        rows = by_run[run_id]
        hs = sorted(rows)
        H = hs[-1]
        window = lambda lo, hi: [rows[h] for h in hs if lo <= h <= hi]
        late_rows, early_rows = window(*late), window(*early)
        n_c = sum(r["n_C"] for r in late_rows)
        pC_late = _mean(r["pC"] for r in late_rows)
        pC_early = _mean(r["pC"] for r in early_rows)
        exams = exams_by_run.get(run_id, {})
        summary = {
            "run_id": run_id, **parse_run_id(run_id),
            "pC_late": pC_late,
            "pC_change": None if pC_late is None or pC_early is None else pC_late - pC_early,
            "succ_late": sum(r["n_succ"] for r in late_rows) / n_c if n_c else None,
            "K_final": rows[H]["K_mean"], "VarK_final": rows[H]["K_var"],
            "dHK_late": _mean(r["dHK"] for r in late_rows),
            "dHK_mean": _mean(rows[h]["dHK"] for h in hs),
            "dGK_last": _mean(exams[e]["dGK_last"] for e in sorted(exams)),
            "dGK_block": _mean(exams[e]["dGK_block"] for e in sorted(exams)),
            "Smax_mean": _mean(casc[(run_id, h)][0] for h in hs),
            "Lmax_mean": _mean(casc[(run_id, h)][1] for h in hs),
            "reach": _mean(rows[h]["reach"] for h in hs),
            "CF": cf.get(run_id),
            "P_C_last": rows[H]["pC"],
            "tipped": None if pC_late is None else float(pC_late > TIPPING_LEVEL),
        }
        for e in sorted(exams):
            summary[f"dGK_last_e{e}"] = exams[e]["dGK_last"]
            summary[f"dGK_block_e{e}"] = exams[e]["dGK_block"]
        out.append(summary)
    return out


def bootstrap_indices(n: int, B: int = 10_000, seed: int = 918100) -> np.ndarray:
    """One shared (B, n) matrix of resampled replicate positions (E1 §5, §4b.3)."""
    return np.random.default_rng(seed).integers(0, n, size=(B, n))


CONDITION_KEY = ("stage", "R", "family")


def _values_by_replicate(summaries: Sequence[Mapping], outcome: str, cond: tuple,
                         key: tuple[str, ...] = CONDITION_KEY) -> dict[int, float | None]:
    return {s["replicate"]: s.get(outcome) for s in summaries if tuple(s[k] for k in key) == tuple(cond)}


def _percentile_ci(stats: np.ndarray) -> tuple[float, float]:
    stats = stats[~np.isnan(stats)]
    if stats.size == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


def paired_contrast(summaries: Sequence[Mapping], outcome: str, a: tuple, b: tuple, boot: np.ndarray,
                    key: tuple[str, ...] = CONDITION_KEY) -> dict:
    """Mean over replicates of (a - b), NA pairs dropped, 95% percentile CI on the shared resamples.
    Conditions are matched on the summary fields in `key` (default stage, R, family)."""
    va, vb = _values_by_replicate(summaries, outcome, a, key), _values_by_replicate(summaries, outcome, b, key)
    reps = sorted(va)
    if sorted(vb) != reps:
        raise ValueError(f"conditions {a} and {b} cover different replicates")
    if boot.shape[1] != len(reps):
        raise ValueError(f"bootstrap matrix has {boot.shape[1]} columns for {len(reps)} replicates")
    diffs = np.array([va[r] - vb[r] if va[r] is not None and vb[r] is not None else np.nan for r in reps], float)
    n = int(np.isfinite(diffs).sum())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        estimate = float(np.nanmean(diffs)) if n else float("nan")
        lo, hi = _percentile_ci(np.nanmean(diffs[boot], axis=1))
    return {"outcome": outcome, "a": a, "b": b, "n": n, "estimate": estimate, "lo": lo, "hi": hi}


def classify(lo: float, hi: float, delta: float) -> tuple[str, str | None]:
    """E1 §6. detected (CI excludes 0) with its magnitude relative to delta, negligible (CI within
    ±delta), otherwise inconclusive; not_estimable when there is no CI."""
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return "not_estimable", None
    if lo > 0 or hi < 0:
        if lo >= -delta and hi <= delta:
            return "detected", "below_delta"
        if lo > delta or hi < -delta:
            return "detected", "above_delta"
        return "detected", "straddles_delta"
    if lo >= -delta and hi <= delta:
        return "negligible", None
    return "inconclusive", None


def precision_check(contrast: Mapping, delta: float, fraction: float = 0.25) -> dict:
    """Adequacy rule replacing E1's void §8 rule: the 95% CI half-width must be <= fraction x delta.
    Unlike the E1 rule it shrinks with the number of replicates (validated on synthetic data)."""
    lo, hi = contrast["lo"], contrast["hi"]
    half_width = (hi - lo) / 2 if math.isfinite(lo) and math.isfinite(hi) else float("nan")
    limit = fraction * delta
    return {"half_width": half_width, "limit": limit,
            "adequate": bool(math.isfinite(half_width) and half_width <= limit + 1e-15)}


def boundary_precision_check(contrast: Mapping, delta: float) -> dict:
    """Decision-relevant adequacy rule (Vavan, 2026-09-18; replaces the half-width rule from E4 on):
    adequate iff the 95% CI contains neither +delta nor -delta, so the delta-interpretation can't change
    anywhere inside the CI. An endpoint exactly at a boundary doesn't count as crossing."""
    lo, hi = contrast["lo"], contrast["hi"]
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return {"adequate": False, "crosses": None}
    crosses = [b for b in (-delta, delta) if lo < b < hi]
    return {"adequate": not crosses, "crosses": crosses}


def tipping_threshold(betas: Sequence[float], shares: Sequence[float],
                      level: float = TIPPING_LEVEL) -> tuple[float | None, str]:
    """Peer-influence strength where the share of tipped classrooms first reaches `level`, by linear
    interpolation between grid points. Returns (value, status): 'interpolated', 'below_grid' (already
    reached at the first grid point; value = that point, an upper bound) or 'above_grid' (never; None)."""
    if shares[0] >= level:
        return float(betas[0]), "below_grid"
    for k in range(1, len(betas)):
        if shares[k] >= level:
            b0, b1, s0, s1 = betas[k - 1], betas[k], shares[k - 1], shares[k]
            return float(b0 + (level - s0) / (s1 - s0) * (b1 - b0)), "interpolated"
    return None, "above_grid"


def tipping_threshold_ci(summaries: Sequence[Mapping], labels_by_beta: Sequence[tuple[float, str]],
                         boot: np.ndarray, level: float = TIPPING_LEVEL) -> dict:
    """Threshold on the replicate means of `tipped`, with a 95% percentile CI over the shared resamples.
    Resamples with no crossing are counted, not dropped silently."""
    betas = [b for b, _ in labels_by_beta]
    rows = []
    for _, label in labels_by_beta:
        by_rep = {s["replicate"]: s["tipped"] for s in summaries if s["experiment_id"] == label}
        rows.append([by_rep[r] for r in sorted(by_rep)])
    T = np.array(rows, float)  # (n_beta, n_rep)
    if boot.shape[1] != T.shape[1]:
        raise ValueError("bootstrap matrix does not match the number of replicates")
    shares = T.mean(axis=1)
    value, status = tipping_threshold(betas, list(shares), level)
    resampled, statuses = [], defaultdict(int)
    for row in boot:
        v, st = tipping_threshold(betas, list(T[:, row].mean(axis=1)), level)
        statuses[st] += 1
        if v is not None:
            resampled.append(v)
    lo, hi = _percentile_ci(np.array(resampled, float))
    return {"threshold": value, "status": status, "lo": lo, "hi": hi, "resample_status": dict(statuses),
            "shares": {b: float(s) for b, s in zip(betas, shares)}}


def _ranks(values: Sequence[float]) -> np.ndarray:
    values = np.asarray(values, float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values))
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1  # average rank for ties
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    rx, ry = _ranks(x), _ranks(y)
    dx, dy = rx - rx.mean(), ry - ry.mean()
    denominator = math.sqrt(float((dx ** 2).sum() * (dy ** 2).sum()))
    return float((dx * dy).sum() / denominator) if denominator > 0 else float("nan")


def proxy_check(summaries: Sequence[Mapping], threshold: float = 0.8, x: str = "dGK_last",
                y: str = "dHK_late") -> dict:
    """E1 validity check: Spearman rho between condition means of x and y."""
    groups: dict[tuple, list[Mapping]] = defaultdict(list)
    for s in summaries:
        groups[(s["stage"], s["R"], s["family"])].append(s)
    conditions = []
    for cond in sorted(groups):
        mx, my = _mean(s.get(x) for s in groups[cond]), _mean(s.get(y) for s in groups[cond])
        if mx is not None and my is not None:
            conditions.append({"condition": cond, x: mx, y: my})
    rho = spearman([c[x] for c in conditions], [c[y] for c in conditions]) if len(conditions) > 1 else float("nan")
    return {"n_conditions": len(conditions), "rho": rho, "threshold": threshold,
            "adequate": bool(math.isfinite(rho) and rho >= threshold), "conditions": conditions}


_STATISTICS = {"mean": np.nanmean, "median": np.nanmedian, "q95": lambda a: np.nanpercentile(a, 95)}


def convergence(values: Sequence[float | None], boot: np.ndarray, statistic: str = "mean", tail: int = 50,
                tol: float = 0.1) -> dict:
    """E1 §8 / §4b.4: max over the last `tail` replicates of |running stat - final stat| must be below
    tol x the half-width of the final stat's 95% bootstrap CI (or both zero)."""
    stat = _STATISTICS[statistic]
    v = np.array([np.nan if x is None else x for x in values], float)
    n = len(v)
    if not 1 <= tail <= n:
        raise ValueError("tail must be between 1 and the number of replicates")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        final = float(stat(v))
        running = np.array([stat(v[:m]) for m in range(n - tail + 1, n + 1)], float)
        movement = float(np.nanmax(np.abs(running - final))) if np.isfinite(running).any() else float("nan")
        lo, hi = _percentile_ci(np.array([stat(v[row]) for row in boot], float))
    half_width = (hi - lo) / 2
    passed = bool(movement < tol * half_width or (half_width == 0 and movement == 0))
    return {"statistic": statistic, "final": final, "movement": movement, "half_width": half_width,
            "passed": passed}


def broker_scores(B_obs: Mapping[int, int], B_null: Sequence[Mapping[int, int]]) -> dict[int, dict]:
    """E1 §7: per student B, null mean and sample SD, excess, Z (None if SD = 0), permutation p."""
    L = len(B_null)
    out = {}
    for i, b in B_obs.items():
        null = np.array([member[i] for member in B_null], float)
        mu = float(null.mean())
        sd = float(null.std(ddof=1)) if L > 1 else 0.0
        out[i] = {"B": b, "mu": mu, "sd": sd, "excess": b - mu,
                  "Z": (b - mu) / sd if sd > 0 else None,
                  "p": (1 + int((null >= b).sum())) / (L + 1)}
    return out


def broker_share(scores: Mapping[int, Mapping], alpha: float = 0.05) -> float:
    return sum(1 for s in scores.values() if s["p"] <= alpha) / len(scores)
