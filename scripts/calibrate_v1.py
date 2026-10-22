"""§41 calibration, steps 1-2 (docs/06 B): alpha and measurement noise.

Runs only forced-S simulations (SimulationControls(force_action="S"), stage M1: exams are probes,
eta_E inactive). There is no copying and no model comparison, so no research result is produced.

Pass criteria, fixed before the first run:
  Step 1  |alpha_literal - alpha_exact| < 1e-4, and the simulated K_H of every student matches
          1 - (1 - K0)(1 - alpha)^H to 1e-12.
  Step 2  For every homework and exam: mean residual (grade - K) within 4 standard errors of 0, and
          empirical residual SD within +/-10 % of the binomial theory sqrt(K(1-K)/M).
          Also reported, with no criterion: the classroom noise floor of Delta_GK under all-S.

    .venv\\Scripts\\python.exe scripts/calibrate_v1.py [--replicates 200] [--master-seed 20260918]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from classroom_swarm.config import Params, RunSpec, SimulationControls, Stage, alpha_from_trajectory
from classroom_swarm.engine import simulate
from classroom_swarm.graphs import generate_graph
from classroom_swarm.rng import Draws, graph_seed

FORCED_S = SimulationControls(force_action="S")


def run_all_S(params: Params, replicate: int, master_seed: int, family: str = "SBM"):
    spec = RunSpec("calibration", replicate, family, 1, Stage.M1, params, master_seed)
    graph = generate_graph(family, params, graph_seed(master_seed, replicate, family))
    draws = Draws(master_seed, replicate, params.N, params.M_H, params.M_E, R_max=1)
    return simulate(spec, graph, draws, controls=FORCED_S)


def _rows(log, name):
    cols = log.tables[name]
    return [dict(zip(cols, values)) for values in zip(*cols.values())]


def measurements(log, params: Params):
    """Per-homework (grade, K) and per-exam (exam grade, K) pairs from the raw tables."""
    events = {e["event_id"]: e for e in _rows(log, "events")}
    K_after = {}
    for s in _rows(log, "state_snapshots"):
        e = events[s["event_id"]]
        K_after[(e["event_type"], e["homework_index"], s["student_id"])] = s["K"]
    homework = [(d["homework_index"], d["grade"], K_after[("homework", d["homework_index"], d["student_id"])])
                for d in _rows(log, "decisions")]
    exam_correct: dict[tuple[str, int], int] = {}
    for r in _rows(log, "item_outcomes"):
        if r["mode"] == "exam":
            key = (r["event_id"], r["student_id"])
            exam_correct[key] = exam_correct.get(key, 0) + int(r["correct"])
    exams = []
    for (event_id, i), correct in exam_correct.items():
        h = events[event_id]["homework_index"]
        exams.append((h, correct / params.M_E, K_after[("exam", h, i)]))
    return homework, exams


def residual_table(pairs, M):
    """Group (index, grade, K) by index; compare residual mean/SD with binomial theory."""
    out = []
    for idx in sorted({p[0] for p in pairs}):
        grades = np.array([g for j, g, _ in pairs if j == idx])
        K = np.array([k for j, _, k in pairs if j == idx])
        resid = grades - K
        theory = float(np.sqrt(np.mean(K * (1 - K)) / M))
        sd = float(resid.std(ddof=1))
        se = sd / math.sqrt(len(resid))
        out.append({"index": int(idx), "n": len(resid), "K_mean": float(K.mean()),
                    "resid_mean": float(resid.mean()), "resid_sd": sd, "theory_sd": theory,
                    "sd_ratio": sd / theory if theory > 0 else float("nan"),
                    "mean_ok": bool(abs(resid.mean()) <= 4 * se),
                    "sd_ok": bool(theory > 0 and abs(sd / theory - 1) <= 0.10)})
    return out


def delta_gk_floor(all_logs, params: Params):
    """Classroom Delta_GK at each exam, all-S: mean G_H (homework just before) - mean G_E."""
    per_exam: dict[int, list[float]] = {}
    for log in all_logs:
        homework, exams = measurements(log, params)
        for h in sorted({h for h, _, _ in exams}):
            gh = np.mean([g for j, g, _ in homework if j == h])
            ge = np.mean([g for j, g, _ in exams if j == h])
            per_exam.setdefault(h, []).append(float(gh - ge))
    out = []
    for h, values in sorted(per_exam.items()):
        v = np.array(values)
        out.append({"homework": h, "n_replicates": len(v), "mean": float(v.mean()), "sd": float(v.std(ddof=1)),
                    "q025": float(np.quantile(v, 0.025)), "q975": float(np.quantile(v, 0.975))})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--replicates", type=int, default=200)
    ap.add_argument("--master-seed", type=int, default=20260918)
    ap.add_argument("--out", type=Path, default=Path("runs/calibration"))
    args = ap.parse_args()
    base = Params()

    # step 1: alpha
    alpha_exact = alpha_from_trajectory(base.K0, 0.85, base.H)
    predicted = 1 - (1 - base.K0) * (1 - base.alpha) ** base.H
    log = run_all_S(base, 1, args.master_seed)
    K_final = [s["K"] for s in _rows(log, "state_snapshots") if s["event_id"] == f"h{base.H}"]
    step1 = {"alpha_literal": base.alpha, "alpha_exact": alpha_exact,
             "alpha_range_K20_0.80_0.90": [alpha_from_trajectory(base.K0, 0.80, base.H),
                                           alpha_from_trajectory(base.K0, 0.90, base.H)],
             "K_H_predicted": predicted, "K_H_max_abs_error": max(abs(k - predicted) for k in K_final)}
    step1["pass"] = abs(base.alpha - alpha_exact) < 1e-4 and step1["K_H_max_abs_error"] < 1e-12

    # step 2: measurement noise, reference M_H / M_E and near-noiseless M = 1000
    logs = [run_all_S(base, rep, args.master_seed) for rep in range(1, args.replicates + 1)]
    pairs_h, pairs_e = [], []
    for lg in logs:
        h, e = measurements(lg, base)
        pairs_h += h
        pairs_e += e
    hw, ex = residual_table(pairs_h, base.M_H), residual_table(pairs_e, base.M_E)
    big = Params(M_H=1000, M_E=1000)
    big_h, big_e = [], []
    for rep in range(1, 21):
        h, e = measurements(run_all_S(big, rep, args.master_seed), big)
        big_h += h
        big_e += e
    step2 = {"replicates": args.replicates, "homework": hw, "exams": ex,
             "noiseless_M1000": {"homework": residual_table(big_h, 1000), "exams": residual_table(big_e, 1000)},
             "delta_gk_floor_all_S": delta_gk_floor(logs, base)}
    step2["pass"] = all(r["mean_ok"] and r["sd_ok"] for r in hw + ex)

    summary = {"master_seed": args.master_seed, "base_params": base.__dict__, "step1": step1, "step2": step2}
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"calibration_steps1-2_seed{args.master_seed}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"STEP 1  alpha literal {base.alpha} vs exact {alpha_exact:.10f}; K_{base.H} predicted {predicted:.6f}, "
          f"max |sim - predicted| = {step1['K_H_max_abs_error']:.2e}  -> {'PASS' if step1['pass'] else 'FAIL'}")
    print(f"STEP 2  {args.replicates} replicates x {base.N} students, forced S -> {'PASS' if step2['pass'] else 'FAIL'}")
    for label, table in (("homework (M_H=10)", hw), ("exam (M_E=30)", ex)):
        worst = max(table, key=lambda r: abs(r["sd_ratio"] - 1))
        print(f"  {label}: sd/theory {min(r['sd_ratio'] for r in table):.3f}-{max(r['sd_ratio'] for r in table):.3f}, "
              f"worst index {worst['index']}; all means within 4 SE: {all(r['mean_ok'] for r in table)}")
    for r in step2["delta_gk_floor_all_S"]:
        print(f"  Delta_GK floor at h={r['homework']}: mean {r['mean']:+.4f}, sd {r['sd']:.4f}, "
              f"95% [{r['q025']:+.4f}, {r['q975']:+.4f}]")
    nb = step2["noiseless_M1000"]
    print(f"  M=1000 residual sd: homework max {max(r['resid_sd'] for r in nb['homework']):.4f}, "
          f"exam max {max(r['resid_sd'] for r in nb['exams']):.4f}")
    print(f"written: {path}")
    return 0 if step1["pass"] and step2["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
