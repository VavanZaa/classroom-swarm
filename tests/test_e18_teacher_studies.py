"""E18 study assignment, population control, development selection and seed gates."""
from copy import deepcopy
from dataclasses import asdict
import numpy as np
import pytest

from scripts import e18_teacher_studies as e18
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4_teacher import simulate_teacher,validate_teacher_log


def test_star_realized_mean_and_spread_are_identical_across_class_sizes():
    for n in (15,24):
        k = e18.balanced_population(n)
        assert k.mean()==pytest.approx(.45)
        assert k.std()==pytest.approx(.10)
        assert np.min(k)>0 and np.max(k)<1
        pop = e18.cohort('star',100,2,n=n)
        assert sorted(pop['knowledge'])==sorted(k.tolist())


def test_school_assignment_preserves_the_same_students_traits_and_observed_groups():
    p = e18.cohort('kenya',100,0)
    assert len(p['student_ids'])==84 and len(p['low'])==len(p['high'])==42
    for arm in ('mixed','tracked'):
        assert all(len(ids)==42 for ids in p[arm])
        assert sorted(p[arm][0]+p[arm][1])==list(range(84))
        assert not set(p[arm][0]) & set(p[arm][1])
    assert set(p['tracked'][0])==set(p['low'])
    assert set(p['tracked'][1])==set(p['high'])
    assert max(p['observed_baseline'][i] for i in p['low']) <= min(p['observed_baseline'][i] for i in p['high'])
    assert any(p['knowledge'][i]>p['knowledge'][j] for i in p['low'] for j in p['high'])


def test_pretest_and_assignment_are_reproducible_and_confirmation_is_fresh():
    a = e18.cohort('kenya',e18.SEEDS['development'],2)
    assert a==e18.cohort('kenya',e18.SEEDS['development'],2)
    b = e18.cohort('kenya',e18.SEEDS['confirmation'],2)
    assert a['observed_baseline']!=b['observed_baseline']
    assert a['mixed']!=b['mixed']


def test_teacher_prior_is_observed_class_test_average_and_school_budget_is_equal():
    jobs = [j for j in e18.jobs('development',0) if j['study']=='kenya' and j['profile']=='reference']
    assert len(jobs)==4
    for job in jobs:
        r,pop,ids=job['resolved'],job['cohort'],job['global_ids']
        assert r['teacher']['observation_prior']==np.mean([pop['observed_baseline'][i] for i in ids])
        assert r['initial']['knowledge']['values']==[pop['knowledge'][i] for i in ids]
        assert r['teacher']['time_budget']==3
    assert sum(j['resolved']['teacher']['time_budget'] for j in jobs if j['arm']=='mixed')==sum(j['resolved']['teacher']['time_budget'] for j in jobs if j['arm']=='tracked')
    assert len({j['resolved']['teacher']['identity'] for j in jobs})==2


def test_candidate_parent_changes_are_explicit_and_bounded():
    p=e18.resolve_profile('star','short_explanations')
    assert p['teacher']=={'actions':['explanation'],'explanation_ticks':2}
    assert e18.resolve_profile('kenya','learning_2')['teacher']=={'learning_multiplier':2.}
    for job in e18.jobs('development',0):
        r=job['resolved'];TutoringParams(**r['params']).validate()
        assert r['params']['N'] in (15,24,42)
        assert not r['params']['allow_answer']


def fake_effects(study,values):
    result=[]
    groups=['all'] if study=='star' else ['low','high']
    for p in e18.profiles()[study]:
        for group in groups:
            for metric in ('exam','knowledge_gain'):
                result.append(dict(study=study,profile=p['name'],control='main',group=group,metric=metric,
                                   effect=values.get((p['name'],group,metric),-1.)))
    return result


def test_selection_prefers_smallest_change_and_never_uses_other_study_outcomes():
    values={('guidance_02','all',m):.2 for m in ('exam','knowledge_gain')}
    values.update({('short_explanations','all',m):5. for m in ('exam','knowledge_gain')})
    effects=fake_effects('star',values)
    result=e18.choose('star',effects)
    assert result['profile']=='guidance_02' and result['development_target_met']
    assert e18.choose('star',effects+fake_effects('kenya',{}))['profile']==result['profile']


def test_tracking_selection_requires_both_knowledge_and_exams_in_both_halves():
    values={('reference',group,m):.1 for group in ('low','high') for m in ('exam','knowledge_gain')}
    values[('reference','high','exam')]=-.01
    values.update({('readiness_03',group,m):.2 for group in ('low','high') for m in ('exam','knowledge_gain')})
    result=e18.choose('kenya',fake_effects('kenya',values))
    assert result['profile']=='readiness_03'
    assert not next(c for c in result['candidates'] if c['profile']=='reference')['eligible']


def test_failed_development_target_is_reported_instead_of_assumed():
    result=e18.choose('kenya',fake_effects('kenya',{}))
    assert not result['development_target_met']


def test_class_metrics_weight_subgroups_by_student_counts_not_class_counts():
    actual=e18.aggregate_class_metrics([dict(students=1,exam=0.,knowledge=10.),dict(students=3,exam=100.,knowledge=50.)])
    assert actual==dict(students=4,exam=75.,knowledge=40.)


def test_bootstrap_is_paired_reproducible_and_handles_exact_null():
    assert e18.paired([1.,2.,3.])==e18.paired([1.,2.,3.])
    assert e18.paired([0.]*12)['lo95']==e18.paired([0.]*12)['hi95']==0


def test_confirmation_needs_hashed_selection_gate(tmp_path):
    with pytest.raises(FileNotFoundError):
        e18.selected(tmp_path)
    (tmp_path/'development-review.md').write_text('review')
    e18.save_json(tmp_path/'selection.json',dict(studies={},gate_hashes={'development-review.md':e18.sha256(tmp_path/'development-review.md')}))
    assert e18.selected(tmp_path)=={}
    (tmp_path/'development-review.md').write_text('changed')
    with pytest.raises(ValueError,match='gate changed'):
        e18.selected(tmp_path)


def test_actual_class_runs_and_a30_audit_and_declared_cohort_identity_hold():
    job=next(e18.jobs('development',0))
    r=job['resolved'];p=TutoringParams(**{**r['params'],'H':1})
    graph=e18.make_graph(r['network'],p.N,job['seed'],0)
    log=simulate_teacher(p,graph,PublicAIDraws(job['seed'],0,p.N,p.items,p.exam_items),condition=job['name'],initial=r['initial'],teacher=r['teacher'])
    validate_teacher_log(log)
    assert len(log.tables['students'])==15 and len(log.tables['traits'])==15
    assert log.tables['teacher_identity'][0]['student_count']==15
    assert e18.metrics(log,list(range(15)))['students']==15
