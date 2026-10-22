"""A34 corrections: causal inputs, dependency semantics and independent audits."""
from copy import deepcopy
import json
import pytest
from classroom_swarm import repaired_config as config
from classroom_swarm.v4_repaired import simulate_repaired
from classroom_swarm.v4_promising import simulate_promising
from classroom_swarm.repaired_validation import validate_repaired_log
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws

def constant(value): return dict(kind='constant',value=value)

def declaration(curriculum=True):
    c=config.template(); c.update(seed=88234,replicates=1)
    c['params'].update(N=4,H=3,exam_every=1,exam_items=36,feedback_delay=0,
        tutoring_activity='joint_practice',allow_hint=True,allow_answer=False,confidence_weight=.8)
    c['network'].update(family='CUSTOM',edges=[[0,1],[2,3]])
    c['initial'].update(knowledge=constant(.45),confidence=constant(.5),effort_aversion=constant(.1))
    c['teacher'].update(enabled=True,grading_ticks_per_student=0,admin_ticks=0,observation_sources=['exam'])
    c['extensions']['learning_process']['enabled']=True
    c['extensions']['teacher_work'].update(enabled=True,total_budget=8,actions=[])
    c['design']['curriculum']['enabled']=curriculum
    return c

def run(c,repair=True):
    r=config.resolve_config(c); config.preflight(r); v=r['conditions'][0]; p=TutoringParams(**v['params'])
    g=config.make_graph(v['network'],p.N,c['seed'],0); d=PublicAIDraws(c['seed'],0,p.N,p.items,p.exam_items)
    log=simulate_repaired(p,g,d,v['name'],v['initial'],v['teacher'],v['mechanisms'],v['extensions'],v['design'],repair)
    validate_repaired_log(log,p)
    return log

@pytest.mark.parametrize('curriculum',[False,True])
def test_optional_legacy_parity(curriculum):
    c=declaration(curriculum); c['repairs_enabled']=False
    a=run(c,False); v=config.resolve_config(c)['conditions'][0]; p=TutoringParams(**v['params'])
    b=simulate_promising(p,config.make_graph(v['network'],p.N,c['seed'],0),PublicAIDraws(c['seed'],0,p.N,p.items,p.exam_items),v['name'],v['initial'],v['teacher'],v['mechanisms'],v['extensions'],v['design'])
    assert a.manifest==b.manifest and a.tables==b.tables

@pytest.mark.parametrize('curriculum',[False,True])
@pytest.mark.parametrize('benefit',['attempt','hint'])
def test_private_benefits_affect_policy(curriculum,benefit):
    c=declaration(curriculum); c['initial']['benefit_'+benefit]=constant(.05); a=run(c)
    c['initial']['benefit_'+benefit]=constant(.95); b=run(c)
    first=lambda log: next(r for r in log.tables['policy_inputs'] if r['student']==0)
    assert first(a)[benefit+'_belief']!=first(b)[benefit+'_belief']
    assert first(a)[benefit+'_utility']!=first(b)[benefit+'_utility']

def test_access_affects_hint_expected_utility():
    c=declaration(); c['initial']['access_hint']=constant(.05); a=run(c)
    c['initial']['access_hint']=constant(.95); b=run(c)
    def score(log):
        return json.loads(next(r for r in log.tables['events'] if r['action'].startswith('choose_') and r['student']==0)['detail'])['scores']['hint']
    assert score(a)!=score(b)

def test_from_effective_skill_matrix():
    c=declaration(); c['initial'].update(knowledge=constant(.9),confidence={'kind':'from_knowledge'},benefit_attempt={'kind':'from_knowledge'})
    c['design']['curriculum']['initial_values']=[[.1,.2,.3]]*4
    log=run(c)
    assert log.manifest['declared_base_knowledge']==[.9]*4
    for r in log.tables['initial_states']:
        assert r['knowledge']==pytest.approx(.2)
        assert r['confidence']==pytest.approx(.2)
        assert r['benefit_attempt']==pytest.approx(.2)

@pytest.mark.parametrize('table',['curriculum_pretest','curriculum_choices','curriculum_readiness','policy_inputs'])
def test_deleted_records_rejected(table):
    log=run(declaration()); assert log.tables[table]
    log.tables[table]=[]
    with pytest.raises(AssertionError): validate_repaired_log(log)

def test_invented_observed_means_rejected():
    log=run(declaration()); row=log.tables['curriculum_choices'][0]
    means=json.loads(row['observed_means']); means[0]+=.001; row['observed_means']=json.dumps(means)
    with pytest.raises(AssertionError): validate_repaired_log(log)

def test_policy_cannot_read_true_knowledge():
    c=declaration(False); c['teacher']['observation_coverage']=0.
    for action in ('attempt','hint','answer','ai_answer','ai_tutor'):
        c['initial']['benefit_'+action]=constant(.5)
    c['initial']['knowledge']=constant(.1); a=run(c)
    c['initial']['knowledge']=constant(.9); b=run(c)
    assert a.tables['policy_inputs'][:4]==b.tables['policy_inputs'][:4]

def test_invalid_enabled_state_rejected():
    c=declaration(); c['repairs_enabled']='yes'
    with pytest.raises(ValueError): config.resolve_config(c)
