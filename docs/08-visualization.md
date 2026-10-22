---
type: spec
updated: 2026-09-18
status: PLAN (later phase; not part of the V1 engine)
tags:
  - spec
  - visualization
---
# 08 · Visualisation plan

Vavan's plan, recorded 2026-09-18. Nothing here is built yet. Every view reads the canonical outputs ([[docs/07-output-schema]]).

## Rules
- **Node positions are computed once from the static graph $A$ and never move.** A layout that moves between frames invents social dynamics that aren't in the model.
- Separate **scientific** views (to decide whether something is real) from **cinematic/exploratory** ones (video).
- Show one state encoding at a time, with a toggle. Never all at once.
- Tools: **Plotly** for interactive analysis (`Scatter3d` for the 3D views), **PyVista** for polished 3D and video. Obsidian export later, in `exporters/obsidian.py`.

## Views

| | View | What it shows | Role |
|---|---|---|---|
| A | Fixed 2D network | $A$ as thin background edges; $H^{(h)}$ as directed foreground edges, thickness = packets; node symbol/colour = state | **authoritative** |
| B | 3D micro-round cascade | $x,y$ fixed, $z$ = routing round; one homework's cascade as a branching structure | analysis + video |
| C | 3D semester spacetime | $z=h$; each student a vertical worldline; transmissions drawn at their layer, so repeated routes appear as "highways" | video |
| D | Node-state modes (toggle) | behaviour S/D/C plus source / receiver / broker / failed seeker; $K$; $M=C-K$; $P(C)$ | all views |
| E | Cascade animation | one homework frame by frame; new edges drawn, earlier ones faded | video |
| F | Knowledge landscape | $z=K_i$ over time, with transmissions overlaid | exploratory |
| G | Event raster | students × homework coloured by action; overlays for copy success/failure and exams | **authoritative** (shows lock-in) |
| H | Answer-flow matrix | $H^{cum}$ as a directed weighted matrix sorted by SBM community; off-diagonal bright cells mark bridges | **authoritative** |
| I | Cascade statistics over time | $S_{max}$, $L_{max}$, number of sources, fraction reached, broker count, alongside $P(C,t)$, $\bar K(t)$, $\Delta_{GK}(t)$ | **authoritative** |

## Eventual dashboard
Fixed network (A) | event raster (G)
$P(C)$, $\bar K$, $\Delta_{GK}$ over time | cascade statistics (I)
Clicking a homework opens its 3D micro-round cascade (B).

**For deciding what's real:** A, G, H, I and the null-normalised statistics. **For the YouTube presentation:** C and E.
