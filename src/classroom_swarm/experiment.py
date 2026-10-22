"""Paired replicate runner (docs/01, docs/09 experiment.py). Orchestration only: no model equations.

One replicate = one graph per family + ONE shared Draws(R_max = max(Rs)) for every family, R and
stage. That shared object is the common-random-numbers design; don't split it per family.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

import networkx
import numpy
import pyarrow

from .config import Params, RunSpec, Stage
from .derive import brokerage
from .engine import simulate
from .graphs import Graph, generate_graph, rewire_degree_preserving
from .rng import BIT_GENERATOR, FAMILY_CODE, RNG_SCHEME, STREAM_CODE, Draws, graph_seed, null_seed
from .storage import to_arrow, write_replicate


def _git_state() -> dict:
    """Commit and dirty flag of the code that produced the run ('unknown' without git)."""
    git = shutil.which("git")
    repo = Path(__file__).resolve().parents[2]
    if git is None:
        return {"git_commit": "unknown", "git_dirty": None}
    try:
        commit = subprocess.run([git, "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True,
                                check=True).stdout.strip()
        dirty = bool(subprocess.run([git, "status", "--porcelain"], cwd=repo, capture_output=True, text=True,
                                    check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": "unknown", "git_dirty": None}
    return {"git_commit": commit, "git_dirty": dirty}


def run_replicate(experiment_id: str, replicate: int, master_seed: int, base: Params, out_root: Path,
                  families: Sequence[str] = ("ER", "WS", "SBM"), Rs: Sequence[int] = (1, 3),
                  stages: Sequence[Stage] = tuple(Stage)) -> Path:
    """Run every family x R x stage on one replicate and write one table set to out_root/rep<NNNN>."""
    base.validate()
    if not families or not Rs or not stages:
        raise ValueError("families, Rs and stages must be non-empty")
    R_max = max(Rs)
    draws = Draws(master_seed, replicate, base.N, base.M_H, base.M_E, R_max=R_max)
    logs = []
    for family in families:
        graph = generate_graph(family, base, graph_seed(master_seed, replicate, family))
        for R in Rs:
            for stage in stages:
                spec = RunSpec(experiment_id=experiment_id, replicate=replicate, family=family, R=R,
                               stage=Stage(stage), params=base, master_seed=master_seed)
                logs.append(simulate(spec, graph, draws))
    shared = {
        "experiment_id": experiment_id, "replicate": replicate, "master_seed": master_seed,
        "rng_scheme": RNG_SCHEME, "bit_generator": BIT_GENERATOR, "stream_codes": dict(STREAM_CODE),
        "family_codes": dict(FAMILY_CODE), "R_max": R_max,
        "versions": {"python": platform.python_version(), "numpy": numpy.__version__,
                     "networkx": networkx.__version__, "pyarrow": pyarrow.__version__},
        **_git_state(),
    }
    rep_dir = Path(out_root) / f"rep{replicate:04d}"
    write_replicate(rep_dir, logs, shared)
    return rep_dir


def run_conditions(conditions: Sequence[tuple], replicate: int, master_seed: int,
                   out_root: Path, family: str = "SBM", R: int = 3, R_max: int = 3) -> Path:
    """Condition designs (E2-E4): several conditions on one replicate world.

    A condition is (label, stage, params) or (label, stage, params, family, R); the short form uses the
    `family` and `R` arguments. Every condition shares one Draws (common random numbers) and, per family,
    one graph. The label becomes the run's experiment_id, so run_ids stay unique. Graph- and
    draw-relevant parameters (N, M_H, M_E, d_bar, omega, sbm_ratio) must be identical across conditions.
    """
    if not conditions:
        raise ValueError("conditions must be non-empty")
    conditions = [tuple(c) if len(c) == 5 else (*c, family, R) for c in conditions]
    if any(c[4] > R_max or c[4] < 1 for c in conditions):
        raise ValueError(f"every condition's R must be between 1 and R_max = {R_max}")
    labels = [c[0] for c in conditions]
    if len(set(labels)) != len(labels):
        raise ValueError("condition labels must be unique")
    shape = lambda p: (p.N, p.M_H, p.M_E, p.d_bar, p.omega, p.sbm_ratio)
    first = conditions[0][2]
    if any(shape(c[2]) != shape(first) for c in conditions):
        raise ValueError("conditions must share graph- and draw-relevant parameters")
    for c in conditions:
        c[2].validate()
    draws = Draws(master_seed, replicate, first.N, first.M_H, first.M_E, R_max=R_max)
    graphs = {fam: generate_graph(fam, first, graph_seed(master_seed, replicate, fam))
              for fam in dict.fromkeys(c[3] for c in conditions)}
    logs = [simulate(RunSpec(label, replicate, fam, r, Stage(stage), params, master_seed), graphs[fam], draws)
            for label, stage, params, fam, r in conditions]
    shared = {
        "experiment_id": "conditions", "condition_labels": labels, "replicate": replicate,
        "master_seed": master_seed, "rng_scheme": RNG_SCHEME, "bit_generator": BIT_GENERATOR,
        "stream_codes": dict(STREAM_CODE), "family_codes": dict(FAMILY_CODE), "R_max": R_max,
        "versions": {"python": platform.python_version(), "numpy": numpy.__version__,
                     "networkx": networkx.__version__, "pyarrow": pyarrow.__version__},
        **_git_state(),
    }
    rep_dir = Path(out_root) / f"rep{replicate:04d}"
    write_replicate(rep_dir, logs, shared)
    return rep_dir


def run_broker_null(specs: Sequence[RunSpec], graph: Graph, L: int, master_seed: int,
                    R_max: int = 3) -> dict[str, list[dict[int, int]]]:
    """Degree-preserving broker null (E1 §7, §4b.7): for each l, one rewired graph and one fresh Draws, both
    seeded by null_seed(master_seed, replicate, family, l), shared by every stage in `specs`.

    Returns {stage name: [B_i per student, one dict per null member]}. Null logs are not kept.
    """
    if not specs:
        raise ValueError("specs must be non-empty")
    replicate, family, params = specs[0].replicate, specs[0].family, specs[0].params
    if any((s.replicate, s.family, s.params) != (replicate, family, params) for s in specs):
        raise ValueError("all specs must share replicate, family and params")
    out: dict[str, list[dict[int, int]]] = {s.stage.name: [] for s in specs}
    for ell in range(L):
        seed = null_seed(master_seed, replicate, family, ell)
        null_graph, _ = rewire_degree_preserving(graph, seed)
        draws = Draws(seed, replicate, params.N, params.M_H, params.M_E, R_max=R_max)
        for spec in specs:
            log = simulate(spec, null_graph, draws)
            B = brokerage(to_arrow(log, "routing_events"), to_arrow(log, "decisions"))
            out[spec.stage.name].append({student: b for (_, student), b in B.items()})
    return out
