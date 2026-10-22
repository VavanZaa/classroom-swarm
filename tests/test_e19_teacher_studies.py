"""E19 checks the changed search, measurement-based assignment and preserved sources."""
import numpy as np
import pytest
from scripts import e19_teacher_studies as e19
from scripts import e18_teacher_studies as e18
from classroom_swarm.tutoring_settings import TutoringParams


def effects(study,patches):
    groups=['all'] if study=='star' else ['low','high']
    rows=[]
    for p in e19.profiles()[study]:
        for g in groups:
            for m in ('exam','knowledge_gain'):
                value,lower=patches.get((p['name'],g,m),(-1.,-2.))
                rows.append(dict(study=study,profile=p['name'],control='main',group=g,metric=m,effect=value,lo95=lower,hi95=value+1))
    return rows


def test_new_seeds_do_not_reuse_e18():
    assert not set(e19.SEEDS.values()) & set(e18.SEEDS.values())
    assert e19.SEEDS['development']!=e19.SEEDS['confirmation']
    assert e19.cohort('kenya',e19.SEEDS['development'],0)!=e19.cohort('kenya',e19.SEEDS['confirmation'],0)


@pytest.mark.parametrize('mean',[.4,.45,.5])
def test_shifted_population_retains_spread_and_same_students_in_both_arms(mean):
    pop=e19.cohort('kenya',100,0,mean=mean)
    k=np.asarray(pop['knowledge'])
    assert k.mean()==pytest.approx(mean)
    assert k.max()-k.min()==pytest.approx(.6)
    assert 0<k.min()<k.max()<1
    for arm in ('mixed','tracked'):
        assert sorted(pop[arm][0]+pop[arm][1])==list(range(84))
        assert len(pop[arm][0])==len(pop[arm][1])==42
    assert max(pop['observed_baseline'][i] for i in pop['low'])<=min(pop['observed_baseline'][i] for i in pop['high'])


def test_reference_retains_failed_e18_setup_and_selected_tracking_coefficient():
    for study in ('star','kenya'):
        old=e18.base_config(study)
        new=e19.base_config(study)
        assert new['params']==old['params'] and new['initial']==old['initial']
        expected={**old['teacher'],'learning_multiplier':2.} if study=='kenya' else old['teacher']
        assert new['teacher']==expected


def test_parent_bundles_are_explicit_and_all_candidates_resolve():
    assert e19.resolve_profile('star','brief_explanations_4')['teacher']==dict(actions=['explanation'],explanation_ticks=2,learning_multiplier=4.)
    assert e19.resolve_profile('kenya','readiness_08_learning_4')['params']=={'readiness_band':.8}
    assert e19.resolve_profile('kenya','readiness_08_learning_4')['teacher']=={'learning_multiplier':4.}
    for j in e19.jobs('development',0):
        p=TutoringParams(**j['resolved']['params']);p.validate()
        assert not p.allow_answer and p.N in (15,24,42)
        assert j['resolved']['teacher']['observation_prior']==np.mean([j['cohort']['observed_baseline'][g] for g in j['global_ids']])


def test_selection_rejects_weak_positive_means_and_prefers_fewer_changes():
    values={('reference','all',m):(.1,-.1) for m in ('exam','knowledge_gain')}
    values.update({('guidance_03','all',m):(.3,.02) for m in ('exam','knowledge_gain')})
    values.update({('brief_explanations_4','all',m):(5.,4.) for m in ('exam','knowledge_gain')})
    selected=e19.choose('star',effects('star',values))
    assert selected['profile']=='guidance_03' and selected['development_target_met']
    assert not next(c for c in selected['candidates'] if c['profile']=='reference')['eligible']


def test_selection_requires_both_knowledge_and_exam_support_in_each_half():
    values={('readiness_08',g,m):(.3,.01) for g in ('low','high') for m in ('exam','knowledge_gain')}
    values[('readiness_08','high','knowledge_gain')]=(.3,-.01)
    values.update({('learning_4',g,m):(.4,.02) for g in ('low','high') for m in ('exam','knowledge_gain')})
    assert e19.choose('kenya',effects('kenya',values))['profile']=='learning_4'


def test_failed_grid_remains_marked_unmet_and_ranked_by_minimum_exam_bound():
    values={('learning_4',g,m):(.1,-.01) for g in ('low','high') for m in ('exam','knowledge_gain')}
    result=e19.choose('kenya',effects('kenya',values))
    assert result['profile']=='learning_4' and not result['development_target_met']


def test_null_support_preserves_selected_calendar_and_disable_preserves_student_setup():
    selection={'star':{'profile':'brief_explanations_4'},'kenya':{'profile':'readiness_08_learning_4'}}
    jobs=list(e19.jobs('confirmation',0,selection))
    main=next(j for j in jobs if j['study']=='star' and j['control']=='main' and j['profile']=='brief_explanations_4' and j['arm']=='small')
    null=next(j for j in jobs if j['control']=='zero_support' and j['arm']=='small')
    disabled=next(j for j in jobs if j['control']=='disabled' and j['arm']=='small')
    for j in (null,disabled):
        assert j['resolved']['params']==main['resolved']['params']
        assert j['resolved']['initial']==main['resolved']['initial']
        assert j['cohort']==main['cohort']
    for field in ('actions','explanation_ticks','time_budget','curriculum','observation_prior'):
        assert null['resolved']['teacher'][field]==main['resolved']['teacher'][field]
    assert null['resolved']['teacher']['learning_multiplier']==0
    assert not disabled['resolved']['teacher']['enabled']


def test_fixed_curriculum_changes_only_target_policy_and_peers_are_separate():
    selection={'star':{'profile':'guidance_03'},'kenya':{'profile':'readiness_08_learning_4'}}
    jobs=list(e19.jobs('confirmation',0,selection))
    main=next(j for j in jobs if j['study']=='kenya' and j['control']=='main' and j['profile']==selection['kenya']['profile'] and j['arm']=='tracked' and j['section']==0)
    fixed=next(j for j in jobs if j['control']=='fixed' and j['arm']=='tracked' and j['section']==0)
    assert fixed['resolved']['params']==main['resolved']['params']
    assert fixed['resolved']['initial']==main['resolved']['initial']
    delta={k for k in fixed['resolved']['teacher'] if fixed['resolved']['teacher'][k]!=main['resolved']['teacher'][k]}
    assert delta=={'curriculum'}
    assert fixed['resolved']['teacher']['fixed_difficulty']==.5
    peer=next(j for j in jobs if j['control']=='peers' and j['arm']=='tracked' and j['section']==0)
    assert peer['resolved']['params']['allow_hint'] and peer['resolved']['network']['family']=='ER'


def test_preserved_historical_engines_and_e18_report_match_hashes():
    assert e19.historical()>274
