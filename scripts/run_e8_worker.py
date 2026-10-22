"""Isolated one-replicate E8 worker."""
from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e8
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table


def write_rows(path: Path, rows: list[dict]) -> None:
    columns = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({column: [row.get(column) for row in rows] for column in columns}), path)


def summarize(rep_dir: Path) -> tuple[list[dict], list[dict]]:
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    return e8.run_outputs(tables, e8.read_ai_table(rep_dir))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", choices=("primary", "surface", "robustness"), required=True)
    parser.add_argument("--replicate", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    e8.verify_lock()
    checkpoint = args.out / "checkpoints" / args.block / f"rep{args.replicate:04d}"
    if (checkpoint / "summaries.parquet").exists() and (checkpoint / "trajectories.parquet").exists():
        return 0
    if args.block == "primary":
        rep_dir = args.out / "primary" / f"rep{args.replicate:04d}"
        if not rep_dir.exists():
            rep_dir = e8.run_block_replicate("primary", args.replicate, e8.PRIMARY_SEED,
                                             args.out / "primary", e8.primary_conditions())
        summaries, trajectories = summarize(rep_dir)
    else:
        if args.block == "surface":
            seed, plan, size = e8.SURFACE_SEED, e8.surface_conditions(), 10
        else:
            seed, plan, size = e8.ROBUSTNESS_SEED, e8.robustness_conditions(), 12
        summaries, trajectories = [], []
        shards = e8.run_sharded_replicate(args.block, args.replicate, seed,
                                           args.out / args.block, plan, size, resume=True)
        for shard in shards:
            srows, trows = summarize(shard)
            summaries.extend(srows)
            trajectories.extend(trows)
    write_rows(checkpoint / "summaries.parquet", summaries)
    write_rows(checkpoint / "trajectories.parquet", trajectories)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
