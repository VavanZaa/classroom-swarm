"""Experiment 3 constants and plan (V2 friend contagion), copied from the locked preregistration.

docs/experiments/E3-preregistration.md (locked 2026-09-18, SHA-256 in docs/experiments/E3-lock.json).
"""
from __future__ import annotations

from . import e1, e2

EXPERIMENT_ID = "E3"
SMOKE_ID = "E3-smoke"
MASTER_SEED = 918004
SMOKE_SEED = 918996
BOOT_SEED = 918400
BOOT_B = 10_000
REPLICATES = tuple(range(1, 401))
SMOKE_REPLICATES = (1, 2)
STAGE, R, FAMILY = e2.STAGE, e2.R, e2.FAMILY
EARLY, LATE = e1.EARLY, e1.LATE
CONFIRMATORY, SECONDARY, DELTA = e1.CONFIRMATORY, e1.SECONDARY, e1.DELTA
PRECISION_FRACTION = 0.25
BETAS = (0.5, 1.5, 3.0, 4.5, 6.0)
REFERENCE = "E3-v2-b0"
PREREG = "docs/experiments/E3-preregistration.md"
LOCK = "docs/experiments/E3-lock.json"
verify_lock = e1.verify_lock


def _label(version: str, beta: float) -> str:
    return f"E3-{version}-b{beta:g}"


CONDITIONS: dict[str, dict] = {REFERENCE: {"exposure": "copying", "beta_P": 0.0}}
CONDITIONS.update({_label("v2", b): {"exposure": "copying", "beta_P": b} for b in BETAS})
CONDITIONS.update({_label("v1", b): {"exposure": "requests", "beta_P": b} for b in BETAS})


def conditions():
    return e2.build_conditions(CONDITIONS, STAGE)


def contrasts() -> list[dict]:
    """§4: A (V2 - V1 at each beta), B (V2 dose vs V2-b0), C (V1 dose vs the exposure-inert b0)."""
    plan = [{"name": f"A: V2-V1 b{b:g}", "a": (_label("v2", b),), "b": (_label("v1", b),), "stress": b > 1.5}
            for b in BETAS]
    plan += [{"name": f"B: V2 b{b:g}-b0", "a": (_label("v2", b),), "b": (REFERENCE,), "stress": b > 1.5}
             for b in BETAS]
    plan += [{"name": f"C: V1 b{b:g}-b0", "a": (_label("v1", b),), "b": (REFERENCE,), "stress": b > 1.5}
             for b in BETAS]
    return plan
