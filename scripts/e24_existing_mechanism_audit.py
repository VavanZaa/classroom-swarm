"""Configuration-only audit of frozen A32/A33; adds no simulation mechanism."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import sys
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from classroom_swarm import promising_config as config
from classroom_swarm.effort_runtime import semantic
from classroom_swarm.v4_promising import simulate_promising
from classroom_swarm.promising_validation import validate_promising_log
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4 import V4Log

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import e23_promising_mechanisms as e23

ROOT = REPO / 'runs/E24-existing-mechanism-audit-r1'
PLAN = REPO / 'docs/experiments/E24-existing-mechanism-audit-plan.md'
REPLICATES = 4
DRAW_OFFSET = 41000
SETTINGS = {
    'kenya': [('observation_rate_1', 'teacher.observation_learning_rate', 1.),
              ('pretest_120', 'design.curriculum.pretest_items', 120),
              ('threshold_06', 'design.curriculum.mastery_threshold', .6),
              ('threshold_08', 'design.curriculum.mastery_threshold', .8)],
    'star': [('lower_cost', 'extensions.teacher_work.effort_cost', .0001)],
    'teacher_rewards': [('intrinsic_1', 'extensions.teacher_work.intrinsic_weight', 1.),
                        ('novel_contract', 'extensions.teacher_work.contract.forms', ['novel'])],
    'seating': [('helper_intrinsic_01', 'extensions.helper_contract.helper_intrinsic_value', .1),
                ('no_reasoning', 'design.shared_reasoning.enabled', False)],
    'ai': [('no_corrective_feedback', 'extensions.learning_process.corrective_feedback', False)],
}


def deep_audit(log):
    """Independently recover start-time prerequisites and released policy evidence."""
    if log.manifest['model'] != 'A33-v4.8-content-choice' or not log.manifest['design']['curriculum']['enabled']:
        return {'readiness': 0, 'choices': 0, 'pretests': 0}
    t = log.tables; p = TutoringParams(**log.manifest['params'])
    d = log.manifest['design']['curriculum']; teacher = log.manifest['teacher']
    n, count, levels = p.N, log.manifest['topic_count'], len(d['levels'])
    ids = log.manifest['extensions']['student_ids'] or list(range(n))
    k = np.zeros((n, count)); observed = np.full((n, count), teacher['observation_prior'])
    initial_keys = [(r['student'], r['topic']) for r in t['topic_initial']]
    assert len(set(initial_keys)) == n * count == len(initial_keys), 'incomplete initial skill ledger'
    for r in t['topic_initial']: k[r['student'], r['topic']] = r['knowledge']
    draws = PublicAIDraws(log.manifest['seed'], log.manifest['replicate'], n, p.items, p.exam_items)
    assert len(t['curriculum_pretest']) == n * count, 'missing pretest records'
    pretest_keys = set()
    for r in t['curriculum_pretest']:
        i, topic = r['student'], r['topic']; pretest_keys.add((i, topic))
        u = semantic(draws, 170, ids[i], topic, size=d['pretest_items'])
        assert np.allclose(u, json.loads(r['item_draws']), atol=0, rtol=0), 'changed pretest draws'
        score = float(np.mean(u < k[i, topic]))
        covered = semantic(draws, 162, ids[i], 0, topic) >= 1 - teacher['observation_coverage']
        noise = semantic(draws, 163, ids[i], 0, topic, normal=True)
        value = float(np.clip(score + teacher['observation_noise_std'] * noise, 0, 1)) if covered else None
        assert abs(score - r['score']) < 1e-12 and value == r['observed'], 'pretest evidence mismatch'
        if value is not None: observed[i, topic] = value
    assert len(pretest_keys) == n * count, 'duplicate pretest record'
    doses = Counter((r['homework'], r['start'], r['student'], r['topic']) for r in t['learning_doses'])
    readiness = Counter((r['homework'], r['start'], r['student'], r['topic']) for r in t['curriculum_readiness'])
    assert doses == readiness, 'missing or duplicate readiness records'
    updates = sorted(t['topic_learning'], key=lambda r: (r['homework'], r['tick']))
    pointer = 0
    for r in sorted(t['curriculum_readiness'], key=lambda r: (r['homework'], r['start'])):
        stamp = r['homework'], r['start']
        while pointer < len(updates) and (updates[pointer]['homework'], updates[pointer]['tick']) <= stamp:
            u = updates[pointer]; key = u['student'], u['topic']
            assert abs(k[key] - u['before']) < 1e-10, 'broken independent skill history'
            k[key] = u['after']; pointer += 1
        i, topic = r['student'], r['topic']; prerequisite = d['prerequisites'][topic % levels]
        value = 1. if prerequisite < 0 else float(k[i, topic // levels * levels + prerequisite])
        expected = 1. if prerequisite < 0 else float(np.clip((value - (d['mastery_threshold'] - d['readiness_width'])) / d['readiness_width'], 0, 1))
        assert prerequisite == r['prerequisite'] and abs(value - r['value']) < 1e-10 and abs(expected - r['readiness']) < 1e-10, 'readiness disagrees with start-time knowledge'
    assert len(t['curriculum_choices']) == p.H and {r['homework'] for r in t['curriculum_choices']} == set(range(1, p.H + 1)), 'missing curriculum choices'
    observations = sorted(t['teacher_observations'], key=lambda r: (r['homework'], r['tick']))
    pointer = 0
    for r in sorted(t['curriculum_choices'], key=lambda r: r['homework']):
        while pointer < len(observations) and (observations[pointer]['homework'], observations[pointer]['tick']) <= (r['homework'], 0):
            u = observations[pointer]; key = u['student'], u['topic']
            assert abs(observed[key] - u['estimate_before']) < 1e-10, 'broken released-observation history'
            if u['observed_score'] is not None and u['weight'] > 0:
                observed[key] += teacher['observation_learning_rate'] * u['weight'] * (u['observed_score'] - observed[key])
            assert abs(observed[key] - u['estimate_after']) < 1e-10, 'observer update mismatch'
            pointer += 1
        means = observed[:, r['domain'] * levels:(r['domain'] + 1) * levels].mean(axis=0)
        assert np.allclose(means, json.loads(r['observed_means']), atol=1e-10, rtol=0), 'curriculum uses unavailable or incorrect observations'
    return {'readiness': sum(readiness.values()), 'choices': p.H, 'pretests': n * count}


def build_jobs(rep):
    jobs = []
    for original in e23.build_jobs('confirmation', DRAW_OFFSET + rep - e23.PHASES['confirmation'][1]):
        if original['variant'] != 'A33' or original['profile'] != 'default' or original['case'] not in SETTINGS: continue
        for label, path, value in [('baseline', None, None)] + SETTINGS[original['case']]:
            j = deepcopy(original); j.update(cohort=rep, phase='audit', profile=label)
            j['condition'] = f"{j['case']}_{label}_{j['arm']}_s{j['section']}"
            j['resolved']['name'] = j['condition']
            if path:
                branch = j['resolved']; keys = path.split('.')
                for key in keys[:-1]: branch = branch[key]
                branch[keys[-1]] = value
            j['changed_parameter'] = path
            jobs.append(j)
    return jobs


def verify():
    lock = config.load_config(ROOT / 'design-lock.json')
    for name, digest in lock['sources'].items(): assert config.sha256(REPO / name) == digest, name
    for name, digest in lock['declarations'].items(): assert config.sha256(ROOT / name) == digest, name
    e23.verify(e23.ROOT)
    return lock


def prepare():
    assert not ROOT.exists(), 'choose a fresh audit identity'
    e23.verify(e23.ROOT)
    declarations = [build_jobs(rep) for rep in range(REPLICATES)]
    for jobs in declarations:
        for j in jobs:
            c = config.template(); c.update(seed=j['seed'], replicates=1, conditions=[j['resolved']])
            config.preflight(config.resolve_config(c))
    ROOT.mkdir(parents=True)
    for rep, jobs in enumerate(declarations): config.save_json(ROOT / f'cohort{rep:04d}.json', jobs)
    sources = sorted((REPO / 'src/classroom_swarm').glob('*.py')) + [Path(__file__), PLAN, REPO / 'tests/test_e24_mechanism_audit.py']
    config.save_json(ROOT / 'design-lock.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources={str(p.relative_to(REPO)).replace('\\', '/'): config.sha256(p) for p in sources},
        declarations={p.name: config.sha256(p) for p in sorted(ROOT.glob('cohort*.json'))},
        classrooms=sum(map(len, declarations)), cohorts=REPLICATES, settings=SETTINGS,
        status='configuration-only exploratory audit locked before outcomes; no model changes or field calibration'))
    print(f'Locked {sum(map(len, declarations))} audit classrooms.', flush=True)


def read(folder):
    complete = config.load_config(folder / 'complete.json')
    for name, digest in complete['hashes'].items(): assert config.sha256(folder / name) == digest, name
    log = V4Log(config.load_config(folder / 'manifest.json'))
    log.tables = {name[:-8]: pq.read_table(folder / name).to_pylist() for name in complete['hashes'] if name.endswith('.parquet')}
    validate_promising_log(log); counts = deep_audit(log)
    return log, counts, len(complete['hashes'])


def worker(rep):
    rows, inventory = [], []
    for j in config.load_config(ROOT / f'cohort{rep:04d}.json'):
        r = j['resolved']; p = TutoringParams(**r['params'])
        folder = ROOT / 'raw' / f'cohort{rep:04d}' / j['condition']
        if not (folder / 'complete.json').exists():
            assert not folder.exists(), 'partial audit output; retain and choose a new identity'
            log = simulate_promising(p, config.make_graph(r['network'], p.N, j['seed'], j['replicate']),
                PublicAIDraws(j['seed'], j['replicate'], p.N, p.items, p.exam_items), j['condition'],
                r['initial'], r['teacher'], r['mechanisms'], r['extensions'], r['design'])
            log.manifest['declared_job'] = j
            validate_promising_log(log); deep_audit(log)
            folder.mkdir(parents=True)
            config.save_json(folder / 'manifest.json', log.manifest)
            for name, values in log.tables.items(): pq.write_table(pa.Table.from_pylist(values), folder / f'{name}.parquet', compression='zstd')
            config.save_json(folder / 'complete.json', dict(hashes={p.name: config.sha256(p) for p in sorted(folder.iterdir())}))
        log, counts, hashes = read(folder)
        assert log.manifest['declared_job'] == j
        for group, ids in j['groups'].items():
            if not ids: continue
            row = dict(case=j['case'], profile=j['profile'], arm=j['arm'], group=group,
                       section=j['section'], cohort=rep, **e23.metrics(log, ids))
            helper = [x for x in log.tables['student_costs'] if x['activity'] == 'helper' and x['student'] in ids]
            row['helper_effortful_share'] = float(np.mean([x['effort'] > 0 for x in helper])) if helper else None
            row['foundation_lesson_share'] = float(np.mean([x['level'] == 0 for x in log.tables['curriculum_choices']]))
            rows.append(row)
        inventory.append(dict(condition=j['condition'], cohort=rep, hashes=hashes, checks=counts,
                              complete_sha256=config.sha256(folder / 'complete.json')))
    return rows, inventory


def run(workers):
    lock = verify(); assert not (ROOT / 'run-complete.json').exists(), 'audit already complete'
    rows, inventory = [], []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, rep): rep for rep in range(REPLICATES)}
        for future in as_completed(futures):
            r, i = future.result(); rows += r; inventory += i
            print(f'Audited cohort {futures[future] + 1}: {len(inventory)}/{lock["classrooms"]} classrooms.', flush=True)
    assert len(inventory) == lock['classrooms']
    config.save_json(ROOT / 'class-metrics.json', rows); config.save_json(ROOT / 'raw-inventory.json', inventory)
    config.save_json(ROOT / 'run-complete.json', dict(classrooms=len(inventory),
        file_hashes_verified=sum(x['hashes'] for x in inventory),
        independent_checks={k: sum(x['checks'][k] for x in inventory) for k in ('readiness', 'choices', 'pretests')},
        hashes={p: config.sha256(ROOT / p) for p in ('class-metrics.json', 'raw-inventory.json')},
        design_sha256=config.sha256(ROOT / 'design-lock.json')))
    verify()


def analyze():
    verify(); complete = config.load_config(ROOT / 'run-complete.json')
    for name, digest in complete['hashes'].items(): assert config.sha256(ROOT / name) == digest
    rows = config.load_config(ROOT / 'class-metrics.json'); grouped = defaultdict(list)
    exclude = {'case', 'profile', 'arm', 'group', 'section', 'cohort', 'students'}
    for r in rows: grouped[r['case'], r['profile'], r['arm'], r['group'], r['cohort']].append(r)
    cohorts = []
    for key, parts in sorted(grouped.items()):
        result = dict(zip(('case', 'profile', 'arm', 'group', 'cohort'), key)); result['students'] = sum(p['students'] for p in parts)
        for name in parts[0].keys() - exclude:
            available = [p for p in parts if p[name] is not None]
            result[name] = sum(p[name] * p['students'] for p in available) / sum(p['students'] for p in available) if available else None
        cohorts.append(result)
    by = {(r['case'], r['profile'], r['arm'], r['group'], r['cohort']): r for r in cohorts}
    effects = []
    pairs = {'kenya': [('tracked', 'mixed', 'low'), ('tracked', 'mixed', 'high')],
             'star': [('small', 'regular', 'all')], 'teacher_rewards': [('rewarded', 'unrewarded', 'all')],
             'seating': [('reward', 'cross', 'low'), ('reward', 'cross', 'high'), ('cross', 'random', 'low')],
             'ai': [('answer', 'none', 'all'), ('tutor', 'answer', 'all'), ('tutor', 'none', 'all')]}
    metrics = ['knowledge_gain', 'core_potential', 'familiar_potential', 'novel_potential', 'familiar_participation',
               'guidance_count', 'followup_count', 'group_coaching_count', 'foundation_lesson_share', 'helper_effortful_share']
    for case, contrasts in pairs.items():
        for profile in ['baseline'] + [s[0] for s in SETTINGS[case]]:
            for a, b, group in contrasts:
                for metric in metrics:
                    values, changes = [], []
                    for rep in range(REPLICATES):
                        x, y = by[case, profile, a, group, rep], by[case, profile, b, group, rep]
                        if x.get(metric) is None or y.get(metric) is None: continue
                        v = x[metric] - y[metric]; values.append(v)
                        bx, by_ = by[case, 'baseline', a, group, rep], by[case, 'baseline', b, group, rep]
                        if bx.get(metric) is not None and by_.get(metric) is not None: changes.append(v - (bx[metric] - by_[metric]))
                    if values:
                        effects.append(dict(case=case, profile=profile, a=a, b=b, group=group, metric=metric,
                            mean=float(np.mean(values)), cohort_min=min(values), cohort_max=max(values), cohorts=len(values),
                            change_from_baseline=float(np.mean(changes)) if changes else None))
    config.save_json(ROOT / 'summary.json', dict(cohort_metrics=cohorts, effects=effects,
        limitation='Four exploratory paired cohorts; ranges describe these cohorts and are not confidence intervals or field validation.'))
    print(json.dumps(complete, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run', 'analyze']); parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'prepare': prepare()
    elif args.command == 'run': run(args.workers)
    else: analyze()
