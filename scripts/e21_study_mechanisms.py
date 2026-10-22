"""Frozen study-case comparisons, paired changes, historical replay and safe resume."""
from __future__ import annotations
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import sys, json

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src')); sys.path.insert(0, str(REPO / 'scripts'))
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from classroom_swarm import mechanism_config as config
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_mechanisms import simulate_mechanisms, validate_mechanism_log
import e19_teacher_studies as e19
import e20_mechanism_diagnostic as e20

SEED, REPLICATES, BOOTSTRAPS, BOOTSTRAP_SEED = 10072101, 24, 5000, 10072199
ROOT = REPO / 'runs/E21-study-mechanisms-r1'
METRICS = ('exam', 'exam_active', 'homework', 'knowledge_gain', 'copied', 'ai_use',
           'guided_sessions', 'helper_sessions', 'practice_ticks', 'teacher_attention',
           'teacher_effort', 'mandatory_work', 'effective_skill', 'instruction_difficulty',
           'instruction_count', 'teacher_gain_active', 'helper_gain_active', 'peer_updates',
           'peer_pending', 'grade_return_fraction')


def convert(old, condition, activity=None):
    c = config.template()
    for key in ('params', 'initial', 'network', 'teacher'):
        c[key].update(deepcopy(old.get(key, {})))
    if activity: c['params']['tutoring_activity'] = activity
    c['conditions'] = [deepcopy(condition)]
    return c


def student_profiles(legacy=False):
    result = [dict(name='reference', mechanisms={})]
    if legacy: result.append(dict(name='bridge', activity='joint_practice', mechanisms={}))
    result += [dict(name='topics', mechanisms={'topics': {'enabled': True}}),
               dict(name='peer_observation', mechanisms={'peer_observation': {'enabled': True}}),
               dict(name='combined', mechanisms={'topics': {'enabled': True}, 'peer_observation': {'enabled': True}})]
    return result


def teacher_profiles(kenya=False):
    result = [dict(name='reference', mechanisms={}),
              dict(name='topics', mechanisms={'topics': {'enabled': True}}),
              dict(name='linear_incentives', mechanisms={'incentives': {'enabled': True}}),
              dict(name='convex_incentives', mechanisms={'incentives': {'enabled': True, 'reward_power': 2.}}),
              dict(name='workload', mechanisms={'workload': {'enabled': True}}),
              dict(name='peer_observation', mechanisms={'peer_observation': {'enabled': True}})]
    all_on = {b: {'enabled': True} for b in ('incentives', 'workload', 'topics', 'peer_observation')}
    result.append(dict(name='combined', mechanisms=deepcopy(all_on)))
    for b in ('incentives', 'workload'):
        patch = deepcopy(all_on); patch[b]['enabled'] = False
        result.append(dict(name='combined_without_' + b, mechanisms=patch))
    result += [dict(name='grading_reference', teacher={'grading_ticks_per_student': 1}, mechanisms={}),
               dict(name='grading_combined', teacher={'grading_ticks_per_student': 1}, mechanisms=deepcopy(all_on), matched='grading_reference'),
               dict(name='automated_combined', teacher={'grading_ticks_per_student': 1, 'grading_automation': 1.}, mechanisms=deepcopy(all_on), matched='grading_reference')]
    if kenya:
        result += [dict(name='resourced_reference', teacher={'time_budget': 6}, mechanisms={}),
                   dict(name='resourced_combined', teacher={'time_budget': 6}, mechanisms=deepcopy(all_on), matched='resourced_reference'),
                   dict(name='peer_context', peers=True, mechanisms={}),
                   dict(name='peer_combined', peers=True, mechanisms=deepcopy(all_on), matched='peer_context')]
    return result


def cases():
    """Retrieve fixed earlier protocols, not outcomes or a new setup search."""
    result = {}
    selection = e19.selected(REPO / 'runs/E19-teacher-study-r1')
    for case, offset in [('star', 100), ('kenya', 200)]:
        c = e19.base_config(case)
        patch = e19.resolve_profile(case, selection[case]['profile'])
        c['params'].update(patch['params']); c['teacher'].update(patch['teacher'])
        c = convert(c, dict(name='reference', params={}, initial={}, network={}, teacher={}))
        result[case] = dict(offset=offset, kind=case, configs=[c], profiles=teacher_profiles(case == 'kenya'),
                            baseline='reference', inherited_profile=selection[case]['profile'],
                            population=patch['population'], groups=['all', 'low', 'high'])
    lab = config.load_config(REPO / 'runs/E17-tutoring-robustness-r1/confirmation.json')
    for case, suffix, offset in [('lab_repeated', 'reference', 300), ('lab_single', 'single_voluntary', 400)]:
        chosen = [c for c in lab['conditions'] if c['name'] in {f'{a}_{suffix}' for a in ('mixed', 'tracked', 'solo')}]
        result[case] = dict(offset=offset, kind='student', configs=[convert(lab, c) for c in chosen],
                            arms=[c['name'].split('_')[0] for c in chosen], profiles=student_profiles(),
                            baseline='reference', groups=['all', 'low', 'high'])
    old = config.load_config(REPO / 'runs/E14/ai_and_spread.json')
    chosen = [c for c in old['conditions'] if c['name'] in {'middle_none', 'middle_answer', 'middle_tutor'}]
    result['ai'] = dict(offset=500, kind='student', configs=[convert(old, c, 'legacy_hint') for c in chosen],
                        arms=[c['name'].split('_')[1] for c in chosen], profiles=student_profiles(True),
                        baseline='bridge', groups=['all'])
    old = config.load_config(REPO / 'runs/E14/grouping.json')
    chosen = [c for c in old['conditions'] if c['name'] in {'cross_pairs', 'random_pairs'}]
    result['seating'] = dict(offset=600, kind='student', configs=[convert(old, c, 'legacy_hint') for c in chosen],
                             arms=[c['name'].split('_')[0] for c in chosen], profiles=student_profiles(True),
                             baseline='bridge', groups=['all', 'low', 'high'])
    old = config.load_config(REPO / 'runs/E16-tutoring-r1/validation_composition.json')
    for case, suffix, offset in [('composition', 'joint', 700), ('composition_copy', 'joint_copy', 800)]:
        chosen = [c for c in old['conditions'] if c['name'] in {f'low_{suffix}', f'high_{suffix}'}]
        result[case] = dict(offset=offset, kind='student', configs=[convert(old, c) for c in chosen],
                            arms=[c['name'].split('_')[0] for c in chosen], profiles=student_profiles(),
                            baseline='reference', groups=['focal'])
    c = config.template()
    c['params'].update(N=30, H=12, ticks=18, items=12, exam_items=100, exam_every=1,
                       feedback_delay=0, allow_answer=False, ai_mode='none', tutoring_activity='joint_practice')
    c['network'].update(family='ER', d_bar=6)
    c['teacher'].update(enabled=True, time_budget=8, admin_ticks=0, grading_ticks_per_student=0,
                        actions=['instruction', 'guidance'], observation_sources=['exam'])
    c['initial']['learning_efficiency'] = dict(kind='constant', value=.0584)
    c['initial']['effort_aversion'] = dict(kind='constant', value=.15)
    c['mechanisms']['incentives']['enabled'] = True
    no = deepcopy(c); no['mechanisms']['incentives']['reward_strength'] = 0.
    result['teacher_rewards'] = dict(offset=900, kind='student', configs=[no, c], arms=['unrewarded', 'rewarded'],
                                    profiles=[dict(name='reference', mechanisms={}),
                                              dict(name='workload', mechanisms={'workload': {'enabled': True}}),
                                              dict(name='topics', mechanisms={'topics': {'enabled': True}}),
                                              dict(name='combined', mechanisms={'workload': {'enabled': True}, 'topics': {'enabled': True}, 'peer_observation': {'enabled': True}})],
                                    baseline='reference', groups=['all'])
    return result


def comparisons():
    return [
        dict(case='star', a='small', b='regular', group='all', metric='exam', target='positive', primary=True),
        *[dict(case='kenya', a='tracked', b='mixed', group=g, metric='exam', target='positive', primary=True) for g in ('low', 'high')],
        *[dict(case=c, a='mixed', b=b, group='low', metric='exam_active' if c == 'lab_single' else 'exam', target='positive', primary=True)
          for c in ('lab_repeated', 'lab_single') for b in ('tracked', 'solo')],
        *[dict(case='ai', a=a, b=b, group='all', metric='exam_active', target=t, primary=True)
          for a, b, t in [('answer', 'none', 'negative'), ('tutor', 'answer', 'positive'), ('tutor', 'none', 'near_zero')]],
        dict(case='seating', a='cross', b='random', group='low', metric='exam', target='near_zero', primary=True),
        *[dict(case=c, a='high', b='low', group='focal', metric='exam', target='context_dependent', primary=False) for c in ('composition', 'composition_copy')],
        dict(case='teacher_rewards', a='rewarded', b='unrewarded', group='all', metric='exam', target='mechanism_probe', primary=False)]


def common_settings(c, case):
    h = config.resolve_config(c)['conditions'][0]['params']['H']; count = 4 if case == 'ai' else 2
    c['mechanisms']['topics'].update(names=[f'topic_{i}' for i in range(count)],
        transfer=[[1. if i == j else .2 for j in range(count)] for i in range(count)], helper_consolidation_rate=.2)
    c['mechanisms']['workload'].update(preparation_ticks=1, topic_switch_ticks=1,
        admin_bursts=[int((h0 + 1) % 4 == 0) for h0 in range(h)], fatigue_per_tick=.02, recovery=.5, quality_loss=.5)
    c['mechanisms']['peer_observation'].update(sensitivity=.7, specificity=.7, delay_ticks=4)
    c['mechanisms']['incentives']['intrinsic_weight'] = .2


def build_jobs(declarations, rep):
    jobs = []
    for case, definition in declarations.items():
        seed = SEED + definition['offset']
        if definition['kind'] in {'star', 'kenya'}:
            choices = []
            for n in ([15, 24] if case == 'star' else [42]):
                pop = e19.cohort(case, seed, rep, n=n, mean=definition['population'].get('mean', .5))
                arms = [('small' if n == 15 else 'regular', pop['mixed'])] if case == 'star' else [('mixed', pop['mixed']), ('tracked', pop['tracked'])]
                for arm, sections in arms:
                    for section, ids in enumerate(sections):
                        c = deepcopy(definition['configs'][0]); c['params']['N'] = n
                        c['teacher'].update(identity=f'{case}-section-{section}', observation_prior=float(np.mean([pop['observed_baseline'][i] for i in ids])))
                        c['initial']['knowledge'] = dict(kind='values', values=[pop['knowledge'][i] for i in ids])
                        groups = {g: [i for i, node in enumerate(ids) if node in set(pop['student_ids'] if g == 'all' else pop[g])] for g in definition['groups']}
                        choices.append((arm, section, c, groups, ids, [pop['observed_baseline'][i] for i in ids]))
        else:
            choices = []
            for arm, source in zip(definition['arms'], definition['configs']):
                c = deepcopy(source); resolved = config.resolve_config(c)['conditions'][0]
                n = resolved['params']['N']
                groups = {'all': list(range(n))}
                if 'low' in definition['groups']:
                    groups.update(low=list(range(n // 2)), high=list(range(n // 2, n)))
                if 'focal' in definition['groups']: groups = {'focal': list(range(15))}
                choices.append((arm, 0, c, groups, list(range(n)), []))
        for arm, section, base, groups, ids, scores in choices:
            for profile in definition['profiles']:
                c = deepcopy(base); c.update(experiment_id='E21_' + case, seed=seed + section, replicates=1)
                name = f"{case}_{profile['name']}_{arm}_s{section}"
                c['conditions'][0]['name'] = name
                common_settings(c, case)
                if definition.get('baseline') == 'bridge' and profile['name'] != 'reference':
                    c['params']['tutoring_activity'] = 'joint_practice'
                c['params'].update(profile.get('params', {})); c['teacher'].update(profile.get('teacher', {}))
                if profile.get('peers'):
                    c['params']['allow_hint'] = True; c['network'].update(family='ER', edges=None, d_bar=6)
                for branch, patch in profile.get('mechanisms', {}).items(): c['mechanisms'][branch].update(patch)
                resolved = config.resolve_config(c)['conditions'][0]
                jobs.append(dict(case=case, profile=profile['name'], arm=arm, section=section,
                                 condition=name, seed=c['seed'], replicate=rep, resolved=resolved,
                                 groups=groups, global_ids=ids, baseline_scores=scores,
                                 matched=profile.get('matched', definition['baseline'])))
    return jobs


def replay_paths():
    paths = [REPO / 'runs/E19-teacher-study-r1/confirmation/raw/rep0000/star_guidance_03_longer_day_small_s0',
             REPO / 'runs/E19-teacher-study-r1/confirmation/raw/rep0000/kenya_population_mean_045_tracked_s0']
    paths += [REPO / 'runs/E17-tutoring-robustness-r1/confirmation/raw/rep0000' / n for n in ('mixed_reference', 'mixed_single_voluntary')]
    paths += [REPO / 'runs/E14/ai_and_spread/raw/rep0000' / f'middle_{a}' for a in ('none', 'answer', 'tutor')]
    paths += [REPO / 'runs/E14/grouping/raw/rep0000' / n for n in ('cross_pairs', 'random_pairs')]
    paths += [REPO / 'runs/E16-tutoring-r1/validation_composition/raw/rep0000' / n for n in ('low_joint', 'high_joint', 'low_joint_copy', 'high_joint_copy')]
    return paths


def historical():
    e20.verify(REPO / 'runs/E20-mechanisms-r1')
    for name, digest in config.load_config(REPO / 'docs/experiments/E20-mechanism-results.sources.json')['sources'].items():
        assert config.sha256(REPO / name) == digest, name
    return e20.historical()


def prepare(root):
    if root.exists(): raise ValueError('Use a new E21 identity')
    historical(); definitions = cases(); all_jobs = [build_jobs(definitions, rep) for rep in range(REPLICATES)]
    for jobs in all_jobs:
        for j in jobs:
            c = config.template(); c.update(seed=j['seed'], replicates=1, conditions=[j['resolved']])
            config.preflight(config.resolve_config(c))
    root.mkdir(parents=True); config.save_json(root / 'cases.json', definitions)
    config.save_json(root / 'comparisons.json', comparisons())
    sources = sorted((REPO / 'src/classroom_swarm').glob('*.py')) + [Path(__file__),
        REPO / 'scripts/e19_teacher_studies.py', REPO / 'scripts/e20_mechanism_diagnostic.py',
        REPO / 'tests/test_e21_study_mechanisms.py', REPO / 'docs/experiments/E21-study-mechanism-plan.md']
    jobs_hashes = {}
    for rep, jobs in enumerate(all_jobs):
        path = root / f'rep{rep:04d}.json'; config.save_json(path, jobs); jobs_hashes[path.name] = config.sha256(path)
    replays = [{'path': str(p.relative_to(REPO)).replace('\\', '/'), 'complete_sha256': config.sha256(p / 'complete.json')} for p in replay_paths()]
    assert len(replays) == 13
    config.save_json(root / 'design-lock.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources={str(p.relative_to(REPO)).replace('\\', '/'): config.sha256(p) for p in sources},
        declarations={p: config.sha256(root / p) for p in ('cases.json', 'comparisons.json')},
        job_files=jobs_hashes, classrooms=sum(map(len, all_jobs)), replicates=REPLICATES, seed=SEED,
        replays=replays, bootstrap_resamples=BOOTSTRAPS, bootstrap_seed=BOOTSTRAP_SEED,
        primary_family_size=sum(x['primary'] for x in comparisons()), historical_entries_verified=historical(),
        identities=['All-off exact historical continuity.', 'Positive direct gains and fatigue skill penalty are encoded.',
                    'Finite teacher resources can block instruction.', 'No student helper financial reward exists.',
                    'Scheduled tutoring frequency is fixed.', 'Payments grant no knowledge.'],
        interpretation='Known-direction study-informed sensitivity, no fitting or human calibration. All declared setups retained.'))
    print(f'Locked {sum(map(len, all_jobs))} classrooms and 13 historical replays; no selection or tuning.', flush=True)


def verify(root):
    lock = config.load_config(root / 'design-lock.json')
    for name, digest in lock['sources'].items(): assert config.sha256(REPO / name) == digest, name
    for name, digest in {**lock['declarations'], **lock['job_files']}.items(): assert config.sha256(root / name) == digest, name
    for r in lock['replays']: assert config.sha256(REPO / r['path'] / 'complete.json') == r['complete_sha256']
    historical(); return lock


def read_raw(folder):
    complete = config.load_config(folder / 'complete.json')
    for name, digest in complete['hashes'].items(): assert config.sha256(folder / name) == digest, name
    log = V4Log(config.load_config(folder / 'manifest.json'))
    for name in complete['hashes']:
        if name.endswith('.parquet'): log.tables[name[:-8]] = pq.read_table(folder / name).to_pylist()
    return log


def replay(root):
    lock = verify(root); results = []
    if (root / 'historical-replay.json').exists(): raise ValueError('Replay evidence already exists')
    for item in lock['replays']:
        old = read_raw(REPO / item['path']); m = old.manifest
        p = TutoringParams(**m['params'])
        if m['model'].startswith('A28'): p = TutoringParams(**m['params'], tutoring_activity='legacy_hint')
        graph = config.make_graph(m['network'], p.N, m['seed'], m['replicate'])
        new = simulate_mechanisms(p, graph, PublicAIDraws(m['seed'], m['replicate'], p.N, p.items, p.exam_items),
                                 condition=m['condition'], initial=m['initial'], teacher=m.get('teacher'))
        validate_mechanism_log(new)
        for table, rows in old.tables.items():
            assert [r for r in rows if r] == [r for r in new.tables[table] if r], (item['path'], table)
        results.append(dict(**item, raw_tables_compared=len(old.tables), result='exact parity'))
        print('Replayed ' + item['path'], flush=True)
    config.save_json(root / 'historical-replay.json', dict(results=results, all_passed=True, design_sha256=config.sha256(root / 'design-lock.json')))


def metrics(log, ids):
    ids = set(ids); m = log.manifest; h = m['params']['H']; n = len(ids)
    final = [r for r in log.tables['students'] if r['homework'] == h and r['student'] in ids]
    exams = [r for r in log.tables['exams'] if r['homework'] == h and r['student'] in ids]
    assert len(final) == len(exams) == n
    topics = {r['student']: r.get('topic', 0) for r in final}
    active = [r['score'] for r in log.tables.get('exam_topics', []) if r['homework'] == h and r['student'] in ids and r['topic'] == topics[r['student']]]
    events = [r for r in log.tables['events'] if r['student'] in ids]
    initial = {r['student']: r['K0'] for r in log.tables['traits']}
    actions = [r for r in log.tables.get('teacher_actions', []) if r['homework'] <= h]
    lessons = [r for r in actions if r['action'] == 'instruction']
    runtime = [r for r in log.tables.get('teacher_runtime', []) if r['homework'] <= h]
    components = [r for r in log.tables.get('learning_components', []) if r['student'] in ids]
    content = log.tables.get('tutoring_content', [])
    skills = [json.loads(r['settings'])['teaching_skill'] for r in runtime]
    return dict(students=n, exam=100 * float(np.mean([r['score'] for r in exams])),
        exam_active=100 * float(np.mean(active if active else [r['score'] for r in exams])),
        homework=100 * float(np.mean([r['grade'] for r in final])),
        knowledge_gain=100 * float(np.mean([r['K'] - initial[r['student']] for r in final])),
        copied=100 * float(np.mean([r['copied'] for r in final])),
        ai_use=sum(r['student'] in ids for r in log.tables['ai_uses']) / (n * h),
        guided_sessions=sum(r['requester'] in ids for r in content) / (n * h),
        helper_sessions=sum(r['provider'] in ids for r in content) / (n * h),
        practice_ticks=sum(r['end'] - r['start'] for r in events if r['action'] in {'attempt', 'guided_practice', 'scheduled_practice'}) / (n * h),
        teacher_attention=sum(r['end'] - r['start'] for r in events if r['action'].startswith('teacher_') and r['action'] != 'teacher_phase_wait') / (n * h),
        teacher_effort=sum(r['cost'] for r in actions) / h,
        mandatory_work=sum(r['cost'] for r in log.tables.get('teacher_workload', []) if r['homework'] <= h) / h,
        effective_skill=float(np.mean(skills)) if skills else m.get('teacher', {}).get('teaching_skill', 0.),
        instruction_difficulty=float(np.mean([r['difficulty'] for r in lessons])) if lessons else 0.,
        instruction_count=len(lessons) / h,
        teacher_gain_active=100 * sum(r.get('teacher_gain', 0.) for r in components) / n,
        helper_gain_active=100 * sum(r['helper_gain'] for r in components) / n,
        peer_updates=sum(r['requester'] in ids for r in log.tables.get('quality_feedback', [])) / (n * h),
        peer_pending=sum(r['requester'] in ids for r in log.tables.get('peer_signal_backlog', [])) / (n * h),
        grade_return_fraction=sum(r['student'] in ids for r in log.tables['homework_feedback']) / (n * h))


def aggregate(parts):
    n = sum(r['students'] for r in parts)
    return {'students': n, **{key: sum(r[key] * r['students'] for r in parts) / n for key in METRICS}}


def check_job(log, job, folder):
    assert config.load_config(folder / 'declared_class.json') == job
    m = log.manifest
    assert (m['seed'], m['replicate'], m['condition']) == (job['seed'], job['replicate'], job['condition'])
    assert m['experiment_groups'] == job['groups'] and m['cohort_global_ids'] == job['global_ids']
    assert m['cohort_baseline_scores'] == job['baseline_scores']
    for key, value in job['resolved']['params'].items():
        if key in m['params']: assert m['params'][key] == value
    if job['resolved']['teacher']['enabled']: assert m['teacher'] == job['resolved']['teacher']
    if any(v['enabled'] for v in job['resolved']['mechanisms'].values()): assert m['mechanisms'] == job['resolved']['mechanisms']


def worker(root_string, rep):
    root = Path(root_string); jobs = config.load_config(root / f'rep{rep:04d}.json')
    rows, inventory, graphs, new, reused = [], [], {}, 0, 0
    for job in jobs:
        r = job['resolved']; p = TutoringParams(**r['params'])
        folder = root / 'raw' / f'rep{rep:04d}' / job['condition']
        if (folder / 'complete.json').exists(): reused += 1
        else:
            if folder.exists():
                target = folder.with_name(folder.name + '-partial-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
                assert folder.resolve().is_relative_to(root.resolve()) and target.resolve().is_relative_to(root.resolve())
                folder.rename(target)
            key = (job['seed'], p.N, json.dumps(r['network'], sort_keys=True))
            if key not in graphs: graphs[key] = config.make_graph(r['network'], p.N, job['seed'], rep)
            log = simulate_mechanisms(p, graphs[key], PublicAIDraws(job['seed'], rep, p.N, p.items, p.exam_items),
                                     condition=job['condition'], initial=r['initial'], teacher=r['teacher'], mechanisms=r['mechanisms'])
            log.manifest.update(experiment_case=job['case'], mechanism_profile=job['profile'], assignment=job['arm'],
                                section=job['section'], experiment_groups=job['groups'], cohort_global_ids=job['global_ids'],
                                cohort_baseline_scores=job['baseline_scores'], network=r['network'])
            validate_mechanism_log(log); folder.mkdir(parents=True)
            config.save_json(folder / 'declared_class.json', job); config.save_json(folder / 'manifest.json', log.manifest)
            for name, values in log.tables.items(): pq.write_table(pa.Table.from_pylist(values), folder / f'{name}.parquet', compression='zstd')
            config.save_json(folder / 'complete.json', {'hashes': {f.name: config.sha256(f) for f in sorted(folder.iterdir())}})
            new += 1
        # Saved-file replay, including newly written runs: truth is the recorded data.
        log = read_raw(folder); check_job(log, job, folder); validate_mechanism_log(log)
        for group, ids in job['groups'].items():
            if ids: rows.append(dict(case=job['case'], profile=job['profile'], arm=job['arm'], group=group,
                                     section=job['section'], replicate=rep, **metrics(log, ids)))
        inventory.append(dict(condition=job['condition'], case=job['case'], profile=job['profile'], arm=job['arm'],
                              section=job['section'], replicate=rep, graph_hash=log.manifest['graph_hash'],
                              complete_sha256=config.sha256(folder / 'complete.json')))
    return rows, inventory, new, reused


def run(root, workers=4):
    lock = verify(root)
    assert config.load_config(root / 'historical-replay.json')['all_passed']
    if (root / 'run-complete.json').exists(): raise ValueError('Execution complete; analyze rather than rerun')
    rows, inventory, new, reused = [], [], 0, 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, str(root), rep): rep for rep in range(REPLICATES)}
        for future in as_completed(futures):
            r, i, n, u = future.result(); rows.extend(r); inventory.extend(i); new += n; reused += u
            print(f"Audited replicate {futures[future]+1}/{REPLICATES}: {len(inventory)}/{lock['classrooms']} classrooms; new={new}, reused={reused}", flush=True)
    assert len(inventory) == lock['classrooms']
    rows.sort(key=lambda r: (r['case'], r['profile'], r['arm'], r['group'], r['replicate'], r['section']))
    inventory.sort(key=lambda r: (r['replicate'], r['condition']))
    config.save_json(root / 'class-metrics.json', rows); config.save_json(root / 'raw-inventory.json', inventory)
    config.save_json(root / 'run-complete.json', dict(classrooms=len(inventory), saved_raw_audits='all passed',
        design_sha256=config.sha256(root / 'design-lock.json'),
        hashes={p: config.sha256(root / p) for p in ('class-metrics.json', 'raw-inventory.json', 'historical-replay.json')},
        new=new, reused=reused, execution_workers=workers))
    verify(root)


def paired(delta, alpha=.05):
    values = np.asarray(delta, float)
    assert len(values) == REPLICATES and np.all(np.isfinite(values))
    values[np.abs(values) < 1e-10] = 0.
    indices = np.random.default_rng(BOOTSTRAP_SEED).integers(0, REPLICATES, (BOOTSTRAPS, REPLICATES))
    boot = values[indices].mean(axis=1); lo, hi = np.quantile(boot, [alpha / 2, 1-alpha / 2])
    return dict(effect=float(values.mean()), lo95=float(lo), hi95=float(hi), replicates=REPLICATES)


def analyze(root):
    lock = verify(root); complete = config.load_config(root / 'run-complete.json')
    for name, digest in complete['hashes'].items(): assert config.sha256(root / name) == digest
    assert complete['design_sha256'] == config.sha256(root / 'design-lock.json')
    inventory = config.load_config(root / 'raw-inventory.json')
    for r in inventory: assert config.sha256(root / 'raw' / f"rep{r['replicate']:04d}" / r['condition'] / 'complete.json') == r['complete_sha256']
    collected = defaultdict(list)
    for r in config.load_config(root / 'class-metrics.json'):
        collected[(r['case'], r['profile'], r['arm'], r['group'], r['replicate'])].append(r)
    by = {key: aggregate(parts) for key, parts in collected.items()}; effects, changes = [], []
    definitions = config.load_config(root / 'cases.json')
    for spec in config.load_config(root / 'comparisons.json'):
        case = spec['case']
        for profile in definitions[case]['profiles']:
            name = profile['name']; matched = profile.get('matched', definitions[case]['baseline'])
            for metric in METRICS:
                def values(label):
                    return np.array([by[(case, label, spec['a'], spec['group'], rep)][metric] - by[(case, label, spec['b'], spec['group'], rep)][metric] for rep in range(REPLICATES)])
                delta = values(name)
                identity = {k: spec[k] for k in ('case', 'a', 'b', 'group', 'target', 'primary')}
                identity.update(profile=name, matched=matched, metric=metric, headline_metric=spec['metric'])
                effects.append(dict(**identity, **paired(delta)))
                change = delta - values(matched)
                adjusted = paired(change, .05 / lock['primary_family_size']) if name == 'combined' and spec['primary'] and metric == spec['metric'] else None
                changes.append(dict(**identity, **paired(change), simultaneous_lo95=adjusted['lo95'] if adjusted else None,
                                    simultaneous_hi95=adjusted['hi95'] if adjusted else None))
    out = root / 'derived'
    if out.exists(): raise ValueError('Preserve existing derived analysis')
    out.mkdir(); config.save_json(out / 'school-metrics.json', [dict(case=k[0], profile=k[1], arm=k[2], group=k[3], replicate=k[4], **v) for k, v in sorted(by.items())])
    config.save_json(out / 'effects.json', effects); config.save_json(out / 'changes.json', changes)
    config.save_json(out / 'analysis-manifest.json', dict(raw_audits='all passed', classrooms=len(inventory),
        design_sha256=config.sha256(root / 'design-lock.json'), execution_sha256=config.sha256(root / 'run-complete.json'),
        hashes={p.name: config.sha256(p) for p in sorted(out.iterdir())},
        bootstrap_resamples=BOOTSTRAPS, bootstrap_seed=BOOTSTRAP_SEED, primary_family_size=lock['primary_family_size']))
    for r in effects:
        if r['profile'] in {'reference', 'bridge', 'combined'} and r['metric'] == r['headline_metric']:
            print(f"{r['case']}/{r['profile']}/{r['group']}/{r['a']}-{r['b']}: {r['effect']:+.3f} [{r['lo95']:+.3f}, {r['hi95']:+.3f}]", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'replay', 'run', 'analyze', 'verify'])
    parser.add_argument('--root', type=Path, default=ROOT); parser.add_argument('--workers', type=int, default=4)
    a = parser.parse_args()
    if a.command == 'prepare': prepare(a.root)
    elif a.command == 'replay': replay(a.root)
    elif a.command == 'run': run(a.root, a.workers)
    elif a.command == 'analyze': analyze(a.root)
    else: print('Verified E21 and historical source locks.', flush=True); verify(a.root)


if __name__ == '__main__': main()
