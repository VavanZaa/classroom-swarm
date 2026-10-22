"""Integrity checks for E14 declarations and measurement, without fitting outcomes."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('e14', Path(__file__).parents[1]/'scripts/e14_classroom_trends.py')
e14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e14)


def test_declarations_are_identifiable_and_primary_comparisons_exist():
    configs = {name:e14.resolve_config(config) for name,config in e14.declarations().items()}
    assert sum(len(c['conditions']) for c in configs.values()) == 33
    assert len(e14.PRIMARY) == 10
    for group,a,b,_,_ in e14.PRIMARY:
        assert any(c['condition']==a and c['reference']==b for c in configs[group]['contrasts'])
    for c in configs.values():
        assert c['replicates']==100


def test_metrics_measure_same_episode_and_exogenous_students():
    log=e14.V4Log({'params':{'H':2}})
    log.tables['traits']=[{'student':0,'K0':.2},{'student':1,'K0':.8}]
    log.tables['students']=[dict(homework=h,student=i,K=k,grade=g,copied=False,attempt=1)
        for h,i,k,g in [(1,0,.3,.1),(2,0,.4,.5),(2,1,.9,.9)]]
    log.tables['exams']=[dict(homework=h,student=i,score=s) for h,i,s in [(1,0,.1),(2,0,.4),(2,1,.9)]]
    log.tables['requests']=[dict(requester=0,mode='hint',success=True)]
    log.tables['ai_uses']=[dict(student=0),dict(student=1)]
    result=e14.metrics(log,[0])
    assert result['exam']==.4
    assert result['homework']==.5
    assert result['knowledge_gain']==pytest.approx(.2)
    assert result['hint_deliveries_per_episode']==.5
    assert result['ai_uses_per_episode']==.5


def test_constant_bootstrap_is_exact():
    assert e14.interval([.25]*100,e14.np.random.default_rng(1))==(.25,.25,.25)
