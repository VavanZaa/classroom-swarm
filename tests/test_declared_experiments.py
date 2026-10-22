"""A28 distribution, parameter, configuration and execution contracts."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

from classroom_swarm.declared_settings import (
    DeclaredParams, declared_scores, initial_state,
)
from classroom_swarm.distributions import sample_distribution, validate_distribution
from classroom_swarm.experiment_config import (
    load_config, make_graph, preflight, resolve_config, run_experiment, sha256, template,
)
from classroom_swarm.graphs import generate_er
from classroom_swarm.v4_corrected import CorrectedParams, corrected_scores, simulate_corrected
from classroom_swarm.v4_declared import simulate_declared, validate_declared_log
from classroom_swarm.v4_public_ai import PublicAIDraws


def run(p, initial=None):
    return simulate_declared(p, generate_er(p.N, 3, 71),
                            PublicAIDraws(82, 0, p.N, p.items, p.exam_items), initial=initial)


@pytest.mark.parametrize('mode', ['none', 'answer', 'tutor'])
@pytest.mark.parametrize('motivation', [True, False])
def test_declared_defaults_reproduce_a26_every_shared_table(mode, motivation):
    settings = dict(N=8, H=8, ai_mode=mode)
    if not motivation:
        settings.update(grade_effort_only=False, learning_value=.25, wait_value=.025)
    p = DeclaredParams(**settings)
    old = simulate_corrected(CorrectedParams(**settings), generate_er(8, 3, 71),
                             PublicAIDraws(82, 0, 8, 10, 30))
    log = run(p)
    for key, rows in old.tables.items():
        assert log.tables[key] == rows, key
    validate_declared_log(log)


def test_score_parity_and_new_coefficients_are_live():
    p = DeclaredParams(grade_effort_only=False, learning_value=.25)
    args = (.6, .5, np.array([.5] * 5), .15, .2, True, True, (.5, .5), True, True, 12)
    kw = dict(ai_available=True)
    for mode in ('none', 'answer', 'tutor'):
        q = replace(p, ai_mode=mode)
        assert declared_scores(q, *args, **kw) == corrected_scores(q, *args, **kw)
    base = declared_scores(p, *args, **kw)
    for field, value in [('effort_time_scale', 6), ('perceived_hint_boost', .5),
                         ('hint_learning_value_multiplier', 2), ('peer_request_ticks', 2),
                         ('peer_hint_ticks', 3), ('peer_answer_ticks', 2), ('submit_value', .1)]:
        assert declared_scores(replace(p, **{field: value}), *args, **kw) != base, field


@pytest.mark.parametrize('spec', [
    {'kind': 'constant', 'value': .8},
    {'kind': 'normal', 'mean': .5, 'std': .1},
    {'kind': 'truncated_normal', 'mean': .85, 'std': .05, 'low': 0, 'high': 1},
    {'kind': 'lognormal', 'mean': .2, 'log_sd': .3},
    {'kind': 'lognormal', 'mean': .2, 'std': .05},
    {'kind': 'uniform', 'low': .2, 'high': .8},
    {'kind': 'choice', 'values': [.1, .9], 'weights': [1, 3]},
    {'kind': 'values', 'values': [.1, .2, .3, .4]},
])
def test_every_distribution_has_repeatable_finite_samples(spec):
    z = np.array([-1., 0., .5, 1.])
    a = sample_distribution(spec, z)
    np.testing.assert_array_equal(a, sample_distribution(spec, z))
    assert np.all(np.isfinite(a))
    if spec['kind'] == 'values':
        assert a.tolist() == spec['values']


def test_choice_quantiles_and_zero_spread():
    z = np.array([-2., 0., 2.])
    assert sample_distribution({'kind': 'choice', 'values': [1, 2], 'weights': [1, 3]}, z).tolist() == [1, 2, 2]
    assert sample_distribution({'kind': 'truncated_normal', 'mean': 1, 'std': 0,
                                'low': 0, 'high': 1}, z).tolist() == [1, 1, 1]


def test_lognormal_accepts_arithmetic_std_and_rejects_ambiguous_spread():
    z = np.array([-1., 0., 1.])
    mean, std = .1, .02
    sigma = np.sqrt(np.log1p((std / mean) ** 2))
    np.testing.assert_allclose(sample_distribution({'kind': 'lognormal', 'mean': mean, 'std': std}, z),
                               sample_distribution({'kind': 'lognormal', 'mean': mean, 'log_sd': sigma}, z))
    for spec in ({'kind': 'lognormal', 'mean': mean, 'std': std, 'log_sd': .25},
                 {'kind': 'lognormal', 'mean': 0, 'std': .1}):
        with pytest.raises(ValueError):
            validate_distribution(spec)


@pytest.mark.parametrize('spec', [
    {'kind': 'unknown'}, {'kind': 'constant', 'value': True},
    {'kind': 'uniform', 'low': 2, 'high': 1},
    {'kind': 'truncated_normal', 'mean': 100, 'std': .001, 'low': 0, 'high': 1},
    {'kind': 'normal', 'mean': 0, 'std': -1},
    {'kind': 'choice', 'values': [1], 'weights': [0]},
    {'kind': 'values', 'values': []},
    {'kind': 'constant', 'value': float('inf')},
    {'kind': 'lognormal', 'mean': 1, 'log_sd': -1},
    {'kind': 'constant', 'value': 1, 'typo': 4},
])
def test_bad_distribution_declarations_rejected(spec):
    with pytest.raises(ValueError):
        validate_distribution(spec)


def test_initial_states_independent_and_declared_values_reach_the_engine():
    initial = {
        'knowledge': {'kind': 'values', 'values': [.8] * 8},
        'learning_efficiency': {'kind': 'constant', 'value': .1},
        'effort_aversion': {'kind': 'constant', 'value': 0},
        'confidence': {'kind': 'constant', 'value': .2},
        'control': {'kind': 'constant', 'value': .7},
        'benefit_attempt': {'kind': 'constant', 'value': .9},
        'access_hint': {'kind': 'uniform', 'low': .1, 'high': .3},
    }
    log = run(DeclaredParams(N=8, H=1), initial)
    row = log.tables['initial_states'][0]
    assert (row['knowledge'], row['learning_efficiency'], row['effort_aversion'],
            row['confidence'], row['control'], row['benefit_attempt'], row['benefit_answer']) == (.8,.1,0,.2,.7,.9,.8)
    assert log.tables['students'][0]['C_before'] == .2
    assert all(.1 <= r['hint'] <= .3 for r in log.tables['initial_access'])
    validate_declared_log(log)
    p = DeclaredParams(N=8, H=1)
    draws = PublicAIDraws(82, 0, 8, 10, 30)
    a = initial_state(p, draws)[1]
    b = initial_state(p, draws, {'control': {'kind': 'uniform', 'low': .1, 'high': .9}})[1]
    for name in a:
        if name != 'control':
            np.testing.assert_array_equal(a[name], b[name])


@pytest.mark.parametrize('settings', [
    dict(peer_request_ticks=2, peer_hint_ticks=3, peer_answer_ticks=2, submit_ticks=2, wait_ticks=3),
    dict(max_ai_uses=0, ai_mode='answer'), dict(max_ai_uses=3, ai_mode='answer'),
    dict(peer_hint_base=0, peer_hint_knowledge_weight=0, tutor_attempt_credit=.8, ai_mode='tutor'),
    dict(attempt_learning_divisor=8, helper_learning_divisor=4, hint_learning_multiplier=.2,
         hint_performance_multiplier=.5, peer_attempt_credit=.7),
])
def test_custom_durations_credits_and_learning_pass_raw_audits(settings):
    log = run(DeclaredParams(N=8, H=8, **settings))
    validate_declared_log(log)
    if settings.get('max_ai_uses') == 0:
        assert not log.tables['ai_uses']


def small_config():
    return dict(schema_version=1, experiment_id='smoke', seed=82, replicates=2,
                params={'N': 8, 'H': 3}, network={'family': 'ER', 'd_bar': 3},
                conditions=[{'name': 'no_ai'}, {'name': 'answer', 'params': {'ai_mode': 'answer'}}],
                contrasts=[dict(condition='answer', reference='no_ai', kind='single_parameter',
                                identity='not_identity')])


def test_template_complete_valid_and_custom_sbm_and_weights():
    config = template()
    config['replicates'] = 1
    resolved = resolve_config(config)
    assert resolved['conditions'][0]['params'] == config['params']
    preflight(resolved)
    config['network'].update(block_sizes=[5, 10, 15], edge_weights={'kind': 'uniform', 'low': .5, 'high': 1.5})
    resolved = resolve_config(config)
    graph = make_graph(resolved['conditions'][0]['network'], 30, 82, 0)
    assert [graph.community.count(i) for i in range(3)] == [5,10,15]
    assert all(.5 <= v <= 1.5 for v in graph.weights)


def test_runner_locks_defaults_and_writes_actual_initial_states_and_hashes(tmp_path):
    config = small_config()
    resolved = resolve_config(config)
    assert resolved['contrasts'][0]['changed_settings'] == ['params.ai_mode']
    out = run_experiment(config, tmp_path / 'run')
    lock = json.loads((out / 'lock.json').read_text())
    assert lock['conditions'] == resolved['conditions']
    assert lock['sources'] and lock['software']
    for rep in (0,1):
        first = out / 'raw' / f'rep{rep:04d}' / 'no_ai'
        second = first.parent / 'answer'
        assert pq.read_table(first / 'traits.parquet').to_pylist() == pq.read_table(second / 'traits.parquet').to_pylist()
        assert pq.read_table(first / 'contacts.parquet').to_pylist() == pq.read_table(second / 'contacts.parquet').to_pylist()
        assert pq.read_table(first / 'initial_states.parquet').num_rows == 8
        complete = json.loads((first / 'complete.json').read_text())
        assert all(sha256(first / name) == digest for name,digest in complete['hashes'].items())
    with pytest.raises(ValueError, match='already exists'):
        run_experiment(config, out)


@pytest.mark.parametrize('change', [
    {'params': {'typo': 1}}, {'params': {'K0': .8}}, {'params': {'N': True}},
    {'params': {'self_assessment': 1}}, {'params': {'effort_time_scale': 0}},
    {'initial': {'knowledge': {'kind': 'normal', 'mean': .8, 'std': .1}}},
    {'initial': {'access_hint': {'kind': 'constant', 'value': 0}}},
    {'initial': {'learning_efficiency': {'kind': 'constant', 'value': 0}}},
    {'initial': {'knowledge': {'kind': 'values', 'values': [.8]}}},
    {'conditions': [{'name': '../bad'}]},
    {'conditions': [{'name': 'duplicate'}, {'name': 'DUPLICATE'}]},
    {'network': {'family': 'WS', 'd_bar': 3}},
    {'network': {'family': 'CUSTOM', 'edges': [[0,8]]}},
])
def test_invalid_configs_fail_before_any_output(change, tmp_path):
    config = small_config()
    config.update(change)
    output = tmp_path / 'invalid'
    with pytest.raises(ValueError):
        run_experiment(config, output)
    assert not output.exists()


def test_bundled_contrast_must_disclose_identification_limits():
    config = small_config()
    config['conditions'][1]['params']['grade_response'] = 0
    with pytest.raises(ValueError, match='exactly one'):
        resolve_config(config)
    config['contrasts'][0].update(kind='bundled', reason='Cannot identify AI and pressure separately.')
    assert len(resolve_config(config)['contrasts'][0]['changed_settings']) == 2


def test_custom_network_and_duplicate_json_fields(tmp_path):
    config = small_config()
    config['network'] = {'family': 'CUSTOM', 'edges': [[0,1],[1,2]]}
    resolved = resolve_config(config)
    preflight(resolved)
    graph = make_graph(resolved['conditions'][0]['network'], 8, 82, 0)
    assert graph.edges == ((0,1),(1,2))
    file = tmp_path / 'bad.json'
    file.write_text('{"seed": 1, "seed": 2}')
    with pytest.raises(ValueError, match='duplicate'):
        load_config(file)


def test_historical_sources_still_match_e13_lock():
    repo = Path(__file__).resolve().parents[1]
    lock = json.loads((repo / 'runs/E13/lock.json').read_text())
    for name, digest in lock['sources'].items():
        assert sha256(repo / name) == digest, name
