r"""Run the locked E8 universal-access AI policy experiment.

    .venv\Scripts\python.exe scripts/run_e8.py --smoke
    .venv\Scripts\python.exe scripts/run_e8.py --full
    .venv\Scripts\python.exe scripts/run_e8.py --resume
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
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e5, e8
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
    if not np.isfinite(array).any():
        return {"n": 0, "estimate": None, "lo": float("nan"), "hi": float("nan")}
    with warnings.catch_warnings(), np.errstate(invalid="ignore"):
        warnings.simplefilter("ignore", category=RuntimeWarning)
        estimates = np.nanmean(array[boot], axis=1)
    finite = estimates[np.isfinite(estimates)]
    lo, hi = np.percentile(finite, [2.5, 97.5]) if len(finite) else (np.nan, np.nan)
    return {"n": int(np.isfinite(array).sum()),
            "estimate": float(np.nanmean(array)) if np.isfinite(array).any() else None,
            "lo": float(lo), "hi": float(hi)}


def absolute_interval(rows, condition: str, outcome: str, boot: np.ndarray) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return e5.mean_ci(rows, condition, outcome, boot)


def file_hashes(root: Path) -> dict[str, str]:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "hashes.json")
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def load_outputs(rep_dir: Path) -> tuple[list[dict], list[dict]]:
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    return e8.run_outputs(tables, e8.read_ai_table(rep_dir))


def contrast(rows, outcome, treatment, reference, boot):
    return paired_contrast(rows, outcome, (treatment,), (reference,), boot, key=("experiment_id",))


def marginal_values(rows: list[dict], outcome: str, selector_high, selector_low) -> list[float]:
    by_rep = defaultdict(list)
    for row in rows:
        by_rep[row["replicate"]].append(row)
    values = []
    for replicate in sorted(by_rep):
        high = [r[outcome] for r in by_rep[replicate] if selector_high(r["experiment_id"]) and r[outcome] is not None]
        low = [r[outcome] for r in by_rep[replicate] if selector_low(r["experiment_id"]) and r[outcome] is not None]
        values.append(float(np.mean(high) - np.mean(low)) if high and low else float("nan"))
    return values


def _surface_parts(label: str):
    return e8.surface_policy(label)


def _classification_row(block: str, condition: str, reference: str, outcome: str, result: dict) -> dict:
    delta = e8.DELTA[outcome]
    label, magnitude = classify(result["lo"], result["hi"], delta)
    return {"block": block, "condition": condition, "reference": reference, "outcome": outcome,
            **{k: result[k] for k in ("n", "estimate", "lo", "hi")}, "delta": delta,
            "label": label, "magnitude": magnitude,
            "adequate": boundary_precision_check(result, delta)["adequate"]}


def _run_smoke_block(block: str, replicate: int, seed: int, plan, out: Path, shard_size: int | None):
    if shard_size is None:
        paths = [e8.run_block_replicate(block, replicate, seed, out / block, plan)]
    else:
        paths = e8.run_sharded_replicate(block, replicate, seed, out / block, plan, shard_size)
    summaries, trajectories = [], []
    for path in paths:
        srows, trows = load_outputs(path)
        summaries.extend(srows); trajectories.extend(trows)
        gc.collect(); pa.default_memory_pool().release_unused()
    return summaries, trajectories


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    prereg_sha = e8.verify_lock(REPO)
    commit, clean = git_state()
    if not clean:
        raise SystemExit("refusing to run: git tree is dirty")
    out = REPO / "runs" / ("E8-smoke" if args.smoke else "E8")
    if out.exists():
        if args.full:
            raise SystemExit(f"refusing to run: {out} exists and E8 runs exactly once")
        if args.smoke:
            shutil.rmtree(out)
    elif args.resume:
        raise SystemExit("refusing to resume: runs/E8 does not exist")

    blocks = (
        ("primary", e8.PRIMARY_SEED, e8.PRIMARY_REPLICATES, e8.primary_conditions(), None),
        ("surface", e8.SURFACE_SEED, e8.SURFACE_REPLICATES, e8.surface_conditions(), 10),
        ("robustness", e8.ROBUSTNESS_SEED, e8.ROBUSTNESS_REPLICATES, e8.robustness_conditions(), 12),
    )
    all_summaries, all_trajectories = {}, {}
    runtimes = {}
    started = time.perf_counter()
    for block, full_seed, full_reps, plan, shard_size in blocks:
        reps = e8.SMOKE_REPLICATES if args.smoke else full_reps
        seed = e8.SMOKE_SEED if args.smoke else full_seed
        summaries, trajectories = [], []
        block_started = time.perf_counter()
        for n, replicate in enumerate(reps, 1):
            if args.smoke:
                srows, trows = _run_smoke_block(block, replicate, seed, plan, out, shard_size)
            else:
                checkpoint = out / "checkpoints" / block / f"rep{replicate:04d}"
                if not (checkpoint / "summaries.parquet").exists():
                    subprocess.run([sys.executable, str(REPO / "scripts" / "run_e8_worker.py"),
                                    "--block", block, "--replicate", str(replicate), "--out", str(out)],
                                   cwd=REPO, check=True)
                srows = pq.read_table(checkpoint / "summaries.parquet").to_pylist()
                trows = pq.read_table(checkpoint / "trajectories.parquet").to_pylist()
            summaries.extend(srows); trajectories.extend(trows)
            if n % (20 if block == "primary" else 5) == 0 or n == len(reps):
                print(f"{block} replicate {replicate} ({n}/{len(reps)}, "
                      f"{time.perf_counter()-block_started:.0f} s)", flush=True)
        all_summaries[block], all_trajectories[block] = summaries, trajectories
        runtimes[block] = time.perf_counter() - block_started

    primary, surface, robust = (all_summaries[x] for x in ("primary", "surface", "robustness"))
    a_boot = bootstrap_indices(len(e8.SMOKE_REPLICATES if args.smoke else e8.PRIMARY_REPLICATES),
                               e8.BOOT_B, e8.BOOT_SEED)
    b_boot = bootstrap_indices(len(e8.SMOKE_REPLICATES if args.smoke else e8.SURFACE_REPLICATES),
                               e8.BOOT_B, e8.BOOT_SEED)
    c_boot = bootstrap_indices(len(e8.SMOKE_REPLICATES if args.smoke else e8.ROBUSTNESS_REPLICATES),
                               e8.BOOT_B, e8.BOOT_SEED)

    primary_absolute = []
    for label in e8.PRIMARY_LABELS:
        for outcome in e8.SUMMARY_OUTCOMES:
            row = absolute_interval(primary, label, outcome, a_boot)
            primary_absolute.append({"condition": label, "outcome": outcome, **row})
    primary_contrasts = []
    for treatment, reference in (("E8-A-unrestricted", "E8-A-none"),
                                 ("E8-A-controlled", "E8-A-none"),
                                 ("E8-A-unrestricted", "E8-A-controlled"),
                                 ("E8-A-controlled", "E8-A-unrestricted")):
        for outcome in e8.SUMMARY_OUTCOMES:
            primary_contrasts.append(_classification_row(
                "primary", treatment, reference, outcome,
                contrast(primary, outcome, treatment, reference, a_boot)))

    trajectory_summaries = []
    for label in e8.PRIMARY_LABELS:
        for h in range(1, 21):
            subset = [r for r in all_trajectories["primary"]
                      if r["experiment_id"] == label and r["homework_index"] == h]
            for outcome in ("pA", "pS", "pD", "pC", "grade", "K", "C"):
                interval = mean_interval([r[outcome] for r in subset], a_boot)
                trajectory_summaries.append({"condition": label, "homework_index": h,
                                             "outcome": outcome, **interval})

    surface_contrasts = []
    surface_absolute = []
    for label in e8.SURFACE_LABELS:
        for outcome in e8.SUMMARY_OUTCOMES:
            absolute = absolute_interval(surface, label, outcome, b_boot)
            surface_absolute.append({"condition": label, "outcome": outcome, **absolute})
            if label != "E8-B-none":
                surface_contrasts.append(_classification_row(
                    "surface", label, "E8-B-none", outcome,
                    contrast(surface, outcome, label, "E8-B-none", b_boot)))

    cost_values = marginal_values(surface, "pA_late",
                                   lambda x: _surface_parts(x)[0] == "T" and _surface_parts(x)[3] == 2,
                                   lambda x: _surface_parts(x)[0] == "T" and _surface_parts(x)[3] == 1)
    learn_values = marginal_values(surface, "K_final",
                                    lambda x: _surface_parts(x)[0] == "T" and _surface_parts(x)[1] == 1.5,
                                    lambda x: _surface_parts(x)[0] == "T" and _surface_parts(x)[1] == 0.5)
    cost_effect, learning_effect = mean_interval(cost_values, b_boot), mean_interval(learn_values, b_boot)

    robust_absolute = []
    for label in e8.ROBUSTNESS_LABELS:
        for outcome in e8.PRIMARY_OUTCOMES:
            robust_absolute.append({"condition": label, "outcome": outcome,
                                    **absolute_interval(robust, label, outcome, c_boot)})
    decision_rows = []
    for regime in "UT":
        argmax = f"E8-C-{regime}-00000"
        for choice in (1, 2):
            treatment = f"E8-C-{regime}-0{choice}000"
            result = contrast(robust, "pA_late", treatment, argmax, c_boot)
            decision_rows.append(_classification_row("robustness", treatment, argmax, "pA_late", result))

    abs_lookup = {(r["condition"], r["outcome"]): r for r in primary_absolute}
    con_lookup = {(r["condition"], r["reference"], r["outcome"]): r for r in primary_contrasts}
    robust_lookup = {(r["condition"], r["outcome"]): r for r in robust_absolute}
    u_n_gap = con_lookup[("E8-A-unrestricted", "E8-A-none", "grade_exam_gap")]
    t_u_k = con_lookup[("E8-A-controlled", "E8-A-unrestricted", "K_final")]
    t_u_exam = con_lookup[("E8-A-controlled", "E8-A-unrestricted", "exam_final")]
    u_t_early = con_lookup[("E8-A-unrestricted", "E8-A-controlled", "pA_early")]
    u_t_late = con_lookup[("E8-A-unrestricted", "E8-A-controlled", "pA_late")]
    u_t_d = con_lookup[("E8-A-unrestricted", "E8-A-controlled", "pD_late")]
    u_t_c = con_lookup[("E8-A-unrestricted", "E8-A-controlled", "pC_late")]
    decision_abs = [robust_lookup[(f"E8-C-{regime}-0{choice}000", "pA_late")]
                    for regime in "UT" for choice in (0, 1, 2)]
    decision_sensitive = any((r["lo"] > .02 or r["hi"] < -.02) for r in decision_rows)
    predictions = [
        {"prediction": "P1_voluntary_use", "passed":
         abs_lookup[("E8-A-unrestricted", "pA_late")]["lo"] > .05 and
         abs_lookup[("E8-A-controlled", "pA_late")]["lo"] > .05},
        {"prediction": "P2_adoption_advantage", "passed": u_t_early["lo"] > .05 and u_t_late["lo"] > .05},
        {"prediction": "P3_performance_illusion", "passed": u_n_gap["lo"] > .05},
        {"prediction": "P4_controlled_protection", "passed": t_u_k["lo"] > .02 and t_u_exam["lo"] > .02},
        {"prediction": "P5_unrestricted_displacement", "passed": u_t_d["hi"] < -.02 and u_t_c["hi"] < -.02},
        {"prediction": "P6_controlled_vs_no_ai_open", "passed": None},
        {"prediction": "P7_effort_sensitivity", "passed": cost_effect["hi"] < -.02},
        {"prediction": "P8_tutor_learning_sensitivity", "passed": learning_effect["lo"] > .02},
        {"prediction": "P9_decision_robust_use", "passed": all(r["lo"] > .05 for r in decision_abs)},
        {"prediction": "P10_decision_rule_sensitivity", "passed": decision_sensitive},
    ]

    bcon = {(r["condition"], r["outcome"]): r for r in surface_contrasts}
    babs = {(r["condition"], r["outcome"]): r for r in surface_absolute}
    robust_viable = (robust_lookup[("E8-C-T-00000", "pA_late")]["lo"] > .05 and
                       any(robust_lookup[(f"E8-C-T-0{q}000", "pA_late")]["lo"] > .05 for q in (1, 2)))
    policy_map = []
    by_rep_surface = defaultdict(dict)
    for row in surface: by_rep_surface[row["replicate"]][row["experiment_id"]] = row
    for label in e8.SURFACE_LABELS:
        if label == "E8-B-none": continue
        regime, first, second, cost = _surface_parts(label)
        k, exam = bcon[(label, "K_final")], bcon[(label, "exam_final")]
        grade, gap = bcon[(label, "grade_late")], bcon[(label, "grade_exam_gap")]
        discuss, copy = bcon[(label, "pD_late")], bcon[(label, "pC_late")]
        safe = k["lo"] > -.01 and exam["lo"] > -.01
        useful = safe and k["lo"] > .01 and exam["lo"] > .01
        illusion = grade["lo"] > .05 and exam["hi"] < -.01 and gap["lo"] > .05
        displacement = discuss["hi"] < -.05 or copy["hi"] < -.05
        viable = regime == "T" and safe and babs[(label, "pA_late")]["lo"] > .05 and robust_viable
        if regime == "T":
            traffic = "red" if (not safe or illusion) else ("amber" if (not useful or displacement) else "green")
        else:
            traffic = None
        beat_k = np.mean([rows[label]["K_final"] > rows["E8-B-none"]["K_final"]
                          for rows in by_rep_surface.values()])
        beat_exam = np.mean([rows[label]["exam_final"] > rows["E8-B-none"]["exam_final"]
                             for rows in by_rep_surface.values()])
        policy_map.append({"condition": label, "regime": regime, "mechanism_1": first,
                           "mechanism_2": second, "cost": cost, "safe": safe, "useful": useful,
                           "performance_illusion": illusion, "social_displacement": displacement,
                           "viable_controlled": viable, "traffic": traffic,
                           "classrooms_beating_no_ai_K": float(beat_k),
                           "classrooms_beating_no_ai_exam": float(beat_exam)})

    derived = out / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    datasets = (
        ("primary_summaries", primary), ("primary_trajectories", all_trajectories["primary"]),
        ("primary_absolute", primary_absolute), ("primary_contrasts", primary_contrasts),
        ("trajectory_summaries", trajectory_summaries), ("surface_summaries", surface),
        ("surface_absolute", surface_absolute), ("surface_contrasts", surface_contrasts),
        ("robustness_summaries", robust), ("robustness_absolute", robust_absolute),
        ("decision_contrasts", decision_rows), ("policy_map", policy_map), ("predictions", predictions),
        ("targeted_effects", [{"effect": "controlled_cost_2_minus_1", "outcome": "pA_late", **cost_effect},
                              {"effect": "tutor_learning_1.5_minus_0.5", "outcome": "K_final", **learning_effect}]),
    )
    for name, rows in datasets:
        write_rows(derived / f"{name}.parquet", rows)

    runtime = time.perf_counter() - started
    reps_used = {"primary": len(e8.SMOKE_REPLICATES if args.smoke else e8.PRIMARY_REPLICATES),
                 "surface": len(e8.SMOKE_REPLICATES if args.smoke else e8.SURFACE_REPLICATES),
                 "robustness": len(e8.SMOKE_REPLICATES if args.smoke else e8.ROBUSTNESS_REPLICATES)}
    report = {
        "experiment_id": "E8-smoke" if args.smoke else "E8", "preregistration_sha256": prereg_sha,
        "git_commit": commit,
        "v3_model_commit": json.loads((REPO / e8.MODEL_LOCK).read_text("utf-8"))["git_commit"],
        "seeds": {"primary": e8.SMOKE_SEED if args.smoke else e8.PRIMARY_SEED,
                  "surface": e8.SMOKE_SEED if args.smoke else e8.SURFACE_SEED,
                  "robustness": e8.SMOKE_SEED if args.smoke else e8.ROBUSTNESS_SEED,
                  "bootstrap": e8.BOOT_SEED},
        "replicates": reps_used, "runs": {k: len(v) for k, v in all_summaries.items()},
        "runtime_s": round(runtime, 1), "block_runtime_s": {k: round(v, 1) for k, v in runtimes.items()},
        "primary_contrasts_adequate": sum(r["adequate"] for r in primary_contrasts),
        "primary_contrasts_total": len(primary_contrasts),
        "surface_contrasts_adequate": sum(r["adequate"] for r in surface_contrasts),
        "surface_contrasts_total": len(surface_contrasts),
        "calibration": "omitted; no data", "deviations": [], "control_parity_test": "tests/test_e8.py",
    }
    (derived / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (derived / "hashes.json").write_text(json.dumps(file_hashes(out), indent=2, sort_keys=True) + "\n",
                                          encoding="utf-8")

    expected = {"primary": reps_used["primary"] * 3, "surface": reps_used["surface"] * 37,
                "robustness": reps_used["robustness"] * 144}
    checks = {
        **{f"all {block} runs completed": len(all_summaries[block]) == count for block, count in expected.items()},
        "all primary labels present": {r["experiment_id"] for r in primary} == set(e8.PRIMARY_LABELS),
        "all surface labels present": {r["experiment_id"] for r in surface} == set(e8.SURFACE_LABELS),
        "all robustness labels present": {r["experiment_id"] for r in robust} == set(e8.ROBUSTNESS_LABELS),
        "predictions complete": len(predictions) == 10,
        "policy cells complete": len(policy_map) == 36,
    }
    if not args.smoke:
        if not all(checks.values()):
            raise RuntimeError(f"E8 integrity checks failed: {[k for k, value in checks.items() if not value]}")
        print(f"E8 complete in {runtime/60:.1f} min: {sum(expected.values())} runs. Results in {derived}")
        return 0
    for name, ok in checks.items(): print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    projected = sum(runtimes[k] / 2 * len(reps) for k, _, reps, _, _ in blocks) / 60
    print(f"smoke runtime {runtime:.1f} s; coarse projected full run {projected:.0f} min")
    shutil.rmtree(out)
    print(f"smoke outputs deleted ({out})")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
