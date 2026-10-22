"""Experiment integrity, not desired-result tests."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import e22_a32_study_trends as e


def test_student_identity_and_realized_cohort_survive_reassignment():
    jobs=e.build_jobs(0)
    for case in ('star','kenya'):
        arms=['small','regular'] if case=='star' else ['mixed','tracked']
        cohorts=[]
        for arm in arms:
            values={}
            for j in jobs:
                if (j['case'],j['profile'],j['arm'])!=(case,'default',arm): continue
                assert j['resolved']['extensions']['student_ids']==j['global_ids']
                for i,k in zip(j['global_ids'],j['resolved']['initial']['knowledge']['values']):
                    assert i not in values; values[i]=k
            cohorts.append(values)
        assert cohorts[0]==cohorts[1]


def test_helpers_are_observed_upper_to_lower_and_controls_only_change_contract():
    jobs=[j for j in e.build_jobs(1) if j['case']=='seating' and j['profile']=='stronger_reward']
    by={j['arm']:j for j in jobs}
    for helper,recipient in by['reward']['resolved']['extensions']['helper_contract']['pairs']:
        assert helper in by['reward']['groups']['high'] and recipient in by['reward']['groups']['low']
    for arm,key in [('placebo','placebo_payment'),('high_cost','helper_cost_multiplier')]:
        a={k:v for k,v in by['reward']['resolved'].items() if k!='name'}
        b={k:v for k,v in by[arm]['resolved'].items() if k!='name'}
        assert e.config.legacy.differences(a,b)==[f'extensions.helper_contract.{key}']


def test_aggregation_weights_students_and_preserves_missingness():
    parts=[dict(students=15,x=1.,missing=None),dict(students=24,x=3.,missing=7.)]
    r=e.aggregate(parts)
    assert r['x']==(15+24*3)/39 and r['missing'] is None


def test_paired_bootstrap_and_primary_family_are_fixed():
    r=e.paired(np.ones(e.REPLICATES)*2.)
    assert r==dict(effect=2.,lo95=2.,hi95=2.)
    assert sum(s['primary'] for s in e.comparisons())==14
    for s in e.comparisons(): assert 'default' in s['profiles'] or not s['primary']


def test_every_declared_contrast_has_both_arms_and_exogenous_groups():
    jobs=e.build_jobs(2)
    for s in e.comparisons():
        for profile in s['profiles']:
            for arm in (s['a'],s['b']):
                selected=[j for j in jobs if (j['case'],j['profile'],j['arm'])==(s['case'],profile,arm)]
                assert selected and sum(len(j['groups'][s['group']]) for j in selected)>0
                for j in selected:
                    assert len(j['global_ids'])==j['resolved']['params']['N']
                    assert j['resolved']['extensions']['learning_process']['enabled']
