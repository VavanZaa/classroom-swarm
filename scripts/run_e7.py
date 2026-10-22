r"""Run the locked E7 AI-intervention experiment.

    .venv\Scripts\python.exe scripts/run_e7.py --smoke
    .venv\Scripts\python.exe scripts/run_e7.py --full
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e5, e7
from classroom_swarm.analysis import boundary_precision_check, bootstrap_indices, classify, paired_contrast
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e1 import git_state  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def write_rows(path: Path, rows: list[dict]) -> None:
    columns = sorted({key for row in rows for key in row})
    pq.write_table(pa.table({column: [row.get(column) for row in rows] for column in columns}), path)


def mean_interval(values, boot: np.ndarray) -> dict:
    array = np.asarray([np.nan if value is None else value for value in values], float)
    with np.errstate(invalid="ignore"):
        estimates = np.nanmean(array[boot], axis=1)
    finite = estimates[np.isfinite(estimates)]
    lo, hi = np.percentile(finite, [2.5, 97.5]) if len(finite) else (np.nan, np.nan)
    return {"n": int(np.isfinite(array).sum()),
            "estimate": float(np.nanmean(array)) if np.isfinite(array).any() else None,
            "lo": float(lo), "hi": float(hi)}


def file_hashes(root: Path) -> dict[str, str]:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "hashes.json")
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def load_summary(rep_dir: Path) -> list[dict]:
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    return e7.run_summaries(tables, e7.read_ai_table(rep_dir, "ai_decisions"))


def contrast(rows, outcome, treatment, reference, boot):
    return paired_contrast(rows, outcome, (treatment,), (reference,), boot, key=("experiment_id",))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    prereg_sha = e7.verify_lock(REPO)
    commit, clean = git_state()
    if not clean:
        raise SystemExit("refusing to run: git tree is dirty")
    out = REPO / "runs" / ("E7-smoke" if args.smoke else "E7")
    if out.exists():
        if args.full:
            raise SystemExit(f"refusing to run: {out} exists and E7 runs exactly once")
        if args.smoke:
            shutil.rmtree(out)
    elif args.resume:
        raise SystemExit("refusing to resume: runs/E7 does not exist")

    s_reps = e7.SMOKE_REPLICATES if args.smoke else e7.STRUCTURAL_REPLICATES
    f_reps = e7.SMOKE_REPLICATES if args.smoke else e7.FACTORIAL_REPLICATES
    s_seed = e7.SMOKE_SEED if args.smoke else e7.STRUCTURAL_SEED
    f_seed = e7.SMOKE_SEED if args.smoke else e7.FACTORIAL_SEED
    structural, factorial = [], []
    started = time.perf_counter()
    for n, replicate in enumerate(s_reps, 1):
        if args.smoke:
            rep = e7.run_structural_replicate(replicate, s_seed, out / "structural")
            structural.extend(load_summary(rep))
            gc.collect(); pa.default_memory_pool().release_unused()
        else:
            checkpoint = out / "checkpoints" / "structural" / f"rep{replicate:04d}" / "summaries.parquet"
            if not checkpoint.exists():
                subprocess.run([sys.executable, str(REPO / "scripts" / "run_e7_worker.py"),
                                "--block", "structural", "--replicate", str(replicate), "--out", str(out)],
                               cwd=REPO, check=True)
            structural.extend(pq.read_table(checkpoint).to_pylist())
        if n % 20 == 0 or n == len(s_reps):
            print(f"S replicate {replicate} done ({n}/{len(s_reps)}, {time.perf_counter()-started:.0f} s)",
                  flush=True)
    f_started = time.perf_counter()
    structural_runtime = f_started - started
    for n, replicate in enumerate(f_reps, 1):
        if args.smoke:
            for shard in e7.run_factorial_replicate(replicate, f_seed, out / "factorial"):
                factorial.extend(load_summary(shard))
                gc.collect(); pa.default_memory_pool().release_unused()
        else:
            checkpoint = out / "checkpoints" / "factorial" / f"rep{replicate:04d}" / "summaries.parquet"
            if not checkpoint.exists():
                subprocess.run([sys.executable, str(REPO / "scripts" / "run_e7_worker.py"),
                                "--block", "factorial", "--replicate", str(replicate), "--out", str(out)],
                               cwd=REPO, check=True)
            factorial.extend(pq.read_table(checkpoint).to_pylist())
        if n % 5 == 0 or n == len(f_reps):
            print(f"F replicate {replicate} done ({n}/{len(f_reps)}, {time.perf_counter()-f_started:.0f} s)",
                  flush=True)

    s_boot = bootstrap_indices(len(s_reps), e7.BOOT_B, e7.BOOT_SEED)
    f_boot = bootstrap_indices(len(f_reps), e7.BOOT_B, e7.BOOT_SEED)
    structural_contrasts = []
    for label in e7.STRUCTURAL_LABELS:
        if label == "E7-S-control":
            continue
        for outcome in e7.SUMMARY_OUTCOMES:
            result = contrast(structural, outcome, label, "E7-S-control", s_boot)
            delta = e7.DELTA[outcome]
            classification, magnitude = classify(result["lo"], result["hi"], delta)
            structural_contrasts.append({
                "condition": label, "reference": "E7-S-control", "outcome": outcome,
                **{k: result[k] for k in ("n", "estimate", "lo", "hi")}, "delta": delta,
                "label": classification, "magnitude": magnitude,
                "adequate": boundary_precision_check(result, delta)["adequate"],
            })

    structural_absolute = []
    for label in e7.STRUCTURAL_LABELS:
        if label == "E7-S-control":
            continue
        result = e5.mean_ci(structural, label, "pA_available_late", s_boot)
        result.update(name="ai_adoption", threshold=0.20,
                      passed=bool(math.isfinite(result["lo"]) and result["lo"] > 0.20))
        structural_absolute.append(result)

    effects = []
    effect_specs = [("main", (i,), e7.FACTOR_NAMES[i]) for i in range(7)]
    effect_specs += [("two_way", pair, f"{e7.FACTOR_NAMES[pair[0]]}x{e7.FACTOR_NAMES[pair[1]]}")
                     for pair in combinations(range(7), 2)]
    targeted = {(0, 3), (4, 5)}
    for outcome in e7.PRIMARY:
        for kind, indices, name in effect_specs:
            interval = mean_interval(e7.factorial_effects(factorial, outcome, indices), f_boot)
            delta = e7.DELTA[outcome]
            classification, magnitude = classify(interval["lo"], interval["hi"], delta)
            effects.append({"kind": kind, "effect": name, "indices": "x".join(map(str, indices)),
                            "targeted": indices in targeted, "outcome": outcome, **interval,
                            "delta": delta, "label": classification, "magnitude": magnitude,
                            "adequate": boundary_precision_check(interval, delta)["adequate"]})

    def c(outcome, treatment, reference="E7-S-control"):
        return contrast(structural, outcome, treatment, reference, s_boot)

    base_grade, base_k = c("grade_late", "E7-S-base"), c("K_final", "E7-S-base")
    base_exam, base_conf = c("exam_final", "E7-S-base"), c("C_final", "E7-S-base")
    base_copy = c("pC_late", "E7-S-base")
    withdraw_exam = c("exam_final", "E7-S-withdraw")
    learning_k = c("K_final", "E7-S-learning", "E7-S-base")
    conf_null = c("pA_available_late", "E7-S-conf05", "E7-S-conf0")
    absolute = {r["condition"]: r for r in structural_absolute}
    predictions = [
        {"prediction": "P1_adoption", "passed": absolute["E7-S-base"]["passed"]},
        {"prediction": "P2_performance_learning_separation",
         "passed": base_grade["lo"] > 0.10 and base_k["hi"] < -0.02},
        {"prediction": "P3_unaided_deficit", "passed": base_exam["hi"] < -0.03},
        {"prediction": "P4_confidence_scenario", "passed": base_conf["hi"] < -0.10},
        {"prediction": "P5_human_copy_displacement", "passed": base_copy["hi"] < -0.05},
        {"prediction": "P6_withdrawal_dependence", "passed": withdraw_exam["hi"] < -0.03},
        {"prediction": "P7_learning_support", "passed": learning_k["lo"] > 0.02},
        {"prediction": "P8_confidence_negative_control",
         "passed": conf_null["lo"] >= -0.02 and conf_null["hi"] <= 0.02},
        {"prediction": "P9_decision_rule_adoption",
         "passed": absolute["E7-S-softmax010"]["passed"] and absolute["E7-S-softmax025"]["passed"]},
    ]

    derived = out / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    for name, rows in (("structural_summaries", structural), ("structural_contrasts", structural_contrasts),
                       ("structural_absolute", structural_absolute), ("factorial_summaries", factorial),
                       ("factorial_effects", effects), ("predictions", predictions)):
        write_rows(derived / f"{name}.parquet", rows)
    runtime = time.perf_counter() - started
    report = {
        "experiment_id": "E7-smoke" if args.smoke else "E7", "preregistration_sha256": prereg_sha,
        "git_commit": commit,
        "v3_model_commit": json.loads((REPO / e7.MODEL_LOCK).read_text("utf-8"))["git_commit"],
        "structural_seed": s_seed, "factorial_seed": f_seed, "bootstrap_seed": e7.BOOT_SEED,
        "structural_replicates": len(s_reps), "factorial_replicates": len(f_reps),
        "structural_runs": len(structural), "factorial_runs": len(factorial), "runtime_s": round(runtime, 1),
        "structural_contrasts_adequate": sum(r["adequate"] for r in structural_contrasts),
        "structural_contrasts_total": len(structural_contrasts),
        "factorial_effects_adequate": sum(r["adequate"] for r in effects),
        "factorial_effects_total": len(effects), "calibration": "omitted; no data", "deviations": [],
    }
    (derived / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (derived / "hashes.json").write_text(json.dumps(file_hashes(out), indent=2, sort_keys=True) + "\n",
                                          encoding="utf-8")

    expected_s, expected_f = len(s_reps) * 12, len(f_reps) * 128
    checks = {
        "all structural runs completed": len(structural) == expected_s,
        "all factorial runs completed": len(factorial) == expected_f,
        "all structural labels present": {r["experiment_id"] for r in structural} == set(e7.STRUCTURAL_LABELS),
        "all factorial labels present": {r["experiment_id"] for r in factorial} == set(e7.FACTORIAL_LABELS),
        "structural contrasts complete": len(structural_contrasts) == 11 * len(e7.SUMMARY_OUTCOMES),
        "factorial effects complete": len(effects) == 28 * len(e7.PRIMARY),
        "predictions complete": len(predictions) == 9,
    }
    if not args.smoke:
        if not all(checks.values()):
            raise RuntimeError(f"E7 integrity checks failed: {[k for k, v in checks.items() if not v]}")
        print(f"E7 complete in {runtime/60:.1f} min: {expected_s+expected_f} runs. Results in {derived}")
        return 0
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    projected = (structural_runtime / len(s_reps) * len(e7.STRUCTURAL_REPLICATES)
                 + (runtime - structural_runtime) / len(f_reps) * len(e7.FACTORIAL_REPLICATES)) / 60
    print(f"smoke runtime {runtime:.1f} s; coarse projected full run {projected:.0f} min")
    shutil.rmtree(out)
    print(f"smoke outputs deleted ({out})")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
