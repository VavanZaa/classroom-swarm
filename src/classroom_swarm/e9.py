"""Locked E9 execution and raw-log analysis for A22 (V4.1/V4.2).

Usage: python -m classroom_swarm.e9 lock|run|analyze --root runs/E9 ...
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import platform
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .graphs import generate_graph
from .rng import graph_seed
from .v3 import V3Params, V3RunSpec
from .v4 import V4Params, V4Draws, V4Log, simulate_v4, simulate_legacy, summarize, trajectories, validate_log

REPO = Path(__file__).resolve().parents[2]
LOCK_FILES = ("docs/11-v4-activity-feedback.md", "docs/experiments/E9-preregistration.md",
              "src/classroom_swarm/v4.py", "src/classroom_swarm/e9.py", "tests/test_v4.py",
              "src/classroom_swarm/v3.py", "src/classroom_swarm/graphs.py", "src/classroom_swarm/rng.py")
SEED = 924041
REPLICATES = 100


def conditions():
    base = V4Params()
    v41 = replace(base, self_assessment=False, feedback_mode="none")
    return [
        ("v3_reference", "SBM", None),
        ("v41", "SBM", v41),
        ("v42_no_feedback", "SBM", replace(base, feedback_mode="none")),
        ("v42_recalibrate", "SBM", base),
        ("constructive", "SBM", replace(base, feedback_mode="constructive")),
        ("withdrawal", "SBM", replace(base, feedback_mode="withdrawal")),
        ("delay0", "SBM", replace(base, feedback_delay=0)),
        ("delay4", "SBM", replace(base, feedback_delay=4)),
        ("helper_time_free", "SBM", replace(base, helper_time=False)),
        ("frozen_access", "SBM", replace(base, eta_access=0)),
        ("no_hint", "SBM", replace(base, allow_hint=False)),
        ("no_answer", "SBM", replace(base, allow_answer=False)),
        ("no_check", "SBM", replace(base, allow_check=False)),
        ("misattribute0", "SBM", replace(base, misattribution=0)),
        ("misattribute80", "SBM", replace(base, misattribution=.8)),
        ("prior25", "SBM", replace(base, benefit_prior=.25)),
        ("prior75", "SBM", replace(base, benefit_prior=.75)),
        ("learning_value0", "SBM", replace(base, learning_value=0)),
        ("deadline8", "SBM", replace(base, ticks=8)),
        ("deadline16", "SBM", replace(base, ticks=16)),
        ("argmax_v41", "SBM", replace(v41, choice_rule="argmax")),
        ("argmax_v42", "SBM", replace(base, choice_rule="argmax")),
        ("ER_v41", "ER", v41),
        ("ER_v42", "ER", base),
        ("H40_v41", "SBM", replace(v41, H=40)),
        ("H40_v42", "SBM", replace(base, H=40)),
    ]


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def dump(path, value):
    def clean(v):
        if isinstance(v, float) and not math.isfinite(v):
            return None
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)):
            return [clean(x) for x in v]
        return v
    Path(path).write_text(json.dumps(clean(value), indent=2, sort_keys=True), encoding="utf-8")


def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / "lock.json"
    if path.exists():
        raise FileExistsError("An E9 lock already exists; never silently replace a scientific lock")
    value = dict(seed=SEED, replicates=REPLICATES, bootstrap_seed=924042, bootstrap_samples=2000,
                 sources={str(f): digest(REPO / f) for f in LOCK_FILES},
                 conditions=[dict(name=n, family=f, params=None if p is None else asdict(p)) for n, f, p in conditions()],
                 python=platform.python_version(), numpy=np.__version__, pyarrow=pa.__version__)
    dump(path, value)
    return value


def verify_lock(root):
    value = json.loads((root / "lock.json").read_text())
    for f, expected in value["sources"].items():
        if digest(REPO / f) != expected:
            raise RuntimeError(f"Locked source changed: {f}")
    return value


def run_replicate(root_string, replicate):
    root = Path(root_string)
    verify_lock(root)
    folder = root / "raw" / f"rep{replicate:04d}"
    if (folder / "complete.json").exists():
        result = json.loads((folder / "complete.json").read_text())
        for name, value in result["hashes"].items():
            if digest(folder / name) != value:
                raise RuntimeError("Existing replicate hash mismatch")
        return replicate, "verified existing"
    # Incomplete shards are not reused or overwritten.
    if folder.exists():
        raise FileExistsError(f"Incomplete replicate must be inspected: {folder}")
    folder.mkdir(parents=True)
    begun = time.perf_counter()
    writers, groups, manifests = {}, {}, {}
    graph_params = V3Params()
    graphs = {family: generate_graph(family, graph_params, graph_seed(SEED, replicate, family)) for family in ("SBM", "ER")}
    draws = V4Draws(SEED, replicate, 30, 10, 30)
    try:
        for name, family, p in conditions():
            if p is None:
                old = simulate_legacy(V3RunSpec("E9", replicate, family, 3, graph_params, SEED), graphs[family], draws.legacy)
                legacy = folder / "v3"
                legacy.mkdir()
                for table, cols in old.tables.items():
                    pq.write_table(pa.table(cols), legacy / f"{table}.parquet", compression="zstd")
                dump(legacy / "manifest.json", old.manifest)
                continue
            result = simulate_v4(p, graphs[family], draws, condition=name)
            validate_log(result)
            manifests[name] = result.manifest
            for table, rows in result.tables.items():
                if not rows:
                    continue
                data = pa.Table.from_pylist(rows)
                if table not in writers:
                    writers[table] = pq.ParquetWriter(folder / f"{table}.parquet", data.schema, compression="zstd")
                    groups[table] = []
                # Exactly one row group per condition, including the largest event tables.
                writers[table].write_table(data, row_group_size=max(1, data.num_rows))
                groups[table].append(name)
    finally:
        for writer in writers.values():
            writer.close()
    dump(folder / "manifests.json", manifests)
    dump(folder / "row_groups.json", groups)
    files = sorted(x for x in folder.rglob("*") if x.is_file())
    hashes = {x.relative_to(folder).as_posix(): digest(x) for x in files}
    dump(folder / "complete.json", dict(replicate=replicate, seconds=time.perf_counter() - begun,
                                       runs=len(conditions()), hashes=hashes))
    return replicate, round(time.perf_counter() - begun, 2)


def read_log(folder, name, all_tables=False):
    manifests = json.loads((folder / "manifests.json").read_text())
    groups = json.loads((folder / "row_groups.json").read_text())
    result = V4Log(manifests[name])
    for table in result.tables:
        if not all_tables and table not in {"students", "requests", "traits", "exams", "feedback"}:
            continue
        if table in groups and name in groups[table]:
            index = groups[table].index(name)
            result.tables[table] = pq.ParquetFile(folder / f"{table}.parquet").read_row_group(index).to_pylist()
    return result


def legacy_summary(folder):
    rows = pq.read_table(folder / "v3" / "state_snapshots.parquet").to_pylist()
    decisions = pq.read_table(folder / "v3" / "decisions.parquet").to_pylist()
    final = [r for r in rows if r["event_id"] == "h20"]
    late = [r for r in decisions if r["homework_index"] > 15]
    exam = pq.read_table(folder / "v3" / "item_outcomes.parquet").to_pylist()
    exam = [r for r in exam if r["event_id"] == "e4"]
    value = dict(K_final=float(np.mean([r["K"] for r in final])),
                 exam_final=float(np.mean([r["correct"] for r in exam])),
                 grade_late=float(np.mean([r["grade"] for r in late])),
                 copy_late=float(np.mean([r["copy_success"] is True for r in late])),
                 incomplete_late=0.)
    value["grade_exam_gap"] = value["grade_late"] - value["exam_final"]
    traj = []
    for h in range(1, 21):
        state = [r for r in rows if r["event_id"] == f"h{h}"]
        dec = [r for r in decisions if r["homework_index"] == h]
        traj.append(dict(homework=h, K=float(np.mean([r["K"] for r in state])),
                         grade=float(np.mean([r["grade"] for r in dec])),
                         copied=float(np.mean([r["copy_success"] is True for r in dec])),
                         C=float(np.mean([r["C"] for r in state]))))
    return value, traj


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def interval(values, rng):
    a = np.asarray(values, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return dict(mean=None, low=None, high=None, n=0, sd=None)
    estimates = np.mean(a[rng.integers(0, len(a), (2000, len(a)))], axis=1)
    lo, hi = np.quantile(estimates, [.025, .975])
    return dict(mean=float(a.mean()), low=float(lo), high=float(hi), n=len(a), sd=float(a.std(ddof=1)) if len(a) > 1 else 0.)


def analyze(root, output):
    locked = verify_lock(root)
    output.mkdir(parents=True, exist_ok=True)
    all_summary, all_trajectories, integrity = [], [], []
    for rep in range(locked["replicates"]):
        folder = root / "raw" / f"rep{rep:04d}"
        complete = json.loads((folder / "complete.json").read_text())
        for filename, expected in complete["hashes"].items():
            if digest(folder / filename) != expected:
                raise RuntimeError(f"Raw integrity failure: {folder / filename}")
        integrity.append(dict(replicate=rep, files=len(complete["hashes"]), verified=True))
        for name, _, _ in conditions():
            if name == "v3_reference":
                result, tr = legacy_summary(folder)
            else:
                result_log = read_log(folder, name)
                result, tr = summarize(result_log), trajectories(result_log)
            all_summary.append(dict(condition=name, replicate=rep, **result))
            all_trajectories.extend(dict(condition=name, replicate=rep, **r) for r in tr)
        if rep % 10 == 0:
            print(f"Reconstructed and verified {rep + 1}/{locked['replicates']} classrooms", flush=True)
    # Independent deterministic rerun of one scientific condition; compare every raw table.
    sample = read_log(root / "raw" / "rep0000", "v42_recalibrate", all_tables=True)
    graph = generate_graph("SBM", V3Params(), graph_seed(SEED, 0, "SBM"))
    rerun = simulate_v4(V4Params(), graph, V4Draws(SEED, 0, 30, 10, 30), "v42_recalibrate")
    assert sample.tables == rerun.tables, "Scientific rerun does not reproduce raw output"
    validate_log(sample)
    metrics = sorted({k for r in all_summary for k in r} - {"condition", "replicate"})
    grouped = {name: sorted([r for r in all_summary if r["condition"] == name], key=lambda r: r["replicate"])
               for name, _, _ in conditions()}
    rng = np.random.default_rng(924042)
    estimates = []
    for name, rows in grouped.items():
        for metric in metrics:
            estimates.append(dict(condition=name, metric=metric,
                                  **interval([r.get(metric, np.nan) for r in rows], rng)))
    primary = [("v42_recalibrate", "v42_no_feedback"), ("constructive", "v42_recalibrate"),
               ("withdrawal", "v42_recalibrate"), ("helper_time_free", "v42_recalibrate"),
               ("no_hint", "v42_recalibrate")]
    contrasts = list(primary)
    contrasts += [(n, "v42_recalibrate") for n in grouped if n not in {"v3_reference", "v42_recalibrate", "constructive", "withdrawal", "helper_time_free", "no_hint"}]
    contrasts += [("v42_recalibrate", "v41"), ("argmax_v42", "argmax_v41"),
                  ("ER_v42", "ER_v41"), ("H40_v42", "H40_v41")]
    effects = []
    for a, b in contrasts:
        for metric in metrics:
            delta = [ra.get(metric, np.nan) - rb.get(metric, np.nan) for ra, rb in zip(grouped[a], grouped[b])]
            effects.append(dict(condition=a, reference=b, primary=(a, b) in primary,
                                metric=metric, **interval(delta, rng)))
    write_csv(output / "classroom_results.csv", all_summary)
    write_csv(output / "classroom_trajectories.csv", all_trajectories)
    write_csv(output / "condition_estimates.csv", estimates)
    write_csv(output / "paired_effects.csv", effects)
    dump(output / "analysis.json", dict(runs=len(all_summary), classrooms=REPLICATES,
        conditions=len(conditions()), verified_files=sum(r["files"] for r in integrity),
        independent_rerun="all raw tables identical", estimates=estimates, effects=effects,
        lock_sha256=digest(root / "lock.json"), raw_root=str(root.resolve())))
    figures(output, all_trajectories, estimates, effects)
    print(f"Analysis saved to {output}; {len(all_summary)} runs", flush=True)


def figures(output, trajectories_rows, estimates, effects):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.facecolor": "#f6f8fb",
                         "axes.facecolor": "white", "savefig.facecolor": "#f6f8fb"})
    labels = {"v41": "V4.1: activities", "v42_no_feedback": "Self-assessment only",
              "v42_recalibrate": "Exam recalibration", "constructive": "Constructive response",
              "withdrawal": "Withdrawal-capable response"}
    colors = ["#64748b", "#d97706", "#2563eb", "#059669", "#be185d"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    for ax, (metric, title) in zip(axes.flat, [("K", "Latent knowledge"), ("grade", "Homework grade"),
            ("copied", "Answer-backed submissions"), ("calibration", "Self-assessment error |C - K|"),
            ("mixed", "Mixed activities within homework"), ("control", "Perceived controllability")]):
        for (name, label), color in zip(labels.items(), colors):
            rr = [r for r in trajectories_rows if r["condition"] == name]
            hs = sorted({r["homework"] for r in rr})
            values = np.array([[r[metric] for r in rr if r["homework"] == h] for h in hs])
            means = values.mean(axis=1)
            se = values.std(axis=1, ddof=1) / math.sqrt(values.shape[1])
            ax.plot(hs, means, label=label, color=color, lw=2)
            ax.fill_between(hs, means - 1.96 * se, means + 1.96 * se, alpha=.10, color=color)
        ax.set(title=title, xlabel="Homework")
        ax.grid(alpha=.15)
    handles, names = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, names, loc="outside lower center", ncol=3, frameon=False)
    fig.suptitle("E9 | Activities and delayed feedback\n100 paired classrooms per condition; bands show Monte Carlo uncertainty", fontsize=16)
    fig.savefig(output / "v4-trajectories.png", dpi=160)
    plt.close(fig)
    comparisons = ["constructive", "withdrawal", "helper_time_free", "no_hint", "no_answer", "no_check", "deadline8", "deadline16"]
    human = ["Constructive response", "Withdrawal-capable", "No helper time cost", "No explanation requests",
             "No answer requests", "No checking", "Short deadline (8)", "Long deadline (16)"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 6), constrained_layout=True)
    for ax, metric, title in zip(axes, ["K_final", "copy_late", "incomplete_late"],
                                  ["Final knowledge", "Answer-backed submissions", "Incomplete submissions"]):
        for y, name in enumerate(comparisons):
            r = next(x for x in effects if x["condition"] == name and x["reference"] == "v42_recalibrate" and x["metric"] == metric)
            if r["mean"] is not None:
                ax.errorbar(100 * r["mean"], y, xerr=[[100 * (r["mean"] - r["low"])], [100 * (r["high"] - r["mean"])]],
                            fmt="o", capsize=3, color="#2563eb")
        ax.axvline(0, color="#94a3b8", lw=1)
        ax.set_yticks(range(len(human)), human if ax is axes[0] else [""] * len(human))
        ax.invert_yaxis()
        ax.set(title=title, xlabel="Change vs recalibration (percentage points)")
        ax.grid(axis="x", alpha=.15)
    fig.suptitle("E9 | Paired counterfactual effects\nPointwise 95% bootstrap intervals; assumptions are uncalibrated", fontsize=15)
    fig.savefig(output / "v4-counterfactuals.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    names = ["v41", "v42_recalibrate", "helper_time_free", "frozen_access", "argmax_v42"]
    display = ["V4.1", "Recalibrate", "Free helper time", "Frozen access", "Argmax"]
    for ax, metric, title in zip(axes, ["help_success", "source_top20", "source_persistence"],
                               ["Request success", "Top 20% share of help", "Degree-adjusted helper persistence"]):
        rr = [next(r for r in estimates if r["condition"] == name and r["metric"] == metric) for name in names]
        ax.bar(range(len(names)), [r["mean"] if r["mean"] is not None else 0 for r in rr], color=colors)
        ax.set_xticks(range(len(names)), display, rotation=25, ha="right")
        ax.set(title=title)
        ax.grid(axis="y", alpha=.15)
    fig.suptitle("E9 | Help networks\nPersistence is descriptive; it does not establish roles independent of opportunity", fontsize=15)
    fig.savefig(output / "v4-help-network.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["lock", "run", "analyze"])
    parser.add_argument("--root", type=Path, default=REPO / "runs" / "E9")
    parser.add_argument("--output", type=Path, default=REPO / "output" / "E9")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "lock":
        print(json.dumps({"conditions": len(conditions()), "replicates": lock(args.root)["replicates"]}))
    elif args.command == "run":
        verify_lock(args.root)
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_replicate, str(args.root.resolve()), rep) for rep in range(REPLICATES)]
            for count, future in enumerate(as_completed(futures), 1):
                rep, seconds = future.result()
                print(f"Completed classroom {rep}: {seconds}s; {count}/{REPLICATES}; elapsed {time.perf_counter()-start:.1f}s", flush=True)
        dump(args.root / "execution.json", dict(runs=REPLICATES * len(conditions()), seconds=time.perf_counter()-start,
                                                workers=args.workers, complete=True))
    else:
        analyze(args.root, args.output)


if __name__ == "__main__":
    main()
