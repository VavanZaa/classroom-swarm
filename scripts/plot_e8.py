"""Create the reported E8 scientific figures from derived Parquet outputs."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[1]
DERIVED = REPO / "runs" / "E8" / "derived"
OUT = REPO / "docs" / "experiments" / "figures"

COLORS = {
    "E8-A-none": "#4b5563",
    "E8-A-unrestricted": "#c2413b",
    "E8-A-controlled": "#238b57",
}
NAMES = {
    "E8-A-none": "No AI",
    "E8-A-unrestricted": "Unrestricted AI",
    "E8-A-controlled": "Controlled tutor",
}


def primary_figure() -> None:
    trajectories = pq.read_table(DERIVED / "trajectory_summaries.parquet").to_pylist()
    absolute = pq.read_table(DERIVED / "primary_absolute.parquet").to_pylist()
    trajectory = {(r["condition"], r["homework_index"], r["outcome"]): r for r in trajectories}
    final = {(r["condition"], r["outcome"]): r for r in absolute}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
    panels = (("pA", "AI action share", axes[0, 0]),
              ("K", "Mean knowledge", axes[0, 1]),
              ("grade", "Homework grade", axes[1, 0]))
    for outcome, ylabel, ax in panels:
        labels = ("E8-A-unrestricted", "E8-A-controlled") if outcome == "pA" else tuple(COLORS)
        for label in labels:
            h = np.arange(1, 21)
            rows = [trajectory[(label, int(x), outcome)] for x in h]
            y = np.asarray([r["estimate"] for r in rows], float)
            lo = np.asarray([r["lo"] for r in rows], float)
            hi = np.asarray([r["hi"] for r in rows], float)
            ax.plot(h, y, color=COLORS[label], lw=2, label=NAMES[label])
            ax.fill_between(h, lo, hi, color=COLORS[label], alpha=.14, linewidth=0)
        ax.axvline(2, color="#9ca3af", ls="--", lw=1)
        ax.set(xlabel="Homework", ylabel=ylabel, xlim=(1, 20))
        ax.grid(alpha=.2)
        ax.legend(frameon=False, fontsize=9)

    ax = axes[1, 1]
    outcomes = ("grade_late", "K_final", "exam_final")
    x = np.arange(len(outcomes)); width = .24
    for index, label in enumerate(COLORS):
        y = [final[(label, outcome)]["estimate"] for outcome in outcomes]
        lo = [final[(label, outcome)]["lo"] for outcome in outcomes]
        hi = [final[(label, outcome)]["hi"] for outcome in outcomes]
        err = np.asarray([[value - lower for value, lower in zip(y, lo)],
                          [upper - value for value, upper in zip(y, hi)]])
        ax.bar(x + (index - 1) * width, y, width, color=COLORS[label], label=NAMES[label],
               yerr=err, capsize=2)
    ax.set_xticks(x, ("Late homework\ngrade", "Final\nknowledge", "Unaided\nexam"))
    ax.set_ylim(.65, .90); ax.set_ylabel("Mean outcome")
    ax.grid(axis="y", alpha=.2); ax.legend(frameon=False, fontsize=9)
    fig.suptitle("E8: universal access, voluntary use, and contrasting AI affordances", fontsize=14)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "E8-primary-trends.png", dpi=180)
    plt.close(fig)


def policy_figure() -> None:
    policy = pq.read_table(DERIVED / "policy_map.parquet").to_pylist()
    contrasts = pq.read_table(DERIVED / "surface_contrasts.parquet").to_pylist()
    absolute = pq.read_table(DERIVED / "surface_absolute.parquet").to_pylist()
    contrast = {(r["condition"], r["outcome"]): r for r in contrasts}
    adoption = {(r["condition"], r["outcome"]): r for r in absolute}
    controlled = [r for r in policy if r["regime"] == "T"]
    learning = (.5, 1.0, 1.5); scaffold = (0.0, .25, .5)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for col, cost in enumerate((1, 2)):
        rows = {(r["mechanism_1"], r["mechanism_2"]): r for r in controlled if r["cost"] == cost}
        exam = np.asarray([[contrast[(rows[(m, s)]["condition"], "exam_final")]["estimate"]
                            for s in scaffold] for m in learning])
        adopt = np.asarray([[adoption[(rows[(m, s)]["condition"], "pA_late")]["estimate"]
                             for s in scaffold] for m in learning])
        for row_index, (matrix, title, cmap, vmin, vmax) in enumerate((
            (exam, f"Cost {cost}: unaided-exam change", "RdYlGn", -.06, .06),
            (adopt, f"Cost {cost}: late voluntary use", "YlGnBu", 0, .32),
        )):
            ax = axes[row_index, col]
            image = ax.imshow(matrix, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            for yi, m in enumerate(learning):
                for xi, s in enumerate(scaffold):
                    value = matrix[yi, xi]
                    ax.text(xi, yi, f"{100*value:.1f}", ha="center", va="center", fontsize=9,
                            color="white" if abs(value) > .035 or (row_index == 1 and value > .18) else "black")
                    if rows[(m, s)]["traffic"] == "green":
                        ax.add_patch(Rectangle((xi-.48, yi-.48), .96, .96, fill=False,
                                               edgecolor="#14532d", linewidth=3))
            ax.set_xticks(range(3), ("0", ".25", ".50"))
            ax.set_yticks(range(3), (".50", "1.00", "1.50"))
            ax.set_xlabel("Immediate scaffold strength")
            ax.set_ylabel("Durable learning multiplier")
            ax.set_title(title)
            fig.colorbar(image, ax=ax, shrink=.78, label="Proportion change" if row_index == 0 else "Share")
    fig.suptitle("E8 controlled-tutor policy surface (cell labels are percentage points)", fontsize=14)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "E8-controlled-policy-map.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    primary_figure()
    policy_figure()
