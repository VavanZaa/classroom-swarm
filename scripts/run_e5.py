"""Run the locked E5 V3 emergence experiment.

    .venv\\Scripts\\python.exe scripts/run_e5.py --smoke
    .venv\\Scripts\\python.exe scripts/run_e5.py --full

The smoke checks the complete pipeline without printing outcomes and deletes its output. The full run
is one-shot and refuses an existing runs/E5 directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e5
from classroom_swarm.analysis import boundary_precision_check, bootstrap_indices, classify, paired_contrast
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e1 import git_state  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def write_rows(path: Path, rows: list[dict]) -> None:
    columns = sorted({key for row in rows for key in row})
    pq.write_table(pa.table({column: [row.get(column) for row in rows] for column in columns}), path)


def file_hashes(root: Path) -> dict[str, str]:
    paths = sorted(p for p in root.rglob("*") if p.is_file() and p.name != "hashes.json")
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = parser.parse_args()

    prereg_sha = e5.verify_lock(REPO)
    commit, clean = git_state()
    if not clean:
        raise SystemExit("refusing to run: git tree is dirty")
    if args.smoke:
        exp_id, seed, reps = e5.SMOKE_ID, e5.SMOKE_SEED, e5.SMOKE_REPLICATES
    else:
        exp_id, seed, reps = e5.EXPERIMENT_ID, e5.MASTER_SEED, e5.REPLICATES
    out = REPO / "runs" / exp_id
    if out.exists():
        if args.full:
            raise SystemExit(f"refusing to run: {out} exists and E5 runs exactly once")
        shutil.rmtree(out)

    summaries: list[dict] = []
    started = time.perf_counter()
    for n, replicate in enumerate(reps, start=1):
        rep_dir = e5.run_e5_replicate(replicate, seed, out)
        tables = {name: read_table(rep_dir, name) for name in TABLES}
        summaries.extend(e5.run_summaries(tables))
        if n % 10 == 0 or n == len(reps):
            print(f"replicate {replicate} done ({n}/{len(reps)}, {time.perf_counter() - started:.0f} s)", flush=True)

    boot = bootstrap_indices(len(reps), e5.BOOT_B, e5.BOOT_SEED)
    contrast_rows = []
    for label in e5.CONDITION_LABELS:
        if label == "E5-base":
            continue
        for outcome in e5.CONFIRMATORY:
            result = paired_contrast(summaries, outcome, (label,), ("E5-base",), boot,
                                     key=("experiment_id",))
            delta = e5.DELTA[outcome]
            classification, magnitude = classify(result["lo"], result["hi"], delta)
            adequate = boundary_precision_check(result, delta)["adequate"]
            contrast_rows.append({
                "condition": label, "reference": "E5-base", "outcome": outcome, "n": result["n"],
                "estimate": result["estimate"], "lo": result["lo"], "hi": result["hi"], "delta": delta,
                "label": classification, "magnitude": magnitude, "adequate": adequate,
            })

    mechanism_rows = []
    for name, control, outcome, delta in (
        ("reinforcement_contribution", "E5-etaQ0", "pC_late", 0.02),
        ("learned_targeting_contribution", "E5-etaA0", "succ_late", 0.05),
    ):
        result = paired_contrast(summaries, outcome, ("E5-base",), (control,), boot,
                                 key=("experiment_id",))
        mechanism_rows.append({"name": name, "condition": "E5-base", "reference": control,
                               "outcome": outcome, "delta": delta, **{k: result[k] for k in ("n", "estimate", "lo", "hi")},
                               "adequate": boundary_precision_check(result, delta)["adequate"],
                               "passed": bool(math.isfinite(result["lo"]) and result["lo"] > delta)})

    absolute_rows = e5.absolute_tests(summaries, boot)
    seed_means = {label: e5.mean_ci(summaries, label, "pC_late", boot)["estimate"]
                  for label in ("E5-seed0", "E5-seed05", "E5-base", "E5-seed20")}
    seed_values = list(seed_means.values())
    seed_monotone = all(a <= b for a, b in zip(seed_values, seed_values[1:]))

    derived = out / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    write_rows(derived / "run_summaries.parquet", summaries)
    write_rows(derived / "contrasts.parquet", contrast_rows)
    write_rows(derived / "absolute_tests.parquet", absolute_rows)
    write_rows(derived / "mechanism_tests.parquet", mechanism_rows)
    (derived / "seed_dose.json").write_text(json.dumps({"means": seed_means, "monotone": seed_monotone}, indent=2) + "\n",
                                             encoding="utf-8")
    runtime = time.perf_counter() - started
    report = {
        "experiment_id": exp_id, "preregistration_sha256": prereg_sha, "git_commit": commit,
        "v3_model_commit": json.loads((REPO / e5.MODEL_LOCK).read_text("utf-8"))["git_commit"],
        "master_seed": seed, "bootstrap_seed": e5.BOOT_SEED, "replicates": len(reps),
        "conditions": len(e5.CONDITION_LABELS), "runs": len(summaries), "runtime_s": round(runtime, 1),
        "all_contrasts_adequate": all(row["adequate"] for row in contrast_rows),
        "absolute_criteria_passed": sum(row["passed"] for row in absolute_rows),
        "absolute_criteria_total": len(absolute_rows), "deviations": [],
    }
    (derived / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (derived / "hashes.json").write_text(json.dumps(file_hashes(out), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    expected_runs = len(reps) * len(e5.CONDITION_LABELS)
    checks = {
        f"every run completed ({len(reps)} x {len(e5.CONDITION_LABELS)})": len(summaries) == expected_runs,
        "every condition label present": {s["experiment_id"] for s in summaries} == set(e5.CONDITION_LABELS),
        "every table and manifest present": all((out / f"rep{rep:04d}" / f"{name}.parquet").exists()
                                                for rep in reps for name in TABLES)
                                            and all((out / f"rep{rep:04d}" / "manifest.json").exists()
                                                    for rep in reps),
        "summary table complete": len(summaries) == expected_runs,
        "contrast table complete": len(contrast_rows) == 18 * len(e5.CONFIRMATORY),
        "seven absolute criteria present": len(absolute_rows) == 7,
        "two mechanism tests present": len(mechanism_rows) == 2,
        "all derived files present": all((derived / name).exists() for name in (
            "run_summaries.parquet", "contrasts.parquet", "absolute_tests.parquet",
            "mechanism_tests.parquet", "seed_dose.json", "report.json", "hashes.json")),
        "manifests record current clean commit": all(
            json.loads((out / f"rep{rep:04d}" / "manifest.json").read_text("utf-8"))["git_commit"] == commit
            for rep in reps),
    }
    if args.full:
        if not all(checks.values()):
            failed = [name for name, ok in checks.items() if not ok]
            raise RuntimeError(f"E5 completed but integrity checks failed: {failed}")
        print(f"E5 complete in {runtime / 60:.1f} min: {len(summaries)} runs. Results in {derived}")
        return 0

    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"smoke runtime {runtime:.1f} s; projected full run about {runtime / len(reps) * len(e5.REPLICATES) / 60:.0f} min")
    shutil.rmtree(out)
    print(f"smoke outputs deleted ({out})")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
