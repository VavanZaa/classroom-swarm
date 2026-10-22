"""Independent audit gates, without modifying the frozen simulation engine."""
from copy import deepcopy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from e24_existing_mechanism_audit import deep_audit, build_jobs
from test_v4_promising import declaration, run, constant
from classroom_swarm import promising_config as config
from classroom_swarm.promising_validation import validate_promising_log


def curriculum_log():
    c = declaration(h=3); c['design']['curriculum']['enabled'] = True
    return run(c)


def test_independent_audit_accepts_intact_log():
    counts = deep_audit(curriculum_log())
    assert counts['choices'] == 3 and counts['readiness'] > 0 and counts['pretests'] == 12


@pytest.mark.parametrize('table', ['curriculum_readiness', 'curriculum_choices', 'curriculum_pretest'])
def test_missing_evidence_gap_is_detected(table):
    a = curriculum_log(); a.tables[table] = []
    validate_promising_log(a)  # Existing validator only checks rows that remain.
    with pytest.raises(AssertionError): deep_audit(a)


def test_coordinated_logged_policy_evidence_is_detected():
    a = curriculum_log()
    # Preserve the selected level while lying about the teacher's evidence.
    import json
    row = a.tables['curriculum_choices'][0]
    means = json.loads(row['observed_means']); means[0] += .001
    row['observed_means'] = json.dumps(means)
    validate_promising_log(a)
    with pytest.raises(AssertionError): deep_audit(a)


@pytest.mark.parametrize('branch', ['workload', 'incentives'])
def test_replaced_teacher_branches_are_rejected(branch):
    c = declaration(); c['mechanisms'][branch]['enabled'] = True
    with pytest.raises(ValueError, match='replaces'): config.resolve_config(c)


@pytest.mark.parametrize('field,value', [('time_budget', 1), ('actions', []), ('instruction_ticks', 1), ('allocation', 'round_robin')])
def test_teacher_work_has_authority_over_legacy_controls(field, value):
    c = declaration(); a = run(c); c['teacher'][field] = value; b = run(c)
    for table in ('teacher_actions', 'teacher_forecasts', 'learning_doses', 'topic_states', 'assessment_scores'):
        assert a.tables[table] == b.tables[table]


@pytest.mark.parametrize('field', ['hint_learning_multiplier', 'content_learning_multiplier'])
def test_productive_dose_replaces_legacy_learning_boosts(field):
    c = declaration(); c['params']['allow_hint'] = True
    c['network']['edges'] = [[0, 1], [2, 3]]
    a = run(c); c['params'][field] = 0.; b = run(c)
    assert a.tables['learning_doses'] == b.tables['learning_doses']
    assert a.tables['topic_states'] == b.tables['topic_states']


def test_explicit_skills_do_not_create_initial_gain():
    c = declaration(h=1, teacher=False)
    c['extensions']['learning_process']['effort_grid'] = [0.]
    c['initial']['knowledge'] = constant(.9)
    c['design']['curriculum'].update(enabled=True, adaptive=False, initial_values=[[.1, .2, .3]] * 4)
    a = run(c); deep_audit(a)
    assert not a.tables['topic_learning']
    assert all(abs(r['K0'] - .2) < 1e-12 for r in a.tables['traits'])
    assert all(abs(r['K'] - .2) < 1e-12 for r in a.tables['students'])


def test_diagnostic_changes_one_field_with_same_draws():
    from classroom_swarm import experiment_config as legacy
    jobs = build_jobs(0)
    by = {(j['case'], j['arm'], j['section'], j['profile']): j for j in jobs}
    for j in jobs:
        if j['profile'] == 'baseline': continue
        baseline = by[j['case'], j['arm'], j['section'], 'baseline']
        a, b = deepcopy(j['resolved']), deepcopy(baseline['resolved'])
        a.pop('name'); b.pop('name')
        assert legacy.differences(a, b) == [j['changed_parameter']]
        assert j['seed'] == baseline['seed'] and j['replicate'] == baseline['replicate']
