"""A34 policy reconstruction and complete independent curriculum audit."""
import json
from copy import copy
from collections import Counter
import numpy as np
from .promising_validation import validate_promising_log
from .tutoring_settings import TutoringParams
from .effort_runtime import semantic
from .v4_public_ai import PublicAIDraws

def deep_audit(log):
    """Independently recover start-time prerequisites and released policy evidence."""
    if log.manifest['model'] not in ('A33-v4.8-content-choice','A34-v4.9-policy-repair') or not log.manifest['design']['curriculum']['enabled']:
        return {'readiness': 0, 'choices': 0, 'pretests': 0}
    t = log.tables; p = TutoringParams(**log.manifest['params'])
    d = log.manifest['design']['curriculum']; teacher = log.manifest['teacher']
    n, count, levels = p.N, log.manifest['topic_count'], len(d['levels'])
    ids = log.manifest['extensions']['student_ids'] or list(range(n))
    k = np.zeros((n, count)); observed = np.full((n, count), teacher['observation_prior'])
    initial_keys = [(r['student'], r['topic']) for r in t['topic_initial']]
    assert len(set(initial_keys)) == n * count == len(initial_keys), 'incomplete initial skill ledger'
    for r in t['topic_initial']: k[r['student'], r['topic']] = r['knowledge']
    draws = PublicAIDraws(log.manifest['seed'], log.manifest['replicate'], n, p.items, p.exam_items)
    assert len(t['curriculum_pretest']) == n * count, 'missing pretest records'
    pretest_keys = set()
    for r in t['curriculum_pretest']:
        i, topic = r['student'], r['topic']; pretest_keys.add((i, topic))
        u = semantic(draws, 170, ids[i], topic, size=d['pretest_items'])
        assert np.allclose(u, json.loads(r['item_draws']), atol=0, rtol=0), 'changed pretest draws'
        score = float(np.mean(u < k[i, topic]))
        covered = semantic(draws, 162, ids[i], 0, topic) >= 1 - teacher['observation_coverage']
        noise = semantic(draws, 163, ids[i], 0, topic, normal=True)
        value = float(np.clip(score + teacher['observation_noise_std'] * noise, 0, 1)) if covered else None
        assert abs(score - r['score']) < 1e-12 and value == r['observed'], 'pretest evidence mismatch'
        if value is not None: observed[i, topic] = value
    assert len(pretest_keys) == n * count, 'duplicate pretest record'
    doses = Counter((r['homework'], r['start'], r['student'], r['topic']) for r in t['learning_doses'])
    readiness = Counter((r['homework'], r['start'], r['student'], r['topic']) for r in t['curriculum_readiness'])
    assert doses == readiness, 'missing or duplicate readiness records'
    updates = sorted(t['topic_learning'], key=lambda r: (r['homework'], r['tick']))
    pointer = 0
    for r in sorted(t['curriculum_readiness'], key=lambda r: (r['homework'], r['start'])):
        stamp = r['homework'], r['start']
        while pointer < len(updates) and (updates[pointer]['homework'], updates[pointer]['tick']) <= stamp:
            u = updates[pointer]; key = u['student'], u['topic']
            assert abs(k[key] - u['before']) < 1e-10, 'broken independent skill history'
            k[key] = u['after']; pointer += 1
        i, topic = r['student'], r['topic']; prerequisite = d['prerequisites'][topic % levels]
        value = 1. if prerequisite < 0 else float(k[i, topic // levels * levels + prerequisite])
        expected = 1. if prerequisite < 0 else float(np.clip((value - (d['mastery_threshold'] - d['readiness_width'])) / d['readiness_width'], 0, 1))
        assert prerequisite == r['prerequisite'] and abs(value - r['value']) < 1e-10 and abs(expected - r['readiness']) < 1e-10, 'readiness disagrees with start-time knowledge'
    assert len(t['curriculum_choices']) == p.H and {r['homework'] for r in t['curriculum_choices']} == set(range(1, p.H + 1)), 'missing curriculum choices'
    observations = sorted(t['teacher_observations'], key=lambda r: (r['homework'], r['tick']))
    pointer = 0
    for r in sorted(t['curriculum_choices'], key=lambda r: r['homework']):
        while pointer < len(observations) and (observations[pointer]['homework'], observations[pointer]['tick']) <= (r['homework'], 0):
            u = observations[pointer]; key = u['student'], u['topic']
            assert abs(observed[key] - u['estimate_before']) < 1e-10, 'broken released-observation history'
            if u['observed_score'] is not None and u['weight'] > 0:
                observed[key] += teacher['observation_learning_rate'] * u['weight'] * (u['observed_score'] - observed[key])
            assert abs(observed[key] - u['estimate_after']) < 1e-10, 'observer update mismatch'
            pointer += 1
        means = observed[:, r['domain'] * levels:(r['domain'] + 1) * levels].mean(axis=0)
        assert np.allclose(means, json.loads(r['observed_means']), atol=1e-10, rtol=0), 'curriculum uses unavailable or incorrect observations'
    return {'readiness': sum(readiness.values()), 'choices': p.H, 'pretests': n * count}


def validate_repaired_log(log, p=None):
    if log.manifest['model'] != 'A34-v4.9-policy-repair': return validate_promising_log(log,p)
    proxy=copy(log); proxy.manifest={**log.manifest,'model':'A33-v4.8-content-choice'}
    validate_promising_log(proxy,p)
    deep_audit(log)
    p=TutoringParams(**log.manifest['params']) if p is None else p
    initial={(r['student'],r['topic']):r['knowledge'] for r in log.tables['topic_initial']}
    for r in log.tables['initial_states']:
        mean=np.mean([v for (i,k),v in initial.items() if i==r['student']])
        assert abs(r['knowledge']-mean)<1e-12, 'effective initial knowledge mismatch'
        for name,spec in log.manifest['initial'].items():
            if spec=={'kind':'from_knowledge'}: assert abs(r[name]-mean)<1e-12, 'dependent initial prior mismatch'
    events={(r['homework'],r['start'],r['student']):r for r in log.tables['events'] if r['action'].startswith('choose_')}
    policy=log.tables['policy_inputs']
    assert {(r['homework'],r['tick'],r['student']) for r in policy}==set(events), 'incomplete policy inputs'
    assert len(policy)==len(events), 'duplicate policy inputs'
    for r in policy:
        event=events[r['homework'],r['tick'],r['student']]
        scores=json.loads(event['detail'])
        assert abs(r['confidence']-event['C'])<1e-12 and abs(r['estimate']-event['estimate'])<1e-12, 'policy/event inputs mismatch'
        for action,index in [('attempt',0),('hint',1)]:
            if action not in scores['scores']: continue
            belief=p.confidence_weight*r['benefits'][index]+(1-p.confidence_weight)*r['confidence']
            assert abs(belief-r[action+'_belief'])<1e-12, 'private belief blend mismatch'
            expected=r[action+'_utility']-r['estimate']
            if action=='hint': expected=r['hint_access']*expected-r['request_cost']
            if action=='attempt': expected+=scores['teacher_guidance_bonus']
            assert abs(expected-scores['scores'][action])<1e-12, 'policy service/utility mismatch'
    requests=[r for r in log.tables['events'] if r['action']=='request_hint']
    costs=[r for r in log.tables['student_costs'] if r['activity']=='hint_request']
    assert Counter((r['homework'],r['student'],r['start'],r['end']) for r in requests)==Counter((r['homework'],r['student'],r['start'],r['end']) for r in costs), 'hint requests lack operational cost'
    return None

