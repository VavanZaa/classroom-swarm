"""Experiment 2b constants and plan, copied from the locked preregistration.

docs/experiments/E2b-preregistration.md (locked 2026-09-18, SHA-256 in docs/experiments/E2b-lock.json).
"""
from __future__ import annotations

from . import e1, e2

EXPERIMENT_ID = "E2b"
SMOKE_ID = "E2b-smoke"
MASTER_SEED = 918003
SMOKE_SEED = 918997
BOOT_SEED = 918300
BOOT_B = 10_000
REPLICATES = tuple(range(1, 401))
SMOKE_REPLICATES = (1, 2)
STAGE, R, FAMILY = e2.STAGE, e2.R, e2.FAMILY
EARLY, LATE = e1.EARLY, e1.LATE
CONFIRMATORY, SECONDARY, DELTA = e1.CONFIRMATORY, e1.SECONDARY, e1.DELTA
PRECISION_FRACTION = 0.25
REFERENCE = "E2b-ref"
STRESS: tuple[str, ...] = ()
CONDITIONS: dict[str, dict] = {
    "E2b-ref": {},
    "E2b-plausible-max": dict(e2.CONDITIONS["E2-plausible-max"]),
}
PREREG = "docs/experiments/E2b-preregistration.md"
LOCK = "docs/experiments/E2b-lock.json"
verify_lock = e1.verify_lock


def conditions():
    return e2.build_conditions(CONDITIONS, STAGE)


def contrasts():
    return e2.build_contrasts(CONDITIONS, REFERENCE, STRESS)
