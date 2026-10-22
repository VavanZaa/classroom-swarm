"""E23 protocol/cohort integrity; no assertion of the papers' effect signs."""
import sys
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import e23_promising_mechanisms as e

def test_design_covers_all_previous_families_and_new_probe():
    jobs=e.build_jobs('development',0)
    assert len(jobs)==106
    assert {j['case'] for j in jobs}==set(e.old.CASES)|{'india_probe'}
    assert {j['variant'] for j in jobs}=={'A32','A33','curriculum_only','old_accuracy','fixed_curriculum','forecast_only','forecast_group','no_reasoning'}

@pytest.mark.parametrize('case',['star','kenya'])
def test_same_global_school_cohort_across_reassignment(case):
    jobs=[j for j in e.build_jobs('development',0) if j['case']==case and j['variant']=='A33']
    cohorts={}
    for j in jobs:
        cohorts.setdefault(j['arm'],{}).update(zip(j['global_ids'],j['resolved']['initial']['knowledge']['values']))
    assert len(cohorts)==2 and list(cohorts.values())[0]==list(cohorts.values())[1]

def test_model_arms_share_original_traits_and_opportunities():
    jobs=e.build_jobs('development',0); by={}
    for j in jobs: by.setdefault((j['case'],j['profile'],j['arm'],j['section']),{})[j['variant']]=j
    for variants in by.values():
        a=variants['A32']; b=variants['A33']
        assert a['replicate']==b['replicate'] and a['seed']==b['seed']
        for field in ('initial','params','teacher','mechanisms','extensions','network'): assert a['resolved'][field]==b['resolved'][field]

def test_teacher_cost_correction_and_declared_low_access():
    jobs=e.build_jobs('development',0)
    for j in jobs:
        if j['case']!='teacher_rewards': continue
        x=j['resolved']['extensions']['test_preparation']
        assert x['participation_cost']==0
        assert all(exam['access_cost']==(.6 if j['profile']=='default' else .35) for exam in x['exams'])

def test_confirmation_uses_distinct_frozen_draw_cohorts():
    a=e.build_jobs('development',0); b=e.build_jobs('confirmation',0)
    assert {j['replicate'] for j in a}=={30000}
    assert {j['replicate'] for j in b}=={31000}
    assert set(range(30000,30002)).isdisjoint(range(31000,31016))

def test_bootstrap_pairs_cohorts_and_preserves_exact_identity():
    assert e.paired([0]*16)=={'effect':0.,'lo95':0.,'hi95':0.}
    x=e.paired(np.arange(16)); assert x['lo95']<x['effect']<x['hi95']
    assert e.paired(np.arange(16))==x

def test_unknown_or_infeasible_study_settings_are_preflighted():
    j=next(j for j in e.build_jobs('development',0) if j['variant']=='A33' and j['case']=='teacher_rewards')
    c=e.config.template(); c.update(seed=j['seed'],replicates=1,conditions=[deepcopy(j['resolved'])])
    e.config.preflight(e.config.resolve_config(c))
    c['conditions'][0]['design']['group_preparation']['feedback_capacity']=0
    with pytest.raises(ValueError): e.config.resolve_config(c)
