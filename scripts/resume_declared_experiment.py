"""Resume an interrupted declared experiment after checking its immutable lock.

Completed runs are hash-verified and reused. Incomplete directories and the old
inventory are preserved in a recovery snapshot. Numeric settings never change.
"""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil

import networkx as nx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from classroom_swarm.experiment_config import (REPO,load_config,resolve_config,preflight,
    save_json,sha256,make_graph,DeclaredParams,PublicAIDraws,simulate_declared,validate_declared_log)


def checked_child(root,path):
    resolved=path.resolve()
    if resolved==root or not resolved.is_relative_to(root):
        raise ValueError(f'recovery path escapes declared output: {resolved}')
    return resolved


def resume(output):
    output=Path(output).resolve()
    lock=load_config(output/'lock.json')
    config=load_config(output/'declared_config.json')
    resolved=resolve_config(config)
    for key,value in resolved.items():
        if lock[key]!=value:raise ValueError(f'locked declaration differs: {key}')
    digest=hashlib.sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest()
    if lock['config_sha256']!=digest:raise ValueError('config digest differs')
    for name,digest in lock['sources'].items():
        if sha256(REPO/name)!=digest:raise ValueError(f'locked source differs: {name}')
    software=dict(python=platform.python_version(),numpy=np.__version__,networkx=nx.__version__,pyarrow=pa.__version__)
    if software!=lock['software']:raise ValueError('runtime versions differ from interrupted run')
    if (output/'complete.json').exists():raise ValueError('experiment already complete; no resume needed')
    preflight(resolved)
    completed={};incomplete=[];damaged={}
    expected={}
    for rep in range(resolved['replicates']):
        for condition in resolved['conditions']:
            folder=checked_child(output,output/'raw'/f'rep{rep:04d}'/condition['name'])
            expected[folder]=(rep,condition)
            if (folder/'complete.json').exists():
                try:
                    hashes=load_config(folder/'complete.json')['hashes']
                    if not isinstance(hashes,dict) or not hashes:raise ValueError('invalid completion hashes')
                    for name,digest in hashes.items():
                        if sha256(checked_child(output,folder/name))!=digest:
                            raise ValueError(f'raw output hash differs: {name}')
                    manifest=load_config(folder/'manifest.json')
                except (ValueError,OSError,KeyError) as error:
                    incomplete.append(folder);damaged[str(folder.relative_to(output))]=str(error)
                    continue
                if manifest['params']!=asdict(DeclaredParams(**condition['params'])) or manifest['initial']!=condition['initial']:
                    raise ValueError('completed run settings differ')
                if (manifest['seed'],manifest['replicate'],manifest['condition'])!=(resolved['seed'],rep,condition['name']):
                    raise ValueError('completed run identity differs')
                completed[folder]=manifest
            elif folder.exists():incomplete.append(folder)
    for folder in (output/'raw').glob('rep*/*'):
        if folder.resolve() not in expected:raise ValueError('unexpected raw directory')
    snapshot=checked_child(output,output/'recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    snapshot.mkdir(parents=True,exist_ok=False)
    if (output/'runs.csv').exists():shutil.copyfile(output/'runs.csv',snapshot/'interrupted_runs.csv')
    for folder in incomplete:
        target=checked_child(output,snapshot/'incomplete_raw'/folder.relative_to(output/'raw'))
        target.parent.mkdir(parents=True,exist_ok=True)
        # Both absolute targets have been checked inside the declared output root.
        shutil.move(str(checked_child(output,folder)),str(target))
    record=dict(status='resuming',started_utc=datetime.now(timezone.utc).isoformat(),
        reused_runs=len(completed),missing_runs=len(expected)-len(completed),
        preserved_incomplete=[str(p.relative_to(output)) for p in incomplete],
        damaged_records=damaged,
        lock_sha256=sha256(output/'lock.json'),source_sha256=sha256(Path(__file__)),
        reason='interrupted process; same settings, streams, versions and locked engine')
    save_json(snapshot/'resume.json',record)
    print(f'Checked and reused {len(completed)} completed runs; resuming {len(expected)-len(completed)}',flush=True)
    inventory=[];columns=['replicate','condition','students','homeworks','graph_hash','weight_hash','path']
    with (output/'runs.csv').open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader()
        for rep in range(resolved['replicates']):
            graphs={}
            for condition in resolved['conditions']:
                folder=output/'raw'/f'rep{rep:04d}'/condition['name']
                manifest=completed.get(folder)
                if manifest is None:
                    p=DeclaredParams(**condition['params'])
                    key=(p.N,json.dumps(condition['network'],sort_keys=True))
                    if key not in graphs:graphs[key]=make_graph(condition['network'],p.N,resolved['seed'],rep)
                    graph=graphs[key]
                    draws=PublicAIDraws(resolved['seed'],rep,p.N,p.items,p.exam_items)
                    log=simulate_declared(p,graph,draws,condition['name'],condition['initial'])
                    validate_declared_log(log)
                    log.manifest['network']={**condition['network'],'resolved_seed':graph.seed}
                    folder.mkdir(parents=True,exist_ok=False)
                    save_json(folder/'manifest.json',log.manifest)
                    for table,rows in log.tables.items():
                        pq.write_table(pa.Table.from_pylist(rows),folder/f'{table}.parquet',compression='zstd')
                    save_json(folder/'complete.json',dict(hashes={f.name:sha256(f) for f in sorted(folder.iterdir())}))
                    manifest=log.manifest
                    print(f'Completed replicate {rep+1}/{resolved["replicates"]}: {condition["name"]}',flush=True)
                row=dict(replicate=rep,condition=condition['name'],students=manifest['params']['N'],
                    homeworks=manifest['params']['H'],graph_hash=manifest['graph_hash'],weight_hash=manifest['weight_hash'],
                    path=str(folder.relative_to(output)))
                writer.writerow(row);handle.flush();inventory.append(row)
    save_json(output/'complete.json',dict(runs=len(inventory),hashes={name:sha256(output/name)
        for name in ('lock.json','declared_config.json','runs.csv')}))
    record.update(status='complete',finished_utc=datetime.now(timezone.utc).isoformat(),total_runs=len(inventory),
                  complete_sha256=sha256(output/'complete.json'))
    save_json(snapshot/'resume.json',record)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    resume(parser.parse_args().output)
