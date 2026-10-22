"""E26 protocol fidelity and rejection of an inactive intervention."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import e26_protocol_parameter_fit as fit

def test_unpaid_protocols_have_no_accidental_reward_contract():
    jobs=fit.jobs('training',0,'protocol')
    for j in jobs:
        strength=j['resolved']['extensions']['teacher_work']['contract']['strength']
        if j['case']!='teacher_rewards': assert strength==0
        else: assert strength==int(j['arm']=='rewarded')

def test_legacy_control_preserves_accidental_contract_for_diagnosis():
    legacy=fit.jobs('fresh',0,'legacy',cases=('star',))
    policy=fit.jobs('fresh',0,'policy_only',cases=('star',))
    corrected=fit.jobs('fresh',0,'protocol',cases=('star',))
    for a,b,c in zip(legacy,policy,corrected):
        assert a['resolved']==b['resolved'] or a['resolved']['params']==b['resolved']['params']
        assert a['resolved']['extensions']['teacher_work']['contract']['strength']==1
        assert b['resolved']['extensions']['teacher_work']['contract']['strength']==1
        assert c['resolved']['extensions']['teacher_work']['actions']==['guidance','explanation']
        assert a['resolved']['extensions']['teacher_work']['total_budget']==c['resolved']['extensions']['teacher_work']['total_budget']

def test_fit_cannot_reenable_rewards_in_unpaid_studies():
    jobs=fit.jobs('training',0,'candidate',[1.]*len(fit.PARAMETERS))
    assert all(j['resolved']['extensions']['teacher_work']['contract']['strength']==0 for j in jobs if j['case']!='teacher_rewards')

def test_no_help_rejected_despite_near_null_upper_scores():
    rows=[]
    for arm in ('random','cross','reward'):
        for group in ('all','low','high'):
            rows.append(dict(case='seating',arm=arm,group=group,cohort=0,profile='x',section=0,students=2,
                core_potential=50.,productive_fraction=.9,contract_sessions=0.))
    r=fit.assess(rows,fit.reference_vector())
    assert not r['feasible']
    assert any('helper rewards' in message for message in r['problems'])

def test_corrected_pool_is_unseen_by_superseded_search():
    import e25_plausible_parameter_fit as old
    assert set(offset for count,offset in fit.POOLS.values()).isdisjoint(offset for count,offset in old.POOLS.values())
