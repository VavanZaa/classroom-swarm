"""Excluded V3 smoke runner only. Scientific V3 runs require a future locked preregistration."""
from __future__ import annotations

import argparse
from pathlib import Path

from classroom_swarm.v3 import V3Params, run_v3_replicate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="run two tiny excluded replicates")
    parser.add_argument("--out", type=Path, default=Path("runs/V3-smoke"))
    args = parser.parse_args()
    if not args.smoke:
        parser.error("only --smoke is available; V3 has no locked scientific experiment")
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite existing smoke output: {args.out}")
    params = V3Params(N=12, H=3, F_E=None, M_H=3, M_E=3, d_bar=2)
    for replicate in (1, 2):
        run_v3_replicate("V3-smoke", replicate, 920003, params, args.out,
                         families=("ER", "WS", "SBM"), R=2)
    print(f"V3 smoke completed at {args.out}; excluded from scientific analysis")


if __name__ == "__main__":
    main()
