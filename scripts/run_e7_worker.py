"""Isolated one-replicate E7 worker."""
from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm import e7
from classroom_swarm.records import TABLES
from classroom_swarm.storage import read_table

REPO = Path(__file__).resolve().parents[1]


def write_rows(path: Path, rows: list[dict]) -> None:
    columns = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({column: [row.get(column) for row in rows] for column in columns}), path)


def summarize(rep_dir: Path) -> list[dict]:
    tables = {name: read_table(rep_dir, name) for name in TABLES}
    return e7.run_summaries(tables, e7.read_ai_table(rep_dir, "ai_decisions"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", choices=("structural", "factorial"), required=True)
    parser.add_argument("--replicate", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    e7.verify_lock(REPO)
    checkpoint = args.out / "checkpoints" / args.block / f"rep{args.replicate:04d}" / "summaries.parquet"
    if checkpoint.exists():
        return 0
    if args.block == "structural":
        rep_dir = args.out / "structural" / f"rep{args.replicate:04d}"
        if not rep_dir.exists():
            rep_dir = e7.run_structural_replicate(args.replicate, e7.STRUCTURAL_SEED,
                                                   args.out / "structural")
        summaries = summarize(rep_dir)
    else:
        summaries = []
        for shard in e7.run_factorial_replicate(args.replicate, e7.FACTORIAL_SEED,
                                                 args.out / "factorial", resume=True):
            summaries.extend(summarize(shard))
    write_rows(checkpoint, summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
