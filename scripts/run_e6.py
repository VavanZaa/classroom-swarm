"""Run the locked E6 robustness and full-factorial experiment.

    .venv\\Scripts\\python.exe scripts/run_e6.py --smoke
    .venv\\Scripts\\python.exe scripts/run_e6.py --full
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

from classroom_swarm import e5, e6
from classroom_swarm.analysis import boundary_precision_check, bootstrap_indices, classify, paired_contrast
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e1 import git_state  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUTCOMES = tuple(o for o in e5.CONFIRMATORY if o != "source_resid_persist") + ("source_resid_persist_strict",)


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


def load_tables(path: Path) -> dict[str, pa.Table]:
    return {name: read_table(path, name) for name in TABLES}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--resume", action="store_true", help="resume the documented D1 technical interruption")
    args = parser.parse_args()

    prereg_sha = e6.verify_lock(REPO)
    commit, clean = git_state()
    if not clean:
        raise SystemExit("refusing to run: git tree is dirty")
    out = REPO / "runs" / ("E6-smoke" if args.smoke else "E6")
    if out.exists():
        if args.full:
            raise SystemExit(f"refusing to run: {out} exists and E6 runs exactly once")
        if args.smoke:
            shutil.rmtree(out)
    elif args.resume:
        raise SystemExit("refusing to resume: runs/E6 does not exist")
    s_reps = e6.SMOKE_REPLICATES if args.smoke else e6.STRUCTURAL_REPLICATES
    f_reps = e6.SMOKE_REPLICATES if args.smoke else e6.FACTORIAL_REPLICATES
    s_seed = e6.SMOKE_SEED if args.smoke else e6.STRUCTURAL_SEED
    f_seed = e6.SMOKE_SEED if args.smoke else e6.FACTORIAL_SEED

    structural_summaries, source_null_rows = [], []
    started = time.perf_counter()
    for n, replicate in enumerate(s_reps, start=1):
        if args.smoke:
            rep_dir = e6.run_structural_replicate(replicate, s_seed, out / "structural")
            tables = load_tables(rep_dir)
            summaries = e6.run_summaries(tables)
            structural_summaries.extend(summaries)
            base_run = next(row["run_id"] for row in summaries if row["experiment_id"] == "E6-S-base")
            source_null_rows.append(e6.source_null(tables, base_run, replicate, 9))
            del tables, summaries
            gc.collect()
            pa.default_memory_pool().release_unused()
        else:
            checkpoint = out / "checkpoints" / "structural" / f"rep{replicate:04d}"
            summary_path = checkpoint / "summaries.parquet"
            if not summary_path.exists():
                subprocess.run([sys.executable, str(REPO / "scripts" / "run_e6_worker.py"),
                                "--block", "structural", "--replicate", str(replicate),
                                "--out", str(out)], cwd=REPO, check=True)
            structural_summaries.extend(pq.read_table(summary_path).to_pylist())
            source_null_rows.extend(pq.read_table(checkpoint / "source_null.parquet").to_pylist())
        if n % 20 == 0 or n == len(s_reps):
            print(f"S replicate {replicate} done ({n}/{len(s_reps)}, {time.perf_counter() - started:.0f} s)",
                  flush=True)

    factorial_summaries = []
    f_started = time.perf_counter()
    structural_runtime = f_started - started
    for n, replicate in enumerate(f_reps, start=1):
        if args.smoke:
            shard_dirs = e6.run_factorial_replicate(replicate, f_seed, out / "factorial")
            for shard_dir in shard_dirs:
                tables = load_tables(shard_dir)
                factorial_summaries.extend(e6.run_summaries(tables))
                del tables
                gc.collect()
                pa.default_memory_pool().release_unused()
        else:
            checkpoint = out / "checkpoints" / "factorial" / f"rep{replicate:04d}" / "summaries.parquet"
            if not checkpoint.exists():
                subprocess.run([sys.executable, str(REPO / "scripts" / "run_e6_worker.py"),
                                "--block", "factorial", "--replicate", str(replicate),
                                "--out", str(out)], cwd=REPO, check=True)
            factorial_summaries.extend(pq.read_table(checkpoint).to_pylist())
        if n % 5 == 0 or n == len(f_reps):
            print(f"F replicate {replicate} done ({n}/{len(f_reps)}, {time.perf_counter() - f_started:.0f} s)",
                  flush=True)

    s_boot = bootstrap_indices(len(s_reps), e6.BOOT_B, e6.BOOT_SEED)
    f_boot = bootstrap_indices(len(f_reps), e6.BOOT_B, e6.BOOT_SEED)
    structural_contrasts = []
    for label in e6.STRUCTURAL_LABELS:
        if label == "E6-S-base":
            continue
        for outcome in OUTCOMES:
            result = paired_contrast(structural_summaries, outcome, (label,), ("E6-S-base",), s_boot,
                                     key=("experiment_id",))
            delta = e6.DELTA[outcome]
            classification, magnitude = classify(result["lo"], result["hi"], delta)
            structural_contrasts.append({
                "condition": label, "reference": "E6-S-base", "outcome": outcome,
                **{key: result[key] for key in ("n", "estimate", "lo", "hi")}, "delta": delta,
                "label": classification, "magnitude": magnitude,
                "adequate": boundary_precision_check(result, delta)["adequate"],
            })

    structural_absolute = []
    for label in e6.STRUCTURAL_LABELS:
        result = e5.mean_ci(structural_summaries, label, "pC_late", s_boot)
        result.update(name="copying_robustness", threshold=0.04,
                      passed=bool(math.isfinite(result["lo"]) and result["lo"] > 0.04))
        structural_absolute.append(result)
    base_strict = e5.mean_ci(structural_summaries, "E6-S-base", "source_resid_persist_strict", s_boot)
    base_strict.update(name="strict_role_mean", threshold=0.20,
                       passed=bool(math.isfinite(base_strict["lo"]) and base_strict["lo"] > 0.20))
    source_share = mean_interval([float(row["significant"]) if row["significant"] is not None else None
                                  for row in source_null_rows], s_boot)
    source_share.update(name="strict_role_significant_share", threshold=0.50,
                        passed=bool(math.isfinite(source_share["lo"]) and source_share["lo"] > 0.50))
    structural_absolute.extend((base_strict, source_share))

    factorial_rows = []
    effect_specs = [("main", (index,), e6.FACTOR_NAMES[index]) for index in range(8)]
    effect_specs += [("two_way", pair, f"{e6.FACTOR_NAMES[pair[0]]}x{e6.FACTOR_NAMES[pair[1]]}")
                     for pair in combinations(range(8), 2)]
    effect_specs.append(("targeted_three_way", (0, 1, 2), "copy_costxeta_Qxepsilon"))
    for outcome in e6.PRIMARY:
        for kind, indices, name in effect_specs:
            effects = e6.factorial_effects(factorial_summaries, outcome, indices)
            interval = mean_interval(effects, f_boot)
            delta = e6.DELTA[outcome]
            classification, magnitude = classify(interval["lo"], interval["hi"], delta)
            factorial_rows.append({
                "kind": kind, "effect": name, "indices": "x".join(map(str, indices)), "outcome": outcome,
                **interval, "delta": delta, "label": classification, "magnitude": magnitude,
                "adequate": boundary_precision_check(interval, delta)["adequate"],
            })

    pC_main = sorted((row for row in factorial_rows if row["kind"] == "main" and row["outcome"] == "pC_late"),
                     key=lambda row: abs(row["estimate"]), reverse=True)
    predicted_top = {"eta_social", "R", "copy_cost", "eta_Q"}
    prediction_rows = [
        {"prediction": "P1_base_copying", "passed": next(r["passed"] for r in structural_absolute
                                                            if r.get("condition") == "E6-S-base")},
        {"prediction": "P2_strict_roles", "passed": base_strict["passed"] and source_share["passed"]},
        {"prediction": "P3_equal_cost_copying", "passed": next(r["passed"] for r in structural_absolute
                                                                  if r.get("condition") == "E6-S-equalCost")},
        {"prediction": "P4_softmax_copying", "passed": all(next(r["passed"] for r in structural_absolute
                                                                  if r.get("condition") == label)
                                                            for label in ("E6-S-softmax010", "E6-S-softmax025"))},
        {"prediction": "P5_top_four_pC_factors", "passed": {r["effect"] for r in pC_main[:4]} == predicted_top},
    ]

    derived = out / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    for name, rows in (
        ("structural_summaries", structural_summaries), ("source_null", source_null_rows),
        ("structural_contrasts", structural_contrasts), ("structural_absolute", structural_absolute),
        ("factorial_summaries", factorial_summaries), ("factorial_effects", factorial_rows),
        ("predictions", prediction_rows),
    ):
        write_rows(derived / f"{name}.parquet", rows)

    runtime = time.perf_counter() - started
    report = {
        "experiment_id": "E6-smoke" if args.smoke else "E6", "preregistration_sha256": prereg_sha,
        "git_commit": commit, "v3_model_commit": json.loads((REPO / e6.MODEL_LOCK).read_text("utf-8"))["git_commit"],
        "structural_seed": s_seed, "factorial_seed": f_seed, "bootstrap_seed": e6.BOOT_SEED,
        "source_null_seed": e6.SOURCE_NULL_SEED, "structural_replicates": len(s_reps),
        "factorial_replicates": len(f_reps), "structural_runs": len(structural_summaries),
        "factorial_runs": len(factorial_summaries), "runtime_s": round(runtime, 1),
        "structural_contrasts_adequate": sum(row["adequate"] for row in structural_contrasts),
        "structural_contrasts_total": len(structural_contrasts),
        "factorial_effects_adequate": sum(row["adequate"] for row in factorial_rows),
        "factorial_effects_total": len(factorial_rows), "calibration": "omitted; no data",
        "deviations": ([] if not args.resume else [
            {"id": "D1", "type": "technical",
             "description": "resumed after MemoryError; complete raw replicates were not overwritten"},
            {"id": "D2", "type": "technical",
             "description": "isolated one replicate per worker after cumulative analysis memory persisted"},
        ]),
    }
    (derived / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (derived / "hashes.json").write_text(json.dumps(file_hashes(out), indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")

    expected_s, expected_f = len(s_reps) * 14, len(f_reps) * 256
    checks = {
        "all structural runs completed": len(structural_summaries) == expected_s,
        "all factorial runs completed": len(factorial_summaries) == expected_f,
        "all structural labels present": {r["experiment_id"] for r in structural_summaries} == set(e6.STRUCTURAL_LABELS),
        "all factorial labels present": {r["experiment_id"] for r in factorial_summaries} == set(e6.FACTORIAL_LABELS),
        "source null complete": len(source_null_rows) == len(s_reps),
        "structural contrasts complete": len(structural_contrasts) == 13 * len(OUTCOMES),
        "factorial effects complete": len(factorial_rows) == 37 * len(e6.PRIMARY),
        "predictions complete": len(prediction_rows) == 5,
        "all derived outputs present": all((derived / f"{name}.parquet").exists() for name in (
            "structural_summaries", "source_null", "structural_contrasts", "structural_absolute",
            "factorial_summaries", "factorial_effects", "predictions")),
    }
    if not args.smoke:
        if not all(checks.values()):
            raise RuntimeError(f"E6 integrity checks failed: {[name for name, ok in checks.items() if not ok]}")
        print(f"E6 complete in {runtime / 60:.1f} min: {expected_s + expected_f} runs. Results in {derived}")
        return 0

    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    factorial_runtime = runtime - structural_runtime
    projected = (structural_runtime / len(s_reps) * len(e6.STRUCTURAL_REPLICATES)
                 + factorial_runtime / len(f_reps) * len(e6.FACTORIAL_REPLICATES)) / 60
    print(f"smoke runtime {runtime:.1f} s; coarse projected full run {projected:.0f} min")
    shutil.rmtree(out)
    print(f"smoke outputs deleted ({out})")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
