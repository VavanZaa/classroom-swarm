"""Post-hoc robustness check on E13's contrast ladder. NOT part of the E13 lock.

E13's preregistered ladder adds one component per rung and therefore attributes each component's
effect at its own position in the sequence. Because the components interact, that attribution is
path-dependent. This script brackets it: every component is measured both when ADDED FIRST to
`motivation_only` and when REMOVED LAST from the finished `public_no_ai` model, on the same 100
paired classrooms, the same graphs and the same semantic draws as E13.

It reads nothing from runs/E13 and writes nothing into it. Re-simulation is deterministic, so the
numbers reproduce exactly.

    .venv\\Scripts\\python.exe scripts/e13_order_robustness.py
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from classroom_swarm.e13 import SEED  # noqa: E402
from classroom_swarm.graphs import generate_graph  # noqa: E402
from classroom_swarm.rng import graph_seed  # noqa: E402
from classroom_swarm.v3 import V3Params  # noqa: E402
from classroom_swarm.v4_corrected import CorrectedParams, simulate_corrected  # noqa: E402
from classroom_swarm.v4_public_ai import PublicAIDraws  # noqa: E402

BOOTSTRAP_SEED, REPLICATES = 924402, 100

FULL = CorrectedParams()
MOTIVATION = replace(FULL, peer_rule="legacy", distant_weight=0, closeness_spread=0,
                     grade_bias=0, public_signal=0)
ON = {"acquaintances": dict(distant_weight=.1, closeness_spread=.5),
      "grade_filter": dict(peer_rule="higher"),
      "grade_weighting": dict(grade_bias=3),
      "public_signal": dict(public_signal=.5)}
OFF = {"acquaintances": dict(distant_weight=0, closeness_spread=0),
       "grade_filter": dict(peer_rule="legacy"),
       "grade_weighting": dict(grade_bias=0),
       "public_signal": dict(public_signal=0)}
CONDITIONS = ([("motivation_only", MOTIVATION), ("full", FULL)]
              + [("first_" + k, replace(MOTIVATION, **v)) for k, v in ON.items()]
              + [("last_" + k, replace(FULL, **v)) for k, v in OFF.items()])


def replicate(rep):
    graph = generate_graph("SBM", V3Params(), graph_seed(SEED, rep, "SBM"))
    draws = PublicAIDraws(SEED, rep, 30, 10, 30)
    out = {}
    for name, p in CONDITIONS:
        log = simulate_corrected(p, graph, draws, name)
        late = [r for r in log.tables["students"] if r["homework"] > p.H - 5]
        exam = [r for r in log.tables["exams"] if r["homework"] == p.H]
        out[name] = (float(np.mean([r["score"] for r in exam])),
                     float(np.mean([r["peer_copied"] for r in late])))
    return out


def main():
    with ProcessPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(replicate, range(REPLICATES)))
    rng = np.random.default_rng(BOOTSTRAP_SEED)

    def series(name, index):
        return np.array([r[name][index] for r in results]) * 100

    def interval(values):
        draw = np.mean(values[rng.integers(0, len(values), (2000, len(values)))], axis=1)
        return (values.mean(), *np.quantile(draw, [.025, .975]))

    print(f"Post-hoc ladder robustness, {REPLICATES} paired classrooms, E13 seed {SEED}. "
          "Not part of the lock.\n")
    for index, label in ((0, "unaided exam"), (1, "late peer copying")):
        total = series("full", index).mean() - series("motivation_only", index).mean()
        print(f"{label}: full - motivation_only = {total:+.2f}")
        print(f"  {'component':<17}{'added first':>26}{'removed last':>26}")
        first_sum = last_sum = 0.
        for key in ON:
            first = interval(series("first_" + key, index) - series("motivation_only", index))
            last = interval(series("full", index) - series("last_" + key, index))
            first_sum += first[0]
            last_sum += last[0]
            print(f"  {key:<17}{first[0]:+8.2f} [{first[1]:+6.2f},{first[2]:+6.2f}]"
                  f"{last[0]:+8.2f} [{last[1]:+6.2f},{last[2]:+6.2f}]")
        print(f"  {'sum of parts':<17}{first_sum:+8.2f}{'':<15}{last_sum:+8.2f}")
        print(f"  {'(total)':<17}{total:+8.2f}{'':<15}{total:+8.2f}\n")


if __name__ == "__main__":
    main()
