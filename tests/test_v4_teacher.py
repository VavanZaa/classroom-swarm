"""A30 teacher identity, information, interventions, time and declarations."""
from copy import deepcopy
from dataclasses import asdict, replace
import json

import numpy as np
import pyarrow.parquet as pq
import pytest

from classroom_swarm.teacher_settings import TeacherSettings, TeacherObserver, plan_teacher
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4_tutoring import simulate_tutoring
from classroom_swarm.v4_teacher import simulate_teacher, validate_teacher_log
from classroom_swarm.teacher_config import template, resolve_config, make_graph, run_experiment, load_config


def run(teacher=None, initial=None, seed=1234, **overrides):
    p = TutoringParams(**{**dict(N=4,H=3,exam_every=1,feedback_delay=0,
        distant_weight=0.,closeness_spread=0.,allow_answer=False), **overrides})
    graph = make_graph({**template()['network'], 'family':'CUSTOM',
        'edges':[[i,j] for i in range(p.N) for j in range(i+1,p.N)]},p.N,seed,0)
    settings = TeacherSettings(enabled=True) if teacher is None else teacher
    log = simulate_teacher(p,graph,PublicAIDraws(seed,0,p.N,p.items,p.exam_items),initial=initial,teacher=settings)
    validate_teacher_log(log)
    return log


@pytest.mark.parametrize('mode',['legacy_hint','joint_practice','shared_practice'])
def test_disabled_teacher_exactly_preserves_every_old_raw_table_and_manifest(mode):
    p = TutoringParams(N=4,H=3,exam_every=1,tutoring_activity=mode)
    graph = make_graph({**template()['network'],'family':'ER','d_bar':2},4,1234,0)
    a = simulate_teacher(p,graph,PublicAIDraws(1234,0,4,p.items,p.exam_items),teacher=TeacherSettings(enabled=False))
    b = simulate_tutoring(p,graph,PublicAIDraws(1234,0,4,p.items,p.exam_items))
    assert a.manifest == b.manifest and a.tables == b.tables
    validate_teacher_log(a)


def test_separate_identity_never_enters_population_graph_or_assessments():
    log = run()
    assert log.manifest['model'] == 'A30-v4.5-teacher-role'
    assert log.tables['teacher_identity'][0]['teacher'] == 'teacher-0'
    assert len(log.tables['traits']) == 4
    assert len(log.tables['students']) == len(log.tables['exams']) == 12
    assert all(r['root'] != 'teacher-0' for r in log.tables['packets'])
    assert all(0 <= r['student'] < 4 for r in log.tables['events'])


@pytest.mark.parametrize('n',[2,6])
def test_instruction_is_one_broadcast_charged_once_even_with_more_students(n):
    log = run(TeacherSettings(enabled=True,actions=['instruction'],time_budget=3),N=n)
    assert len(log.tables['teacher_actions']) == 3
    assert all(r['cost'] == 3 and len(json.loads(r['attendees'])) == n for r in log.tables['teacher_actions'])
    assert all(r['spent'] == 3 for r in log.tables['teacher_budget'] if r['homework'] <= 3)
    assert len(log.tables['teacher_learning']) == n*3


def test_individual_capacity_unserved_queue_and_round_robin_fairness():
    log = run(TeacherSettings(enabled=True,actions=['explanation'],time_budget=3,allocation='round_robin'),H=4)
    assert [json.loads(r['targets'])[0] for r in log.tables['teacher_actions']] == [0,1,2,3]
    assert len([r for r in log.tables['teacher_queue'] if r['reason']=='capacity']) == 12


def test_zero_capacity_is_student_physics_null_when_grading_cost_is_zero():
    settings = TeacherSettings(enabled=True,time_budget=0)
    a,b = run(settings),run(replace(settings,enabled=False))
    assert a.tables['students'] == b.tables['students']
    assert a.tables['exams'] == b.tables['exams']
    assert not a.tables['teacher_actions']


def test_grading_automation_releases_actual_budget_and_removes_grading_backlog():
    manual = TeacherSettings(enabled=True,actions=['guidance'],time_budget=4,
                             admin_ticks=1,grading_ticks_per_student=1)
    a,b = run(manual),run(replace(manual,grading_automation=1.))
    assert len(b.tables['teacher_guidance']) > len(a.tables['teacher_guidance'])
    assert any(r['kind']=='grading' for r in a.tables['teacher_backlog'])
    assert not any(r['kind']=='grading' for r in b.tables['teacher_backlog'])
    assert len(b.tables['homework_feedback']) == 12
    assert any(r['homework'] > r['source_homework']+1 for r in a.tables['homework_feedback'])
    assert all(r['homework']==r['source_homework']+1 for r in b.tables['homework_feedback'])


def test_unfinished_admin_is_carried_and_does_not_disappear():
    log = run(TeacherSettings(enabled=True,time_budget=2,admin_ticks=4))
    assert not log.tables['teacher_actions']
    assert [r['admin_backlog'] for r in log.tables['teacher_budget']] == [2,4,6,4]
    assert sum(r['amount'] for r in log.tables['teacher_backlog'] if r['kind']=='admin') == 4


def test_observations_are_delayed_and_first_policy_uses_prior_only():
    log = run(TeacherSettings(enabled=True,curriculum='adaptive',actions=['instruction'],observation_delay=1))
    assert all(r['difficulty']==.5 for r in log.tables['teacher_actions'] if r['homework']<=2)
    assert all(r['homework'] >= r['source_homework']+2 for r in log.tables['teacher_observations'])
    assert not any(r['homework']==1 for r in log.tables['teacher_observations'])


def test_absent_observations_never_update_prior_or_adaptation():
    log = run(TeacherSettings(enabled=True,curriculum='adaptive',observation_coverage=0.))
    assert all(r['observed_score'] is None and r['estimate_before']==r['estimate_after']==.5 for r in log.tables['teacher_observations'])
    assert all(r['observed_estimate']==.5 for r in log.tables['teacher_actions'])


def test_assisted_homework_can_be_ignored_and_noise_is_reproducible():
    s = TeacherSettings(enabled=True,observation_noise_std=.2)
    d = PublicAIDraws(12,0,4,10,30)
    a,b = TeacherObserver(s,4),TeacherObserver(s,4)
    for observer in (a,b):
        observer.enqueue('homework',1,0,1.,True,2)
        observer.enqueue('exam',1,1,.1,False,2)
        assert observer.release(1,d) == []
    x,y = a.release(2,d),b.release(2,d)
    assert x == y
    assert a.estimate[0] == .5 and a.seen[0] == 0
    assert a.estimate[1] != .5 and a.seen[1] == 1
    assert any(r['score'] != r['observed_score'] for r in x)


def test_teacher_policy_is_invariant_to_latent_initial_knowledge_without_observations():
    settings = TeacherSettings(enabled=True,curriculum='adaptive',observation_sources=[])
    a = run(settings,initial={'knowledge':{'kind':'constant','value':.1}})
    b = run(settings,initial={'knowledge':{'kind':'constant','value':.9}})
    assert a.tables['teacher_actions'] == b.tables['teacher_actions']
    assert a.tables['teacher_queue'] == b.tables['teacher_queue']
    assert a.tables['teacher_observation_state'] == b.tables['teacher_observation_state']


def test_adaptation_and_targeting_use_released_assessment_not_hidden_current_knowledge():
    s = TeacherSettings(enabled=True,actions=['explanation'],curriculum='adaptive',difficulty_offset=.1,time_budget=3)
    plans, _, _ = plan_teacher(s,np.array([.9,.2,.6,.8]),np.ones(4,dtype=int),np.full(4,-1),3,0,12)
    assert plans[0]['targets'] == [1]
    assert plans[0]['difficulty'] == pytest.approx(.3)
    assert plans[0]['observed_estimate'] == .2


def test_corrective_feedback_requires_released_evidence():
    log = run(TeacherSettings(enabled=True,actions=['corrective_feedback'],time_budget=6))
    assert not [r for r in log.tables['teacher_actions'] if r['homework']==1]
    assert any(r['action']=='corrective_feedback' and r['homework']>1 for r in log.tables['teacher_actions'])
    assert any(r['reason']=='no_released_assessment' for r in log.tables['teacher_queue'])


@pytest.mark.parametrize('field,value',[('teaching_skill',0.),('learning_multiplier',0.),('fixed_difficulty',1.)])
def test_unusable_content_grants_no_teacher_learning(field,value):
    s = replace(TeacherSettings(enabled=True,actions=['instruction']),**{field:value})
    log = run(s,initial={'knowledge':{'kind':'constant','value':0.}})
    assert log.tables['teacher_learning']
    assert all(r['gain']==0 for r in log.tables['teacher_learning'])


def test_usable_completed_content_grants_auditable_gain_and_no_answer_packet():
    log = run(TeacherSettings(enabled=True,actions=['instruction'],knowledge=1.,fixed_difficulty=.2),
              initial={'knowledge':{'kind':'constant','value':.2}})
    assert sum(r['gain'] for r in log.tables['teacher_learning']) > 0
    assert not any(r['origin'].startswith('teacher') for r in log.tables['packets'])
    assert sum(r['gain'] for r in log.tables['teacher_learning']) == pytest.approx(sum(r['teacher_gain'] for r in log.tables['learning_components']))


def test_declined_appointments_consume_teacher_time_but_no_student_time_or_learning():
    log = run(TeacherSettings(enabled=True,actions=['instruction'],participation_probability=0.))
    assert all(not r['attended'] for r in log.tables['teacher_attendance'])
    assert not log.tables['teacher_learning']
    assert not any(e['action']=='teacher_instruction' for e in log.tables['events'])
    assert all(r['cost']==3 for r in log.tables['teacher_actions'])


def test_guidance_has_no_direct_knowledge_gain_and_is_read_by_choices():
    s = TeacherSettings(enabled=True,actions=['guidance'],time_budget=4,guidance_strength=.8,guidance_confidence_rate=0.)
    log = run(s)
    assert not log.tables['teacher_learning']
    assert all(r['teacher_gain']==0 for r in log.tables['learning_components'])
    assert any(json.loads(e['detail'])['teacher_guidance_bonus']>0 for e in log.tables['events'] if e['action'].startswith('choose_'))
    neutral = run(replace(s,guidance_strength=0.))
    assert log.tables['students'] != neutral.tables['students']
    assert any(r['attempt'] > q['attempt'] for r,q in zip(log.tables['students'],neutral.tables['students']))


@pytest.mark.parametrize('wait_ticks,helper_time',[(1,True),(4,True),(4,False)])
def test_appointments_and_peer_jobs_never_overlap(wait_ticks,helper_time):
    run(TeacherSettings(enabled=True,actions=['explanation','guidance'],time_budget=8),
        wait_ticks=wait_ticks,helper_time=helper_time,allow_answer=True,ai_mode='tutor')


def test_shared_practice_shifts_after_instruction_or_is_explicitly_displaced():
    a = run(TeacherSettings(enabled=True,actions=['instruction'],time_budget=3),tutoring_activity='shared_practice')
    assert all(r['start']==3 for r in a.tables['tutoring_content'])
    b = run(TeacherSettings(enabled=True,actions=['instruction'],instruction_ticks=10,time_budget=10),tutoring_activity='shared_practice')
    assert len(b.tables['teacher_displaced_practice']) == 3
    assert not b.tables['tutoring_content']


@pytest.mark.parametrize('override',[
    {'time_budget':True},{'enabled':True,'time_budget':13},{'observation_delay':-1},
    {'guidance_ticks':0},{'knowledge':float('nan')},{'observation_noise_std':-1},
    {'grading_automation':1.1},{'actions':['lecture']},{'actions':['guidance','guidance']},
    {'observation_sources':['K']},{'enabled':'yes'},{'allocation':'omniscient'},
    {'identity':0},{'curriculum':'hidden_K'}, {'participation_probability':False}])
def test_invalid_teacher_settings_rejected(override):
    with pytest.raises(ValueError):
        replace(TeacherSettings(),**override).validate(TutoringParams())


def test_strict_config_teacher_overrides_and_identified_contrasts():
    config = template()
    config['conditions'] = [dict(name='manual',teacher={'enabled':True}),
                            dict(name='automated',teacher={'enabled':True,'grading_automation':1.})]
    config['contrasts'] = [dict(condition='automated',reference='manual',kind='single_parameter',identity='identity',
                               explanation='Automation reduces the declared grading work.')]
    resolved = resolve_config(config)
    assert resolved['contrasts'][0]['changed_settings'] == ['teacher.grading_automation']
    config['teacher']['secret_K_policy'] = True
    with pytest.raises(ValueError,match='unknown teacher'):
        resolve_config(config)


@pytest.mark.parametrize('table,key,value',[
    ('teacher_budget','spent',999),('teacher_actions','difficulty',.9999),
    ('teacher_observations','release',0),('teacher_guidance','bonus_after',999),
    ('teacher_learning','gain',.999),('teacher_workload','cost',999)])
def test_raw_validator_detects_corrupted_resource_information_and_effects(table,key,value):
    log = deepcopy(run())
    assert log.tables[table]
    log.tables[table][0][key] = value
    with pytest.raises(AssertionError):
        validate_teacher_log(log)


def test_declared_runner_locks_teacher_settings_and_writes_all_raw_tables(tmp_path):
    config = template()
    config.update(experiment_id='teacher_smoke',replicates=1)
    config['params'].update(N=4,H=2,exam_every=1)
    config['network'].update(family='ER',d_bar=2)
    config['teacher'].update(enabled=True,time_budget=4,actions=['guidance'])
    destination = tmp_path/'teacher_run'
    run_experiment(config,destination)
    lock = json.loads((destination/'lock.json').read_text())
    assert lock['conditions'][0]['teacher']['enabled']
    assert 'src/classroom_swarm/v4_teacher.py' in lock['sources']
    raw = destination/'raw'/'rep0000'/'reference'
    assert len(pq.read_table(raw/'teacher_identity.parquet').to_pylist()) == 1
    assert len(pq.read_table(raw/'students.parquet').to_pylist()) == 8
    assert (raw/'teacher_budget.parquet').exists() and (raw/'complete.json').exists()
    assert load_config(destination/'declared_config.json') == config
    with pytest.raises(ValueError,match='already exists'):
        run_experiment(config,destination)


def test_same_seed_reproduces_all_teacher_and_student_tables():
    a,b = run(),run()
    assert a.manifest == b.manifest and a.tables == b.tables


def test_disabled_teacher_preserves_short_old_schedules():
    log = run(TeacherSettings(enabled=False),ticks=3,guided_practice_ticks=3)
    assert log.manifest['model'] == 'A29-v4.4-tutoring-content'


def test_graded_feedback_is_visible_only_after_its_actual_completion_tick():
    log = run(TeacherSettings(enabled=True,actions=[],time_budget=8,admin_ticks=1,
        grading_ticks_per_student=1),allow_answer=True,wait_ticks=2,H=4)
    for r in log.tables['homework_feedback']:
        assert r['tick'] >= (2 if r['homework']<=4 else 1)
        work = next(w for w in log.tables['teacher_workload'] if w['kind']=='grading'
            and w['source_homework']==r['source_homework'] and w['student']==r['student'])
        assert r['tick'] == work['end']
    early = [r for r in log.tables['requests'] if r['homework']==2 and r['start']<2]
    assert all(r['requester_public_grade'] is None and r['provider_public_grade'] is None for r in early)
    assert all(r['release_tick']<=state['tick'] for r in log.tables['teacher_observations']
        for state in log.tables['teacher_observation_state'] if state['homework']==r['homework'])


def test_fully_automated_grades_return_at_zero_even_with_admin_backlog():
    log = run(TeacherSettings(enabled=True,actions=[],time_budget=1,admin_ticks=2,
        grading_ticks_per_student=1,grading_automation=1.))
    assert len(log.tables['homework_feedback']) == 12
    assert all(r['tick']==0 for r in log.tables['homework_feedback'])
    assert not any(r['kind']=='grading' for r in log.tables['teacher_backlog'])


def test_teacher_can_observe_unaided_exams_without_student_exam_feedback():
    log = run(TeacherSettings(enabled=True,observation_sources=['exam'],curriculum='adaptive'),
        feedback_mode='none')
    assert not log.tables['feedback']
    assert log.tables['teacher_observations']
    assert all(r['source']=='exam' for r in log.tables['teacher_observations'])


@pytest.mark.parametrize('n,ticks,budget,mode',[
    (1,3,3,'joint_practice'),(2,6,6,'joint_practice'),(6,12,8,'joint_practice'),
    (3,32,32,'joint_practice'),(4,12,4,'shared_practice'),(6,12,12,'shared_practice')])
def test_boundaries_partial_observations_and_competing_activities_remain_auditable(n,ticks,budget,mode):
    run(TeacherSettings(enabled=True,time_budget=budget,actions=['guidance','explanation','corrective_feedback','instruction'],
        admin_ticks=1,grading_ticks_per_student=2,grading_automation=.5,curriculum='adaptive',
        observation_delay=1,observation_coverage=.4,observation_noise_std=.2,
        participation_probability=.5,assisted_observation_weight=.2),N=n,ticks=ticks,H=5,
        tutoring_activity=mode,helper_time=False,allow_answer=True,ai_mode='answer')
