"""A29 tutoring activity/content fork; A28 sources remain immutable."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .declared_settings import (DeclaredParams, default_initial as old_default,
    resolve_initial as old_resolve, initial_state as old_state, declared_scores)
from .distributions import sample_distribution, validate_distribution


@dataclass(frozen=True)
class TutoringParams(DeclaredParams):
    tutoring_activity: str = 'joint_practice'  # legacy_hint, joint_practice, shared_practice
    guided_practice_ticks: int = 3
    content_learning_multiplier: float = 1.
    content_performance_multiplier: float = 1.
    readiness_band: float = .5
    quality_learning_rate: float = .2
    quality_target_weight: float = 1.
    quality_check_probability: float = 1.
    helper_content_learning: bool = True

    def validate(self):
        super().validate()
        if self.tutoring_activity not in {'legacy_hint', 'joint_practice', 'shared_practice'}:
            raise ValueError('tutoring_activity')
        if not 1 <= self.guided_practice_ticks <= self.ticks:
            raise ValueError('guided_practice_ticks')
        for name in ('content_learning_multiplier', 'quality_target_weight'):
            if not 0 <= getattr(self, name) <= 10:
                raise ValueError(name)
        for name in ('content_performance_multiplier', 'quality_learning_rate', 'quality_check_probability'):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(name)
        if not 0 < self.readiness_band <= 2:
            raise ValueError('readiness_band')


def default_initial(p):
    return {**old_default(p), 'teaching_skill': {'kind': 'constant', 'value': 1.},
        'source_quality': {'kind': 'constant', 'value': .5},
        'task_difficulty': {'kind': 'uniform', 'low': 0., 'high': 1.}}


def resolve_initial(p, overrides=None):
    defaults = default_initial(p)
    overrides = overrides or {}
    if set(overrides) - set(defaults):
        raise ValueError(f'unknown initial fields: {set(overrides) - set(defaults)}')
    extra = {'teaching_skill', 'source_quality', 'task_difficulty'}
    result = old_resolve(p, {k:v for k,v in overrides.items() if k not in extra})
    for name in extra:
        spec = overrides.get(name, defaults[name])
        size = {'teaching_skill': p.N, 'source_quality': p.N*p.N, 'task_difficulty': p.items}[name]
        validate_distribution(spec, low=0., high=1., size=size)
        result[name] = spec
    return result


def initial_state(p, draws, initial=None):
    specs = resolve_initial(p, initial)
    base = {k:v for k,v in specs.items() if k in old_default(p)}
    _, state, traits, B, A = old_state(p, draws, base)
    for name, stream, shape in [('teaching_skill',122,(p.N,)), ('source_quality',121,(p.N,p.N))]:
        z = np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,stream])).standard_normal(shape)
        state[name] = sample_distribution(specs[name], z, low=0., high=1.)
    return specs, state, traits, B, A


def task_content(spec, draws, h):
    z = np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,120,h])).standard_normal(draws.M_H)
    return sample_distribution(spec, z, low=0., high=1.)


def content_effect(p, learner_k, provider_k, skill, difficulty, learner_u, provider_u, explanation_u):
    """Environment physics, never a policy input. Scalar competence, item-specific content.

    Correctness depends on task difficulty; even equal scalar K can complement each
    other because their realized item knowledge differs. Incorrect content cannot
    directly teach. Readiness can suppress otherwise correct but inaccessible content.
    """
    own = learner_u < np.clip(learner_k + .5 - difficulty, 0., 1.)
    known = provider_u < np.clip(provider_k + .5 - difficulty, 0., 1.)
    correct = known & (explanation_u < skill)
    readiness = np.clip(1. - np.maximum(0., difficulty - learner_k) / p.readiness_band, 0., 1.)
    transfer = correct * (~own) * readiness
    return dict(correct=correct, novel=~own, transfer=transfer,
                learner_quality=float(np.mean(transfer)), helper_quality=float(np.mean(correct & ~own)))


def tutoring_scores(p, *args, quality=.5, **kwargs):
    scores = declared_scores(p, *args, **kwargs)
    if p.tutoring_activity != 'joint_practice':
        return scores
    c, control, benefits, effort, estimate, has_packet, has_hint, access, can_hint, can_answer, remaining = args
    scores.pop('hint', None)
    duration = p.peer_request_ticks + p.guided_practice_ticks
    if p.allow_hint and can_hint and remaining >= duration:
        # Private observed source-quality belief affects expected homework value.
        prediction = p.confidence_weight * benefits[1] + (1-p.confidence_weight) * c
        prediction += p.perceived_hint_boost * quality * (1-prediction)
        scores['hint'] = access[0]*(prediction-estimate) - effort*duration/p.effort_time_scale
        scores['hint'] += p.hint_learning_value_multiplier*p.learning_value*control*(1-c)
    return scores
