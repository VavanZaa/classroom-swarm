"""A33 raw reconstruction in addition to the frozen A32 accounting checks."""
import json
from copy import copy
import numpy as np
from .effort_validation import validate_effort_log
from .promising_settings import resolve_promising
from .effort_runtime import semantic
from .v4_public_ai import PublicAIDraws

def validate_promising_log(log,p=None):
    if log.manifest['model']!='A33-v4.8-content-choice': return validate_effort_log(log,p)
    proxy=copy(log); proxy.manifest={**log.manifest,'model':'A32-v4.7-effort-learning'}
    validate_effort_log(proxy,p)
    if p is None:
        from .tutoring_settings import TutoringParams
        p=TutoringParams(**log.manifest['params'])
    d=resolve_promising(log.manifest['design']); errors=[]
    def check(ok,message):
        if not ok: errors.append(message)
    initial={(r['student'],r['topic']):r['knowledge'] for r in log.tables['topic_initial']}
    if d.curriculum.enabled:
        for r in log.tables['curriculum_projection']:
            mean=np.mean([v for (i,k),v in initial.items() if i==r['student']])
            check(abs(mean-r['initial_mean'])<1e-12,'skill projection mismatch')
            if d.curriculum.initial_values is None: check(abs(mean-r['base_K'])<1e-12,'initial mean changed')
        for r in log.tables['curriculum_pretest']:
            expected=np.mean(np.asarray(json.loads(r['item_draws']))<initial[r['student'],r['topic']])
            check(abs(expected-r['score'])<1e-12 and r['release']==0,'pretest mismatch')
        for r in log.tables['curriculum_readiness']:
            expected=1 if r['prerequisite']<0 else np.clip((r['value']-(d.curriculum.mastery_threshold-d.curriculum.readiness_width))/d.curriculum.readiness_width,0,1)
            check(abs(expected-r['readiness'])<1e-12,'prerequisite reconstruction')
        for r in log.tables['curriculum_choices']:
            means=json.loads(r['observed_means']); eligible=[k for k,v in enumerate(d.curriculum.prerequisites) if v<0 or means[v]>=d.curriculum.mastery_threshold]
            expected=max(eligible) if r['rule']=='observed_prerequisites' else (d.curriculum.level_schedule[r['homework']-1] if d.curriculum.level_schedule else d.curriculum.fixed_level)
            check(r['level']==expected,'teacher used invalid skill target')
        states={(r['homework'],r['student'],r['topic']):r['knowledge'] for r in log.tables['topic_states']}
        designs={r['name']:r for r in log.tables['assessment_design']}
        draws=PublicAIDraws(log.manifest['seed'],log.manifest['replicate'],p.N,p.items,p.exam_items)
        for r in log.tables['assessment_items']:
            design=designs[r['assessment']]; index=list(designs).index(r['assessment'])
            weights=np.array(json.loads(design['topic_weights']))
            u=semantic(draws,171,0,index,size=p.exam_items)[r['item']]
            topic=min(len(weights)-1,int(np.searchsorted(np.cumsum(weights),u,side='right')))
            check(topic==r['topic'],'exam tag changed')
            expected=np.clip(states[r['homework'],r['student'],topic]+.5-design['difficulty'],0,1)
            check(abs(expected-r['core_probability'])<1e-12,'tagged exam skill mismatch')
    for r in log.tables['teacher_belief_updates']:
        check(r['homework']>=r['release'],'premature teacher participation update')
        expected=np.clip(r['bias_before']+d.teacher_forecast.update_rate*(int(r['participated'])-r['predicted_probability'])*d.teacher_forecast.uncertainty,-1,1)
        check(abs(expected-r['bias_after'])<1e-12,'participation belief mismatch')
    actions={r['action_id']:r for r in log.tables['teacher_actions']}
    for r in log.tables['learning_doses']:
        check(r['duration']<=r.get('reserved_duration',r['duration']),'learning exceeds reserved duration')
        if r['source']=='coaching':
            action=next(a for a in actions.values() if a['homework']==r['homework'] and a['start']==r['start'] and a['action']=='coaching')
            if action.get('scope')=='group': check(r['duration']==action['delivery_ticks'],'group overhead credited as learning')
    for r in log.tables['teacher_actions']:
        if r.get('scope')=='group':
            expected=d.group_preparation.delivery_ticks+int(np.ceil(p.N/d.group_preparation.feedback_capacity))*d.group_preparation.feedback_ticks
            check(r['duration']==expected and r['cost']==expected,'group work accounting mismatch')
    for r in log.tables['shared_reasoning']:
        a=np.array(json.loads(r['requester_fragments']),bool); b=np.array(json.loads(r['provider_fragments']),bool)
        known=b.all(axis=0); own=a.all(axis=0); union=(a|b).all(axis=0)
        reasoning=union&(np.array(json.loads(r['reasoning_draws']))<r['reasoning_probability']*r['reasoning_effort'])
        correct=(known|reasoning)&(np.array(json.loads(r['explanation_draws']))<r['explanation_probability'])
        bits=lambda x: ''.join(map(str,x.astype(int)))
        check(bits(own)==r['own_bits'] and bits(known)==r['provider_bits'] and bits(union)==r['union_bits'] and bits(correct)==r['correct_bits'],'shared reasoning reconstruction')
        check(int(np.sum(correct&~known&~own))==r['constructed'],'constructive answer count mismatch')
    if errors: raise AssertionError('; '.join(dict.fromkeys(errors)))
