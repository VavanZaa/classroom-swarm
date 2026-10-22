from copy import deepcopy
import json
import pytest
from classroom_swarm.effort_config import template, resolve_config, preflight, run_experiment, load_config


def small():
    c=template(); c.update(experiment_id='A32_config_test',seed=73149,replicates=1)
    c['params'].update(N=4,H=2,items=8,exam_items=12,exam_every=1)
    c['network'].update(family='CUSTOM',edges=[])
    c['extensions']['learning_process']['enabled']=True
    return c


def test_resolve_freezes_all_defaults_and_rejects_unknown_fields():
    c=small(); resolved=resolve_config(c); x=resolved['conditions'][0]['extensions']
    assert x['student_ids']==[0,1,2,3]
    assert len(x['test_preparation']['initial_format'])==4
    assert x['test_preparation']['exams'] and x['helper_contract']['checkpoints']==[1,2]
    preflight(resolved)
    c['extensions']['learning_process']['learning_rate_magic']=.2
    with pytest.raises(ValueError,match='unknown'): resolve_config(c)


def test_single_field_contrast_tracks_new_parameter_and_nested_contract():
    c=small(); c['teacher']['enabled']=True; c['extensions']['teacher_work']['enabled']=True
    c['conditions']=[dict(name='reference'),dict(name='reward',extensions={'teacher_work':{'contract':{'strength':2.}}})]
    c['contrasts']=[dict(condition='reward',reference='reference',kind='single_parameter',identity='not_identity')]
    r=resolve_config(c)
    assert r['contrasts'][0]['changed_settings']==['extensions.teacher_work.contract.strength']
    c['conditions'][1]['extensions']['teacher_work']['total_budget']=10
    with pytest.raises(ValueError,match='single_parameter'): resolve_config(c)


def test_config_runner_freezes_and_saves_audited_raw_hashes(tmp_path):
    c=small(); output=tmp_path/'A32_config'; run_experiment(c,output)
    lock=load_config(output/'lock.json'); complete=load_config(output/'complete.json')
    assert lock['model']=='A32-v4.7-effort-learning' and complete['runs']==1
    assert 'src/classroom_swarm/effort_runtime.py' in lock['sources']
    assert (output/'raw/rep0000/reference/learning_doses.parquet').exists()
    with pytest.raises(ValueError,match='exists'): run_experiment(c,output)


@pytest.mark.parametrize('field,value',[('attention_effort_weight',-1),('recovery',True),('material_access',1),('reference_ticks',0),('fatigue_per_effort_tick',float('nan'))])
def test_malformed_new_numeric_and_boolean_fields_fail_preflight(field,value):
    c=small(); c['extensions']['learning_process'][field]=value
    with pytest.raises(ValueError): resolve_config(c)


def test_duplicate_json_and_nonfinite_values_rejected(tmp_path):
    path=tmp_path/'bad.json'; path.write_text('{"seed":1,"seed":2}')
    with pytest.raises(ValueError,match='duplicate'): load_config(path)
    path.write_text('{"seed":NaN}')
    with pytest.raises(ValueError,match='nonfinite'): load_config(path)
