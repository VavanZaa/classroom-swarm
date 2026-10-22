"""Experiment 2 constants and plan, copied from the locked preregistration.

docs/experiments/E2-preregistration.md (locked 2026-09-18, SHA-256 in docs/experiments/E2-lock.json).
Anything here that disagrees with the locked file is a bug in this module, not a change to E2.
"""
from __future__ import annotations

from dataclasses import replace

from . import e1
from .config import Params, Stage

EXPERIMENT_ID = "E2"
SMOKE_ID = "E2-smoke"
MASTER_SEED = 918002
SMOKE_SEED = 918998
BOOT_SEED = 918200
BOOT_B = 10_000
REPLICATES = tuple(range(1, 201))
SMOKE_REPLICATES = (1, 2)
STAGE = Stage.M2
R = 3
FAMILY = "SBM"
EARLY, LATE = e1.EARLY, e1.LATE
CONFIRMATORY, SECONDARY, DELTA = e1.CONFIRMATORY, e1.SECONDARY, e1.DELTA
PRECISION_FRACTION = 0.25
REFERENCE = "E2-ref"
STRESS = ("E2-betaP3", "E2-betaP6")  # beyond the §32 plausible range, by design

CONDITIONS: dict[str, dict] = {  # §3, in table order
    "E2-ref": {},
    "E2-betaP0": {"beta_P": 0.0},
    "E2-betaP1.5": {"beta_P": 1.5},
    "E2-betaP3": {"beta_P": 3.0},
    "E2-betaP6": {"beta_P": 6.0},
    "E2-kappa0": {"kappa": 0.0},
    "E2-kappa0.40": {"kappa": 0.40},
    "E2-etaQ0.05": {"eta_Q": 0.05},
    "E2-etaQ0.40": {"eta_Q": 0.40},
    "E2-pC0.01": {"p_C0": 0.01},
    "E2-pC0.20": {"p_C0": 0.20},
    "E2-q0-0": {"q0_override": 0.0},
    "E2-q0-0.5": {"q0_override": 0.5},
    "E2-plausible-max": {"beta_P": 1.5, "kappa": 0.40, "eta_Q": 0.40, "p_C0": 0.20},
}

PREREG = "docs/experiments/E2-preregistration.md"
LOCK = "docs/experiments/E2-lock.json"
verify_lock = e1.verify_lock


def build_conditions(table: dict[str, dict], stage: Stage) -> list[tuple[str, Stage, Params]]:
    return [(label, stage, replace(Params(), **overrides)) for label, overrides in table.items()]


def build_contrasts(table: dict[str, dict], reference: str, stress: tuple[str, ...] = ()) -> list[dict]:
    """Every non-reference condition minus the reference, matched on experiment_id."""
    return [{"name": label, "a": (label,), "b": (reference,), "stress": label in stress}
            for label in table if label != reference]


def conditions() -> list[tuple[str, Stage, Params]]:
    return build_conditions(CONDITIONS, STAGE)


def contrasts() -> list[dict]:
    """§5: every non-reference condition minus the reference, matched on experiment_id."""
    return build_contrasts(CONDITIONS, REFERENCE, STRESS)
