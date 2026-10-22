"""A24 user clarification: everyone receives grades, no checking study action."""
from dataclasses import replace
import json
import numpy as np
import pytest
from classroom_swarm.graphs import generate_er, _from_edges
from classroom_swarm.v4 import V4Draws, activity_scores
from classroom_swarm.v4_grades import (GradeParams, simulate_grades, grade_credit,
    grade_update, grade_activity_scores, validate_grade_log)


def run(p=None, seed=82):
    p = p or GradeParams(N=6,H=8)
    return simulate_grades(p, generate_er(p.N,3,71), V4Draws(seed,0,p.N,p.items,p.exam_items))


@pytest.mark.parametrize('seed',[82,95,101])
def test_universal_next_homework_grades_and_no_checking(seed):
    log=run(seed=seed)
    validate_grade_log(log)
    assert {r['homework'] for r in log.tables['homework_feedback']}==set(range(2,10))
    # Receiving grades consumes no within-homework time; no check event exists.
    assert not any('check' in r['action'] for r in log.tables['events'])
    assert all(r['K_before']==r['K_after'] for r in log.tables['homework_feedback'])


def test_grade_reactions_cannot_leak_into_first_homework():
    p=GradeParams(N=6,H=8)
    a,b=run(p),run(replace(p,grade_response=0,eta_benefit=0))
    for table in ('events','students','requests','packets'):
        assert [r for r in a.tables[table] if r['homework']==1]==[
            r for r in b.tables[table] if r['homework']==1]
    # After receipt, at least some changed decisions are possible.
    assert a.tables['events']!=b.tables['events']


def test_rewarding_copied_grade_reinforces_answer_without_knowledge():
    p=GradeParams()
    credit,route=grade_credit(dict(copied=True,assisted=True),[3,0,1])
    b,c,pressure,feeling=grade_update(np.array([.5,.5,.5]),.5,.9,credit,True,True,p)
    assert route=='answer' and list(credit)==[0,0,1]
    np.testing.assert_allclose(b,[.5,.5,.58])
    assert c==pytest.approx(.508)
    assert feeling>0 and pressure==0


def test_bad_grade_encourages_copying_then_good_grade_resets():
    p=GradeParams()
    b,c,pressure,feeling=grade_update(np.array([.5,.5,.8]),.5,.2,[0,0,1],True,True,p)
    assert b[2]<.8 and feeling<0 and pressure==pytest.approx(.55)
    args=(c,.5,b,.15,.4,True,False,(.5,.5),True,12)
    old=activity_scores(p,*args)
    new=grade_activity_scores(p,*args,shortfall=pressure)
    for key in new:
        assert new[key]-old[key]==pytest.approx(.22 if key == 'answer' else 0)
    assert grade_update(b,c,.9,[1,0,0],False,True,p)[2]==0
    # Scarce time or isolation still masks infeasible social work.
    masked=grade_activity_scores(p,c,.5,b,.15,.4,True,False,(0,0),False,1,shortfall=pressure)
    assert set(masked)=={'wait','submit'}


def test_missing_work_receives_grade_and_pressure_without_false_self_assessment():
    p=GradeParams(N=4,H=2,ticks=1)
    log=simulate_grades(p,_from_edges('ER',4,{},0,[]),V4Draws(82,0,4,10,30))
    validate_grade_log(log)
    assert all(r['route']=='missing' and r['grade']==0 and r['shortfall_after']==p.grade_target
               and r['C_before']==r['C_after'] for r in log.tables['homework_feedback'])


def test_guided_route_credit_and_successive_state_continuity():
    credit,route=grade_credit(dict(copied=False,assisted=True),[1,1,0])
    assert route=='guided' and list(credit)==[.5,.5,0]
    log=run()
    fb={(r['homework'],r['student']):r for r in log.tables['homework_feedback']}
    for row in log.tables['students']:
        if row['homework']>1:
            previous=fb[row['homework'],row['student']]
            np.testing.assert_allclose([row['B_attempt'],row['B_hint'],row['B_answer']],
                                      json.loads(previous['B_after']),rtol=0,atol=0)
            assert row['grade_shortfall']==previous['shortfall_after']
    for i in range(6):
        for h in range(3,10):
            assert fb[h,i]['B_before']==fb[h-1,i]['B_after']


def test_reproducibility_and_gain_only_from_attempts_or_explanation():
    a,b=run(),run()
    assert a.tables==b.tables
    for i in range(6):
        gain=sum(e['K_after']-e['K_before'] for e in a.tables['events']
                 if e['student']==i and e['action'] in {'attempt','help_hint'})
        last=next(r for r in a.tables['students'] if r['homework']==8 and r['student']==i)
        assert gain==pytest.approx(last['K']-a.tables['traits'][i]['K0'],abs=1e-12)


def test_pressure_has_no_effect_when_cheating_unavailable():
    p=GradeParams(N=6,H=8,allow_answer=False)
    assert run(p).tables==run(replace(p,grade_response=0)).tables


@pytest.mark.parametrize('changes',[{'allow_check':True},{'grade_response':-1},{'grade_response':float('nan')},
                                  {'grade_target':2},{'grade_target':float('inf')}])
def test_invalid_grade_parameters(changes):
    with pytest.raises(ValueError):
        replace(GradeParams(),**changes).validate()
