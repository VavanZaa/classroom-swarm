"""A25 grade visibility, social tradeoffs, AI causality and reproducibility."""
from dataclasses import replace
import json
import numpy as np
import pytest
from classroom_swarm.graphs import generate_er, _from_edges
from classroom_swarm.v4 import V4Draws
from classroom_swarm.v4_grades import GradeParams, simulate_grades
from classroom_swarm.v4_public_ai import (PublicAIParams, PublicAIDraws, contact_matrix,
    target_options, public_activity_scores, public_grade_credit, simulate_public_ai, validate_public_log)


def run(p=None,seed=82,graph=None):
    p=p or PublicAIParams(N=6,H=8)
    g=graph or generate_er(p.N,3,71)
    return simulate_public_ai(p,g,PublicAIDraws(seed,0,p.N,p.items,p.exam_items))


def test_closer_moderate_scorer_can_outweigh_top_scorer():
    p=PublicAIParams(N=4)
    contacts=np.ones((4,4));contacts[0,2]=.1;np.fill_diagonal(contacts,0)
    grades=np.array([.5,.7,.9,.4]);a=np.full((4,4,2),.5)
    ids,w=target_options(0,'answer',contacts,a,grades,p)
    assert ids==[1,2] and w[0]>w[1]
    assert 3 in target_options(0,'answer',contacts,a,grades,replace(p,peer_rule='relaxed'))[0]
    assert target_options(0,'answer',contacts,a,np.full(4,np.nan),p)==([],[])
    assert target_options(2,'answer',contacts,a,grades,p)==([],[])


def test_contacts_frozen_symmetric_and_semantic_streams_independent():
    p=PublicAIParams(N=6);g=generate_er(6,3,71)
    a,b=PublicAIDraws(82,0,6,10,30),PublicAIDraws(82,0,6,10,30)
    a.tensor('ai_items',2);c=contact_matrix(p,g,a)
    np.testing.assert_array_equal(a.tensor('choice',2),b.tensor('choice',2))
    np.testing.assert_array_equal(c,c.T)
    np.testing.assert_array_equal(c,contact_matrix(p,g,b))
    assert not c.flags.writeable and not np.array_equal(a.tensor('ai_items',2),a.tensor('items',2))


@pytest.mark.parametrize('mode',['none','answer','tutor'])
def test_full_audit_visibility_and_ai_receipt_not_learning(mode):
    log=run(PublicAIParams(N=6,H=8,ai_mode=mode))
    validate_public_log(log)
    assert not any(r['mode']=='answer' and r['homework']==1 for r in log.tables['requests'])
    assert all(r['homework']>=2 for r in log.tables['ai_uses'])
    if mode!='none': assert log.tables['ai_uses']
    for i in range(6):
        gain=sum(e['K_after']-e['K_before'] for e in log.tables['events']
                 if e['student']==i and e['action'] in {'attempt','help_hint'})
        final=next(r['K'] for r in log.tables['students'] if r['student']==i and r['homework']==8)
        assert gain==pytest.approx(final-log.tables['traits'][i]['K0'],abs=1e-12)


def test_ai_available_without_peers_and_not_forced():
    p=PublicAIParams(N=4,H=8,ai_mode='answer',distant_weight=0)
    g=_from_edges('ER',4,{},0,[]);log=run(p,graph=g)
    assert not log.tables['requests'] and log.tables['ai_uses']
    choices=[json.loads(e['detail'])['probabilities'] for e in log.tables['events']
             if e['homework']>=2 and e['action'].startswith('choose_')]
    assert any('ai_answer' in pr and 0<pr['ai_answer']<1 and pr.get('attempt',0)>0 for pr in choices)
    validate_public_log(log)


def test_ai_modes_masked_before_intro_and_after_time_budget():
    p=PublicAIParams(ai_mode='answer')
    args=(.5,.5,np.full(5,.5),.15,0,False,False,(0,0),False,False,6)
    assert 'ai_answer' not in public_activity_scores(p,*args,ai_available=False)
    assert 'ai_answer' in public_activity_scores(p,*args,ai_available=True)
    assert 'ai_tutor' in public_activity_scores(replace(p,ai_mode='tutor'),*args,ai_available=True)
    short=(*args[:-1],4)
    assert 'ai_tutor' not in public_activity_scores(replace(p,ai_mode='tutor'),*short,ai_available=True)
    base=public_activity_scores(p,*args,ai_available=True)
    pressure=public_activity_scores(p,*args,ai_available=True,shortfall=.5)
    assert pressure['ai_answer']-base['ai_answer']==pytest.approx(.2)
    assert pressure['attempt']==base['attempt']


def test_credit_follows_access_route_not_ai_content_origin():
    packet=dict(via='ai',origin='ai_answer',assisted=True)
    assert public_grade_credit(packet,np.zeros(5))[0].tolist()==[0,0,0,1,0]
    packet['via']='peer'
    assert public_grade_credit(packet,np.zeros(5))[0].tolist()==[0,0,1,0,0]
    packet.update(via='attempt',origin='ai_tutor_attempt')
    assert public_grade_credit(packet,np.zeros(5))[0].tolist()==[.5,0,0,0,.5]


def test_exact_ai_answer_packet_can_spread_through_peers():
    p=PublicAIParams(N=12,H=15,ai_mode='answer',ai_accuracy=1,peer_rule='relaxed',willingness=1)
    log=run(p)
    packets={r['packet_id']:r for r in log.tables['packets']}
    forwarded=[e for e in log.tables['events'] if e['action']=='answer_receive'
               and packets[e['packet_id']]['origin']=='ai_answer']
    assert forwarded
    for e in forwarded:
        assert e['root']==-1 and e['depth']>=1
        assert packets[e['packet_id']]['item_bits']=='1'*p.items
        assert e['K_before']==e['K_after']


@pytest.mark.parametrize('seed',[82,101])
def test_legacy_routing_core_trajectory_reproduces_a24(seed):
    p=PublicAIParams(N=6,H=8,peer_rule='legacy',distant_weight=0,closeness_spread=0,
                     grade_bias=0,public_signal=0,grade_effort_only=False,learning_value=.25)
    g=generate_er(6,3,71)
    new=run(p,seed,g)
    old=simulate_grades(GradeParams(N=6,H=8),g,V4Draws(seed,0,6,10,30))
    for a,b in zip(new.tables['students'],old.tables['students']):
        for k in ('K','C','grade','copied','sequence','B_attempt','B_hint','B_answer','packet_id'):
            assert a[k]==b[k]


def test_ai_has_no_effect_before_introduction():
    p=PublicAIParams(N=6,H=8)
    a,b=run(p),run(replace(p,ai_mode='answer',ai_start=4))
    for table in ('students','events','requests','packets'):
        assert [r for r in a.tables[table] if r['homework']<4]==[r for r in b.tables[table] if r['homework']<4]


def test_grade_effort_objective_and_hidden_ai_quality():
    p=PublicAIParams(ai_mode='answer')
    args=(.5,.5,np.full(5,.6),.15,0,False,False,(0,0),False,False,6)
    base=public_activity_scores(p,*args,ai_available=True)
    assert base['wait']==0 and p.learning_value==0
    assert base==public_activity_scores(replace(p,ai_accuracy=.1),*args,ai_available=True)
    tutor=replace(p,ai_mode='tutor')
    assert public_activity_scores(tutor,*args,ai_available=True)==public_activity_scores(
        replace(tutor,ai_hint_strength=.9),*args,ai_available=True)
    # More effort aversion makes the short AI-answer action relatively more attractive.
    expensive=(*args[:3],.6,*args[4:])
    costly=public_activity_scores(p,*expensive,ai_available=True)
    assert costly['ai_answer']-costly['attempt'] > base['ai_answer']-base['attempt']
    with pytest.raises(ValueError): replace(p,learning_value=.25).validate()


def test_ai_answer_and_tutor_logs_share_nullable_storage_schema(tmp_path):
    import pyarrow.parquet as pq
    from classroom_swarm.e12 import encode_table
    a=run(PublicAIParams(N=6,H=8,ai_mode='answer')).tables['ai_uses']
    b=run(PublicAIParams(N=6,H=8,ai_mode='tutor')).tables['ai_uses']
    first,second=encode_table('ai_uses',a),encode_table('ai_uses',b)
    assert first.schema==second.schema and a and b
    path=tmp_path/'ai.parquet'
    with pq.ParquetWriter(path,first.schema) as writer:
        writer.write_table(first);writer.write_table(second)
    restored=pq.read_table(path).to_pylist()
    assert restored==a+b


@pytest.mark.parametrize('changes',[{'ai_accuracy':1.1},{'distant_weight':-1},{'ai_mode':'unknown'},
                                  {'closeness_spread':1},{'grade_bias':float('nan')},{'ai_start':0}])
def test_invalid_parameters(changes):
    with pytest.raises(ValueError): replace(PublicAIParams(),**changes).validate()
