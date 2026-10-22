"""Physical productivity bounds and unchanged treatment/population declarations."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import e27_teacher_belief_check as check

def test_all_candidates_below_conditional_physical_learning_ceiling():
    from classroom_swarm.effort_runtime import dose_fraction
    assert check.CAP==pytest.approx(dose_fraction(.0584,3.,1.,1.))
    for vector in check.candidates().values():
        values=check.fit.transform(vector)
        assert values['teacher_gain_belief']<=check.CAP+1e-12

def test_candidates_stay_inside_previous_bounds():
    for vector in check.candidates().values():
        values=check.fit.transform(vector)
        for name,lo,hi,ref,log,path,cases in check.fit.PARAMETERS: assert lo-1e-12<=values[name]<=hi+1e-12

def test_cap_does_not_change_physical_alpha_or_rewards():
    a=check.fit.jobs('training',3000,'original',check.fit.config.load_config(check.fit.ROOT/'search-complete.json')['vector'],cases=check.CASES)
    b=check.fit.jobs('training',3000,'capped',check.candidates()['cap_only'],cases=check.CASES)
    for x,y in zip(a,b):
        assert x['resolved']['initial']==y['resolved']['initial']
        assert x['resolved']['params']==y['resolved']['params']
        assert x['resolved']['extensions']['teacher_work']['contract']==y['resolved']['extensions']['teacher_work']['contract']
