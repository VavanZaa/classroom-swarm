"""Private-state audit rejects policy snapshots that disagree with released history."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_v4_repaired import declaration,run
from audit_e26_private_inputs import audit_private_inputs

def test_intact_private_inputs_reconstruct():
    counts=audit_private_inputs(run(declaration()))
    assert counts['benefit_inputs']>0 and counts['service_inputs']>0

def test_invented_private_grade_belief_rejected():
    log=run(declaration()); log.tables['policy_inputs'][0]['benefits'][0]+=.001
    with pytest.raises(AssertionError,match='released grade'): audit_private_inputs(log)

def test_invented_access_belief_rejected():
    log=run(declaration()); log.tables['policy_inputs'][0]['hint_access']+=.001
    with pytest.raises(AssertionError,match='unavailable service'): audit_private_inputs(log)

def test_missing_quality_candidate_rejected():
    log=run(declaration()); log.tables['quality_choice_state'].pop(0)
    with pytest.raises(AssertionError,match='quality ledger'): audit_private_inputs(log)
