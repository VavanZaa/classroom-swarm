"""Parameters, the stage ladder and run identity (docs/01, docs/02, docs/09 config.py).

`Params` holds the raw scientific parameters. `resolve_params(stage, base)` is the only place the
stage ladder lives; the engine sees nothing but the resulting `EffectiveParams`.
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Literal

Family = Literal["ER", "WS", "SBM"]
FAMILIES: tuple[str, ...] = ("ER", "WS", "SBM")
EXPOSURES: tuple[str, ...] = ("requests", "copying")  # A19: V1, V2


class Stage(enum.IntEnum):
    M0 = 0  # fixed strategy tendencies
    M1 = 1  # + personal strategy reinforcement
    M2 = 2  # + peer-exposure effect
    M3 = 3  # + confidence affects strategy
    M4 = 4  # + exam updates confidence
    M5 = 5  # + exam changes effort


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


@dataclass(frozen=True)
class Params:
    """Raw scientific parameters. No stage, no controls, no derived values."""

    # environment (§29)
    N: int = 30
    H: int = 20
    F_E: int | None = 5
    M_H: int = 10
    M_E: int = 30
    # learning / init (§31, A12)
    K0: float = 0.5
    C0_offset: float = 0.0
    alpha: float = 0.0584  # reference literal; never recomputed automatically
    p_C0: float = 0.10
    q0_override: float | None = None
    # behaviour magnitudes (§32); whether each is active is decided by resolve_params
    eta_Q: float = 0.20
    kappa: float = 0.15
    chi_C: float = 0.10
    beta_P: float = 0.5
    beta_C: float = 0.5
    eta_C: float = 0.20
    eta_E: float = 0.30
    tau_E: float = 0.70
    # graph (§30, A13, A14); used by graphs.py, not by the engine
    d_bar: int = 6
    omega: float = 0.1
    sbm_ratio: float = 5.0
    # structure (A19): what peer exposure X measures. "requests" = V1 (§7), "copying" = V2
    exposure: str = "requests"

    def validate(self) -> None:
        """Mathematical validity only; experimental sweep ranges are not enforced here."""
        for name in ("N", "H", "M_H", "M_E", "d_bar"):
            value = getattr(self, name)
            _require(isinstance(value, int) and not isinstance(value, bool), f"{name} must be an integer")
        _require(self.N >= 1 and self.H >= 1, "N and H must be >= 1")
        _require(self.M_H >= 1 and self.M_E >= 1, "M_H and M_E must be >= 1")
        _require(self.F_E is None or (isinstance(self.F_E, int) and self.F_E >= 1), "F_E must be None or >= 1")
        _require(_finite(self.K0, self.C0_offset, self.alpha, self.p_C0, self.eta_Q, self.kappa, self.chi_C,
                         self.beta_P, self.beta_C, self.eta_C, self.eta_E, self.tau_E, self.omega,
                         self.sbm_ratio), "parameters must be finite numbers")
        _require(0.0 <= self.K0 <= 1.0, "K0 must be in [0, 1]")
        _require(0.0 <= self.K0 + self.C0_offset <= 1.0, "K0 + C0_offset must be in [0, 1]")
        _require(self.alpha > 0.0, "alpha must be > 0")
        _require(0.0 < self.p_C0 < 1.0, "p_C0 must be in (0, 1)")
        _require(self.q0_override is None or _finite(self.q0_override), "q0_override must be finite")
        _require(self.eta_Q >= 0.0 and self.kappa >= 0.0 and self.eta_E >= 0.0, "rates and kappa must be >= 0")
        _require(0.0 <= self.chi_C <= 1.0, "chi_C must be in [0, 1]")
        _require(0.0 <= self.eta_C <= 1.0, "eta_C must be in [0, 1]")
        _require(0.0 <= self.tau_E <= 1.0, "tau_E must be in [0, 1]")
        _require(self.d_bar >= 2 and self.d_bar % 2 == 0, "d_bar must be a positive even integer (A14)")
        _require(self.d_bar < self.N, "d_bar must be < N")
        _require(0.0 <= self.omega <= 1.0, "omega must be in [0, 1]")
        _require(self.sbm_ratio > 0.0, "sbm_ratio must be > 0")
        _require(self.exposure in EXPOSURES, f"exposure must be one of {EXPOSURES}")


@dataclass(frozen=True)
class EffectiveParams:
    """Exactly the values simulate() uses, fully resolved for one stage."""

    N: int
    H: int
    F_E: int | None
    M_H: int
    M_E: int
    K0: float
    C0: float
    alpha: float
    q0: float
    b_C: float
    kappa: float
    chi_C: float
    eta_C: float
    tau_E: float
    eta_Q: float
    beta_P: float
    beta_C: float
    exam_updates_confidence: bool
    exam_updates_effort: bool
    eta_E: float
    exposure: str


def resolve_params(stage: Stage, base: Params) -> EffectiveParams:
    """Apply the stage ladder (docs/01) once. The only place stage decides anything."""
    base.validate()
    stage = Stage(stage)
    q0 = base.q0_override if base.q0_override is not None else base.K0 - base.kappa  # unclipped (A12)
    return EffectiveParams(
        N=base.N, H=base.H, F_E=base.F_E, M_H=base.M_H, M_E=base.M_E,
        K0=base.K0, C0=base.K0 + base.C0_offset, alpha=base.alpha,
        q0=q0, b_C=math.log(2.0 * base.p_C0 / (1.0 - base.p_C0)),
        kappa=base.kappa, chi_C=base.chi_C, eta_C=base.eta_C, tau_E=base.tau_E,
        eta_Q=base.eta_Q if stage >= Stage.M1 else 0.0,
        beta_P=base.beta_P if stage >= Stage.M2 else 0.0,
        beta_C=base.beta_C if stage >= Stage.M3 else 0.0,
        exam_updates_confidence=stage >= Stage.M4,
        exam_updates_effort=stage >= Stage.M5,
        eta_E=base.eta_E if stage >= Stage.M5 else 0.0,
        exposure=base.exposure,
    )


@dataclass(frozen=True)
class SimulationControls:
    """Testing / calibration interventions. Never part of the scientific model."""

    force_action: Literal["S"] | None = None  # None in every experiment run

    def __post_init__(self) -> None:
        _require(self.force_action in (None, "S"), "force_action must be None or 'S'")


def alpha_from_trajectory(K0: float, K_T: float, T: int) -> float:
    """§31: the alpha that takes an all-independent student from K0 to K_T in T homeworks."""
    _require(0.0 <= K0 < K_T < 1.0, "need 0 <= K0 < K_T < 1")
    _require(isinstance(T, int) and T >= 1, "T must be an integer >= 1")
    return 1.0 - ((1.0 - K_T) / (1.0 - K0)) ** (1.0 / T)


@dataclass(frozen=True)
class RunSpec:
    experiment_id: str
    replicate: int
    family: Family
    R: int
    stage: Stage
    params: Params
    master_seed: int

    def __post_init__(self) -> None:
        _require(self.family in FAMILIES, f"family must be one of {FAMILIES}")
        _require(isinstance(self.R, int) and self.R >= 1, "R must be an integer >= 1")
        _require(isinstance(self.replicate, int) and self.replicate >= 0, "replicate must be an integer >= 0")
        _require(isinstance(self.master_seed, int) and self.master_seed >= 0, "master_seed must be an integer >= 0")
        _require(bool(self.experiment_id) and "/" not in self.experiment_id, "experiment_id must be non-empty, no '/'")
        object.__setattr__(self, "stage", Stage(self.stage))

    @property
    def run_id(self) -> str:
        return f"{self.experiment_id}/rep{self.replicate:04d}/{self.family}/R{self.R}/{self.stage.name}"
