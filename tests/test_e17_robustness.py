"""E17 safeguards: identified controls, exogenous groups and units."""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
from classroom_swarm.tutoring_config import resolve_config

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import e17_tutoring_robustness as e17


def test_design_changes_only_seeds_and_replicates_between_stages():
    a,b=e17.declaration('development'),e17.declaration('confirmation')
    assert (a['seed'],b['seed'])==(10061701,10061791)
    assert (a['replicates'],b['replicates'])==(20,60)
    assert a['conditions']==b['conditions'] and a['contrasts']==b['contrasts']
    assert len(resolve_config(a)['conditions'])==42
    assert len(resolve_config(b)['conditions'])==42


def test_focal_states_and_single_factor_contrasts_are_declared():
    resolved=resolve_config(e17.declaration('development'))
    assert all(c['initial']['knowledge']['values']==[.35]*4+[.75]*4 for c in resolved['conditions'])
    assert all(len(c['changed_settings'])==1 for c in resolved['contrasts'] if c['kind']=='single_parameter')
    c={c['name']:c for c in resolved['conditions']}
    assert c['mixed_single_scheduled']['params']['H']==c['mixed_single_scheduled']['params']['exam_every']==1
    assert c['mixed_no_checks']['params']['quality_check_probability']==0
    assert c['mixed_frozen_quality']['params']['quality_learning_rate']==0


@pytest.mark.parametrize('metric,expected',[('exam',20.),('knowledge_gain',20.),('guided_sessions_per_episode',.2),('guided_ticks_per_episode',.2)])
def test_effect_units_and_pairing(metric,expected):
    result=e17.paired_effect([.5,.7],[.3,.5],metric,np.random.default_rng(5))
    assert result['effect']==pytest.approx(expected)
    assert result['lo95']==pytest.approx(expected)==result['hi95']


def test_confirmation_requires_review_before_run(tmp_path,monkeypatch):
    monkeypatch.setattr(e17,'verify',lambda root:None)
    with pytest.raises(ValueError,match='review'):
        e17.execute(tmp_path,'confirmation')
