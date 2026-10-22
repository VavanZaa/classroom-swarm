"""Runner for one-factor condition experiments (E2 and its follow-ups), each locked by its preregistration.

    .venv\\Scripts\\python.exe scripts/run_e2.py [--experiment E2] --smoke  # pipeline check; no outcome values; deletes outputs
    .venv\\Scripts\\python.exe scripts/run_e2.py [--experiment E2] --full   # the locked run, exactly once

--experiment picks the plan module (E2 default, E2b, ...). Both modes refuse unless the preregistration
matches its lock hash and the git tree is clean; --full also refuses if runs/<experiment> already exists.
E2 itself was run with this script at commit c11d78d (before --experiment existed).
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
import time
from pathlib import Path

from classroom_swarm.analysis import (boundary_precision_check, bootstrap_indices, classify, paired_contrast,
                                      precision_check, run_summaries)
from classroom_swarm.experiment import run_conditions
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e1 import NEVER_NA, git_state, write_rows  # noqa: E402  (shared guard helpers)

REPO = Path(__file__).resolve().parents[1]
MODULES = {"E2": "classroom_swarm.e2", "E2b": "classroom_swarm.e2b", "E3": "classroom_swarm.e3",
           "E4": "classroom_swarm.e4"}


def is_precise(m, contrast: dict, delta: float) -> bool:
    """The adequacy rule each experiment was locked with: half-width (E2-E3) or boundary (E4 on)."""
    if getattr(m, "PRECISION_RULE", "halfwidth") == "boundary":
        return boundary_precision_check(contrast, delta)["adequate"]
    return precision_check(contrast, delta, m.PRECISION_FRACTION)["adequate"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--experiment", default="E2", choices=sorted(MODULES))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = ap.parse_args()
    m = importlib.import_module(MODULES[args.experiment])

    sha = m.verify_lock(REPO / m.PREREG, REPO / m.LOCK)
    commit, clean = git_state()
    if not clean:
        raise SystemExit("refusing to run: git tree is dirty")
    exp_id, seed, reps = ((m.SMOKE_ID, m.SMOKE_SEED, m.SMOKE_REPLICATES) if args.smoke
                          else (m.EXPERIMENT_ID, m.MASTER_SEED, m.REPLICATES))
    out = REPO / "runs" / exp_id
    if out.exists():
        if args.full:
            raise SystemExit(f"refusing to run: {out} exists and {m.EXPERIMENT_ID} runs exactly once")
        shutil.rmtree(out)

    conds = m.conditions()
    plan = m.contrasts()
    summaries = []
    t0 = time.perf_counter()
    for n, rep in enumerate(reps, start=1):
        rep_dir = run_conditions(conds, rep, seed, out, family=m.FAMILY, R=m.R, R_max=3)
        summaries += run_summaries({name: read_table(rep_dir, name) for name in TABLES}, m.EARLY, m.LATE)
        if n % 20 == 0 or n == len(reps):
            print(f"replicate {rep} done ({n}/{len(reps)}, {time.perf_counter() - t0:.0f} s)", flush=True)

    boot = bootstrap_indices(len(reps), m.BOOT_B, m.BOOT_SEED)
    rows = []
    for c in plan:
        for outcome in m.CONFIRMATORY + m.SECONDARY:
            r = paired_contrast(summaries, outcome, c["a"], c["b"], boot, key=("experiment_id",))
            delta = m.DELTA.get(outcome)
            label, magnitude = classify(r["lo"], r["hi"], delta) if delta is not None else ("descriptive", None)
            precise = is_precise(m, r, delta) if delta is not None else None
            rows.append({"condition": c["name"], "block": c.get("block"), "a": c["a"][0], "reference": c["b"][0],
                         "stress": c["stress"], "outcome": outcome,
                         "confirmatory": outcome in m.CONFIRMATORY, "n": r["n"], "estimate": r["estimate"],
                         "lo": r["lo"], "hi": r["hi"], "delta": delta, "label": label, "magnitude": magnitude,
                         "precise": precise})
    derived = out / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    write_rows(derived / "run_summaries.parquet", summaries)
    write_rows(derived / "contrasts.parquet", rows)
    if hasattr(m, "extra_analysis"):
        extra = m.extra_analysis(summaries, boot)
        (derived / "extra.json").write_text(json.dumps(extra, indent=2, default=str) + "\n", encoding="utf-8")
    runtime = time.perf_counter() - t0
    report = {"experiment_id": exp_id, "preregistration_sha256": sha, "git_commit": commit, "master_seed": seed,
              "bootstrap_seed": m.BOOT_SEED, "replicates": len(reps), "conditions": len(conds),
              "runs": len(summaries), "runtime_s": round(runtime, 1),
              "all_confirmatory_precise": all(r["precise"] for r in rows if r["confirmatory"])}
    (derived / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.full:
        print(f"{m.EXPERIMENT_ID} complete in {runtime / 60:.1f} min: {len(summaries)} runs. Results in {derived}")
        return 0

    n_outcomes = len(m.CONFIRMATORY) + len(m.SECONDARY)
    checks = {
        f"every run completed ({len(reps)} x {len(conds)})": len(summaries) == len(reps) * len(conds),
        "every table file and manifest present": all((out / f"rep{r:04d}" / f"{t}.parquet").exists()
                                                     for r in reps for t in TABLES),
        "no unexpected NA in run scalars": all(s[k] is not None for s in summaries for k in NEVER_NA),
        f"contrast table complete ({len(plan)} x {n_outcomes})": len(rows) == len(plan) * n_outcomes,
        "every condition label present": {s["experiment_id"] for s in summaries} == set(m.CONDITIONS),
        "manifests record the clean commit": all(json.loads((out / f"rep{r:04d}" / "manifest.json").read_text("utf-8"))
                                                 ["git_commit"] == commit for r in reps),
        "derived files written": all((derived / f).exists() for f in ("run_summaries.parquet", "contrasts.parquet",
                                                                      "report.json")),
    }
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"smoke runtime {runtime:.1f} s; projected full run about "
          f"{runtime / len(reps) * len(m.REPLICATES) / 60:.0f} min")
    shutil.rmtree(out)
    print(f"smoke outputs deleted ({out})")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
