"""A32 strict declarations, preflight, source freeze and raw experiment execution."""
import argparse
import copy
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from . import mechanism_config as legacy
from .effort_settings import EffortSettings, BRANCHES, resolve_effort, default_exams
from .effort_runtime import STREAMS32, semantic, stable_initial
from .effort_validation import validate_effort_log
from .v4_effort_learning import simulate_effort
from .v4_public_ai import PublicAIDraws
from .tutoring_settings import TutoringParams
from .teacher_settings import resolve_teacher
from .mechanism_settings import resolve_mechanisms
from .distributions import sample_distribution

REPO = legacy.REPO
load_config, save_json, sha256, make_graph = legacy.load_config, legacy.save_json, legacy.sha256, legacy.make_graph


def merge(a, b):
    result = copy.deepcopy(a)
    for key, value in b.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else copy.deepcopy(value)
    return result


def template():
    value = legacy.template()
    value.update(schema_version=2, experiment_id='my_effort_experiment', extensions=asdict(EffortSettings()),
        stated_identities=['No opportunity or productive dose gives no direct knowledge under learning_process.',
            'Copied answers, payments, teacher administration and diagnostic exams grant no direct knowledge.',
            'Zero concept share and zero cross-form transfer isolate format familiarity from concepts and novel forms.'])
    value['conditions'][0]['extensions'] = {}
    return value


def resolve_config(config):
    legacy.object_fields(config, legacy.ROOT_KEYS | {'extensions'}, 'A32 experiment')
    if config.get('schema_version') != 2 or isinstance(config.get('schema_version'), bool): raise ValueError('A32 schema_version must be 2')
    resolve_effort(config.get('extensions'))
    old = copy.deepcopy(config); old.pop('extensions', None); old['schema_version'] = 1
    if not isinstance(old.get('conditions'), list): raise ValueError('conditions must be a list')
    declarations = old['conditions']
    for c in declarations:
        legacy.object_fields(c, {'name','params','initial','network','teacher','mechanisms','extensions'}, 'condition')
        resolve_effort(c.pop('extensions', {}))
    old['contrasts'] = []
    resolved = legacy.resolve_config(old)
    for condition, original in zip(resolved['conditions'], config['conditions']):
        x = resolve_effort(merge(config.get('extensions', {}), original.get('extensions', {})))
        p = TutoringParams(**condition['params']); teacher = resolve_teacher(condition['teacher'])
        mechanisms = resolve_mechanisms(condition['mechanisms']); x.validate(p, teacher, mechanisms)
        if x.active and p.tutoring_activity == 'legacy_hint': raise ValueError('A32 requires joint/shared practice')
        if x.helper_contract.enabled and (not p.helper_time or p.tutoring_activity == 'shared_practice'):
            raise ValueError('helper contract requires scarce helper time and joint_practice')
        complete = asdict(x); complete['student_ids'] = complete['student_ids'] or list(range(p.N))
        count = len(mechanisms.topics.names) if mechanisms.topics.enabled else 1
        complete['test_preparation']['exams'] = complete['test_preparation']['exams'] or default_exams(x.test_preparation, count)
        if not complete['test_preparation']['initial_format']:
            complete['test_preparation']['initial_format'] = np.zeros((p.N,len(x.test_preparation.forms))).tolist()
        if not complete['test_preparation']['format_transfer']:
            complete['test_preparation']['format_transfer'] = np.eye(len(x.test_preparation.forms)).tolist()
        complete['helper_contract']['checkpoints'] = complete['helper_contract']['checkpoints'] or list(range(p.exam_every,p.H+1,p.exam_every))
        condition['extensions'] = complete
    resolved.update(schema_version=2, model='A32-v4.7-effort-learning')
    by_name = {c['name']:c for c in resolved['conditions']}; checked = []
    for contrast in config.get('contrasts', []):
        legacy.object_fields(contrast, {'condition','reference','kind','reason','identity','explanation'}, 'contrast')
        a,b = contrast.get('condition'), contrast.get('reference')
        if a not in by_name or b not in by_name or a==b: raise ValueError('contrast requires two existing conditions')
        difference = legacy.differences({k:v for k,v in by_name[a].items() if k!='name'}, {k:v for k,v in by_name[b].items() if k!='name'})
        if contrast.get('kind')=='single_parameter':
            if len(difference)!=1: raise ValueError('single_parameter contrast changes ' + str(difference))
        elif contrast.get('kind')=='bundled':
            if not difference or not isinstance(contrast.get('reason'),str) or not contrast['reason'].strip(): raise ValueError('bundled contrast requires identification limit')
        else: raise ValueError('unsupported contrast kind')
        if contrast.get('identity') not in ('identity','not_identity'): raise ValueError('contrast must classify identity')
        if contrast['identity']=='identity' and not contrast.get('explanation'): raise ValueError('identity needs explanation')
        checked.append({**contrast,'changed_settings':difference})
    resolved['contrasts'] = checked
    return resolved


def preflight(resolved):
    legacy.preflight(resolved)
    for rep in range(resolved['replicates']):
        for condition in resolved['conditions']:
            p = TutoringParams(**condition['params']); x = resolve_effort(condition['extensions'])
            draws = PublicAIDraws(resolved['seed'],rep,p.N,p.items,p.exam_items)
            stable_initial(p,draws,condition['initial'],x.student_ids)
            for index,key in enumerate(('attention','distraction','fatigue_sensitivity','future_test_value','fatigue_initial')):
                z=np.array([semantic(draws,141,i,index,normal=True) for i in x.student_ids])
                sample_distribution(getattr(x.learning_process,key),z,low=0,high=None if key=='future_test_value' else 1)
            z=np.array([semantic(draws,141,i,5,normal=True) for i in x.student_ids])
            sample_distribution(x.helper_contract.reward_preference,z,low=0,high=None)


def run_experiment(config, output):
    resolved = resolve_config(config); output = Path(output)
    if output.exists(): raise ValueError('output already exists; choose a new run identity')
    preflight(resolved)
    sources = sorted((REPO/'src/classroom_swarm').glob('*.py')) + [REPO/'docs/23-v4-effort-learning.md',
        REPO/'tests/test_v4_effort_learning.py',REPO/'tests/test_effort_config.py']
    # Functional designs can declare an additional runner/plan as source evidence.
    lock = {**resolved, 'status':'declared before simulation', 'sources':{str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources},
        'config_sha256':hashlib.sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        'software':{'python':platform.python_version(),'numpy':np.__version__,'pyarrow':pa.__version__},
        'stream_scheme':{'identity':'stable global student ID; date/tick/item opportunity', 'codes':STREAMS32}}
    output.mkdir(parents=True); save_json(output/'lock.json',lock); save_json(output/'declared_config.json',config)
    inventory=[]
    with (output/'runs.csv').open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['replicate','condition','students','homeworks','graph_hash','weight_hash','path']); writer.writeheader()
        for rep in range(resolved['replicates']):
            graphs={}
            for condition in resolved['conditions']:
                p=TutoringParams(**condition['params']); key=(p.N,json.dumps(condition['network'],sort_keys=True))
                if key not in graphs: graphs[key]=make_graph(condition['network'],p.N,resolved['seed'],rep)
                graph=graphs[key]
                log=simulate_effort(p,graph,PublicAIDraws(resolved['seed'],rep,p.N,p.items,p.exam_items),condition['name'],
                    condition['initial'],condition['teacher'],condition['mechanisms'],condition['extensions'])
                validate_effort_log(log,p)
                folder=output/'raw'/f'rep{rep:04d}'/condition['name']; folder.mkdir(parents=True)
                log.manifest['network']={**condition['network'],'resolved_seed':graph.seed}
                save_json(folder/'manifest.json',log.manifest)
                for table,rows in log.tables.items(): pq.write_table(pa.Table.from_pylist(rows),folder/f'{table}.parquet',compression='zstd')
                save_json(folder/'complete.json',{'hashes':{f.name:sha256(f) for f in sorted(folder.iterdir())}})
                row=dict(replicate=rep,condition=condition['name'],students=p.N,homeworks=p.H,graph_hash=graph.edge_hash,
                    weight_hash=graph.weight_hash,path=str(folder.relative_to(output)))
                writer.writerow(row); handle.flush(); inventory.append(row)
                print(f'Completed {rep+1}/{resolved["replicates"]}: {condition["name"]}',flush=True)
    save_json(output/'complete.json',{'runs':len(inventory),'hashes':{name:sha256(output/name) for name in ('lock.json','declared_config.json','runs.csv')}})
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('template'); create.add_argument('--output',required=True,type=Path)
    check=sub.add_parser('validate'); check.add_argument('config',type=Path)
    run=sub.add_parser('run'); run.add_argument('config',type=Path); run.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='template':
            if args.output.exists(): raise ValueError('template destination exists')
            args.output.parent.mkdir(parents=True,exist_ok=True); save_json(args.output,template()); print(args.output)
        elif args.command=='validate':
            resolved=resolve_config(load_config(args.config)); preflight(resolved); print(json.dumps(resolved,indent=2,allow_nan=False))
        else: run_experiment(load_config(args.config),args.output)
    except (ValueError,TypeError,OSError,AssertionError) as error: parser.exit(2,f'Invalid A32 experiment: {error}\n')


if __name__=='__main__': main()
