"""E25 bounds, assignment integrity, aggregation and scientific classification."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import e25_plausible_parameter_fit as fit

def test_parameter_units_bounds_and_reference():
    v=fit.reference_vector(); values=fit.transform(v)
    for name,lo,hi,ref,log,path,cases in fit.PARAMETERS:
        assert 0<=lo<hi and lo<=values[name]<=hi
        assert values[name]==pytest.approx(ref)
    assert fit.transform(np.zeros(len(v)))=={p[0]:pytest.approx(p[1]) for p in fit.PARAMETERS}

@pytest.mark.parametrize('value',[-.01,1.01,float('nan')])
def test_invalid_candidate_rejected(value):
    v=fit.reference_vector(); v[0]=value
    with pytest.raises(AssertionError): fit.transform(v)

def test_search_does_not_change_population_or_treatment():
    original=fit.jobs('training',0,'default')
    candidate=fit.jobs('training',0,'candidate',np.ones(len(fit.PARAMETERS)))
    assert len(original)==len(candidate)==25
    for a,b in zip(original,candidate):
        assert a['groups']==b['groups'] and a['global_ids']==b['global_ids']
        assert a['resolved']['network']==b['resolved']['network']
        for name in ('N','H','ticks','exam_items','ai_mode','max_ai_uses'):
            assert a['resolved']['params'][name]==b['resolved']['params'][name]
        assert a['resolved']['initial']['knowledge']==b['resolved']['initial']['knowledge']
        assert a['resolved']['extensions']['teacher_work']['contract']==b['resolved']['extensions']['teacher_work']['contract']
        assert a['resolved']['extensions']['helper_contract']['enabled']==b['resolved']['extensions']['helper_contract']['enabled']

def test_teacher_preferences_shared_across_studies_and_arms():
    jobs=fit.jobs('training',0,'candidate',np.ones(len(fit.PARAMETERS)))
    for name in ('effort_cost','quadratic_cost','intrinsic_weight','belief_gain_rate'):
        assert len({j['resolved']['extensions']['teacher_work'][name] for j in jobs})==1

def test_pools_exogenous_and_distinct():
    a=fit.jobs('training',0,'x',fit.reference_vector()); b=fit.jobs('fresh',0,'x',fit.reference_vector())
    assert {j['replicate'] for j in a}.isdisjoint({j['replicate'] for j in b})
    for case in fit.MAIN:
        assert {i for j in a if j['case']==case for i in j['global_ids']}=={i for j in b if j['case']==case for i in j['global_ids']}

def test_aggregate_weights_students_not_number_of_sections():
    rows=[dict(case='x',arm='a',group='all',cohort=0,profile='p',section=0,students=2,score=10.),
          dict(case='x',arm='a',group='all',cohort=0,profile='p',section=1,students=6,score=30.)]
    assert fit.aggregate(rows)['x','a','all',0]['score']==25.

def test_null_equivalence_requires_interval_inside_band():
    rows=[]
    for rep,delta in enumerate([-.5,.5]):
        for arm,v in [('a',50+delta),('b',50.)]: rows.append(dict(case='x',arm=arm,group='all',cohort=rep,profile='p',section=0,students=5,score=v))
    result=fit.effects(rows,[fit.target('x','a','b','all','score','near_zero',.2)])[0]
    assert result['direction_match'] and not result['robust_match']

def test_no_structural_unrelated_null_in_fit():
    assert not any(t['metric']=='unrelated_potential' for t in fit.TARGETS)
