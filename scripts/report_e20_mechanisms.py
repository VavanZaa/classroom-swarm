"""Report every frozen E20 contrast and audit-derived mechanism measures."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow.parquet as pq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import e20_mechanism_diagnostic as e20

ROOT = REPO / 'runs/E20-mechanisms-r1'
METRICS = ('exam', 'knowledge', 'teacher_ticks', 'returned_grades', 'peer_updates',
           'peer_backlog', 'final_fatigue', 'rewards')


def summarize():
    """Preserve the frozen metrics; supplement them from hash-checked raw rows."""
    lock = e20.verify(ROOT)
    rows, inventory = [], []
    for stage in e20.SEEDS:
        audit = e20.config.load_config(ROOT / f'{stage}-audit.json')
        assert audit['raw_audits'] == 'all passed'
        assert audit['design_sha256'] == e20.config.sha256(ROOT / 'design-lock.json')
        assert audit['metrics_sha256'] == e20.config.sha256(ROOT / f'{stage}-metrics.json')
        complete = e20.config.load_config(ROOT / stage / 'complete.json')
        assert complete['runs'] == audit['classrooms'] == 24 * e20.REPLICATES[stage]
        for name, digest in complete['hashes'].items():
            assert e20.config.sha256(ROOT / stage / name) == digest
        for row in e20.config.load_config(ROOT / f'{stage}-metrics.json'):
            folder = ROOT / stage / 'raw' / f"rep{row['replicate']:04d}" / row['condition']
            complete_path = folder / 'complete.json'
            for name, digest in e20.config.load_config(complete_path)['hashes'].items():
                assert e20.config.sha256(folder / name) == digest
            manifest = e20.config.load_config(folder / 'manifest.json')
            def table(name):
                path = folder / f'{name}.parquet'
                return [r for r in pq.read_table(path).to_pylist() if r] if path.exists() else []
            n, h = manifest['params']['N'], manifest['params']['H']
            actions = [r for r in table('teacher_actions') if r['homework'] <= h]
            lessons = [r for r in actions if r['action'] == 'instruction']
            runtime = [r for r in table('teacher_runtime') if r['homework'] <= h]
            events = table('events')
            components = table('learning_components')
            grades = table('homework_feedback')
            budgets = table('teacher_budget')
            new = dict(row)
            new.update(
                instruction_difficulty=float(np.mean([r['difficulty'] for r in lessons])) if lessons else None,
                effective_skill=float(np.mean([json.loads(r['settings'])['teaching_skill'] for r in runtime])) if runtime else manifest['teacher']['teaching_skill'],
                mandatory_ticks=sum(r['cost'] for r in table('teacher_workload') if r['homework'] <= h),
                practice_ticks=sum(r['end'] - r['start'] for r in events if r['occupied'] and r['action'] in {'attempt', 'guided_practice'}) / n,
                teacher_active_gain=100 * sum(r['teacher_gain'] for r in components) / n,
                helper_active_gain=100 * sum(r['helper_gain'] for r in components) / n,
                grades_during_class=sum(r['homework'] <= h for r in grades),
                grade_return_lag=float(np.mean([r['homework'] - r['source_homework'] for r in grades])) if grades else None,
                final_grading_backlog=budgets[-1]['grading_backlog'],
                paid_rewards=new['rewards'],
                pending_rewards=sum(r['amount'] for r in table('reward_backlog')),
            )
            rows.append(new)
            inventory.append(dict(stage=stage, replicate=row['replicate'], condition=row['condition'],
                                  graph_hash=manifest['graph_hash'], complete_sha256=e20.config.sha256(complete_path)))
        stage_inventory = [r for r in inventory if r['stage'] == stage]
        for rep in range(e20.REPLICATES[stage]):
            assert len({r['graph_hash'] for r in stage_inventory if r['replicate'] == rep}) == 1
    effects = []
    for s, stage in enumerate(e20.SEEDS):
        lookup = {(r['replicate'], r['condition']): r for r in rows if r['stage'] == stage}
        for c, profile in enumerate(e20.profiles()[1:]):
            count = e20.REPLICATES[stage]
            indices = np.random.default_rng(np.random.SeedSequence([10062099, s, c])).integers(0, count, (3000, count))
            for metric in METRICS:
                delta = np.array([lookup[(i, profile['name'])][metric] - lookup[(i, profile['parent'])][metric] for i in range(count)])
                lo, hi = np.quantile(delta[indices].mean(axis=1), [.025, .975])
                effects.append(dict(stage=stage, condition=profile['name'], reference=profile['parent'],
                                    metric=metric, effect=float(delta.mean()), lo95=float(lo), hi95=float(hi), replicates=count))
    return lock, rows, effects, inventory


def interval(row):
    return f"{row['effect']:+.3f} [{row['lo95']:+.3f}, {row['hi95']:+.3f}]"


def main():
    report = REPO / 'docs/experiments/E20-mechanism-results.md'
    derived = ROOT / 'reported'
    if report.exists() or derived.exists():
        raise ValueError('Preserve the existing report and derived evidence; choose a new reporting identity.')
    lock, rows, effects, inventory = summarize()
    def effect(condition, metric='exam', stage='confirmation'):
        return next(r for r in effects if (r['stage'], r['condition'], r['metric']) == (stage, condition, metric))
    def mean(condition, metric):
        values = [r[metric] for r in rows if r['stage'] == 'confirmation' and r['condition'] == condition and r[metric] is not None]
        return float(np.mean(values)) if values else None
    def show(value, digits=3):
        return '—' if value is None else f'{value:.{digits}f}'
    lines = ['---', 'type: experiment-results', 'updated: 2026-10-06', '---',
             '# E20 — Teacher incentives, workload, topics and peer observations', '',
             '**All four mechanisms are implemented and configurable in A31.** Human calibration is deferred, as requested. All **576 classroom runs** and saved-log audits passed; the full suite passes **560 tests**, including 39 new mechanism tests. The 24 fixed setups were run on six development replicates and 18 fresh replicates, with no setup selection or parameter tuning between pools.', '',
             'The teacher changes effort and lesson targets in response to declared reward rules and observed scores. Grading, administration and preparation consume the same finite budget; fatigue can reduce teaching quality. Knowledge persists separately by topic, with explicit transfer and helper consolidation. Peer-quality beliefs update only after private checked signals arrive, with configurable coverage, error and delay. Turning all four branches off reproduces A30 exactly.', '',
             '## What the fresh runs show', '',
             '| Change relative to its declared parent | Final exam difference, model pp [95%] | Mean knowledge difference, model pp [95%] | Teaching time difference, ticks/class |',
             '|---|---:|---:|---:|']
    highlights = [
        ('No reward, with intrinsic motivation fixed at zero', 'no_reward'),
        ('Admin bursts', 'admin_bursts'),
        ('Positive-cost grading added to admin bursts', 'costly_grading'),
        ('Grading automation restored', 'automated_grading'),
        ('Fatigue added at unchanged teacher time', 'fatigue'),
        ('Cross-topic transfer 0 → 0.2', 'topics_transfer'),
        ('Helper consolidation 0 → 0.2', 'helper_consolidation'),
        ('Noisy peer signals', 'peer_noise'),
        ('Peer signals delayed by 14 ticks', 'peer_delay'),
        ('All four mechanisms combined', 'combined'),
    ]
    for label, condition in highlights:
        lines.append(f"| {label} | {interval(effect(condition))} | {interval(effect(condition, 'knowledge'))} | {effect(condition, 'teacher_ticks')['effect']:+.3f} |")
    lines += ['',
        f"The zero-reward teacher chooses **{mean('no_reward', 'teacher_ticks'):.1f} teaching ticks**, versus **{mean('linear_reward', 'teacher_ticks'):.1f}** with linear rewards. Intrinsic motivation is deliberately zero in both, so this is a limiting control rather than a prediction that unrewarded human teachers stop teaching. Linear rewards also change the decision rule relative to A30's fixed allocation; the corresponding contrast is a bundle of effort selection and targeting.", '',
        f"Grading automation raises teaching time from **{mean('costly_grading', 'teacher_ticks'):.1f} to {mean('automated_grading', 'teacher_ticks'):.1f} ticks/class** in the admin-burst setup. It restores that setup's declared zero-cost grading behavior. This is a resource/time control. Its net outcome depends on teaching quality, available practice slots and actual feedback timing.", '',
        f"Fatigue leaves teaching time at **{mean('fatigue', 'teacher_ticks'):.1f} ticks** in the non-incentive setup while reducing mean effective skill to **{mean('fatigue', 'effective_skill'):.3f}**. The quality penalty is encoded; the resulting exam difference is measured. In the combined setup, fatigue also enters perceived effort cost, so teaching effort can change.", '',
        'Cross-topic transfer and helper consolidation grant nonnegative direct learning fractions by construction. Their downstream exam and activity effects remain stochastic. Splitting a fixed session across two independent topics lowers average topic exposure relative to a single scalar skill; that contrast changes the representation and measurement, so it is not evidence that adding subject detail harms human learning.', '',
        f"Delayed peer signals produce **{mean('peer_delay', 'peer_updates'):.1f} received updates** and **{mean('peer_delay', 'peer_backlog'):.1f} pending signals/class**, compared with **{mean('peer_reference', 'peer_updates'):.1f}** immediate updates. Absent checks produce **{mean('peer_absent', 'peer_updates'):.1f}** updates. Net score effects are small here: scheduled shared practice still delivers an episode, while private quality chiefly affects partner selection and perceived usefulness. These results do not establish that observations are irrelevant in optional-dialogue or longer-horizon settings.", '',
        '## Mechanism evidence from raw logs', '',
        'Fresh-pool means across six episodes. Teacher and mandatory ticks are per classroom; practice ticks are per student. Difficulty averages delivered instruction only; no instruction is shown as a dash. Direct gains sum logged active-topic components per student in model points; they are not treatment effects or mean-across-topic gains.', '',
        '| Setup | Teaching ticks | Mandatory ticks | Practice ticks/student | Instruction difficulty | Effective skill | Direct teacher gain | Direct helper gain |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for profile in e20.profiles():
        condition = profile['name']
        values = [mean(condition, key) for key in ('teacher_ticks', 'mandatory_ticks', 'practice_ticks', 'instruction_difficulty', 'effective_skill', 'teacher_active_gain', 'helper_active_gain')]
        lines.append(f"| {condition} | " + ' | '.join(show(v) for v in values) + ' |')
    lines += ['',
        '| Setup | Grades returned by class end | Grades returned including closing | Mean grade return lag, episodes | Grading backlog after closing | Paid reward units | Pending reward units | Final fatigue | Peer updates / pending |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for condition in ('reference', 'linear_reward', 'concave_reward', 'convex_reward', 'no_reward', 'costly_grading', 'automated_grading', 'fatigue', 'peer_delay', 'peer_absent', 'combined'):
        values = [mean(condition, key) for key in ('grades_during_class', 'returned_grades', 'grade_return_lag', 'final_grading_backlog', 'paid_rewards', 'pending_rewards', 'final_fatigue')]
        lines.append(f"| {condition} | " + ' | '.join(show(v) for v in values) + f" | {mean(condition, 'peer_updates'):.1f} / {mean(condition, 'peer_backlog'):.1f} |")
    lines += ['',
        'The H+1 closing pass processes already queued feedback and payments within the teacher budget, with no new teaching or preparation. Final fatigue includes that closing work. Payments due later remain pending; rewards never add student knowledge. Positive-cost grading can leave a backlog after closing. Observation and feedback delays are reconstructed using actual completion/release times.', '',
        '## Every declared contrast', '',
        'Child minus parent; brackets are pointwise paired bootstrap 95% intervals using 3,000 resamples and seed 10062099. The same paired replicate indices are used across metrics within a contrast. These descriptive intervals quantify simulator sampling variability, with 23 correlated contrasts and no multiplicity correction. Fresh seeds test numerical repeatability; they are not independent human evidence.', '',
        '| Child | Parent | Development exam pp [95%] | Fresh exam pp [95%] | Fresh knowledge pp [95%] | Fresh teaching ticks [95%] |',
        '|---|---|---:|---:|---:|---:|']
    for profile in e20.profiles()[1:]:
        c = profile['name']
        lines.append(f"| {c} | {profile['parent']} | {interval(effect(c, stage='development'))} | {interval(effect(c))} | {interval(effect(c, 'knowledge'))} | {interval(effect(c, 'teacher_ticks'))} |")
    lines += ['', '![All fresh parent contrasts](figures/E20-mechanism-effects.png)', '',
        'All candidates are retained, including null, contrary and uncertain outcomes. The four combined-module removals are conditional sensitivity contrasts. In particular, removing topics also removes transfer/consolidation and changes the skill representation; it cannot identify one content coefficient. Other multi-setting bundles are marked in the frozen declarations.', '',
        '## Assumptions and what remains unresolved', '',
        '| Mechanism | Why the channel is useful | Assumption and practical limit |',
        '|---|---|---|',
        '| Teacher incentives | Effort and lesson targets can respond to observable outcomes rather than being fixed appointments. Reward curvature has an explicit role. | A myopic teacher enumerates feasible plans using observed estimates and assumed productivity. It has no long-horizon planning, discounting, strategic test preparation or learned response to payment. Forecast utility is defined on active-topic predicted gains; actual payouts normalize received scores across students/topics. It is a declared behavioral proxy, not exact optimization of future cash flows. |',
        '| Workload | Administration, preparation and grading can crowd out instruction or delay feedback. Fatigue can affect quality as well as quantity. | Tick costs, fatigue/recovery rates and quality loss are uncalibrated. Quality is constant within each episode after mandatory work; teaching accumulates fatigue for later episodes. No occupational or medical interpretation is claimed. |',
        '| Topics and helper consolidation | Later tasks can use persistent relevant knowledge; explicit transfer connects topics. Helpers can consolidate even when the recipient already knows the material. | One active topic per homework; initial topics are cloned in E20, though arbitrary initial matrices are configurable. Student confidence and benefit beliefs remain pooled. There is no forgetting, misconception acquisition or language assessment. The consolidation rate is assumed. |',
        '| Peer observation | Private evidence can be incomplete, noisy or late, and beliefs cannot use future or hidden correctness. | Signals are recipients’ direct item checks with a fixed tick delay and independent binary error. Third-party observation, public reputation, dialogue, and friendship development are absent. |', '',
        'The [Duflo–Dupas–Kremer tracking paper](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf) motivates separating teacher effort, instructional level and reward curvature. The current rules are hypotheses inspired by that theoretical framing; the paper does not provide these simulator coefficients. E20 is a functional mechanism comparison, not a rerun of the tracking field protocol. Existing [E18](E18-teacher-study-results.md) and [E19](E19-teacher-study-results.md) results retain their original A30 identity and uncertainty.', '',
        'Human calibration is deferred. The next comparison should use separately declared study protocols with fixed teacher resources, topic exposure and observable incentive criteria. Optional tutoring/dialogue and test-specific preparation are remaining mechanisms; current sign agreement cannot substitute for those channels.', '',
        '## Configuration, preservation and audit', '',
        'Edit [the fresh, unrun A31 example](../../configs/A31-four-mechanisms-example.json). Root settings are authoritative; condition overrides can change individual branches. Validate before running, and use a new output directory:', '',
        '```text',
        'python -m classroom_swarm.mechanism_config validate configs/A31-four-mechanisms-example.json',
        'python -m classroom_swarm.mechanism_config run configs/A31-four-mechanisms-example.json --output runs/NEW_ID',
        '```', '',
        'The [A31 specification](../21-v4-classroom-mechanisms.md) defines the equations and private information boundary. The [E20 plan](E20-mechanism-plan.md) froze both seed pools, 24 setups, parent contrasts and analysis before outcomes. Run evidence is in `runs/E20-mechanisms-r1/`: `design-lock.json`, both configuration/complete locks, raw tables, both saved-log audits, original metrics, and `reported/` derived metrics/effects/inventory. No locked engine, test, specification or historical report was altered after freezing.', '',
        f"The report verifies **{e20.historical()} historical source entries**, the current design sources, stage completions, audit/metric hashes, every raw file hash and graph reuse across conditions. Validators replay topic learning, exam measurement, grade/provenance/time accounting, teacher estimates/choices/content/fatigue, rewards, peer signals and received beliefs. Supplemental time/content measures are exploratory descriptions computed after runs, with their exact raw inventory and hashes retained.", '',
        'Tests cover all-off parity, bounded declarations, isolated/transfer topics, state-neutral exams, helper consolidation with knowledgeable recipients, absent/noisy/delayed evidence, observed-only teacher policy, effort/payment controls, preparation/fatigue, grading delay, serialization and deliberately corrupted logs. Passing these checks establishes the declared implementation, not human validity.', '',
        'Progress: all four mechanisms implemented; 560 tests and 576 audited runs complete; no input pending. Next: study-specific comparisons using these channels, with human calibration deferred.', '']
    derived.mkdir()
    e20.config.save_json(derived / 'metrics.json', rows)
    e20.config.save_json(derived / 'effects.json', effects)
    e20.config.save_json(derived / 'inventory.json', inventory)
    with (derived / 'metrics.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    figure = REPO / 'docs/experiments/figures/E20-mechanism-effects.png'
    figure.parent.mkdir(exist_ok=True)
    profiles = e20.profiles()[1:]
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 11), sharey=True)
    y = np.arange(len(profiles))
    for axis, metric, title in zip(axes, ('exam', 'knowledge'), ('Final exam', 'Mean competence')):
        selected = [effect(p['name'], metric) for p in profiles]
        center = np.array([r['effect'] for r in selected])
        axis.errorbar(center, y, xerr=np.array([[r['effect']-r['lo95'] for r in selected], [r['hi95']-r['effect'] for r in selected]]), fmt='o', capsize=3, color='#24547c', markersize=4)
        axis.axvline(0, color='#666666', linewidth=.9)
        axis.grid(axis='x', alpha=.2); axis.set_title(title)
        axis.set_xlabel('Child minus parent (model percentage points)')
    axes[0].set_yticks(y, [p['name'].replace('_', ' ') for p in profiles], fontsize=9)
    axes[0].invert_yaxis()
    fig.suptitle('E20: all 23 fresh-pool contrasts · 18 paired classrooms per setup', fontsize=13)
    fig.text(.5, .012, 'Pointwise 95% bootstrap intervals; functional diagnostics, human calibration deferred.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .03, 1, .965)); fig.savefig(figure, dpi=165); plt.close(fig)
    report.write_text('\n'.join(lines), encoding='utf-8')
    evidence = [ROOT / 'design-lock.json', ROOT / 'development-audit.json', ROOT / 'confirmation-audit.json',
                ROOT / 'development-metrics.json', ROOT / 'confirmation-metrics.json']
    for stage in e20.SEEDS:
        evidence.append(ROOT / stage / 'complete.json')
    sourcepaths = evidence + list(derived.glob('*')) + [Path(__file__), figure, report]
    e20.config.save_json(report.with_suffix('.sources.json'), dict(
        sources={str(p.relative_to(REPO)).replace('\\', '/'): e20.config.sha256(p) for p in sourcepaths},
        raw_audits='all passed', classrooms=len(rows), tests_passed=560,
        historical_entries_verified=e20.historical(),
        bootstrap=dict(resamples=3000, seed=10062099, kind='paired pointwise descriptive'),
        interpretation='Functional diagnostics only; no tuning, selection or human calibration. Editable example is not a historical source lock.'))
    e20.verify(ROOT)
    print(f'Reported {len(rows)} classrooms, {len(effects)} metric contrasts; preserved all frozen sources.')


if __name__ == '__main__':
    main()
