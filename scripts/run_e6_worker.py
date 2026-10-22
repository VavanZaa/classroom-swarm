"""Isolated one-replicate E6 worker used to prevent cumulative Arrow/Python memory growth."""
from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e6
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

REPO = Path(__file__).resolve().parents[1]


def write_rows(path: Path, rows: list[dict]) -> None:
    columns = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({column: [row.get(column) for row in rows] for column in columns}), path)


def load_tables(path: Path) -> dict[str, pa.Table]:
    return {name: read_table(path, name) for name in TABLES}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", choices=("structural", "factorial"), required=True)
    parser.add_argument("--replicate", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    e6.verify_lock(REPO)
    replicate, out = args.replicate, args.out
    checkpoint = out / "checkpoints" / args.block / f"rep{replicate:04d}"
    summary_path = checkpoint / "summaries.parquet"
    null_path = checkpoint / "source_null.parquet"
    if summary_path.exists() and (args.block == "factorial" or null_path.exists()):
        return 0
    if summary_path.exists() or null_path.exists():
        raise RuntimeError(f"incomplete E6 checkpoint blocks resume: {checkpoint}")

    if args.block == "structural":
        rep_dir = out / "structural" / f"rep{replicate:04d}"
        if not rep_dir.exists():
            rep_dir = e6.run_structural_replicate(replicate, e6.STRUCTURAL_SEED, out / "structural")
        tables = load_tables(rep_dir)
        summaries = e6.run_summaries(tables)
        base_run = next(row["run_id"] for row in summaries if row["experiment_id"] == "E6-S-base")
        null = e6.source_null(tables, base_run, replicate, e6.SOURCE_NULL_B)
        write_rows(summary_path, summaries)
        write_rows(null_path, [null])
    else:
        summaries = []
        shard_dirs = e6.run_factorial_replicate(replicate, e6.FACTORIAL_SEED,
                                                 out / "factorial", resume=True)
        for shard_dir in shard_dirs:
            summaries.extend(e6.run_summaries(load_tables(shard_dir)))
        write_rows(summary_path, summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
