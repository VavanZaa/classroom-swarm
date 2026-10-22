"""A31 information, causal channels, nulls and raw replay corruption checks."""
from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from classroom_swarm.mechanism_settings import resolve_mechanisms,incentive_plan
from classroom_swarm.mechanism_config import template,resolve_config,make_graph,run_experiment,load_config
from classroom_swarm.v4_teacher import simulate_teacher
from classroom_swarm.v4_mechanisms import simulate_mechanisms,validate_mechanism_log
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.teacher_settings import TeacherSettings


def run(mechanisms=None,teacher=None,initial=None,seed=431,**kwargs):
    p=TutoringParams(**{**dict(N=3,H=3,items=12,exam_items=12,exam_every=1,feedback_delay=0,
        allow_answer=False,distant_weight=0,closeness_spread=0),**kwargs})
    net={**template()['network'],'family':'CUSTOM','edges':[[i,j] for i in range(p.N) for j in range(i+1,p.N)]}
    graph=make_graph(net,p.N,seed,0)
    teacher=TeacherSettings(enabled=True,time_budget=3,actions=['instruction']) if teacher is None else teacher
    log=simulate_mechanisms(p,graph,PublicAIDraws(seed,0,p.N,p.items,p.exam_items),initial=initial,teacher=teacher,mechanisms=mechanisms)
    validate_mechanism_log(log)
    return log


@pytest.mark.parametrize('enabled',[False,True])
@pytest.mark.parametrize('mode',['joint_practice','shared_practice'])
def test_all_disabled_preserves_a30_every_table_and_manifest(enabled,mode):
    p=TutoringParams(N=3,H=2,tutoring_activity=mode)
    graph=make_graph({**template()['network'],'family':'ER','d_bar':2},3,431,0)
    draws=PublicAIDraws(431,0,3,p.items,p.exam_items);teacher=TeacherSettings(enabled=enabled)
    a=simulate_mechanisms(p,graph,draws,teacher=teacher)
    b=simulate_teacher(p,graph,PublicAIDraws(431,0,3,p.items,p.exam_items),teacher=teacher)
    assert a.manifest==b.manifest and a.tables==b.tables


def test_topics_persist_and_unexposed_topic_is_unchanged_with_identity_transfer():
    log=run({'topics':{'enabled':True,'schedule':[0,0,0]}},teacher=TeacherSettings(enabled=False))
    initial={(r['student'],r['topic']):r['knowledge'] for r in log.tables['topic_initial']}
    for r in log.tables['topic_states']:
        if r['topic']==1:assert r['knowledge']==initial[r['student'],1]
    assert any(r['after']>r['before'] for r in log.tables['topic_learning'])
    assert all(r['topic']==0 for r in log.tables['topic_learning'])
    for r in log.tables['students']:assert r['K']<r['K_active']


def test_cross_topic_transfer_is_explicit_and_reconstructed():
    a=run({'topics':{'enabled':True,'schedule':[0,0,0],'transfer':[[1.,.25],[0.,1.]]}},teacher=TeacherSettings(enabled=False))
    assert any(r['topic']==1 and r['transfer']==.25 for r in a.tables['topic_learning'])
    assert all(r['after']==pytest.approx(r['before']+(1-r['before'])*r['fraction']*r['transfer']) for r in a.tables['topic_learning'])


def test_exams_use_each_persistent_topic_and_grant_no_learning():
    a=run({'topics':{'enabled':True,'initial_values':[[.1,.9]]*3}},teacher=TeacherSettings(enabled=False),H=1)
    assert len(a.tables['exam_items'])==36 and len(a.tables['exam_topics'])==6
    assert all(r['probability']<.4 if r['topic']==0 else r['probability']==.9 for r in a.tables['exam_items'])
    assert {r['source_topic'] for r in a.tables['topic_learning']}=={0}


def test_helper_consolidation_works_when_recipient_knows_every_item():
    common={'enabled':True,'names':['one'],'initial_values':[[1.],[.4]],'schedule':[0]}
    teacher=TeacherSettings(enabled=False)
    a=run({'topics':common},teacher=teacher,N=2,H=1,tutoring_activity='shared_practice',helper_content_learning=False)
    b=run({'topics':{**common,'helper_consolidation_rate':.5}},teacher=teacher,N=2,H=1,tutoring_activity='shared_practice',helper_content_learning=False)
    assert all(r['helper_gain']==0 for r in a.tables['learning_components'])
    assert any(r['student']==1 and r['helper_gain']>0 for r in b.tables['learning_components'])


def test_perfect_peer_signals_match_true_checked_evidence():
    a=run({'peer_observation':{'enabled':True}},tutoring_activity='shared_practice',quality_check_probability=1.)
    assert a.tables['peer_signals'] and a.tables['quality_feedback']
    assert all(r['observed_quality']==r['correct_checked']/r['checked_items'] for r in a.tables['peer_signals'])


def test_inverted_peer_signals_change_beliefs_but_not_hidden_content():
    a=run({'peer_observation':{'enabled':True,'sensitivity':0.,'specificity':0.}},tutoring_activity='shared_practice',quality_check_probability=1.)
    assert all(r['observed_quality']==pytest.approx(1-r['correct_checked']/r['checked_items']) for r in a.tables['peer_signals'])
    assert any(r['Q_after']!=r['Q_before'] for r in a.tables['quality_feedback'])


def test_no_checks_grant_no_evidence_or_quality_updates():
    a=run({'peer_observation':{'enabled':True,'coverage':0.}},tutoring_activity='shared_practice')
    assert a.tables['peer_signals'] and not a.tables['quality_feedback'] and not a.tables['peer_signal_backlog']
    assert all(r['observed_quality'] is None for r in a.tables['peer_signals'])


def test_delay_hides_signals_and_retains_unreleased_backlog():
    a=run({'peer_observation':{'enabled':True,'delay_ticks':100}},tutoring_activity='shared_practice',quality_check_probability=1.)
    assert not a.tables['quality_feedback']
    assert len(a.tables['peer_signal_backlog'])==len(a.tables['peer_signals'])
    assert all(r['quality']==.5 for r in a.tables['quality_choice_state'])


def test_cross_homework_signal_delay_respects_arrival_and_private_topic_context():
    a=run({'topics':{'enabled':True},'peer_observation':{'enabled':True,'delay_ticks':13}},tutoring_activity='shared_practice',quality_check_probability=1.)
    assert a.tables['quality_feedback']
    assert all((r['homework']-1)*12+r['tick']>=r['release_absolute'] for r in a.tables['quality_feedback'])
    assert any(r['homework']>r['source_homework'] for r in a.tables['quality_feedback'])


def test_workload_bursts_and_preparation_use_budget_and_persist():
    a=run({'workload':{'enabled':True,'admin_bursts':[8,0,0],'preparation_ticks':1}},teacher=TeacherSettings(enabled=True,time_budget=4,actions=['instruction']))
    assert a.tables['teacher_budget'][0]['admin_backlog']==5
    assert not [r for r in a.tables['teacher_actions'] if r['homework']==1]
    assert all(r['spent']<=4 for r in a.tables['teacher_budget'])


def test_topic_switch_preparation_is_charged_only_on_switch_days():
    a=run({'topics':{'enabled':True,'schedule':[0,0,1]},'workload':{'enabled':True,'topic_switch_ticks':2}})
    assert [r['topic_switch'] for r in a.tables['workload_arrivals']]==[0,0,2,0]


def test_fatigue_recovery_and_quality_are_bounded_and_physical():
    a=run({'workload':{'enabled':True,'fatigue_per_tick':.1,'recovery':.5,'quality_loss':.8}},teacher=TeacherSettings(enabled=True,time_budget=6,admin_ticks=1,actions=['instruction']))
    f=a.tables['teacher_fatigue'];assert f[0]['after']==.4 and f[1]['recovered']==pytest.approx(.2)
    runtime=json.loads(a.tables['teacher_runtime'][1]['settings']);assert runtime['teaching_skill']<1
    assert all(0<=r['after']<=1 for r in f)


def test_incentives_change_effort_and_rewards_do_not_directly_grant_knowledge():
    common=dict(enabled=True,intrinsic_weight=0.,effort_cost=.001,quadratic_cost=0.)
    a=run({'incentives':{**common,'reward_strength':0.}})
    b=run({'incentives':{**common,'reward_strength':2.}})
    assert not a.tables['teacher_actions'] and b.tables['teacher_actions']
    assert any(r['amount']>0 for r in b.tables['teacher_rewards'])
    assert all(r['utility']==pytest.approx(r['intrinsic']+r['expected_reward']-r['cost']) for r in b.tables['incentive_candidates'])


def test_teacher_policy_accepts_only_observed_state_and_feasible_effort():
    p=TutoringParams(N=3,H=1);teacher=TeacherSettings(enabled=True,time_budget=8)
    settings=resolve_mechanisms({'incentives':{'enabled':True}}).incentives
    args=(settings,teacher,p,np.array([.1,.5,.9]),np.ones(3,int),np.full(3,-1),1,2,.1)
    a=incentive_plan(*args);b=incentive_plan(*args);assert a==b
    assert a[2]<=8 and all(r['start']>=2 for r in a[0])
    assert sum(r['selected'] for r in a[3])==1


def test_first_teacher_policy_cannot_see_unobserved_true_initial_competence():
    settings={'incentives':{'enabled':True,'effort_cost':0.,'quadratic_cost':0.}}
    a=run(settings,initial={'knowledge':{'kind':'constant','value':.1}})
    b=run(settings,initial={'knowledge':{'kind':'constant','value':.9}})
    assert [r for r in a.tables['incentive_candidates'] if r['homework']==1]==[r for r in b.tables['incentive_candidates'] if r['homework']==1]
    assert [r for r in a.tables['teacher_actions'] if r['homework']==1]==[r for r in b.tables['teacher_actions'] if r['homework']==1]


def test_positive_grading_cost_delays_feedback_and_respects_topic_sources():
    a=run({'topics':{'enabled':True},'workload':{'enabled':True,'preparation_ticks':1}},
        teacher=TeacherSettings(enabled=True,time_budget=3,grading_ticks_per_student=1,actions=['instruction']))
    assert any(r['homework']>r['source_homework']+1 for r in a.tables['homework_feedback'])
    assert a.tables['teacher_backlog']


def test_delayed_payments_preserve_teaching_and_student_results():
    a=run({'incentives':{'enabled':True,'payment_delay':0}})
    b=run({'incentives':{'enabled':True,'payment_delay':20}})
    assert a.tables['students']==b.tables['students'] and a.tables['teacher_actions']==b.tables['teacher_actions']
    assert not b.tables['teacher_rewards'] and b.tables['reward_backlog']


@pytest.mark.parametrize('patch',[
    {'bad':{}},{'topics':{'names':['a','a']}},{'topics':{'initial_values':[]}},
    {'topics':{'transfer':[[0,0],[0,1]]}},{'topics':{'schedule':[0,4,0]}},
    {'peer_observation':{'delay_ticks':-1}},{'peer_observation':{'coverage':True}},
    {'incentives':{'reward_power':0}},{'workload':{'admin_bursts':[1]}},
])
def test_bad_declarations_are_rejected(patch):
    with pytest.raises(ValueError):run(patch)


@pytest.mark.parametrize('table,field',[
    ('topic_learning','after'),('exam_items','probability'),('peer_signals','release_absolute'),
    ('quality_feedback','Q_after'),('teacher_fatigue','after'),('teacher_budget','spent'),
    ('incentive_candidates','utility')])
def test_raw_corruption_is_detected(table,field):
    log=run({'topics':{'enabled':True},'peer_observation':{'enabled':True},'workload':{'enabled':True},
        'incentives':{'enabled':True,'effort_cost':0.,'quadratic_cost':0.}},tutoring_activity='shared_practice',ticks=16)
    assert log.tables[table]
    damaged=deepcopy(log);damaged.tables[table][0][field]+=.1
    with pytest.raises(AssertionError):validate_mechanism_log(damaged)


def test_declarations_and_serialization_include_mechanisms_and_source_lock(tmp_path):
    c=template();c['replicates']=1;c['params'].update(N=3,H=2,exam_every=1)
    c['network'].update(family='ER',d_bar=2);c['teacher']['enabled']=True
    c['mechanisms']['topics']['enabled']=True
    root=run_experiment(c,tmp_path/'new')
    locked=load_config(root/'lock.json')
    assert locked['conditions'][0]['mechanisms']['topics']['enabled']
    assert 'src/classroom_swarm/v4_mechanisms.py' in locked['sources']


def test_previous_grade_belief_audits_remain_active_in_topic_model():
    log=run({'topics':{'enabled':True}})
    damaged=deepcopy(log)
    values=json.loads(damaged.tables['homework_feedback'][0]['B_after']);values[0]+=.1
    damaged.tables['homework_feedback'][0]['B_after']=json.dumps(values)
    with pytest.raises(AssertionError):validate_mechanism_log(damaged)
