"""A34 schema-4 declarations and reproducible locked execution."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import platform
from dataclasses import asdict
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from . import effort_config as legacy
from .effort_settings import resolve_effort
from .promising_settings import resolve_promising, PromisingSettings, expand_curriculum
from .promising_runtime import STREAMS33
from .effort_runtime import STREAMS32, stable_initial
from .repaired_validation import validate_repaired_log
from .v4_repaired import simulate_repaired
from .v4_public_ai import PublicAIDraws
from .tutoring_settings import TutoringParams
from .teacher_settings import resolve_teacher
from .mechanism_settings import resolve_mechanisms

REPO=legacy.REPO
load_config,save_json,sha256,make_graph=legacy.load_config,legacy.save_json,legacy.sha256,legacy.make_graph

def template():
    c=legacy.template()
    c.update(schema_version=4,experiment_id='my_repaired_classroom_experiment',repairs_enabled=True,design=asdict(PromisingSettings()))
    c['conditions'][0]['design']={}
    return c

def resolve_config(c):
    if not isinstance(c,dict) or c.get('schema_version')!=4 or isinstance(c.get('schema_version'),bool): raise ValueError('A34 schema_version must be 4')
    old=copy.deepcopy(c); old['schema_version']=2; root=old.pop('design',{})
    repairs=old.pop('repairs_enabled',True)
    if not isinstance(repairs,bool): raise ValueError('repairs_enabled must be boolean')
    resolve_promising(root)
    declarations=[]
    for condition in old.get('conditions',[]):
        declarations.append(condition.pop('design',{}))
    contrasts=old.get('contrasts',[])
    old['contrasts']=[]
    resolved=legacy.resolve_config(old)
    resolved['contrasts']=copy.deepcopy(contrasts)
    for condition,declared in zip(resolved['conditions'],declarations):
        d=resolve_promising(legacy.merge(root,declared)); p=TutoringParams(**condition['params'])
        d.validate(p,resolve_teacher(condition['teacher']),resolve_mechanisms(condition['mechanisms']),resolve_effort(condition['extensions']))
        condition['design']=asdict(d)
        condition['repairs_enabled']=repairs
        if repairs and not condition['extensions']['learning_process']['enabled']: raise ValueError('A34 requires learning_process enabled')
    resolved.update(schema_version=4,model='A34-v4.9-policy-repair',repairs_enabled=repairs)
    # A33 branch differences must be identified separately; the A32 resolver only
    # sees legacy settings. Validate the complete condition contrast here.
    by={r['name']:r for r in resolved['conditions']}
    for contrast in resolved['contrasts']:
        legacy.legacy.object_fields(contrast, {'condition','reference','kind','reason','identity','explanation'}, 'contrast')
        if contrast.get('condition') not in by or contrast.get('reference') not in by or contrast['condition']==contrast['reference']: raise ValueError('contrast needs existing distinct conditions')
        if contrast.get('kind') not in ('single_parameter','bundled') or contrast.get('identity') not in ('identity','not_identity'): raise ValueError('invalid contrast classification')
        if contrast['kind']=='bundled' and not contrast.get('reason'): raise ValueError('bundled contrast needs identification limit')
        if contrast['identity']=='identity' and not contrast.get('explanation'): raise ValueError('identity requires explanation')
        a,b=by[contrast['condition']],by[contrast['reference']]
        changes=legacy.legacy.differences({k:v for k,v in a.items() if k!='name'},{k:v for k,v in b.items() if k!='name'})
        if contrast['kind']=='single_parameter' and len(changes)!=1: raise ValueError('A33 contrast changes multiple settings')
        contrast['changed_settings']=changes
    return resolved

def preflight(resolved):
    legacy.preflight(resolved)
    for rep in range(resolved['replicates']):
        for r in resolved['conditions']:
            p=TutoringParams(**r['params']); x=resolve_effort(r['extensions']); m=resolve_mechanisms(r['mechanisms']); d=resolve_promising(r['design']); t=resolve_teacher(r['teacher'])
            draws=PublicAIDraws(resolved['seed'],rep,p.N,p.items,p.exam_items)
            _,_,traits,_,_=stable_initial(p,draws,r['initial'],x.student_ids)
            expanded,extensions=expand_curriculum(m,x,traits.K0,p,d.curriculum)
            expanded.validate(p,t); extensions.validate(p,t,expanded)

def run_experiment(config, output):
    resolved = resolve_config(config); output = Path(output)
    if output.exists(): raise ValueError('output already exists; choose a new run identity')
    preflight(resolved)
    sources = sorted((REPO/'src/classroom_swarm').glob('*.py')) + [REPO/'docs/26-v4-policy-repair.md',
        REPO/'tests/test_v4_repaired.py']
    # Functional designs can declare an additional runner/plan as source evidence.
    lock = {**resolved, 'status':'declared before simulation', 'sources':{str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources},
        'config_sha256':hashlib.sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        'software':{'python':platform.python_version(),'numpy':np.__version__,'pyarrow':pa.__version__},
        'stream_scheme':{'identity':'stable global student ID; date/tick/item opportunity', 'codes':{**STREAMS32,**STREAMS33}}}
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
                log=simulate_repaired(p,graph,PublicAIDraws(resolved['seed'],rep,p.N,p.items,p.exam_items),condition['name'],
                    condition['initial'],condition['teacher'],condition['mechanisms'],condition['extensions'],condition['design'],condition['repairs_enabled'])
                validate_repaired_log(log,p)
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
    except (ValueError,TypeError,OSError,AssertionError) as error: parser.exit(2,f'Invalid A34 experiment: {error}\n')


if __name__=='__main__': main()
