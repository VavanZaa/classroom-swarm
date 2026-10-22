"""Descriptive arithmetic partition of E14 gains, not causal mediation estimates."""
import importlib.util
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('e14',REPO/'scripts/e14_classroom_trends.py')
e14=importlib.util.module_from_spec(spec);spec.loader.exec_module(e14)


def main():
    root=REPO/'runs/E14';e14.verify_design(root)
    output=REPO/'runs/E14-audit/learning_decomposition-r1';output.mkdir(exist_ok=False)
    rows=[]
    for group,conditions,n_focal in [('peer_composition',['low_hint_only','high_hint_only'],15),
                                      ('grouping',['mixed_teaching','tracked_teaching'],4)]:
        for condition in conditions:
            for rep in range(100):
                path=root/group/'raw'/f'rep{rep:04d}'/condition
                hashes=e14.load_config(path/'complete.json')['hashes'];tables={}
                for key in ('events','students','traits'):
                    f=path/f'{key}.parquet';assert e14.sha256(f)==hashes[f.name]
                    tables[key]=pq.read_table(f).to_pylist()
                p=e14.load_config(path/'manifest.json')['params'];assert p['helper_time']
                alpha={r['student']:r['alpha'] for r in tables['traits']}
                students=[r for r in tables['students'] if r['student']<n_focal]
                changes={(r['homework'],r['student']):r['K']-r['K_before'] for r in students}
                totals={key:0. for key in changes}
                base=bonus=help_gain=0.
                for r in tables['events']:
                    if r['student']>=n_focal or r['action'] not in ('attempt','help_hint'):continue
                    gain=r['K_after']-r['K_before'];totals[r['homework'],r['student']]+=gain
                    if r['action']=='attempt':
                        own=(1-r['K_before'])*min(1.,alpha[r['student']]/p['attempt_learning_divisor'])
                        base+=own;bonus+=gain-own
                    else:help_gain+=gain
                for key,expected in changes.items():assert abs(expected-totals[key])<1e-12
                total=sum(changes.values())/n_focal*100
                rows.append(dict(group=group,condition=condition,replicate=rep,gain_pp=total,
                    own_attempt_base_pp=base/n_focal*100,consumed_hint_bonus_pp=bonus/n_focal*100,
                    learning_from_helping_pp=help_gain/n_focal*100))
    e14.write_csv(output/'replicate_contributions.csv',rows)
    summaries=[]
    for group,condition in dict.fromkeys((r['group'],r['condition']) for r in rows):
        selected=[r for r in rows if (r['group'],r['condition'])==(group,condition)]
        summaries.append(dict(group=group,condition=condition,
            **{key:float(np.mean([r[key] for r in selected])) for key in rows[0] if key.endswith('_pp')}))
    e14.write_csv(output/'condition_contributions.csv',summaries)
    e14.save_json(output/'manifest.json',dict(runs_read=400,per_student_episode_sum_check='all passed',
        interpretation='Arithmetic partition along realized paths; treatment changes each path and its knowledge headroom. Not independent causal mediation.',
        E14_lock_sha256=e14.sha256(root/'preregistration-lock.json'),source_sha256=e14.sha256(Path(__file__)),
        hashes={p.name:e14.sha256(p) for p in sorted(output.iterdir())}))
    for r in summaries:print(r)


if __name__=='__main__':main()
