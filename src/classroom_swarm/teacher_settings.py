"""A30 teacher interface and policy. No latent student state enters this module."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import math
import numpy as np

from .distributions import number

TEACHER_STREAMS = {'observation_coverage': 126, 'observation_noise': 127,
                   'attendance': 128, 'retrieval': 129, 'explanation': 130}
ACTIONS = {'instruction', 'explanation', 'corrective_feedback', 'guidance'}


@dataclass(frozen=True)
class TeacherSettings:
    enabled: bool = False
    identity: str = 'teacher-0'
    time_budget: int = 8
    admin_ticks: int = 0
    grading_ticks_per_student: int = 0
    grading_automation: float = 0.
    actions: list[str] = field(default_factory=lambda: ['instruction', 'guidance'])
    instruction_ticks: int = 3
    explanation_ticks: int = 3
    corrective_feedback_ticks: int = 3
    guidance_ticks: int = 1
    allocation: str = 'lowest_observed'  # or round_robin
    curriculum: str = 'fixed'  # or adaptive
    fixed_difficulty: float = .5
    difficulty_offset: float = 0.
    knowledge: float = .95
    teaching_skill: float = 1.
    learning_multiplier: float = 1.
    participation_probability: float = 1.
    observation_sources: list[str] = field(default_factory=lambda: ['homework', 'exam'])
    observation_delay: int = 0
    observation_coverage: float = 1.
    observation_noise_std: float = 0.
    observation_prior: float = .5
    observation_learning_rate: float = .5
    assisted_observation_weight: float = 0.
    guidance_strength: float = .1
    guidance_decay: float = .5
    guidance_confidence_rate: float = .2

    def validate(self, p):
        if not isinstance(self.enabled, bool):
            raise ValueError('teacher.enabled must be boolean')
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError('teacher.identity must be a nonempty string distinct from student ids')
        for name in ('time_budget', 'admin_ticks', 'grading_ticks_per_student', 'observation_delay',
                     'instruction_ticks', 'explanation_ticks', 'corrective_feedback_ticks', 'guidance_ticks'):
            value = getattr(self, name)
            minimum = 1 if name.endswith('_ticks') and name not in {'admin_ticks'} else 0
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f'teacher.{name} must be an integer >= {minimum}')
        if self.enabled and self.time_budget > p.ticks:
            raise ValueError('teacher.time_budget must fit within homework ticks')
        if not isinstance(self.actions, list) or any(not isinstance(a,str) for a in self.actions) or set(self.actions) - ACTIONS or len(set(self.actions)) != len(self.actions):
            raise ValueError('teacher.actions must list distinct supported actions in priority order')
        if self.allocation not in {'lowest_observed', 'round_robin'}:
            raise ValueError('teacher.allocation')
        if self.curriculum not in {'fixed', 'adaptive'}:
            raise ValueError('teacher.curriculum')
        if not isinstance(self.observation_sources, list) or any(not isinstance(a,str) for a in self.observation_sources) or set(self.observation_sources) - {'homework', 'exam'} or len(set(self.observation_sources)) != len(self.observation_sources):
            raise ValueError('teacher.observation_sources')
        for name in ('grading_automation', 'fixed_difficulty', 'knowledge', 'teaching_skill',
                     'participation_probability', 'observation_coverage', 'observation_prior',
                     'observation_learning_rate', 'assisted_observation_weight', 'guidance_strength',
                     'guidance_decay', 'guidance_confidence_rate'):
            if not 0 <= number(getattr(self, name), f'teacher.{name}') <= 1:
                raise ValueError(f'teacher.{name} must be in [0,1]')
        if not 0 <= number(self.learning_multiplier, 'teacher.learning_multiplier') <= 10:
            raise ValueError('teacher.learning_multiplier must be in [0,10]')
        if not -1 <= number(self.difficulty_offset, 'teacher.difficulty_offset') <= 1:
            raise ValueError('teacher.difficulty_offset must be in [-1,1]')
        if not 0 <= number(self.observation_noise_std, 'teacher.observation_noise_std') <= 1:
            raise ValueError('teacher.observation_noise_std must be in [0,1]')
        if self.enabled and p.tutoring_activity == 'legacy_hint':
            raise ValueError('enabled teachers require joint_practice or shared_practice')

    @property
    def grading_cost(self):
        return math.ceil(self.grading_ticks_per_student * (1 - self.grading_automation))


def teacher_random(draws, name, homework, shape):
    rng = np.random.default_rng(np.random.SeedSequence(
        [draws.seed, draws.replicate, TEACHER_STREAMS[name], homework]))
    return rng.standard_normal(shape) if name == 'observation_noise' else rng.random(shape)


class TeacherObserver:
    """Released, partially observed assessment scores; never reads K or current errors."""
    def __init__(self, settings, n):
        self.settings = settings
        self.estimate = np.full(n, settings.observation_prior)
        self.seen = np.zeros(n, dtype=int)
        self.queue = []

    def enqueue(self, source, source_homework, student, score, assisted, release, release_tick=0):
        if source in self.settings.observation_sources:
            self.queue.append(dict(source=source, source_homework=source_homework,
                                   student=student, score=score, assisted=bool(assisted),
                                   release=release, release_tick=release_tick))

    def release(self, homework, draws, tick=0):
        s, rows = self.settings, []
        # Index by source homework/id/source, so scheduling never shifts random draws.
        for item in sorted([q for q in self.queue if (q['release'],q['release_tick']) <= (homework,tick)],
                           key=lambda q: (q['release'], q['release_tick'], q['source_homework'], q['source'], q['student'])):
            i, source = item['student'], int(item['source'] == 'exam')
            coverage = teacher_random(draws, 'observation_coverage', item['source_homework'], (2, draws.N))[source, i]
            noise = teacher_random(draws, 'observation_noise', item['source_homework'], (2, draws.N))[source, i]
            observed = float(np.clip(item['score'] + s.observation_noise_std * noise, 0, 1)) if coverage < s.observation_coverage else None
            weight = s.assisted_observation_weight if item['assisted'] else 1.
            before = float(self.estimate[i])
            if observed is not None and weight > 0:
                self.estimate[i] += s.observation_learning_rate * weight * (observed - self.estimate[i])
                self.seen[i] += 1
            rows.append(dict(homework=homework, tick=item['release_tick'] if item['release']==homework else 0,
                             teacher=s.identity, **item,
                             observed_score=observed, weight=weight, estimate_before=before,
                             estimate_after=float(self.estimate[i]), seen=int(self.seen[i])))
            self.queue.remove(item)
        return rows


def plan_teacher(settings, estimates, seen, last_served, homework, cursor, student_ticks):
    """Plan appointments from the observation state and previous service only."""
    n, plans, queue = len(estimates), [], []
    order = sorted(range(n), key=lambda i: ((estimates[i], last_served[i], i)
                   if settings.allocation == 'lowest_observed' else (last_served[i], i)))
    for action in settings.actions:
        groups = [list(range(n))] if action == 'instruction' else [[i] for i in order]
        duration = getattr(settings, action + '_ticks')
        for targets in groups:
            reason = ''
            if action == 'corrective_feedback' and not seen[targets[0]]:
                reason = 'no_released_assessment'
            elif cursor + duration > min(settings.time_budget, student_ticks):
                reason = 'capacity'
            estimate = float(np.mean(estimates[targets]))
            difficulty = settings.fixed_difficulty if settings.curriculum == 'fixed' else float(np.clip(estimate + settings.difficulty_offset, 0, 1))
            record = dict(homework=homework, teacher=settings.identity, action=action,
                          targets=targets, observed_estimate=estimate, seen=[int(seen[i]) for i in targets],
                          difficulty=difficulty, duration=duration, status='queued' if not reason else 'unserved', reason=reason)
            queue.append(record)
            if not reason:
                plans.append(dict(record, start=cursor, end=cursor + duration,
                                  action_id=f'teacher-h{homework}-a{len(plans)}'))
                cursor += duration
    return plans, queue, cursor


def resolve_teacher(overrides=None):
    if overrides is None:
        return TeacherSettings()
    if not isinstance(overrides, dict) or set(overrides) - set(asdict(TeacherSettings())):
        raise ValueError('unknown teacher fields or invalid teacher object')
    return TeacherSettings(**overrides)
