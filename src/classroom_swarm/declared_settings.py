"""A28 active numerical settings and explicit initial-state declarations."""
from __future__ import annotations

from dataclasses import dataclass, fields
import math

import numpy as np

from .distributions import number, sample_distribution, validate_distribution
from .v3 import TraitState
from .v4_population import PopulationParams
from .v4_corrected import blend, corrected_grade_credit

INITIAL_STREAMS = {
    'confidence': 108, 'control': 109, 'benefit_attempt': 110, 'benefit_hint': 111,
    'benefit_answer': 112, 'benefit_ai_answer': 113, 'benefit_ai_tutor': 114,
    'access_hint': 115, 'access_answer': 116, 'grade_shortfall': 117,
    'grade_satisfaction': 118,
}


@dataclass(frozen=True)
class DeclaredParams(PopulationParams):
    alpha_log_sd: float = .25
    kappa_log_sd: float = .25
    peer_request_ticks: int = 1
    peer_hint_ticks: int = 2
    peer_answer_ticks: int = 1
    request_timeout_ticks: int = 2
    wait_ticks: int = 1
    submit_ticks: int = 1
    max_ai_uses: int = 1
    effort_time_scale: float = 12.
    attempt_learning_divisor: float = 3.
    helper_learning_divisor: float = 6.
    hint_learning_multiplier: float = 1.
    hint_performance_multiplier: float = 1.
    perceived_hint_boost: float = .25
    hint_learning_value_multiplier: float = 1.5
    peer_hint_base: float = .15
    peer_hint_knowledge_weight: float = .35
    reciprocity_reference: float = .5
    peer_attempt_credit: float = .5
    tutor_attempt_credit: float = .5
    submit_value: float = 0.

    def validate(self):
        # Inherited annotations give strict JSON/Python types, including inactive compatibility flags.
        for f in fields(self):
            value = getattr(self, f.name)
            if f.type == 'bool' and not isinstance(value, bool):
                raise ValueError(f'{f.name} must be boolean')
            if f.type == 'int' and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f'{f.name} must be an integer')
            if f.type in {'float', 'float | None'} and value is not None:
                number(value, f.name)
        super().validate()
        for name in ('peer_request_ticks', 'peer_hint_ticks', 'peer_answer_ticks',
                     'request_timeout_ticks', 'wait_ticks', 'submit_ticks'):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f'{name} must be a positive integer')
            if name != 'request_timeout_ticks' and value > self.ticks:
                raise ValueError(f'{name} cannot exceed ticks')
        if not isinstance(self.max_ai_uses, int) or isinstance(self.max_ai_uses, bool) or self.max_ai_uses < 0:
            raise ValueError('max_ai_uses must be a nonnegative integer')
        for name in ('effort_time_scale', 'attempt_learning_divisor', 'helper_learning_divisor'):
            if number(getattr(self, name), name) <= 0:
                raise ValueError(f'{name} must be positive')
        for name in ('alpha_log_sd', 'kappa_log_sd', 'hint_learning_multiplier',
                     'hint_learning_value_multiplier'):
            if number(getattr(self, name), name) < 0:
                raise ValueError(f'{name} must be nonnegative')
        for name in ('hint_performance_multiplier', 'perceived_hint_boost', 'peer_hint_base',
                     'peer_hint_knowledge_weight', 'reciprocity_reference',
                     'peer_attempt_credit', 'tutor_attempt_credit'):
            if not 0 <= number(getattr(self, name), name) <= 1:
                raise ValueError(f'{name} must lie in [0,1]')
        if self.peer_hint_base + self.peer_hint_knowledge_weight > 1:
            raise ValueError('peer hint base + knowledge weight cannot exceed 1')
        number(self.submit_value, 'submit_value')


def default_initial(p):
    benefit = {'kind': 'from_knowledge'} if p.benefit_prior is None else {
        'kind': 'constant', 'value': p.benefit_prior}
    return {
        'knowledge': {'kind': 'truncated_normal', 'mean': p.K0, 'std': p.K0_sd, 'low': 0., 'high': 1.},
        'learning_efficiency': {'kind': 'lognormal', 'mean': p.alpha, 'log_sd': p.alpha_log_sd},
        'effort_aversion': {'kind': 'lognormal', 'mean': p.kappa, 'log_sd': p.kappa_log_sd},
        'confidence': {'kind': 'from_knowledge'},
        'control': {'kind': 'constant', 'value': .5},
        **{name: dict(benefit) for name in INITIAL_STREAMS if name.startswith('benefit_')},
        'access_hint': {'kind': 'constant', 'value': .5},
        'access_answer': {'kind': 'constant', 'value': .5},
        'grade_shortfall': {'kind': 'constant', 'value': 0.},
        'grade_satisfaction': {'kind': 'constant', 'value': 0.},
    }


def resolve_initial(p, overrides=None):
    result = default_initial(p)
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError('initial must be an object')
        if set(overrides) - set(result):
            raise ValueError(f'unknown initial states: {sorted(set(overrides) - set(result))}')
        result.update(overrides)
    for name, spec in result.items():
        if spec == {'kind': 'from_knowledge'} and (name == 'confidence' or name.startswith('benefit_')):
            continue
        lower = -1 if name == 'grade_satisfaction' else 0
        upper = None if name in {'learning_efficiency', 'effort_aversion'} else 1
        strict = name == 'learning_efficiency' or name.startswith('access_')
        size = p.N * p.N if name.startswith('access_') else p.N
        validate_distribution(spec, low=lower, high=upper, strict_low=strict, size=size)
    return result


def initial_state(p, draws, overrides=None):
    specs = resolve_initial(p, overrides)
    core = np.asarray(draws.legacy.traits(), dtype=float)
    states = {}
    for row, name in enumerate(('knowledge', 'learning_efficiency', 'effort_aversion')):
        states[name] = sample_distribution(specs[name], core[row], low=0,
            high=1 if row == 0 else None, strict_low=row == 1)
    for name, code in INITIAL_STREAMS.items():
        spec = specs[name]
        if spec == {'kind': 'from_knowledge'}:
            states[name] = states['knowledge'].copy()
            continue
        shape = (p.N, p.N) if name.startswith('access_') else (p.N,)
        z = np.random.default_rng(np.random.SeedSequence([draws.seed, draws.replicate, code])).standard_normal(shape)
        states[name] = sample_distribution(spec, z, low=-1 if name == 'grade_satisfaction' else 0,
                                          high=1, strict_low=name.startswith('access_'))
    traits = TraitState(states['knowledge'], states['learning_efficiency'], states['effort_aversion'])
    benefits = np.column_stack([states['benefit_' + name] for name in
                               ('attempt', 'hint', 'answer', 'ai_answer', 'ai_tutor')])
    access = np.stack([states['access_hint'], states['access_answer']], axis=2)
    return specs, states, traits, benefits, access


def declared_scores(p, c, control, benefits, effort_cost, estimate, has_packet, has_hint, access,
                    can_hint, can_answer, remaining, *, shortfall=0., peer_prediction=None,
                    ai_available=False):
    w, a, scale = p.confidence_weight, p.attempt_ticks, p.effort_time_scale
    peer_benefit = benefits[2] if peer_prediction is None else peer_prediction
    b_s = blend(w, benefits[0], c)
    b_d = blend(w, benefits[1], c, p.perceived_hint_boost)
    if has_hint:
        b_s += p.perceived_hint_boost * (1 - b_s)
    learn = p.learning_value * control * (1 - c)
    scores = {'wait': p.wait_value}
    if remaining >= a:
        scores['attempt'] = b_s - estimate + learn - effort_cost * a / scale
    hint_time = p.peer_request_ticks + p.peer_hint_ticks + a
    answer_time = p.peer_request_ticks + p.peer_answer_ticks
    if can_hint and p.allow_hint and remaining >= hint_time:
        scores['hint'] = access[0] * (b_d - estimate) + p.hint_learning_value_multiplier * learn - effort_cost * hint_time / scale
    if can_answer and p.allow_answer and remaining >= answer_time:
        scores['answer'] = access[1] * (peer_benefit - estimate) - effort_cost * answer_time / scale + p.grade_response * shortfall
    if has_packet and remaining >= p.submit_ticks:
        scores['submit'] = p.submit_value
    if ai_available and p.ai_mode == 'answer' and remaining >= p.ai_answer_ticks:
        scores['ai_answer'] = benefits[3] - estimate - effort_cost * p.ai_answer_ticks / scale + p.grade_response * shortfall
    if ai_available and p.ai_mode == 'tutor' and remaining >= p.ai_tutor_ticks + a:
        predicted = benefits[4] if p.grade_effort_only else blend(w, benefits[4], c, p.perceived_hint_boost)
        scores['ai_tutor'] = predicted - estimate + p.hint_learning_value_multiplier * learn - effort_cost * (p.ai_tutor_ticks + a) / scale
    return scores


def declared_grade_credit(packet, used, p):
    credit, route = corrected_grade_credit(packet, used)
    if route in {'guided', 'ai_guided'}:
        weight = p.peer_attempt_credit if route == 'guided' else p.tutor_attempt_credit
        credit[0] = weight
        credit[1 if route == 'guided' else 4] = 1 - weight
    return credit, route
