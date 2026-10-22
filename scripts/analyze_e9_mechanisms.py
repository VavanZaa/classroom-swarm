"""Exploratory raw-event decomposition AFTER the locked E9r1 run.

Does not change parameters, engine, primary estimands or original outputs.
"""
import argparse
from pathlib import Path

import numpy as np

from classroom_swarm.e9 import read_log, dump, interval, write_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    names = ["v41", "v42_recalibrate", "no_hint", "no_check", "withdrawal", "H40_v41", "H40_v42"]
    rows = []
    for rep in range(100):
        for name in names:
            log = read_log(args.root / "raw" / f"rep{rep:04d}", name, all_tables=True)
            p = log.manifest["params"]
            events = log.tables["events"]
            students = log.tables["students"]
            gains = {a: sum(e["K_after"] - e["K_before"] for e in events if e["action"] == a) / p["N"]
                     for a in ("attempt", "check", "help_hint")}
            total = sum(r["K"] for r in students if r["homework"] == p["H"]) / p["N"] - np.mean([r["K0"] for r in log.tables["traits"]])
            assert abs(sum(gains.values()) - total) < 1e-12, "Learning decomposition does not reconstruct state"
            received = [e for e in events if e["action"] == "hint_receive" and e["homework"] > p["H"] - 5]
            attempted = 0
            for e in received:
                attempted += any(x["action"] == "attempt" and x["student"] == e["student"] and
                                 x["homework"] == e["homework"] and x["start"] >= e["end"] for x in events)
            fb = log.tables["feedback"]
            row = dict(condition=name, replicate=rep, attempt_gain=gains["attempt"],
                       check_gain=gains["check"], explanation_provider_gain=gains["help_hint"], total_gain=float(total),
                       received_hint_then_attempt=attempted / len(received) if received else np.nan,
                       hint_consumed_share=sum(r["assisted"] and r["homework"] > p["H"] - 5
                                               for r in log.tables["packets"]) / len(received) if received else np.nan,
                       received_hints_per_student_homework=len(received) / (p["N"] * min(5, p["H"])),
                       positive_surprise=float(np.mean([x["score"] > x["prediction"] for x in fb])) if fb else np.nan,
                       mean_surprise=float(np.mean([x["score"] - x["prediction"] for x in fb])) if fb else np.nan)
            rows.append(row)
        if rep % 20 == 0:
            print(f"Exploratory decomposition: {rep + 1}/100", flush=True)
    rng = np.random.default_rng(924043)
    metrics = [k for k in rows[0] if k not in {"condition", "replicate"}]
    estimates = [dict(condition=name, metric=metric, **interval([r[metric] for r in rows if r["condition"] == name], rng))
                 for name in names for metric in metrics]
    write_csv(args.output / "mechanism_classrooms.csv", rows)
    dump(args.output / "mechanism_checks.json", dict(status="exploratory, after primary outcome inspection",
        decomposition_assertion="Every classroom reconstructed within 1e-12", estimates=estimates))


if __name__ == "__main__":
    main()
