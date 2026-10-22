"""Experiment 1 constants and plan, copied from the locked preregistration.

docs/experiments/E1-preregistration.md (locked 2026-09-18, SHA-256 in docs/experiments/E1-lock.json).
Anything here that disagrees with the locked file is a bug in this module, not a change to E1.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXPERIMENT_ID = "E1"
SMOKE_ID = "E1-smoke"
MASTER_SEED = 918001
SMOKE_SEED = 918999
BOOT_SEED = 918100
BOOT_B = 10_000
REPLICATES = tuple(range(1, 201))
SMOKE_REPLICATES = (1, 2)
L_NULL = 200
SMOKE_L_NULL = 5
EARLY = (1, 5)
LATE = (16, 20)
CONVERGENCE_TAIL = 50
CONVERGENCE_TOL = 0.1
PROXY_THRESHOLD = 0.8

STAGES = ("M0", "M1", "M2", "M3", "M4", "M5")
RS = (1, 3)
FAMILIES = ("ER", "WS", "SBM")

CONFIRMATORY = ("pC_late", "pC_change", "succ_late", "K_final", "dHK_late", "dGK_last",
                "Smax_mean", "Lmax_mean", "CF")
SECONDARY = ("VarK_final", "dHK_mean", "dGK_block", "reach")
DELTA = {  # §6; VarK_final is reported without a delta
    "pC_late": 0.02, "pC_change": 0.02, "succ_late": 0.05, "K_final": 0.01, "dHK_late": 0.01,
    "dGK_last": 0.02, "Smax_mean": 1.0, "Lmax_mean": 0.25, "CF": 0.05, "broker_share": 0.05,
    "dHK_mean": 0.01, "dGK_block": 0.02, "reach": 0.02,
}

BROKER_SCOPE = (("M0", 3, "SBM"), ("M1", 3, "SBM"), ("M2", 3, "SBM"))
BROKER_CONTRASTS = (("broker M1-M0", ("M1", 3, "SBM"), ("M0", 3, "SBM")),
                    ("broker M2-M1", ("M2", 3, "SBM"), ("M1", 3, "SBM")))
CONVERGENCE_QUANTITIES = (("P_C_last", "mean"), ("K_final", "mean"), ("Smax_mean", "median"), ("Smax_mean", "q95"))


def contrasts() -> list[dict]:
    """§5: three primary contrasts, then 30 + 18 + 24 secondary ones (the primary ones recur there)."""
    plan = [
        {"name": "P1", "tier": "primary", "a": ("M1", 3, "SBM"), "b": ("M0", 3, "SBM")},
        {"name": "P2", "tier": "primary", "a": ("M1", 3, "SBM"), "b": ("M1", 1, "SBM")},
        {"name": "P3", "tier": "primary", "a": ("M2", 3, "SBM"), "b": ("M1", 3, "SBM")},
    ]
    for R in RS:
        for family in FAMILIES:
            for k in range(1, len(STAGES)):
                plan.append({"name": f"{STAGES[k]}-{STAGES[k - 1]} R{R} {family}", "tier": "secondary",
                             "a": (STAGES[k], R, family), "b": (STAGES[k - 1], R, family)})
    for stage in STAGES:
        for family in FAMILIES:
            plan.append({"name": f"R3-R1 {stage} {family}", "tier": "secondary",
                         "a": (stage, 3, family), "b": (stage, 1, family)})
    for stage in STAGES:
        for R in RS:
            for family in ("SBM", "WS"):
                plan.append({"name": f"{family}-ER {stage} R{R}", "tier": "secondary",
                             "a": (stage, R, family), "b": (stage, R, "ER")})
    return plan


def verify_lock(prereg_path: Path, lock_path: Path) -> str:
    """Refuse to proceed unless the preregistration still matches its lock record (§12)."""
    digest = hashlib.sha256(Path(prereg_path).read_bytes()).hexdigest()
    expected = json.loads(Path(lock_path).read_text(encoding="utf-8"))["sha256"]
    if digest != expected:
        raise RuntimeError(f"preregistration SHA-256 {digest} does not match the lock record {expected}")
    return digest
