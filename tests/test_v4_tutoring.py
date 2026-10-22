"""A29 causal boundary, completed activity and raw accounting regressions."""
from dataclasses import asdict
from copy import deepcopy
import numpy as np
import pytest
from classroom_swarm.tutoring_settings import TutoringParams, content_effect, tutoring_scores
from classroom_swarm.tutoring_config import template, resolve_config, preflight, make_graph, run_experiment
from classroom_swarm.v4_tutoring import simulate_tutoring, validate_tutoring_log
from classroom_swarm.v4_declared import simulate_declared
from classroom_swarm.declared_settings import DeclaredParams
from classroom_swarm.v4_public_ai import PublicAIDraws


def run(mode='shared_practice', initial=None, **overrides):
    p=TutoringParams(N=4,H=3,exam_every=1,distant_weight=0.,closeness_spread=0.,
        allow_answer=False,tutoring_activity=mode,**overrides)
    graph=make_graph({'family':'CUSTOM','edges':[[i,j] for i in range(4) for j in range(i+1,4)],
        'edge_weights':{'kind':'constant','value':1.},'seed':None},4,1234,0)
    log=simulate_tutoring(p,graph,PublicAIDraws(1234,0,4,p.items,p.exam_items),initial=initial)
    validate_tutoring_log(log)
    return log


def test_disabled_fork_reproduces_all_old_tables_and_manifest():
    p=TutoringParams(N=4,H=3,exam_every=1,tutoring_activity='legacy_hint')
    graph=make_graph({**template()['network'],'family':'ER','d_bar':2},4,1234,0)
    a=simulate_tutoring(p,graph,PublicAIDraws(1234,0,4,p.items,p.exam_items))
    b=simulate_declared(DeclaredParams(**{k:v for k,v in asdict(p).items() if k in asdict(DeclaredParams())}),
        graph,PublicAIDraws(1234,0,4,p.items,p.exam_items),condition='declared')
    # Default condition label is a caller label; raw physics and provenance match.
    a.manifest['condition']=b.manifest['condition']
    assert a.manifest==b.manifest and a.tables==b.tables


@pytest.mark.parametrize('mode',['joint_practice','shared_practice'])
def test_completed_guidance_consumes_practice_and_quality_is_observable(mode):
    log=run(mode,willingness=1.,temperature=.5,epsilon=.2)
    assert log.tables['tutoring_content']
    assert not [r for r in log.tables['hint_receipts'] if r['source']=='peer']
    assert all(r['end']-r['start']==3 for r in log.tables['tutoring_content'])
    for r in log.tables['quality_feedback']:
        assert r['observed_quality']==r['correct_checked']/r['checked_items']


def test_no_check_no_quality_update_and_no_physical_effect_with_learning_disabled():
    # Equal initial quality remains constant, so policies and physics are identical.
    a=run(quality_check_probability=0.,quality_learning_rate=0.)
    b=run(quality_check_probability=1.,quality_learning_rate=0.)
    assert a.tables['students']==b.tables['students']
    assert all(r['Q_before']==r['Q_after'] and r['observed_quality'] is None for r in a.tables['quality_feedback'])


def test_incorrect_explanations_grant_no_bonus_or_helper_gain():
    log=run(initial={'teaching_skill':{'kind':'constant','value':0.}})
    assert all(r['correct_fraction']==r['usable_fraction']==r['helper_fraction']==0 for r in log.tables['tutoring_content'])
    assert all(r['content_gain']==r['helper_gain']==0 for r in log.tables['learning_components'])
    assert any(r['practice_gain']>0 for r in log.tables['learning_components'])


def test_helper_toggle_is_real_channel_and_wrong_content_remains_zero():
    a,b=run(),run(helper_content_learning=False)
    assert any(r['helper_gain']>0 for r in a.tables['learning_components'])
    assert all(r['helper_gain']==0 for r in b.tables['learning_components'])
    assert a.tables['students']!=b.tables['students']


def test_same_aggregate_knowledge_can_have_complementary_items_and_readiness_matters():
    p=TutoringParams()
    result=content_effect(p,.5,.5,1.,np.array([.5]),np.array([.9]),np.array([.1]),np.array([.1]))
    assert result['learner_quality']==1.
    hard=content_effect(p,.1,1.,1.,np.array([.9]),np.array([.9]),np.array([0.]),np.array([0.]))
    assert hard['correct'][0] and hard['learner_quality']==0.


def test_changed_peers_are_exact_null_without_communication():
    def initial(level):
        result={'knowledge':{'kind':'values','values':[.35,.35,level,level]},'confidence':{'kind':'constant','value':.5}}
        for k in template()['initial']:
            if k.startswith('benefit_'): result[k]={'kind':'constant','value':.5}
        return result
    a,b=run(initial=initial(.35),allow_hint=False),run(initial=initial(.75),allow_hint=False)
    assert [r for r in a.tables['students'] if r['student']<2]==[r for r in b.tables['students'] if r['student']<2]


def test_private_quality_changes_expected_value_without_latent_policy_input():
    p=TutoringParams()
    args=(.5,.5,np.full(5,.5),.15,0.,False,False,[.5,.5],True,False,12)
    assert tutoring_scores(p,*args,quality=.9)['hint']>tutoring_scores(p,*args,quality=.1)['hint']


@pytest.mark.parametrize('field,value',[('guided_practice_ticks',True),('readiness_band',0.),
    ('quality_check_probability',1.1),('helper_content_learning',1),('tutoring_activity','magic')])
def test_invalid_settings_rejected(field,value):
    with pytest.raises(ValueError): TutoringParams(**{field:value}).validate()


def test_extended_json_roundtrip_contrasts_and_raw_runner(tmp_path):
    c=template();c.update(experiment_id='A29_test',replicates=1)
    c['params'].update(N=4,H=1,exam_every=1,tutoring_activity='shared_practice')
    c['network'].update(family='ER',d_bar=2)
    c['conditions']=[{'name':'base'},{'name':'no_helper','params':{'helper_content_learning':False}}]
    c['contrasts']=[dict(condition='no_helper',reference='base',kind='single_parameter',identity='not_identity')]
    resolved=resolve_config(c);preflight(resolved)
    assert resolved['contrasts'][0]['changed_settings']==['params.helper_content_learning']
    output=run_experiment(c,tmp_path/'run')
    assert (output/'complete.json').exists()
    bad=deepcopy(c);bad['initial']['source_quality']={'kind':'constant','value':2.}
    with pytest.raises(ValueError): resolve_config(bad)


def test_validator_detects_unobservable_quality_change_and_missing_gain():
    log=run(); bad=deepcopy(log)
    bad.tables['quality_feedback'][0]['Q_after']+=.01
    with pytest.raises(AssertionError): validate_tutoring_log(bad)
    bad=deepcopy(log);bad.tables['learning_components'][0]['content_gain']+=.01
    with pytest.raises(AssertionError): validate_tutoring_log(bad)
