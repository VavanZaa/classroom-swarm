# E16: tutoring content and activity diagnostics

A29 reproduces similar directions to the peer-teaching lab comparison in the explicitly scheduled shared-practice protocol: mixed groups help low starters more than tracked groups, and shared practice exceeds equal-duration independent practice. Both final unaided exam and latent knowledge-gain means are positive on untouched validation seeds. This is directional correspondence within the assumed model, not empirical validation or effect-size replication.

All 3,120 runs completed and passed raw audits: 720 development runs (24 conditions × 30 replicates), then 2,400 validation runs (the same 24 conditions × 100 separate replicates). Settings, source code and both seed sets were frozen before development outcomes. No coefficient or engine revision was made after outcomes were inspected.

## Main effects

All values below are final-exam percentage-point differences for exogenously defined low starters, with paired pointwise 95% bootstrap Monte Carlo intervals. Intervals describe simulation uncertainty; they do not quantify uncertainty about real classrooms.

| Comparison | Development | Validation |
|---|---:|---:|
| Mixed − tracked, shared practice | +0.417 [+0.083, +0.750] | +0.300 [+0.158, +0.450] |
| Shared practice − independent practice | +0.972 [+0.528, +1.472] | +0.992 [+0.692, +1.292] |
| Stronger peers, voluntary practice | +0.400 [+0.222, +0.593] | +0.482 [+0.378, +0.589] |
| Stronger peers, copying available | -1.541 [-1.933, -1.141] | -1.520 [-1.751, -1.282] |
| Mixed − tracked, voluntary practice | +0.194 [-0.333, +0.611] | +0.392 [+0.150, +0.625] |
| Mixed − tracked, difficult content | -0.222 [-0.528, +0.083] | -0.358 [-0.517, -0.200] |
| Slower − reference shared practice | -1.028 [-1.639, -0.417] | -0.908 [-1.317, -0.525] |

![E16 tutoring diagnostics](<D:/3D Project/AI Student classroom Socio graph multiagent simulation/docs/experiments/figures/E16-tutoring-trends.png>)

For the two primary shared-practice comparisons, validation latent knowledge-gain differences are +0.272 [+0.185, +0.363] pp (mixed minus tracked) and +0.778 [+0.581, +0.965] pp (shared minus independent).

## Mechanism diagnosis and limits

The legacy optional-hint path remains available unchanged. Joint practice removes the old request/explanation/optional-practice separation: the learner works during the session and produces its own packet. Correct item content must also be novel and accessible to contribute a learning bonus. Helpers learn from correct completed explanation opportunities, rather than automatically from every delivered hint. Source-quality beliefs are private, directed and based on personally observed worksheet checks; availability remains separate.

The new voluntary, no-copying composition contrast is positive. The copying-enabled contrast remains negative: stronger sources can improve assisted homework while displacing independent practice. Adding tutoring content does not remove that substitution mechanism, and those contrary arms were retained rather than tuned away.

Longer scheduled sessions lower exams relative to the reference activity, showing the opportunity cost of time. Very difficult content suppresses usable explanations, and the mixed-versus-tracked advantage need not remain positive. Thus the extension does not enforce one aggregate sign across settings. Zero teaching skill yields exactly zero mixed-minus-tracked effect in this declared probe; disabling all communication also yields exact focal-student nulls.

Shared teaching versus independent practice partly encodes a benefit through nonnegative content/helper additions during an equal reserved practice block. It must not be presented as an independent discovery. Mixed versus tracked still depends on item content, helper opportunities, subsequent choices and the network assignment. Gain decomposition is a realized-path accounting identity, not independent causal mediation.

The [Kimbrough, McGee and Shigeoka manuscript](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) uses a common Sudoku task, optional conversation and individual evaluation. A29 represents shared-task opportunities with scheduled practice and sampled peer explanations. It does not model conversational decisions, visible ranks, persistent topic mastery or puzzle-solving speed. These differences limit the comparison, even when signs agree.

Class size with teacher capacity, adaptive instruction under tracking, and [Wu et al.’s helper-reward intervention](https://www.aeaweb.org/articles?id=10.1257/pol.20200563) require separately specified extensions. This implementation does not reproduce those field interventions. Existing AI paths are preserved; E16 makes no new AI replication claim.

## Changes, verification and use

* Added `tutoring_settings.py`, `v4_tutoring.py`, and `tutoring_config.py`, with all A28 parameters plus explicit activity/content coefficients and teaching-skill, source-quality and task-difficulty distributions.
* Added tests for legacy parity, item complementarity, readiness, wrong-content nulls, observable quality, time accounting, complete gain reconstruction, configuration validation and byte-identical interrupted-run recovery.
* Final complete regression suite: 429 tests passed. All 3,120 simulation raw audits and post-run hash checks passed.
* Added `scripts/resume_tutoring_experiment.py`; it checks settings, software/source/raw hashes, preserves incomplete directories, and regenerates only missing or damaged runs.
* All 321 historical source-lock entries checked across A22–A28/E14/E15 matched. Historical code and outputs are preserved.

Editable configuration: [full parameter template](<D:/3D Project/AI Student classroom Socio graph multiagent simulation/configs/A29-tutoring-template.json>) or [shared-practice comparison](<D:/3D Project/AI Student classroom Socio graph multiagent simulation/configs/A29-shared-practice-example.json>). Example commands:

```powershell
.venv\Scripts\python.exe -m classroom_swarm.tutoring_config validate configs/A29-tutoring-template.json
.venv\Scripts\python.exe -m classroom_swarm.tutoring_config run configs/A29-tutoring-template.json --output runs/my-tutoring-experiment
.venv\Scripts\python.exe scripts/resume_tutoring_experiment.py runs/my-tutoring-experiment
```

Sources and raw records: `runs/E16-tutoring-r1/diagnostic-lock.json`, four runtime locks, per-run completion hashes, and `development_derived`/`validation_derived` effects, replicate metrics, raw inventories and analysis manifests. Initial preflight rejected a distribution contrast incorrectly labeled as a single scalar change; it was declared bundled before any run. The unused `runs/E16-tutoring` directory contains no runs. No outcome-driven model changes occurred.

Progress: implementation and diagnostics complete; no approval or user input pending. Teacher/instruction and reward interventions remain separately scoped future work.
