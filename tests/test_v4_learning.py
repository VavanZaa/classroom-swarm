"""A23 learning differentiation without changing the historical A22 engine."""
from dataclasses import replace

import numpy as np
import pytest

from classroom_swarm.graphs import generate_er
from classroom_swarm.v4 import V4Params, V4Draws, simulate_v4, validate_log, activity_scores
from classroom_swarm.v4_learning import LearningParams, simulate_learning, learning_activity_scores


@pytest.mark.parametrize('seed', [82, 95, 101])
@pytest.mark.parametrize('aligned', [False, True])
def test_fraction_one_exact_historical_raw_parity(seed, aligned):
    base = V4Params(N=6, H=7)
    p = LearningParams(N=6, H=7, check_learning_fraction=1, align_check_value=aligned)
    g = generate_er(6, 3, 71)
    d = V4Draws(seed, 0, 6, 10, 30)
    assert simulate_learning(p, g, d).tables == simulate_v4(base, g, d).tables


@pytest.mark.parametrize('fraction', [0, .1, .25, 1])
def test_learning_channels_and_raw_accounting(fraction):
    p = LearningParams(N=6, H=10, check_learning_fraction=fraction)
    log = simulate_learning(p, generate_er(6, 3, 71), V4Draws(82, 0, 6, 10, 30))
    validate_log(log)
    events = log.tables['events']
    assert any(e['action'] == 'check' for e in events)
    for i, trait in enumerate(log.tables['traits']):
        own = [e for e in events if e['student'] == i]
        gain = sum(e['K_after'] - e['K_before'] for e in own
                   if e['action'] in {'attempt', 'check', 'help_hint'})
        final = next(r['K'] for r in log.tables['students'] if r['student'] == i and r['homework'] == p.H)
        assert gain == pytest.approx(final - trait['K0'], abs=1e-12)
        for e in own:
            if e['action'] == 'check':
                assert e['K_after'] - e['K_before'] == pytest.approx(
                    (1-e['K_before']) * min(1., fraction * trait['alpha']/6), abs=1e-12)
            if e['action'] in {'answer_receive', 'help_answer', 'hint_receive'}:
                assert e['K_before'] == e['K_after']


def test_zero_check_still_provides_information_and_uses_time():
    p = LearningParams(N=6, H=7)
    log = simulate_learning(p, generate_er(6, 3, 71), V4Draws(82, 0, 6, 10, 30))
    packets = {r['packet_id']: r['item_bits'] for r in log.tables['packets']}
    changed = 0
    for e in log.tables['events']:
        if e['action'] != 'check':
            continue
        assert e['end']-e['start'] == 2 and e['occupied']
        assert e['K_before'] == e['K_after']
        assert e['estimate'] == packets[e['packet_id']].count('1') / p.items
        before = next(x for x in log.tables['events'] if x['action'] == 'choose_check'
                      and x['student'] == e['student'] and x['homework'] == e['homework']
                      and x['start'] == e['start'])
        changed += e['C'] != before['C']
    assert changed > 0


def test_policy_alignment_changes_only_check_intrinsic_value():
    p = LearningParams(check_learning_fraction=.25)
    args = (.4, .5, np.full(4, .4), .15, .4, True, False, (.5,.5), True, 8)
    old = activity_scores(p, *args)
    new = learning_activity_scores(p, *args)
    assert old['check'] - new['check'] == pytest.approx(.75 * .5 * p.learning_value * .5 * .6)
    assert {k:v for k,v in old.items() if k != 'check'} == {k:v for k,v in new.items() if k != 'check'}
    assert learning_activity_scores(replace(p, align_check_value=False), *args) == old


@pytest.mark.parametrize('fraction', [-.1, 1.1, float('nan'), float('inf')])
def test_invalid_fraction(fraction):
    with pytest.raises(ValueError):
        LearningParams(check_learning_fraction=fraction).validate()
