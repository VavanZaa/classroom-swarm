"""E21 checks cohort pairing, protocol bridges, aggregation and execution integrity."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import numpy as np
import pytest
from scripts import e21_study_mechanisms as e


@pytest.fixture(scope='module')
def jobs():
    return e.build_jobs(e.cases(), 0)


def test_fixed_design_covers_previous_cases_and_eleven_primary_contrasts(jobs):
    assert len(jobs) == 161
    assert set(j['case'] for j in jobs) == {'star', 'kenya', 'lab_repeated', 'lab_single', 'ai', 'seating', 'composition', 'composition_copy', 'teacher_rewards'}
    assert sum(s['primary'] for s in e.comparisons()) == 11
    assert len(e.replay_paths()) == 13


def test_profiles_preserve_assignment_students_and_semantic_draws(jobs):
    for j in jobs:
        same = [x for x in jobs if (x['case'], x['arm'], x['section']) == (j['case'], j['arm'], j['section'])]
        assert len({x['seed'] for x in same}) == 1
        assert all(x['global_ids'] == j['global_ids'] and x['groups'] == j['groups'] for x in same)
        assert all(x['resolved']['initial']['knowledge'] == j['resolved']['initial']['knowledge'] for x in same)
    k = [x for x in jobs if x['case'] == 'kenya' and x['profile'] == 'reference']
    for arm in ('tracked', 'mixed'):
        parts = [x for x in k if x['arm'] == arm]
        assert sorted(i for x in parts for i in x['global_ids']) == list(range(84))
    lows = [set(x['global_ids'][i] for i in x['groups']['low']) for x in k if x['arm'] == 'tracked']
    assert len(set.union(*lows)) == 42


def test_protocol_bridge_is_separate_from_new_features(jobs):
    for case in ('ai', 'seating'):
        reference = next(x for x in jobs if x['case'] == case and x['profile'] == 'reference')
        bridge = next(x for x in jobs if x['case'] == case and x['profile'] == 'bridge' and x['arm'] == reference['arm'])
        assert reference['resolved']['params']['tutoring_activity'] == 'legacy_hint'
        assert bridge['resolved']['params']['tutoring_activity'] == 'joint_practice'
        assert not any(v['enabled'] for v in bridge['resolved']['mechanisms'].values())
        diff = e.config.differences(reference['resolved'], bridge['resolved'])
        assert set(diff) == {'name', 'params.tutoring_activity'}


def test_single_session_and_ai_measurement_scopes_are_declared(jobs):
    single = [j for j in jobs if j['case'] == 'lab_single']
    assert all(j['resolved']['params']['H'] == 1 for j in single)
    assert all(len(j['resolved']['mechanisms']['workload']['admin_bursts']) == 1 for j in single)
    ai = next(j for j in jobs if j['case'] == 'ai' and j['profile'] == 'topics')
    assert len(ai['resolved']['mechanisms']['topics']['names']) == ai['resolved']['params']['H'] == 4
    assert all(s['metric'] == 'exam_active' for s in e.comparisons() if s['case'] in {'ai', 'lab_single'})


def test_teacher_resources_do_not_change_with_class_size_or_assignment(jobs):
    for case in ('star', 'kenya'):
        for profile in {j['profile'] for j in jobs if j['case'] == case}:
            rows = [j for j in jobs if j['case'] == case and j['profile'] == profile]
            assert len({j['resolved']['teacher']['time_budget'] for j in rows}) == 1
            assert len({j['resolved']['teacher']['grading_ticks_per_student'] for j in rows}) == 1
    assert next(j for j in jobs if j['case'] == 'kenya' and j['profile'] == 'resourced_combined')['matched'] == 'resourced_reference'
    assert next(j for j in jobs if j['case'] == 'kenya' and j['profile'] == 'peer_combined')['matched'] == 'peer_context'
    assert next(j for j in jobs if j['case'] == 'star' and j['profile'] == 'grading_combined')['matched'] == 'grading_reference'


def test_focal_composition_states_remain_fixed_and_reward_probe_keeps_intrinsic(jobs):
    for case in ('composition', 'composition_copy'):
        rows = [j for j in jobs if j['case'] == case]
        assert all(j['groups'] == {'focal': list(range(15))} for j in rows)
        assert all(j['resolved']['initial']['knowledge']['values'][:15] == [.35] * 15 for j in rows)
    rewards = [j for j in jobs if j['case'] == 'teacher_rewards' and j['profile'] == 'reference']
    assert {j['resolved']['mechanisms']['incentives']['reward_strength'] for j in rewards} == {0., 1.}
    assert all(j['resolved']['mechanisms']['incentives']['intrinsic_weight'] == .2 for j in rewards)


def test_school_aggregation_uses_students_not_class_count():
    parts = [dict(students=1, **{k: 0. for k in e.METRICS}), dict(students=3, **{k: 4. for k in e.METRICS})]
    assert e.aggregate(parts) == dict(students=4, **{k: 3. for k in e.METRICS})


def test_paired_changes_cancel_common_variation_and_roundoff():
    x = np.arange(e.REPLICATES, dtype=float)
    delta = (x + 2 - x) - (x + 1 - x)
    assert e.paired(delta)['effect'] == 1.
    assert e.paired(delta)['lo95'] == e.paired(delta)['hi95'] == 1.
    assert e.paired(np.full(e.REPLICATES, 1e-12))['effect'] == 0.


def tiny_job():
    c = e.config.template(); c['params'].update(N=4, H=2, ticks=12, items=5, exam_items=10, exam_every=1)
    c['network'].update(family='ER', d_bar=2)
    c['teacher'].update(enabled=True, time_budget=6, admin_ticks=0)
    c['mechanisms']['topics']['enabled'] = True
    c['initial']['knowledge'] = dict(kind='values', values=[.3, .4, .6, .8])
    r = e.config.resolve_config(c)['conditions'][0]
    return dict(case='tiny', profile='topics', arm='a', section=0, condition='reference', seed=77,
                replicate=0, resolved=r, groups={'all': list(range(4))}, global_ids=list(range(4)), baseline_scores=[], matched='reference')


def test_parallel_transport_and_serial_execution_preserve_raw_hashes(tmp_path):
    roots = [tmp_path / 'serial', tmp_path / 'parallel']
    for root in roots:
        root.mkdir(); e.config.save_json(root / 'rep0000.json', [tiny_job()])
    serial = e.worker(str(roots[0]), 0)
    with ProcessPoolExecutor(max_workers=2) as pool:
        parallel = pool.submit(e.worker, str(roots[1]), 0).result()
    assert serial == parallel
    assert e.worker(str(roots[0]), 0)[2:] == (0, 1)
    folder = roots[0] / 'raw/rep0000/reference'
    log = e.read_raw(folder)
    final = [r for r in log.tables['exams'] if r['homework'] == 2]
    assert serial[0][0]['exam'] == pytest.approx(100 * np.mean([r['score'] for r in final]))


def test_resume_rejects_changed_declaration_and_corrupt_saved_evidence(tmp_path):
    job = tiny_job(); e.config.save_json(tmp_path / 'rep0000.json', [job]); e.worker(str(tmp_path), 0)
    changed = deepcopy(job); changed['seed'] += 1
    e.config.save_json(tmp_path / 'rep0000.json', [changed])
    with pytest.raises(AssertionError): e.worker(str(tmp_path), 0)
    e.config.save_json(tmp_path / 'rep0000.json', [job])
    (tmp_path / 'raw/rep0000/reference/manifest.json').write_text('{}')
    with pytest.raises(AssertionError): e.worker(str(tmp_path), 0)


def test_incomplete_output_is_preserved_before_regeneration(tmp_path):
    folder = tmp_path / 'raw/rep0000/reference'; folder.mkdir(parents=True)
    (folder / 'unfinished.txt').write_text('preserve this')
    e.config.save_json(tmp_path / 'rep0000.json', [tiny_job()])
    e.worker(str(tmp_path), 0)
    partials = list(folder.parent.glob('reference-partial-*'))
    assert len(partials) == 1 and (partials[0] / 'unfinished.txt').read_text() == 'preserve this'
