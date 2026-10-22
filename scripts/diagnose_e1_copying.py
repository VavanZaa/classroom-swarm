"""Post hoc diagnosis of E1: why copying doesn't grow (exploratory; not part of any preregistration).

Reads the E1 raw tables for the SBM, R=3 runs of M0, M1 and M2 and reports:
  * mean reward by what a student actually did (S, D, successful copy, failed copy)
  * mean learned values Q_S, Q_D, Q_C at the start and after the last homework
  * how often each student chose C (Q_C is only updated on those homeworks)
  * the peer-exposure signal X and its utility contribution beta_P * X
  * the utility gap U_C - U_S that decides the copying probability

    .venv\\Scripts\\python.exe scripts/diagnose_e1_copying.py [--replicates 50]
"""
from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path

import pyarrow.compute as pc

from classroom_swarm.config import Params, Stage, resolve_params
from classroom_swarm.storage import read_table

REPO = Path(__file__).resolve().parents[1]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicates", type=int, default=50)
    args = ap.parse_args()
    for stage in ("M0", "M1", "M2"):
        ep = resolve_params(Stage[stage], Params())
        rewards = defaultdict(list)
        q_end = defaultdict(list)
        n_copy_choices, x_values, gaps, pc_end = [], [], [], []
        for rep in range(1, args.replicates + 1):
            rep_dir = REPO / "runs" / "E1" / f"rep{rep:04d}"
            run_id = f"E1/rep{rep:04d}/SBM/R3/{stage}"
            dec = read_table(rep_dir, "decisions")
            dec = dec.filter(pc.equal(dec["run_id"], run_id)).to_pylist()
            snaps = read_table(rep_dir, "state_snapshots")
            snaps = snaps.filter(pc.equal(snaps["run_id"], run_id)).to_pylist()
            per_student = defaultdict(int)
            for d in dec:
                kind = d["action"] if d["action"] != "C" else ("C ok" if d["copy_success"] else "C fail")
                rewards[kind].append(d["reward"])
                if d["action"] == "C":
                    per_student[d["student_id"]] += 1
            n_copy_choices += [per_student.get(i, 0) for i in range(30)]
            for s in snaps:
                if s["event_id"] == "h20":
                    for k in ("Q_S", "Q_D", "Q_C"):
                        q_end[k].append(s[k])
                    u_s = s["Q_S"] + ep.beta_C * (s["C"] - 0.5)
                    u_c = ep.b_C + s["Q_C"] + ep.beta_P * s["X"]
                    gaps.append(u_c - u_s)
                if s["event_id"].startswith("h"):
                    x_values.append(s["X"])
            pc_end += [d["P_C"] for d in dec if d["homework_index"] == 20 and d["feasible_C"]]
        print(f"== {stage} (SBM, R=3, {args.replicates} replicates, beta_P effective = {ep.beta_P})")
        print("  mean reward by what was done: " + ", ".join(f"{k} {mean(v):.3f} (n={len(v)})"
                                                           for k, v in sorted(rewards.items())))
        print(f"  Q at start: all {ep.q0:.3f};  after h20: Q_S {mean(q_end['Q_S']):.3f}, Q_D {mean(q_end['Q_D']):.3f}, "
              f"Q_C {mean(q_end['Q_C']):.3f}")
        never = sum(1 for n in n_copy_choices if n == 0) / len(n_copy_choices)
        print(f"  copy choices per student over 20 homeworks: mean {mean(n_copy_choices):.2f}; "
              f"never chose C: {never:.0%}")
        print(f"  X (share of neighbours who asked me): mean {mean(x_values):.3f}, share > 0: "
              f"{mean(1 if x > 0 else 0 for x in x_values):.0%}, max {max(x_values):.2f}; "
              f"mean beta_P*X = {ep.beta_P * mean(x_values):.3f}")
        print(f"  utility gap U_C - U_S after h20: mean {mean(gaps):+.3f} (b_C = {ep.b_C:+.3f}); "
              f"P_C at h20 (feasible): mean {mean(pc_end):.4f}")
    # what utility gain would copying need to reach a given probability, other things equal
    b_c = resolve_params(Stage.M1, Params()).b_C
    for target in (0.2, 0.3, 0.5):
        needed = math.log(2 * target / (1 - target)) - b_c
        print(f"to move P_C from 0.10 to {target:.1f} (S and D equal): U_C must rise by {needed:+.2f} utility units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
