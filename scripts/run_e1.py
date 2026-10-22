"""Experiment 1 runner (docs/experiments/E1-preregistration.md, locked; lock record E1-lock.json).

    .venv\\Scripts\\python.exe scripts/run_e1.py --smoke   # §9 excluded technical check; prints no outcome values,
                                                        # deletes its outputs afterwards
    .venv\\Scripts\\python.exe scripts/run_e1.py --full    # the locked E1 run, exactly once

Both modes refuse to start unless the preregistration matches its lock hash and the git tree is clean.
--full also refuses if runs/E1 already exists.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e1
from classroom_swarm.analysis import (bootstrap_indices, broker_scores, broker_share, classify, convergence,
                                      paired_contrast, proxy_check, run_summaries)
from classroom_swarm.config import Params, RunSpec, Stage
from classroom_swarm.derive import brokerage
from classroom_swarm.experiment import run_broker_null, run_replicate
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import TABLES
from classroom_swarm.rng import graph_seed
from classroom_swarm.storage import read_table

REPO = Path(__file__).resolve().parents[1]
PREREG = REPO / "docs/experiments/E1-preregistration.md"
LOCK = REPO / "docs/experiments/E1-lock.json"
NEVER_NA = ("pC_late", "pC_change", "K_final", "VarK_final", "dHK_late", "dHK_mean", "dGK_last", "dGK_block",
            "Smax_mean", "Lmax_mean", "reach", "P_C_last")
FALLBACK_GIT = Path(r"C:\Program Files\Git\cmd\git.exe")


def git_state() -> tuple[str, bool]:
    git = shutil.which("git")
    if git is None and FALLBACK_GIT.exists():  # shells opened before git was installed lack it on PATH
        os.environ["PATH"] = f"{FALLBACK_GIT.parent}{os.pathsep}{os.environ['PATH']}"
        git = str(FALLBACK_GIT)
    if git is None:
        raise SystemExit("refusing to run: git not found, so the commit can't be recorded")
    run = lambda *a: subprocess.run([git, *a], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    return run("rev-parse", "HEAD"), run("status", "--porcelain") == ""


def write_rows(path: Path, rows: list[dict]) -> None:
    columns = sorted({k for r in rows for k in r})
    pq.write_table(pa.table({c: [r.get(c) for r in rows] for c in columns}), path)


def cond_str(cond: tuple) -> str:
    stage, R, family = cond
    return f"{stage}/R{R}/{family}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = ap.parse_args()

    sha = e1.verify_lock(PREREG, LOCK)
    commit, clean = git_state()
    if not clean:
        raise SystemExit("refusing to run: git tree is dirty (a dirty tree voids the run, §2)")
    if args.smoke:
        exp_id, seed, reps, L, tail = e1.SMOKE_ID, e1.SMOKE_SEED, e1.SMOKE_REPLICATES, e1.SMOKE_L_NULL, 1
    else:
        exp_id, seed, reps, L, tail = e1.EXPERIMENT_ID, e1.MASTER_SEED, e1.REPLICATES, e1.L_NULL, e1.CONVERGENCE_TAIL
    out = REPO / "runs" / exp_id
    if out.exists():
        if args.full:
            raise SystemExit(f"refusing to run: {out} exists and E1 runs exactly once")
        shutil.rmtree(out)

    base = Params()
    summaries, broker_rows, null_rows = [], [], []
    t0 = time.perf_counter()
    t_null = 0.0
    for n, rep in enumerate(reps, start=1):
        rep_dir = run_replicate(exp_id, rep, seed, base, out)
        tables = {name: read_table(rep_dir, name) for name in TABLES}
        rep_summaries = run_summaries(tables, e1.EARLY, e1.LATE)
        by_run = {s["run_id"]: s for s in rep_summaries}
        graph = generate_graph("SBM", base, graph_seed(seed, rep, "SBM"))
        specs = [RunSpec(exp_id, rep, family, R, Stage[stage], base, seed) for stage, R, family in e1.BROKER_SCOPE]
        B_all = brokerage(tables["routing_events"], tables["decisions"])
        t_start_null = time.perf_counter()
        nulls = run_broker_null(specs, graph, L, seed)
        t_null += time.perf_counter() - t_start_null
        for spec in specs:
            B_obs = {i: b for (run_id, i), b in B_all.items() if run_id == spec.run_id}
            scores = broker_scores(B_obs, nulls[spec.stage.name])
            by_run[spec.run_id]["broker_share"] = broker_share(scores)
            broker_rows += [{"run_id": spec.run_id, "student_id": i, **sc} for i, sc in sorted(scores.items())]
            null_rows += [{"run_id": spec.run_id, "ell": ell, "student_id": i, "B": b}
                          for ell, member in enumerate(nulls[spec.stage.name]) for i, b in sorted(member.items())]
        summaries += rep_summaries
        print(f"replicate {rep} done ({n}/{len(reps)}, {time.perf_counter() - t0:.0f} s)", flush=True)

    boot = bootstrap_indices(len(reps), e1.BOOT_B, e1.BOOT_SEED)
    contrast_rows = []
    for c in e1.contrasts():
        for outcome in e1.CONFIRMATORY + e1.SECONDARY:
            r = paired_contrast(summaries, outcome, c["a"], c["b"], boot)
            label, magnitude = classify(r["lo"], r["hi"], e1.DELTA[outcome]) if outcome in e1.DELTA else ("descriptive", None)
            contrast_rows.append({"name": c["name"], "tier": c["tier"], "outcome": outcome,
                                  "confirmatory": outcome in e1.CONFIRMATORY, "a": cond_str(c["a"]),
                                  "b": cond_str(c["b"]), "n": r["n"], "estimate": r["estimate"], "lo": r["lo"],
                                  "hi": r["hi"], "delta": e1.DELTA.get(outcome), "label": label, "magnitude": magnitude})
    for name, a, b in e1.BROKER_CONTRASTS:
        r = paired_contrast(summaries, "broker_share", a, b, boot)
        label, magnitude = classify(r["lo"], r["hi"], e1.DELTA["broker_share"])
        contrast_rows.append({"name": name, "tier": "broker", "outcome": "broker_share", "confirmatory": True,
                              "a": cond_str(a), "b": cond_str(b), "n": r["n"], "estimate": r["estimate"], "lo": r["lo"],
                              "hi": r["hi"], "delta": e1.DELTA["broker_share"], "label": label, "magnitude": magnitude})
    proxy = proxy_check(summaries, e1.PROXY_THRESHOLD)
    conv_rows = []
    for stage in e1.STAGES:
        for R in e1.RS:
            for family in e1.FAMILIES:
                rows = sorted((s for s in summaries if (s["stage"], s["R"], s["family"]) == (stage, R, family)),
                              key=lambda s: s["replicate"])
                for quantity, statistic in e1.CONVERGENCE_QUANTITIES:
                    res = convergence([s[quantity] for s in rows], boot, statistic, tail, e1.CONVERGENCE_TOL)
                    conv_rows.append({"condition": cond_str((stage, R, family)), "quantity": quantity, **res})

    derived = out / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    write_rows(derived / "run_summaries.parquet", summaries)
    write_rows(derived / "contrasts.parquet", contrast_rows)
    write_rows(derived / "convergence.parquet", conv_rows)
    write_rows(derived / "broker_scores.parquet", broker_rows)
    write_rows(derived / "broker_null_B.parquet", null_rows)
    proxy_json = {**proxy, "conditions": [{**c, "condition": cond_str(c["condition"])} for c in proxy["conditions"]]}
    (derived / "proxy_check.json").write_text(json.dumps(proxy_json, indent=2) + "\n", encoding="utf-8")
    runtime = time.perf_counter() - t0
    report = {"experiment_id": exp_id, "preregistration_sha256": sha, "git_commit": commit, "master_seed": seed,
              "bootstrap_seed": e1.BOOT_SEED, "replicates": len(reps), "runs": len(summaries), "L_null": L,
              "runtime_s": round(runtime, 1), "converged_all": all(r["passed"] for r in conv_rows),
              "proxy_adequate": proxy["adequate"]}
    (derived / "e1_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.full:
        print(f"E1 complete in {runtime / 60:.1f} min: {len(summaries)} runs. Results in {derived}")
        return 0

    # --- smoke: pipeline checks only, no outcome values printed (§9) ---
    checks = {
        "every run completed (2 x 36)": len(summaries) == len(reps) * 36,
        "every table file and manifest present": all((out / f"rep{r:04d}" / f"{t}.parquet").exists()
                                                     for r in reps for t in TABLES)
                                                 and all((out / f"rep{r:04d}" / "manifest.json").exists() for r in reps),
        "no unexpected NA in run scalars": all(s[k] is not None for s in summaries for k in NEVER_NA),
        "broker share present for the broker scope": all(s.get("broker_share") is not None for s in summaries
                                                         if (s["stage"], s["R"], s["family"]) in e1.BROKER_SCOPE),
        "contrast table complete (75 x 13 + 2)": len(contrast_rows) == 75 * 13 + 2,
        "convergence table complete (36 x 4)": len(conv_rows) == 36 * 4,
        "proxy check covers 36 conditions": proxy["n_conditions"] == 36,
        "broker null rows complete": len(null_rows) == len(reps) * 3 * L * base.N,
        "manifests record the clean commit": all(json.loads((out / f"rep{r:04d}" / "manifest.json").read_text("utf-8"))
                                                 ["git_commit"] == commit for r in reps),
        "all derived files written": all((derived / f).exists() for f in (
            "run_summaries.parquet", "contrasts.parquet", "convergence.parquet", "broker_scores.parquet",
            "broker_null_B.parquet", "proxy_check.json", "e1_report.json")),
    }
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    main_per_rep = (runtime - t_null) / len(reps)
    null_per_rep_full = t_null / len(reps) * e1.L_NULL / L
    print(f"smoke runtime {runtime:.1f} s (broker null at L={L}: {t_null:.1f} s)")
    print(f"projected full E1 (serial): {len(e1.REPLICATES) * (main_per_rep + null_per_rep_full) / 60:.0f} min "
          f"({main_per_rep:.1f} s + {null_per_rep_full:.1f} s broker null at L={e1.L_NULL}, per replicate)")
    shutil.rmtree(out)
    print(f"smoke outputs deleted ({out})")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
