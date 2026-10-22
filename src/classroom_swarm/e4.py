"""Experiment 4 constants and plan (V2 tipping point), copied from the locked preregistration.

docs/experiments/E4-preregistration.md (locked 2026-09-18, SHA-256 in docs/experiments/E4-lock.json).
"""
from __future__ import annotations

from dataclasses import replace

from . import e1
from .analysis import tipping_threshold_ci
from .config import Params, Stage

EXPERIMENT_ID = "E4"
SMOKE_ID = "E4-smoke"
MASTER_SEED = 918005
SMOKE_SEED = 918995
BOOT_SEED = 918500
BOOT_B = 10_000
REPLICATES = tuple(range(1, 401))
SMOKE_REPLICATES = (1, 2)
FAMILY, R = "SBM", 3  # defaults only; every E4 condition carries its own family and R
EARLY, LATE = e1.EARLY, e1.LATE
CONFIRMATORY = e1.CONFIRMATORY + ("tipped",)
SECONDARY = e1.SECONDARY
DELTA = {**e1.DELTA, "tipped": 0.10}
PRECISION_RULE = "boundary"
PRECISION_FRACTION = None  # not used by the boundary rule
PREREG = "docs/experiments/E4-preregistration.md"
LOCK = "docs/experiments/E4-lock.json"
verify_lock = e1.verify_lock

F_BETAS = (0.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)
T_BETAS = (0.0, 3.0, 4.5, 6.0)
T_FAMILIES = ("ER", "WS", "SBM")
T_RS = (1, 3)
S_STAGES = (Stage.M3, Stage.M4, Stage.M5)


def f_label(b: float) -> str:
    return f"E4-F-b{b:g}"


def cell_label(family: str, r: int, b: float) -> str:
    return f_label(b) if (family, r) == ("SBM", 3) else f"E4-T-{family}-R{r}-b{b:g}"


def stage_label(stage: Stage, b: float) -> str:
    return f_label(b) if stage == Stage.M2 else f"E4-S-{stage.name}-b{b:g}"


def _build() -> dict[str, dict]:
    table: dict[str, dict] = {}
    for b in F_BETAS:
        table[f_label(b)] = {"stage": Stage.M2, "family": "SBM", "R": 3, "beta_P": b}
    for family in T_FAMILIES:
        for r in T_RS:
            for b in T_BETAS:
                table.setdefault(cell_label(family, r, b), {"stage": Stage.M2, "family": family, "R": r, "beta_P": b})
    for stage in S_STAGES:
        for b in T_BETAS:
            table[stage_label(stage, b)] = {"stage": stage, "family": "SBM", "R": 3, "beta_P": b}
    return table


CONDITIONS = _build()


def conditions() -> list[tuple]:
    return [(label, c["stage"], replace(Params(), exposure="copying", beta_P=c["beta_P"]), c["family"], c["R"])
            for label, c in CONDITIONS.items()]


def contrasts() -> list[dict]:
    """§4: F (7), T (18 dose + 12 topology + 9 routing), S (12)."""
    plan = [{"block": "F", "name": f"F b{b:g}-b0", "a": (f_label(b),), "b": (f_label(0.0),), "stress": True}
            for b in F_BETAS[1:]]
    for family in T_FAMILIES:
        for r in T_RS:
            for b in T_BETAS[1:]:
                plan.append({"block": "T", "name": f"T {family} R{r} b{b:g}-b0", "a": (cell_label(family, r, b),),
                             "b": (cell_label(family, r, 0.0),), "stress": True})
    for r in T_RS:
        for b in T_BETAS[1:]:
            for family in ("ER", "WS"):
                plan.append({"block": "T", "name": f"T {family}-SBM R{r} b{b:g}", "a": (cell_label(family, r, b),),
                             "b": (cell_label("SBM", r, b),), "stress": True})
    for family in T_FAMILIES:
        for b in T_BETAS[1:]:
            plan.append({"block": "T", "name": f"T R3-R1 {family} b{b:g}", "a": (cell_label(family, 3, b),),
                         "b": (cell_label(family, 1, b),), "stress": True})
    for stage in S_STAGES:
        for b in T_BETAS:
            plan.append({"block": "S", "name": f"S {stage.name}-M2 b{b:g}", "a": (stage_label(stage, b),),
                         "b": (f_label(b),), "stress": b > 1.5})
    return plan


def extra_analysis(summaries, boot) -> dict:
    """§3 threshold estimates: block F on the 3-6 grid, and each block-T cell on its 3 / 4.5 / 6 grid."""
    out = {"F": tipping_threshold_ci(summaries, [(b, f_label(b)) for b in F_BETAS[1:]], boot)}
    for family in T_FAMILIES:
        for r in T_RS:
            out[f"T {family} R{r}"] = tipping_threshold_ci(
                summaries, [(b, cell_label(family, r, b)) for b in T_BETAS[1:]], boot)
    return out
