"""A32 declarations. Numerical defaults are hypotheses, never fitted study estimates."""
from dataclasses import dataclass, field, fields, asdict
import math
import numpy as np
from .mechanism_settings import bounded, integer
from .distributions import validate_distribution


@dataclass(frozen=True)
class LearningProcess:
    enabled: bool = False
    effort_grid: list = field(default_factory=lambda: [0., .5, 1.])
    reference_ticks: float = 3.
    attention: dict = field(default_factory=lambda: {'kind': 'constant', 'value': .9})
    attention_effort_weight: float = .1
    distraction: dict = field(default_factory=lambda: {'kind': 'constant', 'value': .1})
    fatigue_sensitivity: dict = field(default_factory=lambda: {'kind': 'constant', 'value': .3})
    future_test_value: dict = field(default_factory=lambda: {'kind': 'constant', 'value': 0.})
    fatigue_initial: dict = field(default_factory=lambda: {'kind': 'constant', 'value': 0.})
    fatigue_per_effort_tick: float = .01
    recovery: float = .5
    fatigue_cost: float = .05
    material_access: bool = True
    material_quality: float = .8
    self_reasoning_quality: float = .1
    corrective_feedback: bool = True
    guess_probability: float = 0.
    belief_gain_rate: float = .02
    minimum_operational_effort: float = .1
    shared_explanation_share: float = .5
    costs: dict = field(default_factory=lambda: {'attempt': 1., 'teacher': .15,
        'guided': .75, 'helper': 1., 'answer': .1, 'ai_answer': .1,
        'ai_tutor': .2, 'format_practice': 1., 'concept_revision': 1., 'coaching': .2})
    source_multipliers: dict = field(default_factory=lambda: {'attempt': 1., 'teacher': 1.,
        'guided': 1., 'helper': 1., 'format_practice': 1., 'concept_revision': 1., 'coaching': 1.})


@dataclass(frozen=True)
class RewardContract:
    strength: float = 1.
    power: float = 1.
    mode: str = 'level'
    sources: dict = field(default_factory=lambda: {'exam': 1., 'homework': 0.})
    forms: list = field(default_factory=list)
    missing: str = 'zero'
    denominator: str = 'eligible'
    cap: float = 1.
    payment_delay: int = 1
    discount: float = 1.
    baseline_scores: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TeacherWork:
    enabled: bool = False
    total_budget: int = 8
    before_class_ticks: int = 2
    after_class_ticks: int = 2
    protected_instruction_ticks: int = 3
    minimum_segment_ticks: int = 1
    allow_instruction_crowdout: bool = False
    preparation_ticks: int = 1
    preparation_rate: float = .2
    preparation_quality_bonus: float = .3
    preparation_initial: float = 0.
    preparation_decay: float = 0.
    actions: list = field(default_factory=lambda: ['guidance', 'explanation'])
    planning_horizon: int = 2
    expected_study_opportunities: float = 2.
    expected_engagement: float = .7
    belief_gain_rate: float = .02
    belief_format_rate: float = .1
    belief_update_rate: float = 0.
    intrinsic_weight: float = .2
    effort_cost: float = .001
    quadratic_cost: float = .002
    contract: RewardContract = field(default_factory=RewardContract)


@dataclass(frozen=True)
class HelperContract:
    enabled: bool = False
    pairs: list = field(default_factory=list)  # [helper slot, recipient slot]; explicit assignments
    baseline_scores: list = field(default_factory=list)
    checkpoints: list = field(default_factory=list)
    form: str = 'core'
    top_fraction: float = .1
    prize: float = 1.
    certificate_value: float = 0.
    reward_preference: dict = field(default_factory=lambda: {'kind': 'constant', 'value': 1.})
    payment_delay: int = 1
    discount: float = 1.
    belief_win_probability: float = .1
    belief_progress_rate: float = .03
    offer_ticks: list = field(default_factory=lambda: [3])
    session_ticks: int = 3
    helper_cost_multiplier: float = 1.
    recipient_acceptance: float = 1.
    helper_intrinsic_value: float = .02
    placebo_payment: bool = False


@dataclass(frozen=True)
class TestPreparation:
    enabled: bool = False
    forms: list = field(default_factory=lambda: ['familiar', 'novel', 'unrelated', 'core'])
    initial_format: list = field(default_factory=list)
    format_transfer: list = field(default_factory=list)
    format_decay: float = 0.
    format_rate: float = .1
    practice_form: str = 'familiar'
    practice_ticks: int = 3
    concept_share: float = .2
    format_share: float = .8
    revision_concept_share: float = 1.
    revision_format_share: float = 0.
    coaching_concept_share: float = .2
    coaching_format_share: float = .8
    exams: list = field(default_factory=list)
    # Exam dict: name, form, topic_weights, difficulty, format_loading, stakes, access_cost.
    participation: bool = False
    participation_stakes: float = 1.
    participation_cost: float = 0.
    followup_cost_reduction: float = .2


@dataclass(frozen=True)
class EffortSettings:
    student_ids: list = field(default_factory=list)
    learning_process: LearningProcess = field(default_factory=LearningProcess)
    teacher_work: TeacherWork = field(default_factory=TeacherWork)
    helper_contract: HelperContract = field(default_factory=HelperContract)
    test_preparation: TestPreparation = field(default_factory=TestPreparation)

    @property
    def active(self):
        return any(getattr(self, k).enabled for k in BRANCHES)

    def validate(self, p, teacher, mechanisms):
        ids = self.student_ids or list(range(p.N))
        if len(ids) != p.N or len(set(ids)) != p.N:
            raise ValueError('student_ids must be N distinct nonnegative integers')
        for i in ids: integer(i, 'student_ids')
        for branch in BRANCHES:
            x = getattr(self, branch)
            if not isinstance(x.enabled, bool): raise ValueError(branch + '.enabled must be boolean')
            for descriptor in fields(x):
                k, v = descriptor.name, getattr(x, descriptor.name)
                if descriptor.type is float:
                    bounded(v, branch + '.' + k, 0, 10000)
                elif descriptor.type is bool and not isinstance(v, bool): raise ValueError(k + ' must be boolean')
                elif descriptor.type is list and not isinstance(v, list): raise ValueError(k + ' must be a list')
                elif descriptor.type is dict and not isinstance(v, dict): raise ValueError(k + ' must be an object')
        l = self.learning_process
        if not isinstance(l.effort_grid, list) or not l.effort_grid or len(set(l.effort_grid)) != len(l.effort_grid):
            raise ValueError('effort_grid must be nonempty and distinct')
        for e in l.effort_grid: bounded(e, 'effort_grid')
        bounded(l.reference_ticks, 'reference_ticks', .000001, 10000)
        for key in ('attention_effort_weight', 'recovery', 'material_quality', 'self_reasoning_quality', 'guess_probability', 'shared_explanation_share'):
            bounded(getattr(l, key), key)
        for key in ('material_access', 'corrective_feedback'):
            if not isinstance(getattr(l, key), bool): raise ValueError(key + ' must be boolean')
        for key in ('attention', 'distraction', 'fatigue_sensitivity', 'fatigue_initial', 'future_test_value'):
            validate_distribution(getattr(l, key), low=0, high=None if key == 'future_test_value' else 1, size=p.N)
        defaults = LearningProcess()
        for name in ('costs', 'source_multipliers'):
            v = getattr(l, name)
            if not isinstance(v, dict) or set(v) != set(getattr(defaults, name)):
                raise ValueError(name + ' must declare every supported activity')
            for key, value in v.items(): bounded(value, name + '.' + key, 0, 10000)
        for key in ('attempt', 'teacher', 'guided', 'helper', 'format_practice', 'concept_revision', 'coaching'):
            if l.costs[key] <= 0: raise ValueError('productive cognitive cost must be positive')
        w = self.teacher_work
        for key in ('total_budget', 'before_class_ticks', 'after_class_ticks', 'protected_instruction_ticks',
                    'preparation_ticks', 'planning_horizon', 'minimum_segment_ticks'):
            integer(getattr(w, key), key, 1 if key in ('planning_horizon', 'minimum_segment_ticks') else 0)
        for key in ('preparation_initial', 'preparation_decay', 'preparation_rate', 'expected_engagement', 'belief_update_rate'):
            bounded(getattr(w, key), key)
        if not isinstance(w.allow_instruction_crowdout, bool): raise ValueError('crowdout must be boolean')
        if not isinstance(w.actions, list) or len(set(w.actions)) != len(w.actions) or set(w.actions) - {'guidance', 'explanation', 'coaching', 'followup'}:
            raise ValueError('unsupported teacher_work.actions')
        if w.enabled:
            if not teacher.enabled: raise ValueError('teacher_work requires teacher')
            if mechanisms.workload.enabled or mechanisms.incentives.enabled:
                raise ValueError('A32 teacher_work replaces A31 workload/incentives; cannot combine')
            if w.preparation_ticks + teacher.admin_ticks > w.before_class_ticks:
                raise ValueError('mandatory prep/admin must fit before-class work period')
            if w.preparation_ticks + teacher.admin_ticks > w.total_budget:
                raise ValueError('mandatory prep/admin exceeds total work budget')
            if w.total_budget > w.before_class_ticks + p.ticks + w.after_class_ticks:
                raise ValueError('teacher budget exceeds declared work periods')
            if not w.allow_instruction_crowdout and (w.protected_instruction_ticks > p.ticks or
                    w.preparation_ticks + teacher.admin_ticks + w.protected_instruction_ticks > w.total_budget):
                raise ValueError('infeasible protected instruction')
            if w.protected_instruction_ticks % w.minimum_segment_ticks:
                raise ValueError('protected instruction must contain whole minimum segments')
        c = w.contract
        for key in ('strength', 'cap'): bounded(getattr(c, key), key, 0, 10000)
        bounded(c.power, 'power', .000001, 10); bounded(c.discount, 'discount')
        integer(c.payment_delay, 'payment_delay')
        if c.mode not in ('level', 'gain') or c.missing not in ('zero', 'exclude') or c.denominator not in ('eligible', 'observed'):
            raise ValueError('unsupported teacher reward rule')
        if not isinstance(c.sources, dict) or set(c.sources) != {'exam', 'homework'}:
            raise ValueError('contract.sources must declare exam and homework')
        for v in c.sources.values(): bounded(v, 'source weight', 0, 10000)
        if not isinstance(c.forms, list) or any(not isinstance(f, str) for f in c.forms): raise ValueError('invalid contract forms')
        if not isinstance(c.baseline_scores, dict): raise ValueError('contract baseline_scores must be an object')
        for form, scores in c.baseline_scores.items():
            if not isinstance(form, str) or not isinstance(scores, list) or len(scores) != p.N:
                raise ValueError('contract baseline must contain N observed scores per form')
            for value in scores: bounded(value, 'contract baseline score')
        if w.enabled and c.mode == 'gain' and c.sources['homework'] > 0 and 'homework' not in c.baseline_scores:
            raise ValueError('homework gain reward requires observed baseline_scores.homework')
        h = self.helper_contract
        integer(h.session_ticks, 'session_ticks', 1); integer(h.payment_delay, 'payment_delay')
        for key in ('top_fraction', 'discount', 'belief_win_probability', 'recipient_acceptance'):
            bounded(getattr(h, key), key)
        validate_distribution(h.reward_preference, low=0, high=None, size=p.N)
        if not isinstance(h.placebo_payment, bool): raise ValueError('placebo_payment must be boolean')
        if not isinstance(h.pairs, list): raise ValueError('pairs must be a list')
        flat = []
        for pair in h.pairs:
            if not isinstance(pair, list) or len(pair) != 2: raise ValueError('pair must have helper and recipient')
            for i in pair:
                integer(i, 'pair index')
                if i >= p.N: raise ValueError('pair index out of range')
            flat.extend(pair)
        if len(set(flat)) != len(flat): raise ValueError('contract pairs must be disjoint')
        if h.enabled and not h.pairs: raise ValueError('helper contract requires frozen pairs')
        if h.baseline_scores and len(h.baseline_scores) != p.N: raise ValueError('baseline_scores must have N entries')
        for v in h.baseline_scores: bounded(v, 'baseline score')
        for tick in h.offer_ticks:
            integer(tick, 'offer_ticks')
            if tick + h.session_ticks > p.ticks: raise ValueError('helper session outside classroom')
        for checkpoint in h.checkpoints:
            integer(checkpoint, 'checkpoint', 1)
            if checkpoint > p.H or checkpoint % p.exam_every: raise ValueError('checkpoint must be an exam date')
        t = self.test_preparation
        if not isinstance(t.forms, list) or not t.forms or any(not isinstance(f, str) or not f for f in t.forms) or len(set(t.forms)) != len(t.forms):
            raise ValueError('forms must be distinct nonempty names')
        if t.practice_form not in t.forms: raise ValueError('unknown practice form')
        integer(t.practice_ticks, 'practice_ticks', 1)
        for key in ('format_decay', 'format_rate', 'concept_share', 'format_share', 'revision_concept_share',
                    'revision_format_share', 'coaching_concept_share', 'coaching_format_share'):
            bounded(getattr(t, key), key)
        for a, b in [('concept_share', 'format_share'), ('revision_concept_share', 'revision_format_share'),
                     ('coaching_concept_share', 'coaching_format_share')]:
            if getattr(t, a) + getattr(t, b) > 1 + 1e-12: raise ValueError('concept/form dose shares exceed one')
        count = len(mechanisms.topics.names) if mechanisms.topics.enabled else 1
        for value, shape in [(t.initial_format, (p.N, len(t.forms))), (t.format_transfer, (len(t.forms), len(t.forms)))]:
            if value:
                a = np.asarray(value)
                if a.shape != shape or a.dtype.kind not in 'fi' or not np.all(np.isfinite(a)) or np.any((a < 0) | (a > 1)):
                    raise ValueError('invalid format state/transfer matrix')
        if t.format_transfer and not np.all(np.diag(t.format_transfer) == 1): raise ValueError('format transfer diagonal must be one')
        names = []
        for exam in t.exams:
            required = {'name', 'form', 'topic_weights', 'difficulty', 'format_loading', 'stakes', 'access_cost'}
            if not isinstance(exam, dict) or set(exam) != required: raise ValueError('exam must declare exactly ' + str(sorted(required)))
            if exam['form'] not in t.forms: raise ValueError('unknown exam form')
            if not isinstance(exam['name'], str) or not exam['name']: raise ValueError('exam name required')
            names.append(exam['name'])
            weights = np.asarray(exam['topic_weights'])
            if weights.shape != (count,) or weights.dtype.kind not in 'fi' or np.any(weights < 0) or not np.isclose(weights.sum(), 1):
                raise ValueError('exam topic weights must sum to one')
            for key in ('difficulty', 'format_loading'): bounded(exam[key], key)
            for key in ('stakes', 'access_cost'): bounded(exam[key], key, 0, 10000)
        if len(set(names)) != len(names): raise ValueError('exam names must be distinct')
        if not isinstance(t.participation, bool): raise ValueError('participation must be boolean')
        available = set(t.forms) if t.enabled else {'core'}
        if set(c.forms) - (available | {'homework'}) or (h.enabled and h.form not in available): raise ValueError('reward references unavailable form')
        if set(c.baseline_scores) - (available | {'homework'}): raise ValueError('baseline references unavailable form')
        exam_forms = {d['form'] for d in (t.exams or default_exams(t, count))}
        if set(c.forms) - (exam_forms | {'homework'}) or (h.enabled and h.form not in exam_forms):
            raise ValueError('reward form has no scheduled exam')
        if w.enabled and {'coaching', 'followup'} & set(w.actions) and not t.enabled:
            raise ValueError('coaching/followup require test_preparation')
        if h.enabled and any(tick < w.protected_instruction_ticks for tick in h.offer_ticks) and w.enabled:
            raise ValueError('helper offer conflicts with protected instruction')


BRANCHES = {'learning_process': LearningProcess, 'teacher_work': TeacherWork,
            'helper_contract': HelperContract, 'test_preparation': TestPreparation}


def resolve_effort(value=None):
    if isinstance(value, EffortSettings): return value
    value = {} if value is None else value
    if not isinstance(value, dict) or set(value) - (set(BRANCHES) | {'student_ids'}): raise ValueError('unknown A32 declaration')
    result = {'student_ids': value.get('student_ids', [])}
    for key, cls in BRANCHES.items():
        v = value.get(key, {})
        if not isinstance(v, dict) or set(v) - {f.name for f in fields(cls)}: raise ValueError('unknown ' + key + ' field')
        v = dict(v)
        if key == 'teacher_work' and 'contract' in v:
            c = v['contract']
            if not isinstance(c, dict) or set(c) - {f.name for f in fields(RewardContract)}: raise ValueError('unknown reward contract field')
            v['contract'] = RewardContract(**c)
        result[key] = cls(**v)
    return EffortSettings(**result)


def default_exams(t, count):
    balanced = [1 / count] * count
    if not t.enabled:
        return [dict(name='core', form='core', topic_weights=balanced, difficulty=.5, format_loading=0., stakes=1., access_cost=0.)]
    concept = [1.] + [0.] * (count - 1)
    unrelated = ([0., 1.] + [0.] * (count - 2)) if count > 1 else concept
    return [dict(name=form, form=form, topic_weights=unrelated if form == 'unrelated' else balanced if form == 'core' else concept,
        difficulty=.5, format_loading=.5 if form == t.practice_form else 0., stakes=1., access_cost=0.) for form in t.forms]


def contract_value(contract, scores, baseline=None, source='exam', form='core'):
    """One evaluator for forecasts and payments; missing remains missing in evidence."""
    if contract.forms and form not in contract.forms: return 0.
    baseline = [0.] * len(scores) if baseline is None else baseline
    values = []
    for score, start in zip(scores, baseline):
        if score is None:
            if contract.missing == 'exclude': continue
            contribution = 0.
        else:
            contribution = score if contract.mode == 'level' else max(0., score - start)
        values.append(min(contract.cap, contribution) ** contract.power)
    denominator = len(scores) if contract.denominator == 'eligible' else len(values)
    return contract.strength * contract.sources[source] * sum(values) / max(1, denominator)
