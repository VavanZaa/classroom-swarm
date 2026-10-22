"""Read-only reconstruction of private benefits, service probabilities and request costs."""
from collections import defaultdict
import json
import numpy as np

def audit_private_inputs(log):
    if log.manifest['model']!='A34-v4.9-policy-repair': return dict(benefit_inputs=0,service_inputs=0,request_costs=0)
    t=log.tables; p=log.manifest['params']; n=p['N']
    b=np.zeros((n,5)); a=np.zeros((n,n)); contacts=np.zeros((n,n))
    for r in t['initial_states']:
        b[r['student']]=[r['benefit_'+name] for name in ('attempt','hint','answer','ai_answer','ai_tutor')]
    for r in t['initial_access']: a[r['requester'],r['provider']]=r['hint']
    for r in t['contacts']: contacts[r['u'],r['v']]=contacts[r['v'],r['u']]=r['closeness']
    grades=sorted(t['homework_feedback'],key=lambda r:(r['homework'],r['tick']))
    requests=sorted([r for r in t['requests'] if r['mode']=='hint'],key=lambda r:(r['homework'],r['finish']))
    quality=defaultdict(dict)
    for r in t['quality_choice_state']: quality[r['homework'],r['tick'],r['requester']][r['provider']]=r['quality']
    costs={(r['homework'],r['start'],r['student']):r['cost'] for r in t['student_costs'] if r['activity']=='hint_request'}
    gi=ri=0; checked=0
    for r in sorted(t['policy_inputs'],key=lambda r:(r['homework'],r['tick'],r['student'])):
        stamp=r['homework'],r['tick']; i=r['student']
        while gi<len(grades) and (grades[gi]['homework'],grades[gi]['tick'])<=stamp:
            g=grades[gi]; student=g['student']
            assert np.allclose(b[student],json.loads(g['B_before']),atol=1e-12,rtol=0), 'private grade belief history discontinuity'
            b[student]=json.loads(g['B_after']); gi+=1
        assert np.allclose(b[i],r['benefits'],atol=1e-12,rtol=0), 'choice ignores released grade benefit history'
        while ri<len(requests) and (requests[ri]['homework'],requests[ri]['finish'])<=stamp:
            q=requests[ri]; key=q['requester'],q['provider']
            assert abs(a[key]-q['A_before'])<1e-12, 'private help service history discontinuity'
            a[key]+=p['eta_access']*(int(q['success'])-a[key])
            assert abs(a[key]-q['A_after'])<1e-12, 'incorrect private service update'; ri+=1
        candidates=[j for j in range(n) if j!=i and contacts[i,j]>0]
        q=quality[r['homework'],r['tick'],i]
        assert set(q)==set(candidates), 'choice source quality ledger incomplete'
        w=[contacts[i,j]**p['relationship_strength']*a[i,j]*max(1e-12,q[j])**p['quality_target_weight'] for j in candidates]
        access=float(np.dot(w,a[i,candidates])/sum(w)) if w else 0.
        assert abs(access-r['hint_access'])<1e-12, 'hint access uses unavailable service history'
        key=r['homework'],r['tick'],i
        if key in costs:
            assert abs(costs[key]-r['request_cost'])<1e-12, 'predicted hint request cost differs from charged cost'; checked+=1
    assert checked==len(costs), 'unmatched hint request charges'
    return dict(benefit_inputs=len(t['policy_inputs']),service_inputs=len(t['policy_inputs']),request_costs=checked)
