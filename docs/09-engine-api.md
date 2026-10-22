---
type: spec
updated: 2026-09-20
status: FROZEN THROUGH A21
tags:
  - spec
---
# 09 · Engine API

The module layout and public signatures of `src/classroom_swarm/`, so tests T1–T24 ([[docs/06-validation-and-ablations]]) can be written **before** the engine. Signatures only, no implementation. Everything here implements the frozen docs 01–07. Approved by Vavan on 2026-09-18 with the changes recorded under *Decisions*.

## Design rules
- **`simulate()` is pure:** spec + graph + draws in, an in-memory log out. No file I/O, no global state, no hidden RNG. Writing to disk is a separate step, once per replicate.
- **The engine is stage-blind.** `RunSpec` carries the stage. `resolve_params(stage, base)` runs **once** and returns `EffectiveParams`, which is the only parameter object the engine sees. So the engine can't use a raw magnitude (e.g. $\beta_P=0.5$) in a stage where it's off.
- **Testing and calibration interventions are not model parameters.** They live in `SimulationControls`, never in `Params`, so they can't be swept by accident.
- Functions that choose partners or routes receive **ids and uniforms only, never $K$** (T5 checks their signatures).
- **One `Draws` per replicate, shared by all 36 paired runs**: every stage, every $R$ and **every graph family**. So ER, WS and SBM get the same strategy, partner, item, routing and exam uniforms, and only the graph differs (its own family-specific seed). This is intentional common-random-number pairing across topology. **Do not "fix" it by creating one `Draws` per family.**

## Modules

```
src/classroom_swarm/
  config.py       Stage, Params, EffectiveParams, resolve_params, SimulationControls, RunSpec
  graphs.py       Graph, generators, null rewiring   (docs/04)
  rng.py          stream codes, Draws, seeds, pick   (docs/05)
  engine.py       simulate, strategy_probabilities, route, Packet   (docs/03)
  records.py      RunLog, table/column names          (docs/07, in memory)
  storage.py      Arrow schemas, write_replicate, read_table        (docs/07, on disk)
  derive.py       reconstruction from raw tables      (docs/07 derived/, T13)
  experiment.py   run_replicate                       (36 paired runs → one table set)
  v3.py           separate A21 V3 parameters, equations, routing, simulation and runner
  e5.py           locked E5 V3 conditions, integrity guards, orchestration and summaries
  v3_variants.py  E6-only softmax/reward/access variants; frozen v3.py remains unchanged
  e6.py           locked E6 structural/factorial plans, strict source metric and effects
  e7.py           locked E7 external-AI intervention, sidecar schema, plans and summaries
  e8.py           locked E8 universal-access AI policy mechanisms, plans and policy summaries
```

### `config.py`
```python
class Stage(enum.IntEnum):
    M0 = 0; M1 = 1; M2 = 2; M3 = 3; M4 = 4; M5 = 5

Family = Literal["ER", "WS", "SBM"]

@dataclass(frozen=True)
class Params:
    """Raw scientific parameters. No stage, no controls, no derived values."""
    # environment (§29)
    N: int = 30; H: int = 20; F_E: int | None = 5; M_H: int = 10; M_E: int = 30
    # learning / init (§31, A12)
    K0: float = 0.5; C0_offset: float = 0.0
    alpha: float = 0.0584          # reference literal; never recomputed automatically
    p_C0: float = 0.10; q0_override: float | None = None
    # behaviour magnitudes (§32); whether each is active is decided by resolve_params
    eta_Q: float = 0.20; kappa: float = 0.15; chi_C: float = 0.10
    beta_P: float = 0.5; beta_C: float = 0.5; eta_C: float = 0.20
    eta_E: float = 0.30; tau_E: float = 0.70
    # graph (§30, A13, A14); used by graphs.py, not by the engine
    d_bar: int = 6; omega: float = 0.1; sbm_ratio: float = 5.0
    # structure (A19): what peer exposure X measures; "requests" = V1, "copying" = V2
    exposure: Literal["requests", "copying"] = "requests"
    def validate(self) -> None: ...     # ranges, WS even d_bar, M_H, M_E >= 1, exposure mode, ...

@dataclass(frozen=True)
class EffectiveParams:
    """Exactly the values simulate() uses, fully resolved for one stage."""
    N: int; H: int; F_E: int | None; M_H: int; M_E: int
    K0: float; C0: float                 # C0 = K0 + C0_offset
    alpha: float; q0: float; b_C: float  # q0 = q0_override or K0 - kappa (unclipped); b_C = ln(2p/(1-p))
    kappa: float; chi_C: float; eta_C: float; tau_E: float
    eta_Q: float                         # 0 in M0
    beta_P: float                        # 0 below M2
    beta_C: float                        # 0 below M3
    exam_updates_confidence: bool        # M4+
    exam_updates_effort: bool            # M5
    eta_E: float                         # 0 below M5
    exposure: str                        # A19, passed through unchanged

def resolve_params(stage: Stage, base: Params) -> EffectiveParams: ...   # the only place the stage ladder lives

@dataclass(frozen=True)
class SimulationControls:
    """Testing / calibration interventions. Never part of the scientific model."""
    force_action: Literal["S"] | None = None   # None in every experiment run

def alpha_from_trajectory(K0: float, K_T: float, T: int) -> float: ...   # §31 formula

@dataclass(frozen=True)
class RunSpec:
    experiment_id: str
    replicate: int
    family: Family
    R: int
    stage: Stage
    params: Params
    master_seed: int
    @property
    def run_id(self) -> str: ...        # "<exp>/rep0001/SBM/R3/M1"
```

### `graphs.py`
```python
@dataclass(frozen=True)
class Graph:
    family: Family
    N: int
    generator_params: Mapping[str, float]
    seed: int
    edges: tuple[tuple[int, int], ...]            # sorted, u < v
    neighbors: tuple[tuple[int, ...], ...]        # sorted ascending per node
    community: tuple[int, ...] | None             # SBM only
    weights: tuple[float, ...] | None = None      # aligned with edges; None canonicalises to all 1.0
    @property
    def degree(self) -> tuple[int, ...]: ...
    @property
    def edge_hash(self) -> str: ...               # sha256 of the canonical edge list
    @property
    def weight_hash(self) -> str: ...             # sha256 of canonical (u, v, weight) rows
    @property
    def neighbor_weights(self) -> tuple[tuple[float, ...], ...]: ... # aligned with neighbors
    def has_edge(self, u: int, v: int) -> bool: ...
    def summary(self) -> dict: ...                # mean degree, isolates, components

def sbm_sizes(N: int, blocks: int = 3) -> tuple[int, ...]: ...                              # 7/7/6, 10/10/10, 14/13/13
def sbm_probabilities(sizes: Sequence[int], d_bar: float, r: float) -> tuple[float, float]: ...  # (p_in, p_out), rejects p_in > 1
def generate_er(N: int, d_bar: float, seed: int) -> Graph: ...
def generate_ws(N: int, d_bar: int, omega: float, seed: int) -> Graph: ...   # even d_bar, d_bar < N
def generate_sbm(N: int, d_bar: float, r: float, seed: int) -> Graph: ...
def generate_graph(family: Family, params: Params, seed: int) -> Graph: ...
def with_edge_weights(graph: Graph, weights: Mapping[tuple[int, int], float] | Sequence[float]) -> Graph: ...
def shuffle_edge_weights(graph: Graph, seed: int) -> Graph: ...
def rewire_degree_preserving(graph: Graph, seed: int,
                             nswap_factor: int = 10, max_tries_factor: int = 100) -> tuple[Graph, int]: ...
    # returns (rewired graph, swaps actually performed); node ids and degrees unchanged
```

### `rng.py`
```python
RNG_SCHEME = "v1"
STREAM_CODE = {"graph": 1, "strategy": 2, "partner": 3, "item": 4, "routing": 5, "exam": 6,
               "null": 7, "exploration": 8, "traits": 9, "sharing": 10}
FAMILY_CODE = {"ER": 1, "WS": 2, "SBM": 3}

class DrawProvider(Protocol):
    """What simulate() needs from a source of uniforms. Draws is the production implementation;
    tests may pass a fixed provider with explicitly chosen uniforms (T17–T24)."""
    R_max: int
    def strategy(self, h: int) -> np.ndarray: ...   # (N,)
    def partner(self, h: int) -> np.ndarray: ...    # (N,)
    def item(self, h: int) -> np.ndarray: ...       # (M_H, N)
    def routing(self, h: int) -> np.ndarray: ...    # (R_max, N)
    def exam(self, e: int) -> np.ndarray: ...       # (M_E, N)
    def exploration(self, h: int) -> np.ndarray: ... # (N,), V3 only
    def traits(self) -> np.ndarray: ...              # (3, N) standard normals, V3 only
    def sharing(self, h: int) -> np.ndarray: ...     # (R_max, N), V3 only

class Draws:
    """Semantic uniforms for one replicate, shared by all its paired runs (every stage, R and family)."""
    def __init__(self, master_seed: int, replicate: int, N: int, M_H: int, M_E: int, R_max: int): ...
    def strategy(self, h: int) -> np.ndarray: ...   # (N,)
    def partner(self, h: int) -> np.ndarray: ...    # (N,)
    def item(self, h: int) -> np.ndarray: ...       # (M_H, N)
    def routing(self, h: int) -> np.ndarray: ...    # (R_max, N); a run with R uses rows [:R]
    def exam(self, e: int) -> np.ndarray: ...       # (M_E, N)

def graph_seed(master_seed: int, replicate: int, family: Family) -> int: ...
def null_seed(master_seed: int, replicate: int, family: Family, ell: int) -> int: ...
def pick(sorted_candidates: Sequence[int], u: float) -> int: ...   # candidates[floor(u * len)]
def weighted_pick(sorted_candidates: Sequence[int], weights: Sequence[float], u: float) -> int: ...
```
`h` and `e` are 1-based. Each tensor comes from `default_rng(SeedSequence([master, replicate, code, h_or_e]))`, generated lazily and cached. **$R$ pairing is contractual:** `run_replicate` builds `Draws` with `R_max = max(Rs)`, an $R=1$ run consumes `routing(h)[:1]` and an $R=3$ run `routing(h)[:3]`. `simulate` rejects `spec.R > draws.R_max`.

### `engine.py`
```python
@dataclass(frozen=True)
class Packet:
    answer_id: str          # "h{h}-s{root}"; unique only WITHIN a run, so the key is (run_id, answer_id)
    root: int
    depth: int              # 0 at the root
    items: tuple[bool, ...] # exact item outcomes, inherited unchanged by copies

@dataclass
class RoutingResult:
    received: dict[int, tuple[Packet, int, int]]  # receiver -> (packet, sender, round)
    requests: list[tuple[int, int, int, bool]]    # (round, requester, target, target_had_packet)
    incoming: dict[int, set[int]]                  # target -> distinct requesters

def strategy_probabilities(Q: np.ndarray, C: np.ndarray, X: np.ndarray,
                           feasible_social: np.ndarray, p: EffectiveParams) -> np.ndarray: ...
    # (N, 3) over (S, D, C); rows with feasible_social == False are exactly (1, 0, 0)

def route(neighbors: Sequence[Sequence[int]], holders: Mapping[int, Packet],
          copiers: Sequence[int], U_routing: np.ndarray,
          neighbor_weights: Sequence[Sequence[float]] | None = None) -> RoutingResult: ...
    # synchronous rounds over U_routing's rows; no knowledge state in the signature (T5)

def simulate(spec: RunSpec, graph: Graph, draws: DrawProvider, *,
             controls: SimulationControls = SimulationControls(),
             test_tally: bool = False) -> RunLog: ...
    # resolves spec.params once via resolve_params(spec.stage, ...) and runs docs/03;
    # with controls.force_action == "S", the logged P_* stay the model's probabilities but the action is S;
    # test_tally=True adds an independent H / grade tally (T13 only)
```

### `records.py`
```python
TABLES = ("graph_nodes", "graph_edges", "agent_traits", "events", "state_snapshots", "tie_snapshots",
          "decisions", "v3_decisions", "routing_events", "sharing_events", "item_outcomes")
COLUMNS: dict[str, tuple[str, ...]]       # exactly the docs/07 fields, in order

@dataclass
class RunLog:
    run_id: str
    manifest: dict      # docs/07 entry: stage, base_params, effective_params, controls, seeds, versions, ...
    tables: dict[str, dict[str, list]]     # columnar: table -> column -> values
    test_tally: dict | None = None
```

### `storage.py`
```python
SCHEMA_VERSION = "3"
ARROW_SCHEMAS: dict[str, "pyarrow.Schema"]    # typed and nullable exactly as docs/07

def write_replicate(rep_dir: Path, logs: Sequence[RunLog], shared_manifest: dict) -> list[Path]: ...
    # concatenates the runs; one Parquet file per table + manifest.json
def read_table(rep_dir: Path, name: str) -> "pyarrow.Table": ...
```

### `derive.py` (first phase: only what T13 needs)
Every join on answers uses the composite key **`(run_id, answer_id)`**. `answer_id` alone repeats across the 36 runs of a replicate.
```python
def provenance_paths(routing_events, decisions) -> dict[tuple[str, int, int], tuple[int, ...]]: ...
    # (run_id, h, student) -> root ... student, rebuilt from parent links
def flow_counts(routing_events) -> dict[tuple[str, int, int, int], int]: ...   # H^(h)[source, receiver]
def cascades(decisions) -> list[dict]: ...          # run_id, h, root, size S_s, max depth L_s
def grades_from_items(item_outcomes) -> dict[tuple[str, int, int], float]: ...
```
Brokerage, $Z^B$, $C_F$ and $\Delta_{GK}$ are added in the analysis phase; they're not needed for T1–T24.

### `experiment.py`
```python
def run_replicate(experiment_id: str, replicate: int, master_seed: int, base: Params,
                  out_root: Path, families: Sequence[Family] = ("ER", "WS", "SBM"),
                  Rs: Sequence[int] = (1, 3), stages: Sequence[Stage] = tuple(Stage)) -> Path: ...
    # one graph per family; ONE Draws(R_max=max(Rs)) for the whole replicate (see design rules);
    # 6 x 2 x 3 = 36 paired runs, always with default SimulationControls; one table set
```
A command-line entry point comes later, once the experiment configs exist.

## Test map

| Test file | Tests | Calls |
|---|---|---|
| `test_config.py` | T9, $\alpha$ check | `resolve_params` (stage ladder, derived $q_0$ and $b_C$), `strategy_probabilities`; $\lvert$`Params().alpha` − `alpha_from_trajectory(0.5, 0.85, 20)`$\rvert<10^{-4}$ |
| `test_graphs.py` | T14, T16, T26 | `sbm_sizes`, `sbm_probabilities`, `generate_*`, topology/weight hashes, explicit weights, weight shuffle, `rewire_degree_preserving` |
| `test_rng.py` | T8 (draw part), T26 | `Draws`, `pick`, `weighted_pick` |
| `test_routing.py` | T3, T4, T5, T26 | `route` (hand-built unweighted and weighted graphs) |
| `test_engine.py` | T1, T2, T11, T12, T15 | `simulate` |
| `test_calibration.py` | T10 | `simulate(controls=SimulationControls(force_action="S"))` |
| `test_reproducibility.py` | T6, T7, T8 (run part) | `simulate`, `run_replicate` |
| `test_reconstruction.py` | T13, T26 | `simulate(test_tally=True)`, `derive.*`, schema-v3 storage round trip and schema-v1 unity-weight compatibility |
| `test_equations.py` | T17–T26 | `simulate` on tiny hand-built graphs with a fixed `DrawProvider`; exact hand-computed values |
| `test_v3.py` | T27–T34 | V3 policy, traits, beliefs, learned targeting, sharing/reciprocity/capacity, social learning, synchronous routing, simulation, storage and runner |
| `test_e5.py` | E5 lock | Frozen-model/preregistration integrity, exact condition plan, weighted controls, E5 reconstruction and absolute decision rules |
| `test_e6.py` | E6 lock | Preregistration integrity, exact 14/256 condition plans, frozen-V3 parity, softmax probabilities, strict source metric and factorial product contrasts |
| `test_e7.py` | E7 lock | Exact 12/128 plans, external access assignment, four-action probabilities, frozen-V3 control parity, AI outcome equations, sidecar round-trip and factorial contrasts |
| `test_e8.py` | E8 lock | Exact 3/37/144 plans, universal voluntary access, four-action probabilities, frozen-V3 control parity, unrestricted and controlled AI equations, sidecar round-trip and trend reconstruction |

### `v3.py` (A21, separate from `engine.simulate`)
```python
@dataclass(frozen=True)
class V3Params: ...       # docs/10 approved defaults and validation

@dataclass(frozen=True)
class V3RunSpec: ...      # run_id = <exp>/repNNNN/<family>/R<R>/V3

@dataclass(frozen=True)
class V3Controls:
    trait_permutation: tuple[int, ...] | None = None
    force_action: str | None = None                  # test/calibration only

def initial_traits(p: V3Params, draws: DrawProvider,
                   controls: V3Controls = V3Controls()) -> TraitState: ...
def seed_probabilities(feasible_social, seed_fraction) -> np.ndarray: ...
def action_probabilities(Q, expected_access, kappa, feasible_social, epsilon, A0) -> np.ndarray: ...
def expected_access(neighbors, neighbor_weights, A) -> np.ndarray: ...
def share_probability(base, reciprocity, reverse_belief, A0) -> float: ...
def route_v3(...) -> V3RoutingResult: ...
def update_beliefs(A, outcomes, eta_A) -> np.ndarray: ...
def social_update(Q, actions, rewards, neighbors, neighbor_weights, eta_social) -> np.ndarray: ...
def simulate_v3(spec: V3RunSpec, graph: Graph, draws: DrawProvider, *,
                controls: V3Controls = V3Controls()) -> RunLog: ...
def run_v3_replicate(...) -> Path: ...
```

T12 is statistical: a pre-stated tolerance (e.g. 4 standard errors over ≥ 5,000 feasible student-homeworks) and fixed seeds, so it can't flake.

## Environment
`pyproject.toml` (src layout, `requires-python >= 3.12`) with dependencies `numpy`, `networkx`, `pyarrow` and dev dependency `pytest`. A project-local `.venv` via `uv`. Created in the test commit.

## Test-resolved API conventions (frozen 2026-09-18)
The tests are the executable specification, so every convention they rely on is written down here.
1. Invalid configuration or API input raises **`ValueError`**.
2. `Graph.summary()` returns at least `mean_degree`, `isolates` and `components`.
3. **`homework_index`, routing `round` and `exam_index` are 1-based** in all logged and event-facing data. `student_id` is the graph node id, `0..N-1`.
4. An exam's `homework_index` is the homework immediately before it, so the reference exams are at 5, 10, 15 and 20.
5. `test_tally` is exactly `{"H": {(h, source, receiver): n}, "grades": {(h, student): g}}`.
6. `derive.*` functions take **`pyarrow.Table`** inputs, not pandas objects.
7. `cascades()` returns rows with `run_id`, `h`, `root`, `size` and `max_depth`. **`size` counts the root source plus every student holding that source's packet**, so a source whose answer reaches nobody has `size = 1`, `max_depth = 0`.
8. **A failed copier's fallback answer belongs to no cascade and creates no flow edge.** For traceability it still has its own `answer_id` (`h{h}-s{i}`), `root_id = i`, `depth = 0` and item `mode = fallback` (docs/07, as decided 2026-09-18).
9. `simulate()` takes any `DrawProvider` (above). This makes the stochastic input explicit for tests without adding a simulation feature. The update equations have **no** separate public helpers: they are tested through `simulate()` on small black-box runs (T17–T24), so a correct helper can't hide a wrong combination.
10. `event_id` is `init`, `h<homework>` or `e<exam>` (docs/07 rule 6), so `grades_from_items(item_outcomes)` can recover the homework from `event_id` alone. For events that aren't exams, `diagnostic_only`, `exam_updates_confidence` and `exam_updates_effort` are null, and `init` has a null `homework_index`. (Added 2026-09-18 during the engine build; a spec gap, fixed in the docs first.)

## Decisions (Vavan, 2026-09-18)
1. **Stage lives in `RunSpec`, not `Params`.** `resolve_params(stage, base) → EffectiveParams` runs once, and the engine sees only `EffectiveParams`. The manifest stores `stage`, `base_params` and `effective_params`, so any result can be traced back to its ablation.
2. **Forced-S is a control, not a parameter:** `SimulationControls.force_action`, used only by T10 and §41 calibration and recorded in the manifest. Experiments always use the defaults.
3. **$\alpha$ stays the literal 0.0584** (exact derivation 0.0584225…), with a test against `alpha_from_trajectory`. It is never recomputed from $K_0$, $H$ or $K_T$. Changing those means choosing explicitly between a fixed-$\alpha$ robustness test and recalibration.
4. `Draws` takes `R_max`; runs slice `routing(h)[:R]`.
5. `(run_id, answer_id)` is the composite key for answers.
6. One `Draws` per replicate across families is intentional (design rules).
