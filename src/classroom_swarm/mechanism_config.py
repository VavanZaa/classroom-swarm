"""A31 mechanism JSON experiment declarations: template, validation, lock and execution."""
from __future__ import annotations

import argparse
import copy
import csv
from dataclasses import asdict, fields
import hashlib
import json
from pathlib import Path
import platform
import re

import networkx as nx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .tutoring_settings import TutoringParams as DeclaredParams, default_initial, initial_state, resolve_initial
from .distributions import number, sample_distribution, validate_distribution
from .graphs import _from_edges, generate_er, generate_ws, generate_sbm, sbm_sizes, with_edge_weights
from .rng import FAMILY_CODE, graph_seed
from .v4_public_ai import PublicAIDraws
from .v4_mechanisms import simulate_mechanisms as simulate_declared, validate_mechanism_log as validate_declared_log
from .mechanism_settings import resolve_mechanisms, MechanismSettings
from .teacher_settings import TeacherSettings, resolve_teacher

REPO = Path(__file__).resolve().parents[2]
# JSON has one authoritative location for each initialization assumption.
INIT_ALIASES = {'K0', 'K0_sd', 'alpha', 'kappa', 'alpha_log_sd', 'kappa_log_sd', 'benefit_prior'}
PARAM_NAMES = {f.name for f in fields(DeclaredParams)} - INIT_ALIASES
NETWORK_DEFAULTS = dict(family='SBM', d_bar=6, omega=.1, sbm_ratio=5.,
                        block_sizes=None, seed=None, edges=None,
                        edge_weights={'kind': 'constant', 'value': 1.})
ROOT_KEYS = {'schema_version', 'experiment_id', 'seed', 'replicates', 'params', 'initial',
             'network', 'conditions', 'contrasts', 'stated_identities', 'notes', 'teacher', 'mechanisms'}


def object_fields(value, allowed, name):
    if not isinstance(value, dict):
        raise ValueError(f'{name} must be an object')
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f'unknown {name} fields: {sorted(unknown)}')


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')


def slug(value, name):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value):
        raise ValueError(f'{name} must be a letter followed by up to 63 letters, digits, - or _')
    if value.upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1,10)], *[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError(f'{name} is a reserved filesystem name')


def canonical_params(p):
    return {key: value for key, value in asdict(p).items() if key in PARAM_NAMES}


def template():
    p = DeclaredParams()
    return dict(schema_version=1, experiment_id='my_experiment', seed=924401, replicates=100,
                params=canonical_params(p), initial=default_initial(p),
                network=copy.deepcopy(NETWORK_DEFAULTS), teacher=asdict(TeacherSettings()), mechanisms=asdict(MechanismSettings()),
                conditions=[dict(name='reference', params={}, initial={}, network={}, teacher={}, mechanisms={})],
                contrasts=[], stated_identities=[
                    'Copying and direct answer AI grant no direct knowledge in this model.',
                    'Completed practice grants nonnegative knowledge according to the declared learning rule.',
                    'Teacher content grants only nonnegative usable-content gains; net effects can have either sign.',
                    'Grading automation reduces declared workload, not grading error.',
                ], notes='Edit assumptions before running; values are uncalibrated.')


def validate_network(network, n):
    object_fields(network, set(NETWORK_DEFAULTS), 'network')
    family = network['family']
    if family not in {'ER', 'WS', 'SBM', 'CUSTOM'}:
        raise ValueError('network family must be ER, WS, SBM or CUSTOM')
    if network['seed'] is not None:
        integer(network['seed'], 'network.seed')
    validate_distribution(network['edge_weights'], low=0, strict_low=True)
    degree = number(network['d_bar'], 'network.d_bar')
    omega = number(network['omega'], 'network.omega')
    ratio = number(network['sbm_ratio'], 'network.sbm_ratio')
    if not 0 <= omega <= 1 or ratio <= 0:
        raise ValueError('network omega must be in [0,1] and sbm_ratio positive')
    sizes = network['block_sizes']
    if sizes is not None:
        if family != 'SBM' or not isinstance(sizes, list) or not sizes:
            raise ValueError('block_sizes require a nonempty list for SBM')
        for size in sizes:
            integer(size, 'block size', 1)
        if sum(sizes) != n:
            raise ValueError('block_sizes must sum to N')
    edges = network['edges']
    if family == 'CUSTOM':
        if not isinstance(edges, list):
            raise ValueError('CUSTOM needs an edges list, including [] for isolated students')
        canonical = set()
        for edge in edges:
            if not isinstance(edge, list) or len(edge) != 2:
                raise ValueError('custom edge must be [u,v]')
            for node in edge:
                integer(node, 'edge node')
                if node >= n:
                    raise ValueError('edge node must be < N')
            pair = tuple(sorted(edge))
            if pair[0] == pair[1] or pair in canonical:
                raise ValueError('custom edges cannot be loops or duplicates')
            canonical.add(pair)
    elif edges is not None:
        raise ValueError('edges are only valid for CUSTOM networks')
    elif not 0 < degree <= n - 1:
        raise ValueError('generated networks need 0 < d_bar <= N-1')
    if family == 'WS':
        integer(degree, 'WS d_bar', 2)
        if degree % 2 or degree >= n:
            raise ValueError('WS d_bar must be even and < N')


def make_graph(network, n, seed, replicate):
    family = network['family']
    gseed = network['seed']
    if gseed is None:
        gseed = graph_seed(seed, replicate, family if family != 'CUSTOM' else 'ER')
    if family == 'CUSTOM':
        graph = _from_edges('CUSTOM', n, {'edges': network['edges']}, gseed, network['edges'])
    elif family == 'ER':
        graph = generate_er(n, network['d_bar'], gseed)
    elif family == 'WS':
        graph = generate_ws(n, network['d_bar'], network['omega'], gseed)
    elif network['block_sizes'] is None:
        graph = generate_sbm(n, network['d_bar'], network['sbm_ratio'], gseed)
    else:
        sizes = network['block_sizes']
        from .graphs import sbm_probabilities
        pin, pout = sbm_probabilities(sizes, network['d_bar'], network['sbm_ratio'])
        probabilities = [[pin if i == j else pout for j in range(len(sizes))] for i in range(len(sizes))]
        generated = nx.stochastic_block_model(sizes, probabilities, seed=gseed)
        graph = _from_edges('SBM', n, dict(d_bar=network['d_bar'], r=network['sbm_ratio'],
                            block_sizes=sizes, p_in=pin, p_out=pout), gseed,
                            generated.edges(), [generated.nodes[i]['block'] for i in range(n)])
    code = FAMILY_CODE.get(family, 4)
    z = np.random.default_rng(np.random.SeedSequence([seed, replicate, 119, code])).standard_normal(len(graph.edges))
    # Exact lists refer to canonical sorted edge order; independent of student trait streams.
    weights = sample_distribution(network['edge_weights'], z, low=0, strict_low=True)
    return with_edge_weights(graph, weights)


def differences(a, b, prefix=''):
    result = []
    for key in sorted(set(a) | set(b)):
        path = f'{prefix}.{key}' if prefix else key
        av, bv = a.get(key), b.get(key)
        if isinstance(av, dict) and isinstance(bv, dict):
            result.extend(differences(av, bv, path))
        elif av != bv:
            result.append(path)
    return result


def resolve_config(config):
    object_fields(config, ROOT_KEYS, 'experiment')
    if config.get('schema_version') != 1 or isinstance(config.get('schema_version'), bool):
        raise ValueError('schema_version must be 1')
    slug(config.get('experiment_id'), 'experiment_id')
    integer(config.get('seed'), 'seed')
    integer(config.get('replicates'), 'replicates', 1)
    for key in ('params', 'initial', 'network'):
        object_fields(config.get(key, {}), PARAM_NAMES if key == 'params' else
                      set(default_initial(DeclaredParams())) if key == 'initial' else set(NETWORK_DEFAULTS), key)
    resolve_teacher(config.get('teacher', {}))
    resolve_mechanisms(config.get('mechanisms', {}))
    conditions = config.get('conditions')
    if not isinstance(conditions, list) or not conditions:
        raise ValueError('conditions must be a nonempty list')
    resolved, names = [], set()
    for condition in conditions:
        object_fields(condition, {'name', 'params', 'initial', 'network', 'teacher', 'mechanisms'}, 'condition')
        name = condition.get('name')
        slug(name, 'condition name')
        if name.casefold() in names:
            raise ValueError('condition names must be unique ignoring case')
        names.add(name.casefold())
        object_fields(condition.get('params', {}), PARAM_NAMES, 'condition.params')
        values = {**config.get('params', {}), **condition.get('params', {})}
        try:
            p = DeclaredParams(**values)
            p.validate()
        except (TypeError, ValueError) as error:
            raise ValueError(f'condition {name}: {error}') from error
        initial_overrides = condition.get('initial', {})
        object_fields(initial_overrides, set(default_initial(p)), 'condition.initial')
        initial = resolve_initial(p, {**config.get('initial', {}), **initial_overrides})
        net_override = condition.get('network', {})
        object_fields(net_override, set(NETWORK_DEFAULTS), 'condition.network')
        network = {**copy.deepcopy(NETWORK_DEFAULTS), **config.get('network', {}), **net_override}
        validate_network(network, p.N)
        if network['family'] == 'SBM' and network['block_sizes'] is None:
            network['block_sizes'] = list(sbm_sizes(p.N))
        resolve_teacher(condition.get('teacher', {}))
        teacher = resolve_teacher({**config.get('teacher', {}), **condition.get('teacher', {})})
        teacher.validate(p)
        root_mechanisms=config.get('mechanisms',{})
        branch_overrides=condition.get('mechanisms',{})
        resolve_mechanisms(branch_overrides)
        merged={key:{**root_mechanisms.get(key,{}),**branch_overrides.get(key,{})}
                for key in ('incentives','workload','topics','peer_observation')}
        mechanisms=resolve_mechanisms(merged)
        mechanisms.validate(p,teacher)
        resolved.append(dict(name=name, params=canonical_params(p), initial=initial, network=network, teacher=asdict(teacher), mechanisms=asdict(mechanisms)))
    contrasts = config.get('contrasts', [])
    if not isinstance(contrasts, list):
        raise ValueError('contrasts must be a list')
    by_name = {c['name']: c for c in resolved}
    checked = []
    for contrast in contrasts:
        object_fields(contrast, {'condition', 'reference', 'kind', 'reason', 'identity', 'explanation'}, 'contrast')
        a, b = contrast.get('condition'), contrast.get('reference')
        if a not in by_name or b not in by_name or a == b:
            raise ValueError('contrast needs two distinct existing condition names')
        diff = differences({k: v for k, v in by_name[a].items() if k != 'name'},
                           {k: v for k, v in by_name[b].items() if k != 'name'})
        if contrast.get('kind') == 'single_parameter':
            if len(diff) != 1:
                raise ValueError(f'{a} vs {b}: single_parameter needs exactly one changed setting, got {diff}')
        elif contrast.get('kind') == 'bundled':
            if not diff or not isinstance(contrast.get('reason'), str) or not contrast['reason'].strip():
                raise ValueError('bundled contrast needs changed settings and an identification-limit reason')
        else:
            raise ValueError('contrast kind must be single_parameter or bundled')
        if contrast.get('identity') not in {'identity', 'not_identity'}:
            raise ValueError('contrast must declare identity or not_identity')
        if contrast['identity'] == 'identity' and not contrast.get('explanation'):
            raise ValueError('identity contrast needs an explanation')
        checked.append({**contrast, 'changed_settings': diff})
    identities = config.get('stated_identities', [])
    if not isinstance(identities, list) or any(not isinstance(v, str) or not v.strip() for v in identities):
        raise ValueError('stated_identities must be a list of nonempty strings')
    if not isinstance(config.get('notes', ''), str):
        raise ValueError('notes must be text')
    return dict(schema_version=1, model='A31-v4.6-classroom-mechanisms', experiment_id=config['experiment_id'],
                seed=config['seed'], replicates=config['replicates'], conditions=resolved,
                contrasts=checked, stated_identities=identities, notes=config.get('notes', ''))


def preflight(resolved):
    """Check graph feasibility, exact lengths and numerical sampling for every replicate before execution."""
    for rep in range(resolved['replicates']):
        for condition in resolved['conditions']:
            p = DeclaredParams(**condition['params'])
            make_graph(condition['network'], p.N, resolved['seed'], rep)
            initial_state(p, PublicAIDraws(resolved['seed'], rep, p.N, p.items, p.exam_items), condition['initial'])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def load_config(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'duplicate JSON field: {key}')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError(f'nonfinite JSON constant: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=invalid_constant)


def run_experiment(config, output):
    resolved = resolve_config(config)
    output = Path(output)
    if output.exists():
        raise ValueError(f'output already exists: {output}; choose a new directory')
    preflight(resolved)
    sources = sorted((REPO / 'src/classroom_swarm').glob('*.py')) + [REPO / 'docs/18-v4-tutoring-content.md', REPO / 'docs/20-v4-teacher-role.md', REPO / 'tests/test_v4_mechanisms.py', REPO / 'docs/21-v4-classroom-mechanisms.md']
    lock = {**resolved, 'status': 'declared before simulation',
            'config_sha256': hashlib.sha256(json.dumps(config, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            'sources': {str(p.relative_to(REPO)).replace('\\', '/'): sha256(p) for p in sources},
            'software': dict(python=platform.python_version(), numpy=np.__version__,
                             networkx=nx.__version__, pyarrow=pa.__version__),
            'stream_scheme': 'legacy 1-107; independent initial-state streams 108-118; edge weights 119; tutoring content/quality 120-125; teacher observations, attendance and content 126-130; peer observation error 134'}
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / 'lock.json', lock)
    save_json(output / 'declared_config.json', config)
    inventory = []
    with (output / 'runs.csv').open('w', encoding='utf-8', newline='') as handle:
        columns = ['replicate', 'condition', 'students', 'homeworks', 'graph_hash', 'weight_hash', 'path']
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for rep in range(resolved['replicates']):
            graph_cache = {}
            for condition in resolved['conditions']:
                p = DeclaredParams(**condition['params'])
                key = (p.N, json.dumps(condition['network'], sort_keys=True))
                if key not in graph_cache:
                    graph_cache[key] = make_graph(condition['network'], p.N, resolved['seed'], rep)
                graph = graph_cache[key]
                draws = PublicAIDraws(resolved['seed'], rep, p.N, p.items, p.exam_items)
                log = simulate_declared(p, graph, draws, condition['name'], condition['initial'], condition['teacher'], condition['mechanisms'])
                validate_declared_log(log)
                log.manifest['network'] = {**condition['network'], 'resolved_seed': graph.seed}
                folder = output / 'raw' / f'rep{rep:04d}' / condition['name']
                folder.mkdir(parents=True)
                save_json(folder / 'manifest.json', log.manifest)
                for table, rows in log.tables.items():
                    pq.write_table(pa.Table.from_pylist(rows), folder / f'{table}.parquet', compression='zstd')
                hashes = {file.name: sha256(file) for file in sorted(folder.iterdir())}
                save_json(folder / 'complete.json', {'hashes': hashes})
                row = dict(replicate=rep, condition=condition['name'], students=p.N, homeworks=p.H,
                           graph_hash=graph.edge_hash, weight_hash=graph.weight_hash,
                           path=str(folder.relative_to(output)))
                writer.writerow(row)
                handle.flush()
                inventory.append(row)
                print(f'Completed replicate {rep + 1}/{resolved["replicates"]}: {condition["name"]}', flush=True)
    save_json(output / 'complete.json', dict(runs=len(inventory),
              hashes={name: sha256(output / name) for name in ('lock.json', 'declared_config.json', 'runs.csv')}))
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('template', help='write every default setting for editing')
    create.add_argument('--output', required=True, type=Path)
    validate = sub.add_parser('validate', help='validate and print the resolved experiment')
    validate.add_argument('config', type=Path)
    run = sub.add_parser('run', help='lock and execute a declared experiment')
    run.add_argument('config', type=Path)
    run.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'template':
            if args.output.exists():
                raise ValueError(f'template destination already exists: {args.output}')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as handle:
                handle.write(json.dumps(template(), indent=2, allow_nan=False) + '\n')
            print(args.output)
        elif args.command == 'validate':
            resolved = resolve_config(load_config(args.config))
            preflight(resolved)
            print(json.dumps(resolved, indent=2, allow_nan=False))
        else:
            run_experiment(load_config(args.config), args.output)
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f'Invalid experiment: {error}\n')


if __name__ == '__main__':
    main()
