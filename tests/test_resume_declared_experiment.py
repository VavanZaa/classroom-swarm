import importlib.util
from pathlib import Path
import pytest

from classroom_swarm.experiment_config import template,run_experiment,sha256

spec=importlib.util.spec_from_file_location('resume',Path(__file__).parents[1]/'scripts/resume_declared_experiment.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.mark.parametrize('completion_state',['missing','damaged'])
def test_resume_preserves_complete_rows_and_recovers_identical_output(tmp_path,completion_state):
    config=template();config['params'].update(N=4,H=2,exam_every=1)
    config['network'].update(family='ER',d_bar=2);config['replicates']=2
    output=tmp_path/'run';run_experiment(config,output)
    first=output/'raw/rep0000/reference';second=output/'raw/rep0001/reference'
    before_first={p.name:sha256(p) for p in first.iterdir()}
    before_second={p.name:sha256(p) for p in second.iterdir()}
    inventory_digest=sha256(output/'runs.csv')
    # Simulate interruption using only completion markers in this test-owned directory.
    (output/'complete.json').unlink()
    if completion_state=='missing':(second/'complete.json').unlink()
    else:(second/'complete.json').write_text('\x00'*1431)
    result=module.resume(output)
    assert result['reused_runs']==1 and result['missing_runs']==1
    assert {p.name:sha256(p) for p in first.iterdir()}==before_first
    assert {p.name:sha256(p) for p in second.iterdir()}==before_second
    assert sha256(output/'runs.csv')==inventory_digest
    assert len(list((output/'recovery').glob('*/incomplete_raw/rep0001/reference')))==1
