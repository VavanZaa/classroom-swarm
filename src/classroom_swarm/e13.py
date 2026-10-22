"""A26 corrected-control study, locked before its own outcomes are observed.

Usage: python -m classroom_swarm.e13 lock|run|analyze --root runs/E13 ...
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
from pathlib import Path
import platform
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .e9 import REPO, digest, dump, write_csv, interval
from .e12 import encode_table
from .graphs import generate_graph
from .rng import graph_seed
from .v3 import V3Params
from .v4 import V4Log, summarize
from .v4_public_ai import PublicAIDraws
from .v4_corrected import CorrectedParams, simulate_corrected, validate_corrected_log

SEED, REPLICATES = 924401, 100
LOCK_FILES = ('docs/15-v4-corrected-controls.md', 'docs/experiments/E13-preregistration.md',
              'src/classroom_swarm/v4_corrected.py', 'src/classroom_swarm/e13.py',
              'tests/test_v4_corrected.py',
              'src/classroom_swarm/v4_public_ai.py', 'src/classroom_swarm/e12.py',
              'src/classroom_swarm/v4_grades.py', 'src/classroom_swarm/e11.py',
              'src/classroom_swarm/v4_learning.py', 'src/classroom_swarm/e10.py',
              'src/classroom_swarm/v4.py', 'src/classroom_swarm/e9.py',
              'src/classroom_swarm/v3.py', 'src/classroom_swarm/graphs.py', 'src/classroom_swarm/rng.py')

# Sign-determined consequences of the encoded rules. Reported for magnitude, never as findings.
IDENTITIES = ('answer_ai vs public_no_ai on homework_at_final_exam and matched_gap: an AI that emits '
              'ai_accuracy-correct packets and grants no knowledge must raise homework and widen the gap '
              'at any positive uptake',
              'no_pressure vs public_no_ai on copying: grade_response*shortfall is added directly to the '
              'answer and ai_answer scores',
              'homework_feedback B movement toward the observed grade: that is the update rule')


def conditions():
    """The A25 bundle unpacked into one parameter per rung, then the AI and sensitivity arms."""
    p = CorrectedParams()
    legacy_routing = dict(peer_rule='legacy', distant_weight=0, closeness_spread=0,
                          grade_bias=0, public_signal=0)
    legacy = replace(p, **legacy_routing, grade_effort_only=False, learning_value=.25, wait_value=.025)
    motivation = replace(legacy, grade_effort_only=True, learning_value=0, wait_value=0.)
    acquaintances = replace(motivation, distant_weight=.1, closeness_spread=.5)
    grade_filter = replace(acquaintances, peer_rule='higher')
    grade_weighting = replace(grade_filter, grade_bias=3)
    public = replace(grade_weighting, public_signal=.5)
    # The ladder must land exactly on the corrected main case, or a rung is mis-specified.
    assert asdict(public) == asdict(p)
    rows = [
        ('legacy', 'SBM', legacy),
        ('drop_learning_bonus', 'SBM', replace(legacy, grade_effort_only=True, learning_value=0)),
        ('drop_wait_bonus', 'SBM', replace(legacy, wait_value=0.)),
        ('motivation_only', 'SBM', motivation),
        ('acquaintances', 'SBM', acquaintances),
        ('plus_grade_filter', 'SBM', grade_filter),
        ('plus_grade_weighting', 'SBM', grade_weighting),
        ('public_no_ai', 'SBM', public),
        ('answer_ai', 'SBM', replace(public, ai_mode='answer')),
        ('tutor_ai', 'SBM', replace(public, ai_mode='tutor')),
        ('answer_ai80', 'SBM', replace(public, ai_mode='answer', ai_accuracy=.8)),
        ('answer_ai100', 'SBM', replace(public, ai_mode='answer', ai_accuracy=1)),
        ('tutor_ai0', 'SBM', replace(public, ai_mode='tutor', ai_hint_strength=0)),
        ('tutor_ai50', 'SBM', replace(public, ai_mode='tutor', ai_hint_strength=.5)),
        # The A25 defect itself, as a measured condition rather than an assertion.
        ('tutor_ai0_uncredited', 'SBM', replace(public, ai_mode='tutor', ai_hint_strength=0,
                                                tutor_credit_by_source=False)),
        ('no_pressure', 'SBM', replace(public, grade_response=0)),
        ('answer_no_pressure', 'SBM', replace(public, ai_mode='answer', grade_response=0)),
        ('tutor_no_pressure', 'SBM', replace(public, ai_mode='tutor', grade_response=0)),
        ('public_relaxed', 'SBM', replace(public, peer_rule='relaxed')),
        ('answer_relaxed', 'SBM', replace(public, ai_mode='answer', peer_rule='relaxed')),
        ('score_only', 'SBM', replace(public, relationship_strength=0)),
        ('friends_only', 'SBM', replace(public, distant_weight=0)),
        ('confidence0_no_ai', 'SBM', replace(public, confidence_weight=0.)),
        ('confidence0_answer', 'SBM', replace(public, ai_mode='answer', confidence_weight=0.)),
        ('confidence100_no_ai', 'SBM', replace(public, confidence_weight=1.)),
        ('confidence100_answer', 'SBM', replace(public, ai_mode='answer', confidence_weight=1.)),
        ('prior25_no_ai', 'SBM', replace(public, benefit_prior=.25)),
        ('prior75_no_ai', 'SBM', replace(public, benefit_prior=.75)),
        ('prior25_answer', 'SBM', replace(public, ai_mode='answer', benefit_prior=.25)),
        ('prior75_answer', 'SBM', replace(public, ai_mode='answer', benefit_prior=.75)),
        ('hint_guard_off_no_ai', 'SBM', replace(public, hint_deadline_guard=False)),
        ('effort0_no_ai', 'SBM', replace(public, kappa=0)),
        ('effort0_answer', 'SBM', replace(public, kappa=0, ai_mode='answer')),
        ('effort0_tutor', 'SBM', replace(public, kappa=0, ai_mode='tutor')),
        ('effort50_no_ai', 'SBM', replace(public, kappa=.5)),
        ('effort50_answer', 'SBM', replace(public, kappa=.5, ai_mode='answer')),
        ('effort50_tutor', 'SBM', replace(public, kappa=.5, ai_mode='tutor')),
        ('H40_no_ai', 'SBM', replace(public, H=40)),
        ('H40_answer', 'SBM', replace(public, H=40, ai_mode='answer')),
        ('H40_tutor', 'SBM', replace(public, H=40, ai_mode='tutor')),
        ('ER_no_ai', 'ER', public),
        ('ER_answer', 'ER', replace(public, ai_mode='answer')),
        ('ER_tutor', 'ER', replace(public, ai_mode='tutor')),
        ('answer_no_exam_feedback', 'SBM', replace(public, ai_mode='answer', feedback_mode='none')),
    ]
    return rows


PRIMARY = (('drop_learning_bonus', 'legacy'), ('drop_wait_bonus', 'legacy'),
           ('motivation_only', 'legacy'), ('acquaintances', 'motivation_only'),
           ('plus_grade_filter', 'acquaintances'), ('plus_grade_weighting', 'plus_grade_filter'),
           ('public_no_ai', 'plus_grade_weighting'), ('answer_ai', 'public_no_ai'),
           ('tutor_ai', 'public_no_ai'), ('tutor_ai', 'answer_ai'),
           ('tutor_ai0', 'tutor_ai'), ('tutor_ai0_uncredited', 'tutor_ai0'))

SECONDARY = (('answer_ai80', 'answer_ai'), ('answer_ai100', 'answer_ai'), ('tutor_ai50', 'tutor_ai'),
             ('no_pressure', 'public_no_ai'), ('answer_no_pressure', 'answer_ai'),
             ('tutor_no_pressure', 'tutor_ai'), ('public_relaxed', 'public_no_ai'),
             ('answer_relaxed', 'answer_ai'), ('score_only', 'public_no_ai'),
             ('friends_only', 'public_no_ai'), ('confidence0_no_ai', 'public_no_ai'),
             ('confidence0_answer', 'answer_ai'), ('confidence100_no_ai', 'public_no_ai'),
             ('confidence100_answer', 'answer_ai'), ('prior25_no_ai', 'public_no_ai'),
             ('prior75_no_ai', 'public_no_ai'), ('prior25_answer', 'answer_ai'),
             ('prior75_answer', 'answer_ai'), ('hint_guard_off_no_ai', 'public_no_ai'),
             ('effort0_no_ai', 'public_no_ai'), ('effort0_answer', 'answer_ai'),
             ('effort0_tutor', 'tutor_ai'), ('effort50_no_ai', 'public_no_ai'),
             ('effort50_answer', 'answer_ai'), ('effort50_tutor', 'tutor_ai'),
             ('H40_answer', 'H40_no_ai'), ('H40_tutor', 'H40_no_ai'),
             ('ER_answer', 'ER_no_ai'), ('ER_tutor', 'ER_no_ai'),
             ('answer_no_exam_feedback', 'answer_ai'))


def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'lock.json').exists():
        raise FileExistsError('Never replace an existing scientific lock')
    dump(root / 'lock.json', dict(
        status='exploratory correction of A25 controls and identification; fixed E13 design',
        seed=SEED, replicates=REPLICATES, bootstrap_seed=924402, bootstrap_samples=2000,
        python=platform.python_version(), numpy=np.__version__, pyarrow=pa.__version__,
        stated_identities=list(IDENTITIES),
        subgroup_rule='contrasted subgroups use the exogenous alpha trait; behavioural desc_ groups '
                      'are reported per condition and never differenced',
        primary=[list(c) for c in PRIMARY], secondary=[list(c) for c in SECONDARY],
        sources={f: digest(REPO / f) for f in LOCK_FILES},
        conditions=[dict(name=n, family=f, params=asdict(p)) for n, f, p in conditions()]))


def verify_lock(root):
    value = json.loads((root / 'lock.json').read_text())
    for f, expected in value['sources'].items():
        if digest(REPO / f) != expected:
            raise RuntimeError(f'Locked source changed: {f}')
    return value


def run_replicate(root_text, rep):
    root = Path(root_text)
    verify_lock(root)
    folder = root / 'raw' / f'rep{rep:04d}'
    if (folder / 'complete.json').exists():
        hashes = json.loads((folder / 'complete.json').read_text())['hashes']
        for f, expected in hashes.items():
            assert digest(folder / f) == expected
        return rep
    if folder.exists():
        raise FileExistsError(f'Inspect incomplete shard instead of overwriting: {folder}')
    folder.mkdir(parents=True)
    graphs = {f: generate_graph(f, V3Params(), graph_seed(SEED, rep, f)) for f in ('SBM', 'ER')}
    draws = PublicAIDraws(SEED, rep, 30, 10, 30)
    writers, groups, manifests = {}, {}, {}
    try:
        for name, family, p in conditions():
            log = simulate_corrected(p, graphs[family], draws, name)
            validate_corrected_log(log)
            manifests[name] = log.manifest
            for table, rows in log.tables.items():
                if not rows:
                    continue
                data = encode_table(table, rows)
                if table not in writers:
                    writers[table] = pq.ParquetWriter(folder / f'{table}.parquet', data.schema, compression='zstd')
                    groups[table] = []
                writers[table].write_table(data, row_group_size=data.num_rows)
                groups[table].append(name)
    finally:
        for w in writers.values():
            w.close()
    dump(folder / 'manifests.json', manifests)
    dump(folder / 'row_groups.json', groups)
    dump(folder / 'complete.json', dict(replicate=rep, runs=len(conditions()),
        hashes={f.name: digest(f) for f in sorted(folder.iterdir()) if f.is_file()}))
    return rep


EXTRA_TABLES = ('homework_feedback', 'ai_uses', 'hint_receipts', 'contacts')


def read_log(folder, name):
    manifests = json.loads((folder / 'manifests.json').read_text())
    groups = json.loads((folder / 'row_groups.json').read_text())
    result = V4Log(manifests[name])
    for table in EXTRA_TABLES:
        result.tables[table] = []
    for table in result.tables:
        if table in groups and name in groups[table]:
            result.tables[table] = pq.ParquetFile(folder / f'{table}.parquet').read_row_group(
                groups[table].index(name)).to_pylist()
    return result


def trait_groups(log):
    """Exogenous thirds by the learning trait: drawn before any behaviour, identical in every
    condition of a replicate, and therefore safe to difference across conditions."""
    traits = log.tables['traits']
    n = len(traits)
    order = sorted(range(n), key=lambda i: (traits[i]['alpha'], i))
    return {i: ('low' if rank < n // 3 else 'high' if rank >= n - n // 3 else 'middle')
            for rank, i in enumerate(order)}


def early_groups(log):
    """Behavioural thirds inside THIS condition. Descriptive only: never differenced, because a
    group defined by one arm's realised behaviour carries that arm's noise into the contrast."""
    n = log.manifest['params']['N']
    counts = np.bincount([e['student'] for e in log.tables['events']
                          if e['action'] == 'attempt' and e['homework'] <= 5], minlength=n)
    order = sorted(range(n), key=lambda i: (counts[i], i))
    return {i: ('low' if rank < n // 3 else 'high' if rank >= n - n // 3 else 'middle')
            for rank, i in enumerate(order)}


def measures(log):
    p = log.manifest['params']
    n, horizon = p['N'], p['H']
    rows, events, traits = log.tables['students'], log.tables['events'], log.tables['traits']
    feedback, receipts = log.tables['homework_feedback'], log.tables['hint_receipts']
    by = {(r['homework'], r['student']): r for r in rows}
    groups, desc = trait_groups(log), early_groups(log)

    def mean(values):
        values = [v for v in values if v is not None]
        return float(np.mean(values)) if len(values) else float('nan')

    students = []
    for i in range(n):
        es = [e for e in events if e['student'] == i]
        gains = {a: sum(e['K_after'] - e['K_before'] for e in es if e['action'] == a)
                 for a in ('attempt', 'help_hint')}
        final, initial = by[horizon, i]['K'], traits[i]['K0']
        assert abs(sum(gains.values()) - (final - initial)) < 1e-12
        end = by[horizon, i]
        students.append(dict(student=i, group=groups[i], desc_group=desc[i], K0=initial,
            K_final=final, gain=final - initial, later_gain=final - by[5, i]['K'],
            alpha=traits[i]['alpha'], kappa=traits[i]['kappa'], degree=traits[i]['degree'],
            attempts=sum(e['action'] == 'attempt' for e in es),
            answers=sum(e['action'] == 'answer_receive' for e in es),
            ai_answer_uses=sum(r['ai_answer'] for r in rows if r['student'] == i),
            ai_tutor_uses=sum(r['ai_tutor'] for r in rows if r['student'] == i),
            final_grade=end['grade'], final_route=end['final_route'],
            **{a + '_gain': v for a, v in gains.items()}))

    out = summarize(log)
    exams = log.tables['exams']
    h_exam = max(r['homework'] for r in exams)
    final = [r for r in rows if r['homework'] == horizon]
    matched = [r for r in rows if r['homework'] == h_exam]
    late = [r for r in rows if r['homework'] > horizon - 5]
    out['homework_final'] = mean([r['grade'] for r in final])
    out['homework_at_final_exam'] = mean([r['grade'] for r in matched])
    out['late_homework_final_exam_gap'] = out['grade_exam_gap']
    out['matched_gap'] = out['homework_at_final_exam'] - out['exam_final']
    out['final_assessment_homework'] = h_exam
    final_k = [r['K_final'] for r in students]
    out['K_p90_p10'] = float(np.diff(np.quantile(final_k, [.1, .9]))[0])
    out['K0_p90_p10'] = float(np.diff(np.quantile([r['K0'] for r in students], [.1, .9]))[0])
    for metric in ('gain', 'later_gain', 'attempts', 'answers', 'attempt_gain', 'help_hint_gain'):
        out[metric] = mean([r[metric] for r in students])

    for metric in ('peer_copied', 'direct_ai_answer', 'ai_answer_origin', 'ai_answer', 'ai_tutor'):
        out[metric + '_late'] = mean([r[metric] for r in late])
        out[metric + '_final'] = mean([r[metric] for r in final])
    out['peer_ai_origin_late'] = mean([r['peer_copied'] and r['ai_answer_origin'] for r in late])
    out['ai_answer_total'] = sum(r['ai_answer'] for r in rows) / n
    out['ai_tutor_total'] = sum(r['ai_tutor'] for r in rows) / n
    out['ai_guided_late'] = mean([r['final_route'] == 'ai_guided' for r in late])
    tutor_uses = sum(r['mode'] == 'ai_tutor' for r in log.tables['ai_uses'])
    consumed = sum(r['hint_source'] == 'ai' for r in log.tables['packets'])
    out['tutor_followthrough'] = consumed / tutor_uses if tutor_uses else float('nan')

    # A26 audit metrics: which belief channels actually receive evidence.
    scored = [r for r in feedback if r['homework'] <= horizon]
    credits = np.array([json.loads(r['credit']) for r in scored]) if scored else np.zeros((1, 5))
    for index, action in enumerate(('attempt', 'hint', 'answer', 'ai_answer', 'ai_tutor')):
        out['credit_share_' + action] = float(np.mean(credits[:, index] > 0))
    out['B_attempt_final'] = mean([r['B_attempt'] for r in final])
    out['B_answer_final'] = mean([r['B_answer'] for r in final])
    out['B_ai_answer_final'] = mean([r['B_ai_answer'] for r in final])
    out['B_ai_tutor_final'] = mean([r['B_ai_tutor'] for r in final])
    out['hint_receipts_total'] = len(receipts) / n
    peer_receipts = [r for r in receipts if r['source'] == 'peer']
    out['hint_usable_share'] = mean([r['usable'] for r in peer_receipts])
    out['hint_receipts_peer_total'] = len(peer_receipts) / n

    peer_requests = [r for r in log.tables['requests'] if r['mode'] == 'answer']
    higher = [r for r in peer_requests if r['provider_public_grade'] is not None
              and r['provider_public_grade'] > r['requester_public_grade']]
    out['higher_grade_source_requests'] = len(higher)
    out['higher_grade_source_not_higher_K'] = mean(
        [r['research_provider_K'] <= r['research_requester_K'] for r in higher])
    out['source_closeness'] = mean([r['closeness'] for r in peer_requests])
    contacts = {(r['u'], r['v']): r['friend'] for r in log.tables['contacts']}
    out['friend_source_share'] = mean(
        [contacts[tuple(sorted((r['requester'], r['provider'])))] for r in peer_requests])

    # Exogenous-trait subgroups: safe to difference. Behavioural ones are descriptive only.
    for metric in ('K0', 'K_final', 'gain', 'later_gain', 'attempts', 'answers'):
        for group in ('low', 'high'):
            out[f'{group}_{metric}'] = mean([r[metric] for r in students if r['group'] == group])
        out[f'group_gap_{metric}'] = out[f'high_{metric}'] - out[f'low_{metric}']
        for group in ('low', 'high'):
            out[f'desc_{group}_{metric}'] = mean([r[metric] for r in students if r['desc_group'] == group])
        out[f'desc_group_gap_{metric}'] = out[f'desc_high_{metric}'] - out[f'desc_low_{metric}']

    tr = []
    for h in range(1, horizon + 1):
        rr = [r for r in rows if r['homework'] == h]
        ex = [r for r in exams if r['homework'] == h]
        tr.append(dict(homework=h, K=mean([r['K'] for r in rr]), grade=mean([r['grade'] for r in rr]),
            exam=mean([r['score'] for r in ex]), C=mean([r['C'] for r in rr]),
            peer_copy=mean([r['peer_copied'] for r in rr]), direct_ai=mean([r['direct_ai_answer'] for r in rr]),
            ai_origin=mean([r['ai_answer_origin'] for r in rr]), attempt=mean([r['attempt'] for r in rr]),
            B_attempt=mean([r['B_attempt'] for r in rr]), B_ai_tutor=mean([r['B_ai_tutor'] for r in rr]),
            K_p90_p10=float(np.diff(np.quantile([r['K'] for r in rr], [.1, .9]))[0])))
    return out, students, tr


def analyze(root, output):
    locked = verify_lock(root)
    output.mkdir(parents=True, exist_ok=True)
    summaries, students, trajectory, inventory = [], [], [], []
    for rep in range(REPLICATES):
        folder = root / 'raw' / f'rep{rep:04d}'
        hashes = json.loads((folder / 'complete.json').read_text())['hashes']
        for f, expected in hashes.items():
            assert digest(folder / f) == expected, f
            inventory.append(dict(path=str((folder / f).resolve()), sha256=expected))
        for name, family, p in conditions():
            log = read_log(folder, name)
            result, ss, tr = measures(log)
            summaries.append(dict(condition=name, replicate=rep, **result))
            students.extend(dict(condition=name, replicate=rep, **r) for r in ss)
            trajectory.extend(dict(condition=name, replicate=rep, **r) for r in tr)
        if (rep + 1) % 20 == 0:
            print(f'Raw audit and decomposition: {rep + 1}/{REPLICATES}', flush=True)
    for name in ('legacy', 'public_no_ai', 'answer_ai', 'tutor_ai', 'tutor_ai0'):
        family, p = next((f, q) for n, f, q in conditions() if n == name)
        graph = generate_graph(family, V3Params(), graph_seed(SEED, 0, family))
        rerun = simulate_corrected(p, graph, PublicAIDraws(SEED, 0, 30, 10, 30), name)
        assert rerun.tables == read_log(root / 'raw' / 'rep0000', name).tables
    grouped = {n: [r for r in summaries if r['condition'] == n] for n, _, _ in conditions()}
    metrics = sorted(set(summaries[0]) - {'condition', 'replicate'})
    # Behavioural subgroups are defined inside each arm, so they are never differenced.
    effect_metrics = [m for m in metrics if not m.startswith('desc_')]
    rng = np.random.default_rng(locked['bootstrap_seed'])
    estimates, effects = [], []
    for name, rs in grouped.items():
        for metric in metrics:
            estimates.append(dict(condition=name, metric=metric, **interval([r[metric] for r in rs], rng)))
    for name, reference in PRIMARY + SECONDARY:
        for metric in effect_metrics:
            effects.append(dict(condition=name, reference=reference,
                primary=(name, reference) in PRIMARY, metric=metric,
                **interval([a[metric] - b[metric] for a, b in zip(grouped[name], grouped[reference])], rng)))
    write_csv(output / 'classroom_results.csv', summaries)
    write_csv(output / 'student_results.csv', students)
    write_csv(output / 'trajectories.csv', trajectory)
    write_csv(output / 'condition_estimates.csv', estimates)
    write_csv(output / 'paired_effects.csv', effects)
    dump(output / 'dataset_manifest.json', dict(raw_root=str(root.resolve()), files=inventory))
    dump(output / 'analysis.json', dict(status='exploratory', runs=len(summaries), replicates=REPLICATES,
        source_lock=digest(root / 'lock.json'), verified_raw_files=len(inventory),
        stated_identities=list(IDENTITIES),
        student_gain_reconstruction='all within 1e-12',
        differenced_metrics=len(effect_metrics), descriptive_only_metrics=len(metrics) - len(effect_metrics),
        independent_reruns='legacy, public_no_ai, answer_ai, tutor_ai and tutor_ai0: every raw table identical',
        estimates=estimates, effects=effects))
    print(f'Analysis saved to {output}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['lock', 'run', 'analyze'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'lock':
        lock(args.root)
    elif args.command == 'run':
        verify_lock(args.root)
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_replicate, str(args.root), r) for r in range(REPLICATES)]
            for j, f in enumerate(as_completed(futures), 1):
                f.result()
                if j % 10 == 0:
                    print(f'Completed {j}/{REPLICATES} replicate sets', flush=True)
        dump(args.root / 'execution.json', dict(runs=REPLICATES * len(conditions()),
            seconds=time.perf_counter() - start, workers=args.workers))
    else:
        if args.output is None:
            parser.error('--output required for analysis')
        analyze(args.root, args.output)


if __name__ == '__main__':
    main()
