"""A26 corrected controls: A25 parity, learnable tutor credit, hint deadlines, live belief channels."""
from dataclasses import replace
import json
import numpy as np
import pytest
from classroom_swarm.graphs import generate_er
from classroom_swarm.v4_public_ai import (PublicAIParams, PublicAIDraws, public_activity_scores,
                                          simulate_public_ai)
from classroom_swarm.v4_corrected import (CorrectedParams, blend, corrected_scores,
                                          corrected_grade_credit, simulate_corrected,
                                          validate_corrected_log)

SHARED = ('events', 'requests', 'packets', 'students', 'exams', 'feedback', 'graph', 'traits',
          'homework_feedback', 'ai_uses', 'contacts')
# The flag settings under which A26 must behave exactly like A25.
LEGACY = dict(tutor_credit_by_source=False, hint_deadline_guard=False, confidence_weight=.5)


def run(p=None, seed=82, graph=None):
    p = p or CorrectedParams(N=6, H=8)
    g = graph or generate_er(p.N, 3, 71)
    return simulate_corrected(p, g, PublicAIDraws(seed, 0, p.N, p.items, p.exam_items))


@pytest.mark.parametrize('seed', [82, 101])
@pytest.mark.parametrize('mode', ['none', 'answer', 'tutor'])
@pytest.mark.parametrize('motivation', [True, False])
def test_legacy_flags_reproduce_a25_on_every_shared_table(seed, mode, motivation):
    old = PublicAIParams(N=8, H=10, ai_mode=mode) if motivation else PublicAIParams(
        N=8, H=10, ai_mode=mode, grade_effort_only=False, learning_value=.25)
    new = CorrectedParams(**{**{f.name: getattr(old, f.name) for f in old.__dataclass_fields__.values()},
                             **LEGACY, 'wait_value': 0. if motivation else .025})
    g = generate_er(8, 4, 71)
    a = simulate_corrected(new, g, PublicAIDraws(seed, 0, 8, 10, 30))
    b = simulate_public_ai(old, g, PublicAIDraws(seed, 0, 8, 10, 30))
    for table in SHARED:
        assert a.tables[table] == b.tables[table], table


@pytest.mark.parametrize('motivation', [True, False])
@pytest.mark.parametrize('mode', ['none', 'answer', 'tutor'])
def test_score_dictionary_parity_at_legacy_settings(motivation, mode):
    old = PublicAIParams(ai_mode=mode) if motivation else PublicAIParams(
        ai_mode=mode, grade_effort_only=False, learning_value=.25)
    new = CorrectedParams(**{**{f.name: getattr(old, f.name) for f in old.__dataclass_fields__.values()},
                             **LEGACY, 'wait_value': 0. if motivation else .025})
    rng = np.random.default_rng(7)
    for _ in range(200):
        c, control = rng.random(), rng.random()
        benefits, effort, estimate = rng.random(5), rng.random(), rng.random()
        packet, hint = bool(rng.integers(2)), bool(rng.integers(2))
        access = tuple(rng.random(2))
        ch, ca, remaining, short, avail = (bool(rng.integers(2)), bool(rng.integers(2)),
                                           int(rng.integers(0, 13)), rng.random(), bool(rng.integers(2)))
        peer = float(rng.random()) if rng.integers(2) else None
        args = (c, control, benefits, effort, estimate, packet, hint, access, ch, ca, remaining)
        kw = dict(shortfall=short, peer_prediction=peer, ai_available=avail)
        assert corrected_scores(new, *args, **kw) == public_activity_scores(old, *args, **kw)


def test_blend_is_exactly_a25_at_the_legacy_weight():
    rng = np.random.default_rng(3)
    for _ in range(500):
        b, c = rng.random(), rng.random()
        assert blend(.5, b, c) == .5 * (b + c)
        assert blend(.5, b, c, .25) == .5 * (b + c + .25 * (1 - c))
        assert blend(0., b, c, .25) == pytest.approx(b)
        assert blend(1., b, c, .25) == pytest.approx(c + .25 * (1 - c))


def test_zero_strength_tutor_is_credited_and_therefore_learnable():
    p = CorrectedParams(N=10, H=15, ai_mode='tutor', ai_hint_strength=0)
    log = run(p, graph=generate_er(10, 4, 71))
    validate_corrected_log(log)
    guided = [r for r in log.tables['students'] if r['final_route'] == 'ai_guided']
    assert guided, 'a consulted zero-strength tutor must still produce a credited route'
    credited = [r for r in log.tables['homework_feedback'] if json.loads(r['credit'])[4] > 0]
    assert len(credited) == len(guided)
    # The hint adds nothing, so the packet is exactly an unaided attempt.
    for r in log.tables['packets']:
        if r['hint_source'] == 'ai':
            assert r['origin'] == 'ai_tutor_attempt' and not r['assisted']


def test_legacy_flag_restores_the_a25_tutor_blind_spot():
    p = CorrectedParams(N=10, H=15, ai_mode='tutor', ai_hint_strength=0, **LEGACY, wait_value=0.)
    log = run(p, graph=generate_er(10, 4, 71))
    assert any(r['hint_source'] == 'ai' for r in log.tables['packets'])
    assert not any(r['origin'] == 'ai_tutor_attempt' for r in log.tables['packets'])
    assert not any(json.loads(r['credit'])[4] > 0 for r in log.tables['homework_feedback'])


def test_credit_prefers_tutor_origin_over_the_assisted_flag():
    assert corrected_grade_credit(dict(via='attempt', origin='ai_tutor_attempt', assisted=False),
                                  np.zeros(5))[0].tolist() == [.5, 0, 0, 0, .5]
    assert corrected_grade_credit(dict(via='attempt', origin='student', assisted=True),
                                  np.zeros(5))[0].tolist() == [.5, .5, 0, 0, 0]
    assert corrected_grade_credit(dict(via='ai', origin='ai_answer', assisted=True),
                                  np.zeros(5))[1] == 'ai_answer'
    assert corrected_grade_credit(None, [1, 0, 1, 0, 0])[1] == 'missing'


def test_hint_deadline_guard_removes_unusable_arrivals_and_the_flag_restores_them():
    base = dict(N=14, H=20, ai_mode='none', allow_answer=False, willingness=1.)
    guarded = [run(CorrectedParams(**base), seed=s, graph=generate_er(14, 6, 71)) for s in (82, 101, 7)]
    legacy = [run(CorrectedParams(**base, **LEGACY, wait_value=0.), seed=s, graph=generate_er(14, 6, 71))
              for s in (82, 101, 7)]
    assert all(r['usable'] for log in guarded for r in log.tables['hint_receipts'])
    assert any(not r['usable'] for log in legacy for r in log.tables['hint_receipts'])
    assert sum(len(log.tables['hint_receipts']) for log in guarded) > 0


@pytest.mark.parametrize('mode,indices', [('answer', (0, 1, 2, 3)), ('tutor', (0, 1, 2, 4))])
def test_no_benefit_channel_is_write_only(mode, indices):
    """A22's B_check was updated on every homework and read by nothing. Never again."""
    p = CorrectedParams(ai_mode=mode)
    args = (.5, .5, np.full(5, .5), .15, .1, False, False, (.6, .6), True, True, 12)
    base = corrected_scores(p, *args, peer_prediction=None, ai_available=True)
    for index in indices:
        moved = np.full(5, .5)
        moved[index] = .9
        other = corrected_scores(p, .5, .5, moved, .15, .1, False, False, (.6, .6), True, True, 12,
                                 peer_prediction=None, ai_available=True)
        assert other != base, f'benefit index {index} is never read by the policy'


def test_confidence_weight_moves_own_work_scores_only():
    p = CorrectedParams(ai_mode='answer')
    args = (.2, .5, np.full(5, .9), .15, .1, False, False, (.6, .6), True, True, 12)
    kw = dict(peer_prediction=None, ai_available=True)
    half = corrected_scores(p, *args, **kw)
    pure = corrected_scores(replace(p, confidence_weight=0.), *args, **kw)
    assert pure['attempt'] > half['attempt'] and pure['hint'] > half['hint']
    for key in ('answer', 'ai_answer', 'wait'):
        assert pure[key] == half[key]


def test_wait_value_is_independent_of_the_motivation_flag():
    p = CorrectedParams()
    args = (.5, .5, np.full(5, .5), .15, .1, True, False, (.6, .6), True, True, 12)
    assert corrected_scores(p, *args)['wait'] == 0.
    assert corrected_scores(replace(p, wait_value=.025), *args)['wait'] == .025
    legacy = replace(p, grade_effort_only=False, learning_value=.25, wait_value=0.)
    assert corrected_scores(legacy, *args)['wait'] == 0.


@pytest.mark.parametrize('mode', ['none', 'answer', 'tutor'])
def test_full_audit_and_knowledge_reconstruction(mode):
    log = run(CorrectedParams(N=8, H=10, ai_mode=mode), graph=generate_er(8, 4, 71))
    validate_corrected_log(log)
    for i in range(8):
        gain = sum(e['K_after'] - e['K_before'] for e in log.tables['events']
                   if e['student'] == i and e['action'] in {'attempt', 'help_hint'})
        final = next(r['K'] for r in log.tables['students'] if r['student'] == i and r['homework'] == 10)
        assert gain == pytest.approx(final - log.tables['traits'][i]['K0'], abs=1e-12)


@pytest.mark.parametrize('changes', [{'confidence_weight': 1.1}, {'wait_value': -.1},
                                     {'attempt_ticks': 0}, {'attempt_ticks': 99},
                                     {'tutor_credit_by_source': 1}, {'hint_deadline_guard': 'yes'},
                                     {'learning_value': .25}])
def test_invalid_parameters(changes):
    with pytest.raises(ValueError):
        replace(CorrectedParams(), **changes).validate()
