"""A32 functional acceptance gates; no test requires agreement with a field-study sign."""
from copy import deepcopy
from dataclasses import replace
import itertools
import numpy as np
import pytest
from classroom_swarm.effort_settings import resolve_effort, contract_value, RewardContract
from classroom_swarm.effort_runtime import dose_fraction, semantic, stable_initial
from classroom_swarm.effort_validation import validate_effort_log
from classroom_swarm.v4_effort_learning import simulate_effort
from classroom_swarm.v4_mechanisms import simulate_mechanisms
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.teacher_settings import TeacherSettings
from classroom_swarm.mechanism_config import make_graph, template


def run(x=None, teacher=None, initial=None, mechanisms=None, seed=72431, **kwargs):
    p = TutoringParams(**{**dict(N=4, H=3, items=12, exam_items=20, exam_every=1, feedback_delay=0,
        allow_answer=False, allow_hint=False, distant_weight=0, closeness_spread=0), **kwargs})
    graph = make_graph({**template()['network'], 'family':'CUSTOM', 'edges':[]}, p.N, seed, 0)
    teacher = TeacherSettings(enabled=False) if teacher is None else teacher
    log = simulate_effort(p, graph, PublicAIDraws(seed, 0, p.N, p.items, p.exam_items), initial=initial,
        teacher=teacher, mechanisms=mechanisms, extensions={'learning_process':{'enabled':True}} if x is None else x)
    validate_effort_log(log, p)
    return log


def constant(value): return {'kind':'constant', 'value':value}


@pytest.mark.parametrize('teacher_on', [False, True])
@pytest.mark.parametrize('topics', [False, True])
def test_all_off_exact_a31_manifest_and_every_raw_table(teacher_on, topics):
    p = TutoringParams(N=4, H=2, exam_items=20)
    graph = make_graph({**template()['network'], 'family':'CUSTOM', 'edges':[]}, 4, 11, 0)
    teacher = TeacherSettings(enabled=teacher_on)
    mechanisms = {'topics':{'enabled':topics}}
    a = simulate_effort(p, graph, PublicAIDraws(11,0,4,p.items,p.exam_items), teacher=teacher, mechanisms=mechanisms)
    b = simulate_mechanisms(p, graph, PublicAIDraws(11,0,4,p.items,p.exam_items), teacher=teacher, mechanisms=mechanisms)
    assert a.manifest == b.manifest and a.tables == b.tables
    validate_effort_log(a)


@pytest.mark.parametrize('effort,multiplier', [(0,1),(1,0),(.5,1),(1,1),(1,2)])
def test_efficiency_converts_productive_dose_without_inflation(effort, multiplier):
    assert dose_fraction(.06,3,multiplier,effort) == pytest.approx(1 - .98 ** (multiplier*effort))
    assert dose_fraction(3,3,multiplier,effort) == (1 if multiplier*effort > 0 else 0)


def test_task_response_uses_prelearning_knowledge():
    a = run(initial={'knowledge':constant(.2),'confidence':constant(.8),'effort_aversion':constant(0.)}, H=1, epsilon=0.)
    packets = [r for r in a.tables['packets'] if r['origin']=='student']
    assert packets and packets[0]['probability'] == .2
    assert any(r['after'] > r['before'] for r in a.tables['topic_learning'])


@pytest.mark.parametrize('branch', ['zero_effort','no_attention','no_content','zero_multiplier'])
def test_nonlearning_reasons_still_consume_time_and_effort(branch):
    l={'enabled':True, 'attention':constant(1.),'distraction':constant(0.)}
    if branch=='zero_effort': l['effort_grid']=[0.]
    if branch=='no_attention': l.update(attention=constant(0.), attention_effort_weight=0.)
    if branch=='no_content': l.update(material_access=False, self_reasoning_quality=0.)
    if branch=='zero_multiplier':
        l['source_multipliers']={key:0. for key in resolve_effort().learning_process.source_multipliers}
    a=run({'learning_process':l}, epsilon=1., H=4)
    assert a.tables['learning_doses'] and a.tables['student_costs']
    assert not a.tables['topic_learning']
    assert any(r['end']>r['start'] and r['cost']>0 for r in a.tables['student_costs'])
    if branch=='zero_effort': assert all(r['probability']==0 for r in a.tables['packets'])


def test_score_only_feedback_does_not_supply_content():
    a=run({'learning_process':{'enabled':True,'corrective_feedback':False,'self_reasoning_quality':0.}}, H=4)
    assert a.tables['homework_feedback']
    assert not a.tables['topic_learning']


def test_absence_and_inattention_are_separate():
    teacher=TeacherSettings(enabled=True, participation_probability=0., actions=['instruction'], time_budget=3)
    a=run(teacher=teacher, H=1)
    assert all(not r['attended'] for r in a.tables['teacher_attendance'])
    assert not any(r['source']=='teacher' for r in a.tables['learning_doses'])
    b=run({'learning_process':{'enabled':True,'attention':constant(0.),'attention_effort_weight':0.}},
        teacher=replace(teacher,participation_probability=1.), H=1)
    assert all(r['attended'] for r in b.tables['teacher_attendance'])
    assert all(r['fraction']==0 for r in b.tables['learning_doses'] if r['source']=='teacher')


def test_effort_forecast_performance_changes_with_effort():
    a=run(H=1)
    rows=[r for r in a.tables['effort_choices'] if r['activity']=='attempt' and r['tick']==0 and r['student']==0]
    assert len(rows)==3
    assert [r['predicted_performance'] for r in rows]==sorted(r['predicted_performance'] for r in rows)
    assert rows[0]['predicted_performance']==0
    assert rows[-1]['predicted_performance']>0


def test_stable_student_draws_and_initial_traits_survive_reassignment():
    p=TutoringParams(N=3); draws=PublicAIDraws(91,0,3,p.items,p.exam_items)
    _,a,_,_,_=stable_initial(p,draws,None,[10,20,30])
    _,b,_,_,_=stable_initial(p,draws,None,[30,10,20])
    for name in ('knowledge','learning_efficiency','effort_aversion','teaching_skill'):
        assert np.array_equal(a[name], b[name][[1,2,0]])
    assert np.array_equal(semantic(draws,142,20,2,3,size=12),semantic(draws,142,20,2,3,size=12))


def teacher_case(**work):
    return {'learning_process':{'enabled':True,'attention':constant(1.),'distraction':constant(0.)},
        'teacher_work':{'enabled':True, **work}}


def test_teacher_resource_budget_protected_instruction_and_nonoverlap():
    a=run(teacher_case(), teacher=TeacherSettings(enabled=True,grading_ticks_per_student=1), H=3)
    assert all(r['spent']<=r['total_budget'] and r['spent']+r['unused']==r['total_budget'] for r in a.tables['teacher_resources'])
    assert all(sum(r['cost'] for r in a.tables['teacher_work_schedule'] if r['homework']==h and r['kind']=='instruction')==3 for h in range(1,4))
    assert any(r['period']=='after' and r['cost']>0 for r in a.tables['teacher_work_schedule'])


def test_infeasible_instruction_rejected_before_simulation_and_crowdout_declared():
    with pytest.raises(ValueError, match='infeasible protected'):
        run(teacher_case(total_budget=2), teacher=TeacherSettings(enabled=True))
    a=run(teacher_case(total_budget=2,allow_instruction_crowdout=True), teacher=TeacherSettings(enabled=True))
    assert any(r['reason']=='declared_crowdout' for r in a.tables['teacher_queue'])


def test_preparation_has_reusable_product_with_tax_only_control():
    common=dict(total_budget=4, actions=[])
    a=run(teacher_case(**common, preparation_quality_bonus=.5), teacher=TeacherSettings(enabled=True,teaching_skill=.2))
    b=run(teacher_case(**common, preparation_quality_bonus=0.), teacher=TeacherSettings(enabled=True,teaching_skill=.2))
    assert a.tables['teacher_preparation'][-1]['after'] > a.tables['teacher_preparation'][0]['after']
    assert a.tables['teacher_preparation'][0]['effective_skill'] > .2
    assert all(r['effective_skill']==.2 for r in b.tables['teacher_preparation'])
    assert a.tables['teacher_work_schedule']==b.tables['teacher_work_schedule']


def test_partial_lesson_scales_dose_and_guidance_forecasts_downstream():
    a=run(teacher_case(protected_instruction_ticks=1,preparation_ticks=0,actions=['guidance'],
        effort_cost=0.,quadratic_cost=0.), teacher=TeacherSettings(enabled=True), H=1)
    doses=[r for r in a.tables['learning_doses'] if r['source']=='teacher']
    assert doses and all(r['duration']==1 and r['dose']<=1/3 for r in doses)
    forecasts=[r for r in a.tables['teacher_forecasts'] if r['action']=='guidance']
    assert forecasts and all(r['immediate_concept_gain']==0 for r in forecasts)
    assert any(r['predicted_after']>r['observed_before'] for r in forecasts)


@pytest.mark.parametrize('denominator,missing',list(itertools.product(['eligible','observed'],['zero','exclude'])))
def test_contract_evaluator_denominator_gain_curvature_and_missing(denominator,missing):
    c=RewardContract(strength=2.,power=2.,mode='gain',denominator=denominator,missing=missing)
    denominator_value=2 if denominator=='eligible' or missing=='zero' else 1
    assert contract_value(c,[.8,None],[.3,.2])==pytest.approx(2*.25/denominator_value)
    assert contract_value(replace(c,forms=['linked']),[1.],form='novel')==0


def test_teacher_payments_use_released_contract_and_delay():
    a=run(teacher_case(contract={'payment_delay':0,'power':2.,'mode':'gain'}), teacher=TeacherSettings(enabled=True), H=3)
    assert a.tables['contract_observations'] and a.tables['contract_payments']
    assert all(r['signal_homework']>r['source_homework'] for r in a.tables['contract_payments'])


def helper_case(**helper):
    return {'learning_process':{'enabled':True,'attention':constant(1.),'distraction':constant(0.)},
        'helper_contract':{'enabled':True,'pairs':[[0,1],[2,3]],'baseline_scores':[.8,.2,.8,.2],
            'prize':100.,'belief_progress_rate':.3,'top_fraction':.5, **helper}}


def test_helper_offer_accept_explain_and_delayed_observed_progress_reward():
    a=run(helper_case(payment_delay=0), initial={'knowledge':{'kind':'values','values':[.8,.2,.8,.2]}}, H=4)
    assert any(r['accepted'] for r in a.tables['helper_offers'])
    assert a.tables['helper_sessions'] and a.tables['helper_checkpoints'] and a.tables['helper_payments']
    for r in a.tables['helper_checkpoints']:
        assert r['progress']==pytest.approx(r['score']-r['baseline']) if r['score'] is not None else r['progress'] is None
    assert all(r['homework']>r['source_homework'] for r in a.tables['helper_payments'])
    assert all(r['duration']==3 for r in a.tables['learning_doses'] if r['source']=='helper')


def test_zero_and_placebo_reward_remove_marginal_offer_incentive():
    a=run(helper_case(prize=0.,certificate_value=0.,helper_intrinsic_value=0.),H=1)
    b=run(helper_case(placebo_payment=True,helper_intrinsic_value=0.),H=1)
    assert a.tables['helper_offers'] and b.tables['helper_offers']
    assert all(r['expected_reward']==0 for r in a.tables['helper_offers']+b.tables['helper_offers'])
    assert not a.tables['helper_sessions'] and not b.tables['helper_sessions']


def test_helper_refusal_and_high_cost_prevent_sessions():
    a=run(helper_case(recipient_acceptance=0.), H=1)
    b=run(helper_case(helper_cost_multiplier=10000.), H=1)
    assert not a.tables['helper_sessions'] and not b.tables['helper_sessions']
    assert any(r['offered'] and not r['accepted'] for r in a.tables['helper_offers'])


def test_helper_payments_do_not_directly_change_knowledge():
    a=run(helper_case(prize=100.,placebo_payment=True,top_fraction=1.,payment_delay=0,helper_intrinsic_value=0.),H=3)
    b=run(helper_case(prize=0.,placebo_payment=True,top_fraction=1.,payment_delay=0,helper_intrinsic_value=0.),H=3)
    assert a.tables['topic_states']==b.tables['topic_states']
    assert a.tables['helper_payments'] != b.tables['helper_payments']


def test_format_only_dose_has_no_direct_concept_or_novel_form_gain():
    a=run({'learning_process':{'enabled':True,'future_test_value':constant(100.),'effort_grid':[1.],
        'attention':constant(1.),'distraction':constant(0.)},
        'test_preparation':{'enabled':True,'concept_share':0.,'format_share':1.}},H=2,epsilon=0.,
        initial={'effort_aversion':constant(0.),'knowledge':constant(.2)})
    assert a.tables['format_learning']
    assert not a.tables['topic_learning']
    assert any(r['form']=='familiar' and r['after']>0 for r in a.tables['format_learning'])
    assert all(r['after']==0 for r in a.tables['format_learning'] if r['form']!='familiar')
    assert all(r['probability']==pytest.approx(.2) for r in a.tables['assessment_items'] if r['form'] in ('novel','core'))


def test_exam_participation_missing_score_and_potential_draws_are_separate():
    x={'learning_process':{'enabled':True},'test_preparation':{'enabled':True,'participation':True,'participation_cost':0.}}
    a=run(x,H=1); x['test_preparation']['participation_cost']=100.
    b=run(x,H=1)
    assert all(r['score'] is None for r in b.tables['assessment_scores'])
    assert all(r['cohort_contribution']==0 for r in b.tables['assessment_scores'])
    assert [r['potential_draw'] for r in a.tables['assessment_items']]==[r['potential_draw'] for r in b.tables['assessment_items']]
    assert a.tables['topic_states']==b.tables['topic_states']


@pytest.mark.parametrize('table,column', [('learning_doses','dose'),('topic_learning','after'),('assessment_items','probability')])
def test_raw_audit_detects_corruption(table,column):
    a=run(H=2); assert a.tables[table]
    a.tables[table][0][column]+=.1
    with pytest.raises(AssertionError): validate_effort_log(a)


@pytest.mark.parametrize('x', [ {'learning_process':{'unknown':1}}, {'test_preparation':{'concept_share':.8,'format_share':.8}},
    {'student_ids':[1,1,2,3]}, {'teacher_work':{'enabled':True,'actions':['magic']}},
    {'helper_contract':{'pairs':[[0,1],[1,2]]}}, {'test_preparation':{'format_transfer':[[2.]]}} ])
def test_bad_declarations_rejected(x):
    with pytest.raises(ValueError): run(x,teacher=TeacherSettings(enabled=True))


def test_shared_practice_partitions_real_explanation_effort():
    p=TutoringParams(N=4,H=1,exam_items=20,exam_every=1,tutoring_activity='shared_practice',allow_answer=False,distant_weight=0)
    graph=make_graph({**template()['network'],'family':'CUSTOM','edges':[[i,j] for i in range(4) for j in range(i+1,4)]},4,32,0)
    a=simulate_effort(p,graph,PublicAIDraws(32,0,4,p.items,p.exam_items),extensions={'learning_process':{'enabled':True}})
    validate_effort_log(a)
    for i in range(4):
        doses=[r for r in a.tables['learning_doses'] if r['student']==i and r['start']==0]
        assert sum(r['effort'] for r in doses)<=1.+1e-12


def runtime_for_plan(x=None, mechanisms=None):
    from classroom_swarm.v4 import V4Log
    from classroom_swarm.mechanism_settings import resolve_mechanisms
    from classroom_swarm.effort_runtime import EffortRuntime
    p=TutoringParams(N=4,H=2,exam_items=20)
    draws=PublicAIDraws(38,0,4,p.items,p.exam_items)
    _,_,traits,_,_=stable_initial(p,draws,None,[0,1,2,3])
    return EffortRuntime(resolve_mechanisms(mechanisms),TeacherSettings(enabled=True),p,traits.K0,
        np.full((4,4),.5),V4Log({}),resolve_effort(x or teacher_case()),draws,traits)


def test_teacher_plan_does_not_read_latent_student_states_or_future_draws():
    a=runtime_for_plan(); b=runtime_for_plan()
    a.remaining_total=b.remaining_total=7
    b.knowledge[:]=.99; b.student_fatigue[:]=1.; b.formats[:]=1.
    b.draws=PublicAIDraws(999,999,4,b.p.items,b.p.exam_items)
    arguments=(TeacherSettings(enabled=True),np.full(4,.5),np.zeros(4,int),np.full(4,-1),1,0,0)
    assert a.teacher_plan(*arguments)==b.teacher_plan(*arguments)
    assert a.log.tables['teacher_forecasts']==b.log.tables['teacher_forecasts']


@pytest.mark.parametrize('denominator,missing',list(itertools.product(['eligible','observed'],['zero','exclude'])))
def test_payment_forecast_exactly_integrates_same_realized_contract(denominator,missing):
    r=runtime_for_plan(teacher_case(contract={'denominator':denominator,'missing':missing,'mode':'gain','power':2.}))
    scores=[.8,.7,.6,.9]; probabilities=[.1,.3,.5,.8]; baseline=[.2]*4
    expectation=0.
    for present in itertools.product([False,True],repeat=4):
        probability=np.prod([probabilities[i] if present[i] else 1-probabilities[i] for i in range(4)])
        outcomes=[scores[i] if present[i] else None for i in range(4)]
        expectation+=probability*contract_value(r.w.contract,outcomes,baseline)
    assert r.expected_contract(scores,probabilities,baseline,'core')==pytest.approx(expectation)


def test_unrelated_exam_cannot_pay_teacher_for_untransferred_topic_gain_forecast():
    x=teacher_case(actions=['explanation'],contract={'forms':['unrelated']},intrinsic_weight=0.,effort_cost=0.,quadratic_cost=0.)
    x['test_preparation']={'enabled':True}
    r=runtime_for_plan(x, {'topics':{'enabled':True,'schedule':[0,0]}}); r.remaining_total=7
    r.teacher_plan(TeacherSettings(enabled=True),np.full(4,.5),np.zeros(4,int),np.full(4,-1),1,0,0)
    assert r.log.tables['teacher_forecasts']
    assert all(row['expected_payment_increment']==0 for row in r.log.tables['teacher_forecasts'])


def test_followup_changes_access_without_concept_gain():
    x=teacher_case(actions=['followup'],contract={'strength':10.},protected_instruction_ticks=0,preparation_ticks=0)
    x['test_preparation']={'enabled':True,'participation':True,'participation_cost':.6}
    a=run(x,teacher=TeacherSettings(enabled=True),H=1)
    assert a.tables['teacher_followup']
    assert all(r['K_before']==r['K_after'] for r in a.tables['teacher_followup'])


def test_helper_tournament_fractional_quota_and_tie_lottery():
    r=runtime_for_plan(helper_case(top_fraction=.25,payment_delay=0))
    r.helper_pending=[dict(source_homework=1,scores=[.8,.3,.8,.3],release=2)]
    r.release_payments(2)
    rows=r.log.tables['helper_checkpoints']; winners=sum(row['winner'] for row in rows)
    assert len(rows)==2 and winners in (0,1)
    assert all(row['quota']==.5 for row in rows)
    if winners:
        assert next(row for row in rows if row['winner'])['tie_draw']==min(row['tie_draw'] for row in rows)
