"""Figures for the project report (docs/report/). Reads only the experiment outputs under runs/.

    uv sync --group viz
    .venv\\Scripts\\python.exe scripts/make_report_figures.py

Writes docs/report/figures/*.png plus figure_data.json (every plotted number, so the report can cite
values that come from data). Colours: the dataviz reference palette, validated with its validator
(categorical slots 1-3 all-pairs; a 5-step ordinal blue ramp). Static images: the report's tables are
the table view.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
OUT = REPO / "docs" / "report" / "figures"

# --- reference palette (dataviz skill, references/palette.md) -------------------------------------
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"          # categorical slots 1-3 (validated all-pairs)
ORDINAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]  # validated --ordinal
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
V1_COLOR, V2_COLOR = BLUE, ORANGE
DATA: dict = {}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "semibold", "axes.titlelocation": "left", "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "lines.linewidth": 2.0, "lines.markersize": 6,
})


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def summaries(exp: str) -> list[dict]:
    return pq.read_table(RUNS / exp / "derived" / "run_summaries.parquet").to_pylist()


def contrasts(exp: str) -> list[dict]:
    return pq.read_table(RUNS / exp / "derived" / "contrasts.parquet").to_pylist()


def mean_ci(values) -> tuple[float, float, float]:
    v = np.array([x for x in values if x is not None], float)
    m, se = float(v.mean()), float(v.std(ddof=1) / math.sqrt(len(v)))
    return m, m - 1.96 * se, m + 1.96 * se


def wilson(p: float, n: int) -> tuple[float, float]:
    z = 1.96
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def by_label(rows, key, label_field="experiment_id"):
    out = defaultdict(list)
    for r in rows:
        out[r[label_field]].append(r[key])
    return out


def trajectories(exp: str, run_ids_for_rep, reps) -> dict:
    """Per (label, h): per-replicate copying rate, copy success and mean K, from the raw tables."""
    out = defaultdict(lambda: {"pC": [], "succ": [], "K": []})
    for rep in reps:
        rd = RUNS / exp / f"rep{rep:04d}"
        wanted = run_ids_for_rep(rep)
        dec = pq.read_table(rd / "decisions.parquet", columns=["run_id", "homework_index", "action", "copy_success"])
        dec = dec.filter(pc.is_in(dec["run_id"], value_set=pa.array(list(wanted)))).to_pylist()
        snap = pq.read_table(rd / "state_snapshots.parquet", columns=["run_id", "event_id", "K"])
        snap = snap.filter(pc.is_in(snap["run_id"], value_set=pa.array(list(wanted)))).to_pylist()
        cnt = defaultdict(lambda: [0, 0, 0])  # n, nC, nSucc
        for d in dec:
            c = cnt[(d["run_id"], d["homework_index"])]
            c[0] += 1
            c[1] += d["action"] == "C"
            c[2] += bool(d["action"] == "C" and d["copy_success"])
        ksum = defaultdict(lambda: [0.0, 0])
        for s in snap:
            if s["event_id"].startswith("h"):
                a = ksum[(s["run_id"], int(s["event_id"][1:]))]
                a[0] += s["K"]
                a[1] += 1
        for (run_id, h), (n, nc, ns) in cnt.items():
            label = wanted[run_id]
            out[(label, h)]["pC"].append(nc / n)
            if nc:
                out[(label, h)]["succ"].append(ns / nc)
            out[(label, h)]["K"].append(ksum[(run_id, h)][0] / ksum[(run_id, h)][1])
    return out


def band(ax, hs, per_h, color, label, lw=2.0):
    m = np.array([np.mean(v) for v in per_h])
    se = np.array([np.std(v, ddof=1) / math.sqrt(len(v)) if len(v) > 1 else 0 for v in per_h])
    ax.fill_between(hs, m - 1.96 * se, m + 1.96 * se, color=color, alpha=0.15, linewidth=0)
    ax.plot(hs, m, color=color, lw=lw, label=label)
    return m


# --- Figure 1: E1 null result ------------------------------------------------------------------------
def fig_e1() -> None:
    stages = ("M0", "M1", "M5")
    wanted = lambda rep: {f"E1/rep{rep:04d}/SBM/R3/{s}": s for s in stages}
    tr = trajectories("E1", wanted, range(1, 201))
    hs = list(range(1, 21))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    DATA["fig1"] = {}
    for s, color in zip(stages, (BLUE, ORANGE, AQUA)):
        m = band(ax, hs, [tr[(s, h)]["pC"] for h in hs], color, s)
        DATA["fig1"][s] = {"pC_h1": float(m[0]), "pC_h20": float(m[-1])}
        ax.annotate(s, (20.2, m[-1]), color=INK2, va="center", fontsize=9)
    ax.set_ylim(0, 0.2)
    ax.set_xlim(1, 21)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_xlabel("homework")
    ax.set_ylabel("share of students choosing C")
    ax.set_title("E1 · Copying never grows at the reference parameters (V1, SBM, R = 3, 200 replicates)")
    ax.legend(loc="upper left", ncols=3)
    save(fig, "fig1_e1_null_copying.png")


# --- Figure 2: E2 lever screen -----------------------------------------------------------------------
def fig_e2() -> None:
    rows = contrasts("E2")
    order = ["E2-betaP0", "E2-betaP1.5", "E2-betaP3", "E2-betaP6", "E2-kappa0", "E2-kappa0.40", "E2-etaQ0.05",
             "E2-etaQ0.40", "E2-pC0.01", "E2-pC0.20", "E2-q0-0", "E2-q0-0.5", "E2-plausible-max"]
    names = {"E2-betaP0": "β_P 0", "E2-betaP1.5": "β_P 1.5", "E2-betaP3": "β_P 3 (stress)",
             "E2-betaP6": "β_P 6 (stress)", "E2-kappa0": "κ 0", "E2-kappa0.40": "κ 0.40", "E2-etaQ0.05": "η_Q 0.05",
             "E2-etaQ0.40": "η_Q 0.40", "E2-pC0.01": "p_C⁰ 0.01", "E2-pC0.20": "p_C⁰ 0.20", "E2-q0-0": "q₀ 0",
             "E2-q0-0.5": "q₀ 0.5", "E2-plausible-max": "plausible max"}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
    DATA["fig2"] = {}
    for ax, outcome, title in zip(axes, ("pC_late", "pC_change"),
                                  ("Δ copying level (late) vs reference", "Δ copying growth (late − early) vs reference")):
        ax.axvspan(-0.02, 0.02, color=GRID, alpha=0.8, linewidth=0)
        ax.axvline(0, color=AXIS, lw=0.8)
        for y, cond in enumerate(order):
            r = next(x for x in rows if x["condition"] == cond and x["outcome"] == outcome)
            ax.errorbar(r["estimate"], y, xerr=[[r["estimate"] - r["lo"]], [r["hi"] - r["estimate"]]], fmt="o",
                        color=BLUE, ecolor=BLUE, elinewidth=1.5, capsize=0)
            DATA["fig2"].setdefault(cond, {})[outcome] = [r["estimate"], r["lo"], r["hi"]]
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("difference in share of students (95% CI)")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(order)), [names[c] for c in order])
    axes[0].invert_yaxis()
    fig.suptitle("E2 · Only the seed rate and all levers together move copying (V1, M2, SBM, R = 3, 200 replicates; "
                 "grey band = ±δ 0.02)", x=0.01, ha="left", fontweight="semibold")
    fig.tight_layout()
    save(fig, "fig2_e2_lever_screen.png")


# --- Figure 3: E3 V1 vs V2 dose-response -------------------------------------------------------------
def fig_e3() -> None:
    s = by_label(summaries("E3"), "pC_late")
    betas = [0.0, 0.5, 1.5, 3.0, 4.5, 6.0]
    lab = lambda v, b: "E3-v2-b0" if b == 0 else f"E3-{v}-b{b:g}"
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.axvspan(0, 1.5, color=GRID, alpha=0.7, linewidth=0)
    ax.text(0.75, 0.93, "plausible range\n(blueprint §32)", ha="center", va="top", color=INK2, fontsize=8)
    DATA["fig3"] = {}
    for v, color, name in (("v1", V1_COLOR, "V1: X = friends who asked me"), ("v2", V2_COLOR, "V2: X = friends who copy")):
        stats = [mean_ci(s[lab(v, b)]) for b in betas]
        m = [x[0] for x in stats]
        ax.fill_between(betas, [x[1] for x in stats], [x[2] for x in stats], color=color, alpha=0.18, linewidth=0)
        ax.plot(betas, m, "-o", color=color, label=name)
        ax.annotate(v.upper(), (6.1, m[-1]), color=INK2, va="center", fontsize=9)
        DATA["fig3"][v] = {f"{b:g}": x for b, x in zip(betas, m)}
    ax.set_xlim(-0.1, 6.5)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("peer-influence strength β_P")
    ax.set_ylabel("late copying (homeworks 16–20)")
    ax.set_title("E3 · Only 'friends copy' exposure (V2) makes copying spread (M2, SBM, R = 3, 400 replicates)")
    ax.legend(loc="center left")
    save(fig, "fig3_e3_v1_vs_v2.png")


# --- Figure 4: E4 tipping curve ----------------------------------------------------------------------
def fig_e4_tipping() -> None:
    extra = json.loads((RUNS / "E4" / "derived" / "extra.json").read_text("utf-8"))["F"]
    s = summaries("E4")
    betas = [0.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    tip = by_label(s, "tipped")
    late = by_label(s, "pC_late")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
    ax = axes[0]
    ax.axvspan(3.5, 4.5, color=GRID, alpha=0.8, linewidth=0)
    ax.text(4.0, 0.97, "predicted\nβ* range", ha="center", va="top", color=INK2, fontsize=8)
    shares = [float(np.mean(tip[f"E4-F-b{b:g}"])) for b in betas]
    ci = [wilson(p, len(tip[f"E4-F-b{b:g}"])) for p, b in zip(shares, betas)]
    ax.fill_between(betas, [c[0] for c in ci], [c[1] for c in ci], color=V2_COLOR, alpha=0.18, linewidth=0)
    ax.plot(betas, shares, "-o", color=V2_COLOR)
    ax.axvline(extra["threshold"], color=INK, lw=1)
    ax.annotate(f"β* = {extra['threshold']:.2f}\n[{extra['lo']:.2f}, {extra['hi']:.2f}]",
                (extra["threshold"], 0.5), xytext=(8, -4), textcoords="offset points", fontsize=9, color=INK)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("peer-influence strength β_P")
    ax.set_ylabel("share of classrooms tipped")
    ax.set_title("Classrooms tipped (late copying > 50%)", fontsize=10)
    ax = axes[1]
    stats = [mean_ci(late[f"E4-F-b{b:g}"]) for b in betas]
    ax.fill_between(betas, [x[1] for x in stats], [x[2] for x in stats], color=V2_COLOR, alpha=0.18, linewidth=0)
    ax.plot(betas, [x[0] for x in stats], "-o", color=V2_COLOR)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("peer-influence strength β_P")
    ax.set_ylabel("late copying (homeworks 16–20)")
    ax.set_title("Mean late copying", fontsize=10)
    fig.suptitle("E4 · A sharp tipping point at β_P ≈ 4.3 (V2, M2, SBM, R = 3, 400 replicates)", x=0.01, ha="left",
                 fontweight="semibold")
    fig.tight_layout()
    DATA["fig4"] = {"threshold": [extra["threshold"], extra["lo"], extra["hi"]],
                    "tipped": {f"{b:g}": p for b, p in zip(betas, shares)},
                    "late": {f"{b:g}": x[0] for b, x in zip(betas, stats)}}
    save(fig, "fig4_e4_tipping_curve.png")


# --- Figure 5: E4 dynamics over the semester ----------------------------------------------------------
def fig_e4_dynamics() -> None:
    levels = [3.0, 4.0, 4.5, 5.0, 6.0]
    labels = {0.0: "E4-F-b0", **{b: f"E4-F-b{b:g}" for b in levels}}
    wanted = lambda rep: {f"{lab}/rep{rep:04d}/SBM/R3/M2": lab for lab in labels.values()}
    tr = trajectories("E4", wanted, range(1, 401))
    hs = list(range(1, 21))
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    DATA["fig5"] = {}
    for key, ax, title, ylab in (("pC", axes[0], "Copying", "share choosing C"),
                                 ("succ", axes[1], "Copy success", "successful / attempted copies"),
                                 ("K", axes[2], "Knowledge", "mean K")):
        band(ax, hs, [tr[(labels[0.0], h)][key] for h in hs], MUTED, "β_P 0", lw=1.5)
        for b, color in zip(levels, ORDINAL):
            m = band(ax, hs, [tr[(labels[b], h)][key] for h in hs], color, f"β_P {b:g}")
            DATA["fig5"].setdefault(f"{b:g}", {})[f"{key}_h20"] = float(m[-1])
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("homework")
        ax.set_ylabel(ylab)
        ax.set_xlim(1, 20)
    axes[0].set_ylim(0, 1)
    axes[1].set_ylim(0, 1.02)
    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="lower center", ncols=6, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("E4 · Past the tipping point copying takes over, copy success collapses and knowledge falls "
                 "(V2, SBM, R = 3, 400 replicates; bands = 95% CI)", x=0.01, ha="left", fontweight="semibold")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, "fig5_e4_dynamics.png")


# --- Figure 6: spread of classroom outcomes near the threshold ---------------------------------------
def fig_e4_spread() -> None:
    late = by_label(summaries("E4"), "pC_late")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2), sharey=True)
    DATA["fig6"] = {}
    for ax, b in zip(axes, (4.0, 4.5, 5.0)):
        v = late[f"E4-F-b{b:g}"]
        ax.hist(v, bins=np.linspace(0, 1, 26), color=V2_COLOR, edgecolor=SURFACE, linewidth=1)
        ax.axvline(0.5, color=INK, lw=1)
        share = float(np.mean([x > 0.5 for x in v]))
        ax.set_title(f"β_P {b:g}: {share:.1%} of classrooms tipped", fontsize=10)
        ax.set_xlabel("late copying of one classroom")
        DATA["fig6"][f"{b:g}"] = share
    axes[0].set_ylabel("classrooms (of 400)")
    fig.suptitle("E4 · Near the threshold, identical classrooms end up in very different places", x=0.01, ha="left",
                 fontweight="semibold")
    fig.tight_layout()
    save(fig, "fig6_e4_outcome_spread.png")


# --- Figure 7: robustness (topology x R, stages) ------------------------------------------------------
def fig_e4_robustness() -> None:
    tip = by_label(summaries("E4"), "tipped")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [3, 2]})
    ax = axes[0]
    fams = ("ER", "WS", "SBM")
    label = lambda f, r: "E4-F-b4.5" if (f, r) == ("SBM", 3) else f"E4-T-{f}-R{r}-b4.5"
    DATA["fig7"] = {"topology": {}, "stages": {}}
    for k, (r, color) in enumerate(((1, BLUE), (3, ORANGE))):
        xs = [i + (k - 0.5) * 0.25 for i in range(3)]
        ps = [float(np.mean(tip[label(f, r)])) for f in fams]
        cis = [wilson(p, len(tip[label(f, r)])) for p, f in zip(ps, fams)]
        ax.errorbar(xs, ps, yerr=[[p - c[0] for p, c in zip(ps, cis)], [c[1] - p for p, c in zip(ps, cis)]],
                    fmt="o", color=color, elinewidth=1.5, capsize=0, label=f"R = {r}")
        for f, p in zip(fams, ps):
            DATA["fig7"]["topology"][f"{f} R{r}"] = p
    ax.set_xticks(range(3), fams)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of classrooms tipped")
    ax.set_title("Topology × routing depth (β_P 4.5)", fontsize=10)
    ax.legend(loc="lower right")
    ax.grid(axis="x", visible=False)
    ax = axes[1]
    stages = ("M2", "M3", "M4", "M5")
    lab = lambda st: "E4-F-b4.5" if st == "M2" else f"E4-S-{st}-b4.5"
    ps = [float(np.mean(tip[lab(st)])) for st in stages]
    cis = [wilson(p, len(tip[lab(st)])) for p, st in zip(ps, stages)]
    ax.errorbar(range(4), ps, yerr=[[p - c[0] for p, c in zip(ps, cis)], [c[1] - p for p, c in zip(ps, cis)]],
                fmt="o", color=BLUE, elinewidth=1.5, capsize=0)
    for st, p in zip(stages, ps):
        DATA["fig7"]["stages"][st] = p
    ax.set_xticks(range(4), ["M2", "M3\n+confidence", "M4\n+exam→C", "M5\n+exam→E"])
    ax.set_ylim(0, 1)
    ax.set_title("Feedback stages (SBM, R = 3, β_P 4.5)", fontsize=10)
    ax.grid(axis="x", visible=False)
    fig.suptitle("E4 · The tipping point is robust to topology and routing; confidence feedback damps it slightly "
                 "(Wilson 95% CI)", x=0.01, ha="left", fontweight="semibold")
    fig.tight_layout()
    save(fig, "fig7_e4_robustness.png")


# --- Figures 8 and 9: one classroom world, beta 0 vs 4.5 ---------------------------------------------
def pick_replicate() -> int:
    tip = {r["replicate"]: r["tipped"] for r in summaries("E4") if r["experiment_id"] == "E4-F-b4.5"}
    return min(r for r, t in tip.items() if t == 1.0)


def classroom(rep: int, label: str):
    rd = RUNS / "E4" / f"rep{rep:04d}"
    run_id = f"{label}/rep{rep:04d}/SBM/R3/M2"
    get = lambda name: [r for r in pq.read_table(rd / f"{name}.parquet").filter(
        pc.equal(pq.read_table(rd / f"{name}.parquet")["run_id"], run_id)).to_pylist()]
    return {name: get(name) for name in ("graph_nodes", "graph_edges", "decisions", "routing_events", "state_snapshots")}


def fig_network_and_raster() -> None:
    rep = pick_replicate()
    worlds = {b: classroom(rep, f"E4-F-b{b:g}") for b in (0.0, 4.5)}
    nodes = worlds[0.0]["graph_nodes"]
    G = nx.Graph()
    G.add_nodes_from(n["student_id"] for n in nodes)
    G.add_edges_from((e["u"], e["v"]) for e in worlds[0.0]["graph_edges"])
    pos = nx.spring_layout(G, seed=7)  # computed once; identical in both panels (docs/08 rule)
    community = {n["student_id"]: n["community_id"] for n in nodes}
    cmap = LinearSegmentedColormap.from_list("blue_seq", SEQ)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    DATA["fig8"] = {"replicate": rep}
    flows = {}
    for b in (0.0, 4.5):
        flows[b] = defaultdict(int)
        for r in worlds[b]["routing_events"]:
            if r["transfer_success"]:
                flows[b][tuple(sorted((r["requester_id"], r["target_id"])))] += 1
    top = max(max(f.values(), default=1) for f in flows.values())  # one width scale for both panels
    for ax, b in zip(axes, (0.0, 4.5)):
        w = worlds[b]
        flow = flows[b]
        K = {s["student_id"]: s["K"] for s in w["state_snapshots"] if s["event_id"] == "h20"}
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color=GRID, width=0.8)
        if flow:
            nx.draw_networkx_edges(G, pos, ax=ax, edgelist=list(flow), edge_color=ORANGE, alpha=0.85,
                                   width=[0.6 + 4.0 * flow[e] / top for e in flow])
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=[K[i] for i in G.nodes], cmap=cmap, vmin=0.5, vmax=0.9,
                               node_size=160, edgecolors=SURFACE, linewidths=1.5)
        n_c = sum(d["action"] == "C" for d in w["decisions"])
        ax.set_title(f"β_P {b:g}\n{sum(flow.values())} answer transfers · {n_c} copy attempts (20 homeworks)",
                     fontsize=10)
        ax.set_axis_off()
        DATA["fig8"][f"{b:g}"] = {"transfers": sum(flow.values()), "copy_attempts": n_c,
                                  "mean_K_final": float(np.mean(list(K.values())))}
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0.5, 0.9))
    cb = fig.colorbar(sm, ax=axes, shrink=0.6, pad=0.01)
    cb.set_label("final knowledge K")
    cb.outline.set_visible(False)
    fig.suptitle(f"One classroom world (E4 replicate {rep}, SBM): social ties (grey) and answer flows (orange, "
                 "width = transfers on one shared scale)", x=0.01, y=1.04, ha="left", fontweight="semibold")
    save(fig, "fig8_network_flows.png")

    # raster (docs/08 view G): students sorted by community, homeworks left to right
    order = sorted(community, key=lambda i: (community[i], i))
    code = {"S": 0, "D": 1, "C": 2}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    for ax, b in zip(axes, (0.0, 4.5)):
        w = worlds[b]
        M = np.zeros((len(order), 20))
        fails = []
        row = {i: k for k, i in enumerate(order)}
        for d in w["decisions"]:
            M[row[d["student_id"]], d["homework_index"] - 1] = code[d["action"]]
            if d["action"] == "C" and not d["copy_success"]:
                fails.append((d["homework_index"] - 1, row[d["student_id"]]))
        ax.imshow(M, aspect="auto", cmap=ListedColormap([BLUE, AQUA, ORANGE]), vmin=0, vmax=2,
                  interpolation="nearest")
        if fails:
            ax.scatter([f[0] for f in fails], [f[1] for f in fails], marker="x", s=14, color=INK, linewidths=1)
        ax.set_xticks(range(0, 20, 5), [str(h) for h in range(1, 21, 5)])
        ax.set_xlabel("homework")
        ax.set_title(f"β_P {b:g}", fontsize=10)
        ax.grid(False)
    axes[0].set_ylabel("student (grouped by community)")
    axes[0].set_yticks([])
    handles = [Patch(color=BLUE, label="S independent"), Patch(color=AQUA, label="D discussion"),
               Patch(color=ORANGE, label="C copy"),
               plt.Line2D([], [], marker="x", color=INK, linestyle="", label="failed copy")]
    axes[1].legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.suptitle(f"Who did what, homework by homework (E4 replicate {rep}, same classroom world)", x=0.01,
                 ha="left", fontweight="semibold")
    fig.tight_layout()
    save(fig, "fig9_action_raster.png")


if __name__ == "__main__":
    fig_e1()
    fig_e2()
    fig_e3()
    fig_e4_tipping()
    fig_e4_dynamics()
    fig_e4_spread()
    fig_e4_robustness()
    fig_network_and_raster()
    (OUT / "figure_data.json").write_text(json.dumps(DATA, indent=2) + "\n", encoding="utf-8")
    print("wrote figure_data.json")
