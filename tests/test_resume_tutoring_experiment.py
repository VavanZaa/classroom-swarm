import importlib.util
from pathlib import Path
import pytest
from classroom_swarm.tutoring_config import template,run_experiment,sha256

spec=importlib.util.spec_from_file_location('a29_resume',Path(__file__).parents[1]/'scripts/resume_tutoring_experiment.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

@pytest.mark.parametrize('mode',['legacy_hint','shared_practice','joint_practice'])
def test_recovery_is_byte_identical_and_reuses_complete_runs(tmp_path,mode):
    config=template();config['params'].update(N=4,H=2,exam_every=1,tutoring_activity=mode)
    config['network'].update(family='ER',d_bar=2);config['replicates']=2
    output=run_experiment(config,tmp_path/'run')
    before={str(p.relative_to(output)):sha256(p) for p in (output/'raw').rglob('*') if p.is_file()}
    digest=sha256(output/'runs.csv')
    (output/'complete.json').unlink()
    (output/'raw/rep0001/reference/complete.json').write_text('\x00'*40)
    result=module.resume(output)
    assert result['reused_runs']==1 and result['missing_runs']==1
    assert {str(p.relative_to(output)):sha256(p) for p in (output/'raw').rglob('*') if p.is_file()}==before
    assert sha256(output/'runs.csv')==digest
