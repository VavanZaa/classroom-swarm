"""A33 acceptance checks assert mechanisms/accounting, never study trend signs."""
from copy import deepcopy
import numpy as np
import pytest
from classroom_swarm import promising_config as config
from classroom_swarm.promising_settings import centered_skills, resolve_promising
from classroom_swarm.v4_promising import simulate_promising
from classroom_swarm.v4_effort_learning import simulate_effort
from classroom_swarm.promising_validation import validate_promising_log
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws

def constant(v): return {'kind':'constant','value':v}

def declaration(n=4,h=3,teacher=True):
    c=config.template(); c.update(seed=88101,replicates=1)
    c['params'].update(N=n,H=h,exam_every=1,exam_items=36,feedback_delay=0,tutoring_activity='joint_practice',allow_hint=False,allow_answer=False)
    c['network'].update(family='CUSTOM',edges=[])
    c['initial'].update(knowledge=constant(.45),confidence=constant(.5),effort_aversion=constant(.1))
    c['teacher'].update(enabled=teacher,grading_ticks_per_student=0,admin_ticks=0,observation_sources=['exam'])
    c['extensions']['learning_process']['enabled']=True
    c['extensions']['teacher_work'].update(enabled=teacher,total_budget=8,actions=['coaching'],effort_cost=.0001,intrinsic_weight=1.)
    c['extensions']['test_preparation'].update(enabled=True)
    return c

def run(c):
    r=config.resolve_config(c); config.preflight(r); v=r['conditions'][0]; p=TutoringParams(**v['params'])
    g=config.make_graph(v['network'],p.N,c['seed'],0); draws=PublicAIDraws(c['seed'],0,p.N,p.items,p.exam_items)
    log=simulate_promising(p,g,draws,v['name'],v['initial'],v['teacher'],v['mechanisms'],v['extensions'],v['design'])
    validate_promising_log(log,p)
    return log

@pytest.mark.parametrize('teacher',[False,True])
@pytest.mark.parametrize('topics',[False,True])
def test_disabled_exact_a32(teacher,topics):
    c=declaration(teacher=teacher); c['mechanisms']['topics']['enabled']=topics
    a=run(c); r=config.resolve_config(c)['conditions'][0]; p=TutoringParams(**r['params'])
    b=simulate_effort(p,config.make_graph(r['network'],p.N,c['seed'],0),PublicAIDraws(c['seed'],0,p.N,p.items,p.exam_items),r['name'],r['initial'],r['teacher'],r['mechanisms'],r['extensions'])
    assert a.manifest==b.manifest and a.tables==b.tables

def test_projection_preserves_means_and_bounds():
    k=np.linspace(0,1,101); skills=centered_skills(k,[.4,0,-.4])
    assert np.allclose(skills.mean(axis=1),k,atol=1e-14)
    assert np.all((skills>=0)&(skills<=1))
    assert np.all(skills[:,0]>=skills[:,1]) and np.all(skills[:,1]>=skills[:,2])

def test_curriculum_and_common_tagged_assessments():
    c=declaration(); c['design']['curriculum']['enabled']=True
    a=run(c)
    assert a.manifest['topic_count']==3
    assert {r['topic'] for r in a.tables['assessment_items']}=={0,1,2}
    assert all(abs(r['initial_mean']-r['base_K'])<1e-12 for r in a.tables['curriculum_projection'])

def test_prerequisite_failure_no_knowledge_credit():
    c=declaration(h=2); c['design']['curriculum'].update(enabled=True,adaptive=False,fixed_level=1,initial_values=[[0.,.2,.1]]*4)
    a=run(c)
    assert a.tables['learning_doses'] and all(r['fraction']==0 for r in a.tables['learning_doses'])
    assert not a.tables['topic_learning']

def test_teacher_policy_cannot_read_hidden_knowledge():
    c=declaration(h=1); c['design']['curriculum']['enabled']=True; c['design']['teacher_forecast']['enabled']=True
    c['teacher']['observation_coverage']=0.
    a=run(c); c['initial']['knowledge']=constant(.9); b=run(c)
    assert a.tables['curriculum_choices']==b.tables['curriculum_choices']
    assert a.tables['teacher_forecasts']==b.tables['teacher_forecasts']

def test_group_consumes_whole_time_but_only_delivery_learns():
    c=declaration(n=8,h=2); c['design']['teacher_forecast']['enabled']=True; c['design']['group_preparation']['enabled']=True
    a=run(c)
    actions=[r for r in a.tables['teacher_actions'] if r.get('scope')=='group']
    assert actions
    assert all(r['cost']==3 for r in actions)
    doses=[r for r in a.tables['learning_doses'] if r['source']=='coaching']
    assert any(r['duration']==2 and r['reserved_duration']==3 for r in doses)
    assert a.tables['teacher_format_expectations']
    assert all(r['spent']<=8 for r in a.tables['teacher_resources'])

def test_participation_evidence_waits_for_release():
    c=declaration(h=4); c['design']['teacher_forecast']['enabled']=True
    c['extensions']['test_preparation']['participation']=True
    c['extensions']['test_preparation']['participation_cost']=.6
    a=run(c)
    assert a.tables['teacher_belief_updates']
    assert all(r['homework']>=r['release']>r['source_homework'] for r in a.tables['teacher_belief_updates'])

def test_shared_reasoning_can_construct_without_initial_answer():
    c=declaration(n=8,h=4,teacher=False)
    c['params'].update(allow_hint=True,tutoring_activity='shared_practice')
    c['network']['edges']=[[i,j] for i in range(8) for j in range(i+1,8)]
    c['extensions']['learning_process']['future_test_value']=constant(20.)
    c['design']['shared_reasoning']['enabled']=True
    a=run(c)
    assert a.tables['shared_reasoning'] and any(r['constructed']>0 for r in a.tables['shared_reasoning'])
    corrupt=deepcopy(a); corrupt.tables['shared_reasoning'][0]['constructed']+=1
    with pytest.raises(AssertionError): validate_promising_log(corrupt)

@pytest.mark.parametrize('branch,field,value',[
    ('curriculum','prerequisites',[-1,1,1]),('curriculum','offsets',[0]),
    ('curriculum','initial_values',[[1,2,3]]),('curriculum','pretest_items',0),
    ('teacher_forecast','uncertainty',0.),('group_preparation','feedback_capacity',0),
    ('shared_reasoning','reasoning_probability',1.1),('curriculum','enabled',1),
    ('group_preparation','delivery_ticks',True),('teacher_forecast','initial_bias',float('nan')),
])
def test_strict_invalid_declarations(branch,field,value):
    c=declaration(); c['design'][branch][field]=value
    with pytest.raises((ValueError,TypeError)): config.resolve_config(c)

def test_unknown_design_and_branch_fields_rejected():
    with pytest.raises(ValueError): resolve_promising({'novel_magic':{}})
    with pytest.raises(ValueError): resolve_promising({'curriculum':{'magic':1}})

def test_design_only_contrast_is_resolved():
    c=declaration(); c['conditions']=[{'name':'reference'},{'name':'curriculum','design':{'curriculum':{'enabled':True}}}]
    c['contrasts']=[dict(condition='curriculum',reference='reference',kind='single_parameter',identity='not_identity')]
    r=config.resolve_config(c)
    assert r['contrasts'][0]['changed_settings']==['design.curriculum.enabled']

@pytest.mark.parametrize('curriculum,forecast,group,reasoning',[
    (True,False,False,False),(False,True,False,False),(False,False,False,True),
    (True,True,False,False),(True,True,True,False),(True,True,True,True),
])
def test_branch_combinations_and_saved_raw_roundtrip(curriculum,forecast,group,reasoning,tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    c=declaration(h=2)
    for name,value in [('curriculum',curriculum),('teacher_forecast',forecast),('group_preparation',group),('shared_reasoning',reasoning)]: c['design'][name]['enabled']=value
    a=run(c)
    for name,rows in a.tables.items():
        file=tmp_path/f'{name}.parquet'; pq.write_table(pa.Table.from_pylist(rows),file)
        a.tables[name]=pq.read_table(file).to_pylist()
    validate_promising_log(a)
    if group: assert any(r.get('scope')=='group' for r in a.tables['teacher_actions'])

def test_stable_global_ids_survive_reassignment():
    c=declaration(teacher=False,h=2); c['design']['curriculum']['enabled']=True
    c['initial']['knowledge']={'kind':'values','values':[.2,.4,.6,.8]}
    c['extensions']['student_ids']=[11,7,31,2]
    a=run(c)
    c['initial']['knowledge']['values']=[.8,.6,.4,.2]; c['extensions']['student_ids']=[2,31,7,11]
    b=run(c)
    def initial_by_id(log):
        ids=log.manifest['extensions']['student_ids']
        return {(ids[r['student']],r['topic']):r['knowledge'] for r in log.tables['topic_initial']}
    assert initial_by_id(a)==initial_by_id(b)
    def exams_by_id(log):
        ids=log.manifest['extensions']['student_ids']
        return {(ids[r['student']],r['homework'],r['item']):r['potential_draw'] for r in log.tables['assessment_items']}
    assert exams_by_id(a)==exams_by_id(b)

@pytest.mark.parametrize('table,field',[('curriculum_readiness','readiness'),('assessment_items','core_probability'),('learning_doses','fraction')])
def test_corrupted_evidence_rejected(table,field):
    c=declaration(); c['design']['curriculum']['enabled']=True
    a=run(c); a.tables[table][0][field]+=.01
    with pytest.raises(AssertionError): validate_promising_log(a)

def test_cli_executes_and_hashes_new_design(tmp_path):
    c=declaration(h=1); c['design']['curriculum']['enabled']=True
    dest=tmp_path/'a33'; config.run_experiment(c,dest)
    lock=config.load_config(dest/'lock.json')
    assert lock['schema_version']==3 and lock['stream_scheme']['codes']['fragments']==172
    from classroom_swarm.v4 import V4Log
    import pyarrow.parquet as pq
    folder=dest/'raw/rep0000/reference'; complete=config.load_config(folder/'complete.json')
    log=V4Log(config.load_config(folder/'manifest.json')); log.tables={}
    for name,expected in complete['hashes'].items():
        assert config.sha256(folder/name)==expected
        if name.endswith('.parquet'): log.tables[name[:-8]]=pq.read_table(folder/name).to_pylist()
    validate_promising_log(log)
