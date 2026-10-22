"""A30 raw audits, including replay of policies from released observations only."""
from __future__ import annotations

from collections import Counter
import json
import numpy as np

from .v4 import validate_log, MAX_TICKS
from .v4_grades import grade_update
from .declared_settings import DeclaredParams
from .teacher_settings import TeacherSettings, plan_teacher, teacher_random
from .v4_public_ai import PublicAIDraws
from .tutoring_settings import TutoringParams, content_effect


def validate_teacher_student_tables(log):
    """A28 student audits adapted for explicitly delayed A30 homework grading."""
    validate_log(log)
    p = DeclaredParams(**log.manifest['params'])
    by = {(r['homework'], r['student']): r for r in log.tables['students']}
    rows = log.tables['homework_feedback']
    assert len({(r['source_homework'], r['student']) for r in rows}) == len(rows)
    for h in range(1, p.H+2):
        for row in [r for r in rows if r['homework'] == h]:
            i = row['student']
            source = by[row['source_homework'], i]
            assert h >= row['source_homework']+1
            assert row['grade'] == source['grade'] and row['K_before'] == row['K_after']
            expected_k = by[h,i]['K_before'] if h <= p.H else by[p.H,i]['K']
            if h <= p.H:
                expected_k += sum(r['K_after']-r['K_before'] for r in log.tables['learning_components']
                    if r['homework']==h and r['student']==i and r['tick']<=row['tick'])
            assert abs(row['K_before']-expected_k) < 1e-12
            expected = grade_update(np.array(json.loads(row['B_before'])), row['C_before'], row['grade'],
                json.loads(row['credit']), row['assisted'], source['complete'], p)
            np.testing.assert_allclose(json.loads(row['B_after']), expected[0], rtol=0, atol=1e-14)
            assert abs(row['C_after']-expected[1]) < 1e-14
            assert row['shortfall_after'] == expected[2]
        for req in [r for r in log.tables['requests'] if r['homework'] == h]:
            available = {}
            for r in rows:
                if (r['homework'],r['tick']) <= (h,req['start']):
                    available[r['student']] = r['grade']
            assert req['requester_public_grade'] == available.get(req['requester'])
            assert req['provider_public_grade'] == available.get(req['provider'])
            if req['mode'] == 'answer' and p.peer_rule == 'higher':
                assert req['requester_public_grade'] is not None
                assert req['provider_public_grade'] > req['requester_public_grade']
    ai = log.tables['ai_uses']
    assert all(count <= p.max_ai_uses for count in Counter((r['homework'], r['student']) for r in ai).values())
    assert all(r['homework'] >= p.ai_start for r in ai)
    assert p.ai_mode != 'none' or not ai
    assert all(e['action'] not in {'check', 'choose_check'} for e in log.tables['events'])
    peer = [r for r in log.tables['hint_receipts'] if r['source'] == 'peer']
    assert len(peer) == sum(e['action'] == 'hint_receive' for e in log.tables['events'])
    if p.hint_deadline_guard:
        assert all(r['usable'] for r in peer)
    assert all(r['usable'] for r in log.tables['hint_receipts'] if r['source'] == 'ai')
    tutored = {(r['homework'], r['student']) for r in log.tables['packets'] if r['hint_source'] == 'ai'}
    if p.tutor_credit_by_source:
        assert tutored == {(r['homework'], r['student']) for r in log.tables['packets'] if r['origin'] == 'ai_tutor_attempt'}


def validate_teacher_extras(log):
    p, tables = log.manifest['params'], log.tables
    s = TeacherSettings(**log.manifest['teacher'])
    s.validate(TutoringParams(**p))
    n, horizon = p['N'], p['H']
    draws = PublicAIDraws(log.manifest['seed'],log.manifest['replicate'],n,p['items'],p['exam_items'])
    identity = tables['teacher_identity']
    assert len(identity) == 1 and identity[0]['teacher'] == s.identity
    assert identity[0]['student_count'] == n and not identity[0]['included_in_student_outcomes']
    assert len(tables['traits']) == n and len(tables['exams']) == n*(horizon//p['exam_every'])
    for table in ('students', 'traits', 'exams', 'initial_states', 'events', 'packets'):
        assert all(isinstance(r['student'], int) and 0 <= r['student'] < n for r in tables[table])
    for row in tables['graph']:
        assert 0 <= row['u'] < n and 0 <= row['v'] < n
    for name in ('teacher_actions', 'teacher_attendance', 'teacher_observations',
                 'teacher_observation_state', 'teacher_workload', 'teacher_budget',
                 'teacher_learning', 'teacher_guidance', 'teacher_queue'):
        assert all(r['teacher'] == s.identity for r in tables[name])

    # Reconstruct exactly what the teacher could know at each decision time.
    estimates = np.full(n, s.observation_prior)
    seen = np.zeros(n, dtype=int)
    returned = {(r['source_homework'],r['student']): r for r in tables['homework_feedback']}
    exams = {(r['homework'],r['student']): r for r in tables['exams']}
    observation_keys = set()
    admin_backlog, last_served = 0, np.full(n, -1, dtype=int)
    budgets = {r['homework']: r for r in tables['teacher_budget']}
    assert len(budgets) == horizon+1
    graded_keys = set()
    for h in range(1, horizon+2):
        for r in [q for q in tables['teacher_observations'] if q['homework'] == h]:
            i, key = r['student'], (r['source'], r['source_homework'], r['student'])
            assert key not in observation_keys and r['source'] in s.observation_sources
            observation_keys.add(key)
            source = returned[key[1:]] if r['source'] == 'homework' else exams[key[1:]]
            earliest = source['homework'] + s.observation_delay if r['source'] == 'homework' else source['release'] + s.observation_delay
            assert r['release'] == earliest and r['homework'] == earliest
            expected_tick = source['tick'] if r['source']=='homework' and s.observation_delay==0 else 0
            assert r['tick'] == r['release_tick'] == expected_tick
            assert r['score'] == source['grade' if r['source'] == 'homework' else 'score']
            assisted = source['assisted'] if r['source'] == 'homework' else False
            assert r['assisted'] == assisted
            weight = s.assisted_observation_weight if assisted else 1.
            assert r['weight'] == weight and r['estimate_before'] == estimates[i]
            source_index = int(r['source']=='exam')
            coverage = teacher_random(draws,'observation_coverage',r['source_homework'],(2,n))[source_index,i]
            noise = teacher_random(draws,'observation_noise',r['source_homework'],(2,n))[source_index,i]
            expected_signal = float(np.clip(r['score']+s.observation_noise_std*noise,0,1)) if coverage<s.observation_coverage else None
            assert r['observed_score'] == expected_signal
            if r['observed_score'] is not None:
                assert 0 <= r['observed_score'] <= 1
                if s.observation_noise_std == 0:
                    assert r['observed_score'] == r['score']
                if weight > 0:
                    estimates[i] += s.observation_learning_rate*weight*(r['observed_score']-estimates[i])
                    seen[i] += 1
            assert r['estimate_after'] == estimates[i] and r['seen'] == seen[i]
        states = [q for q in tables['teacher_observation_state'] if q['homework'] == h]
        assert sorted(r['student'] for r in states) == list(range(n))
        for r in states:
            assert r['estimate'] == estimates[r['student']] and r['seen'] == seen[r['student']]
            assert r['last_served'] == last_served[r['student']]

        work = [r for r in tables['teacher_workload'] if r['homework'] == h]
        admin = [r for r in work if r['kind'] == 'admin']
        assert len(admin) == 1
        arrived = s.admin_ticks if h <= horizon else 0
        expected_admin = min(s.time_budget, admin_backlog+arrived)
        assert admin[0]['backlog_before'] == admin_backlog and admin[0]['arrived'] == arrived
        assert admin[0]['cost'] == expected_admin and admin[0]['due'] == admin_backlog+arrived
        admin_backlog += arrived-expected_admin
        assert admin[0]['backlog_after'] == admin_backlog
        cursor = expected_admin
        due = sorted((sh,i) for sh in range(1,min(h,horizon+1)) for i in range(n) if (sh,i) not in graded_keys)
        expected_graded = []
        for key in due:
            if cursor + s.grading_cost > s.time_budget or (admin_backlog and s.grading_cost > 0):
                break
            expected_graded.append(key)
            cursor += s.grading_cost
        grading = [r for r in work if r['kind'] == 'grading']
        assert [(r['source_homework'], r['student']) for r in grading] == expected_graded
        for r in grading:
            assert r['cost'] == s.grading_cost
            assert returned[r['source_homework'],r['student']]['homework'] == h
            assert returned[r['source_homework'],r['student']]['tick'] == r['end']
        graded_keys.update(expected_graded)
        assert all(r['tick'] == cursor for r in states)
        assert all(r['tick'] <= cursor for r in tables['teacher_observations'] if r['homework']==h)
        actions = [r for r in tables['teacher_actions'] if r['homework'] == h]
        if h <= horizon:
            plans, queue, end = plan_teacher(s, estimates, seen, last_served, h, cursor, p['ticks'])
            actual_queue = [r for r in tables['teacher_queue'] if r['homework'] == h]
            assert len(queue) == len(actual_queue)
            for expected, actual in zip(queue, actual_queue):
                expected = {**expected, 'targets':json.dumps(expected['targets']), 'seen':json.dumps(expected['seen'])}
                assert expected == actual
            assert len(plans) == len(actions)
            for plan, action in zip(plans, actions):
                for key, value in plan.items():
                    if key == 'status':
                        continue  # the planning queue precedes completed actions
                    assert action[key] == (json.dumps(value) if key in {'targets','seen'} else value)
                assert action['cost'] == plan['duration'] and action['status'] == 'completed'
                attendance = [r for r in tables['teacher_attendance'] if r['action_id'] == action['action_id']]
                assert sorted(r['student'] for r in attendance) == sorted(plan['targets'])
                attendees = [r['student'] for r in attendance if r['attended']]
                u = teacher_random(draws,'attendance',h,(4,MAX_TICKS,n))
                index = ['instruction','explanation','corrective_feedback','guidance'].index(plan['action'])
                for r in attendance:
                    assert r['attended'] == (u[index,plan['start'],r['student']]<s.participation_probability)
                    assert r['start'] == plan['start'] and r['end'] == plan['end']
                assert attendees == json.loads(action['attendees'])
                for i in attendees:
                    last_served[i] = h
        else:
            assert not actions
            end = cursor
        b = budgets[h]
        assert b['workload'] == cursor and b['actions'] == end-cursor
        assert b['spent'] == end <= s.time_budget and b['budget'] == s.time_budget
        assert b['unused'] == s.time_budget-end and b['admin_backlog'] == admin_backlog
        assert b['grading_backlog'] == n*min(h-1,horizon)-len(graded_keys)
        intervals = sorted([(r['start'],r['end']) for r in work+actions])
        assert all(0 <= a <= b <= s.time_budget for a,b in intervals)
        assert all(a[1] <= b[0] for a,b in zip(intervals,intervals[1:]))
        assert sum(b-a for a,b in intervals) == end
    assert graded_keys == set(returned)
    backlog = {(r['source_homework'],r['student']) for r in tables['teacher_backlog'] if r['kind']=='grading'}
    assert backlog | graded_keys == {(h,i) for h in range(1,horizon+1) for i in range(n)}
    assert not backlog & graded_keys
    assert sum(r['amount'] for r in tables['teacher_backlog'] if r['kind']=='admin') == admin_backlog
    expected_observations, future_observations = set(), set()
    for source, records in [('homework',returned),('exam',exams)]:
        if source not in s.observation_sources:
            continue
        for (sh,i),row in records.items():
            release = (row['homework'] if source=='homework' else row['release'])+s.observation_delay
            (expected_observations if release<=horizon+1 else future_observations).add((source,sh,i,release))
    assert {(r['source'],r['source_homework'],r['student'],r['release']) for r in tables['teacher_observations']} == expected_observations
    assert {(r['source'],r['source_homework'],r['student'],r['due']) for r in tables['teacher_backlog'] if r['kind']=='observation'} == future_observations

    # Every attended appointment has exactly one completed student event and effect row.
    actions = {r['action_id']:r for r in tables['teacher_actions']}
    attendance = {(r['action_id'],r['student']):r for r in tables['teacher_attendance']}
    expected_effects = {key for key,r in attendance.items() if r['attended']}
    effects = {(r['action_id'],r['student']):r for r in tables['teacher_learning']+tables['teacher_guidance']}
    assert expected_effects == set(effects)
    events = [r for r in tables['events'] if r['action'].startswith('teacher_') and r['action'] != 'teacher_phase_wait']
    assert len(events) == len(effects)
    for event in events:
        effect = effects[event['detail'],event['student']]
        assert event['start'] == effect['start'] and event['end'] == effect['end']
    components = {(r['homework'],r['tick'],r['student']):r for r in tables['learning_components']}
    alpha = {r['student']:r['alpha'] for r in tables['traits']}
    physics_cache = {}
    total_teacher_gain = 0.
    for r in tables['teacher_learning']:
        action = actions[r['action_id']]
        assert r['action'] == action['action'] != 'guidance' and r['difficulty'] == action['difficulty']
        h = r['homework']
        if h not in physics_cache:
            learner = np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,123,h])).random((MAX_TICKS,n,p['items']))
            provider = teacher_random(draws,'retrieval',h,(4,MAX_TICKS,p['items']))
            explanation = teacher_random(draws,'explanation',h,(4,MAX_TICKS,p['items']))
            physics_cache[h] = learner,provider,explanation
        learner,provider,explanation = physics_cache[h]
        index = ['instruction','explanation','corrective_feedback','guidance'].index(r['action'])
        physics = content_effect(TutoringParams(**p),r['K_before'],s.knowledge,s.teaching_skill,
            np.full(p['items'],r['difficulty']),learner[r['start'],r['student']],
            provider[index,r['start']],explanation[index,r['start']])
        assert r['correct_bits'] == ''.join('1' if x else '0' for x in physics['correct'])
        assert r['novel_bits'] == ''.join('1' if x else '0' for x in physics['novel'])
        transfer = json.loads(r['transfer'])
        assert len(transfer) == len(r['correct_bits']) == len(r['novel_bits']) == p['items']
        readiness = float(np.clip(1-max(0,r['difficulty']-r['K_before'])/p['readiness_band'],0,1))
        expected_transfer = [readiness if c=='1' and novel=='1' else 0. for c,novel in zip(r['correct_bits'],r['novel_bits'])]
        np.testing.assert_allclose(transfer,expected_transfer,rtol=0,atol=1e-14)
        assert abs(np.mean(transfer)-r['usable_fraction']) < 1e-14
        fraction = min(1,alpha[r['student']]/p['attempt_learning_divisor']*s.learning_multiplier*r['usable_fraction'])
        component = components.get((r['homework'],r['end'],r['student']))
        preceding = 0. if component is None else component['practice_gain']+component['content_gain']+component['helper_gain']
        expected_gain = (1-r['K_before']-preceding)*fraction
        assert abs(expected_gain-r['gain']) < 1e-13
        assert abs((component['teacher_gain'] if component else 0.)-r['gain']) < 1e-13
        total_teacher_gain += r['gain']
    assert abs(total_teacher_gain-sum(r['teacher_gain'] for r in components.values())) < 1e-12
    bonus = np.zeros(n)
    for h in range(1,horizon+1):
        bonus *= s.guidance_decay
        for r in sorted([r for r in tables['teacher_guidance'] if r['homework']==h], key=lambda r:(r['end'],r['student'])):
            i, action = r['student'], actions[r['action_id']]
            assert action['action'] == 'guidance' and r['observed_estimate'] == action['observed_estimate']
            assert abs(r['C_after']-(r['C_before']+s.guidance_confidence_rate*(r['observed_estimate']-r['C_before']))) < 1e-14
            assert r['bonus_before'] == bonus[i]
            bonus[i] = min(1,bonus[i]+s.guidance_strength*(1-r['observed_estimate']))
            assert r['bonus_after'] == bonus[i]
        for e in [r for r in tables['events'] if r['homework']==h and r['action'].startswith('choose_')]:
            detail = json.loads(e['detail'])
            before = bonus[e['student']]
            # Within-day choices before a guidance completion still use the prior bonus.
            for r in [r for r in tables['teacher_guidance'] if r['homework']==h and r['student']==e['student'] and r['end']>e['start']]:
                before = r['bonus_before']
            assert detail['teacher_guidance_bonus'] == before
