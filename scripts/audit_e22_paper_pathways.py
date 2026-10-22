"""Read-only diagnosis of delivered teacher content in frozen E22 outputs."""
from pathlib import Path
from collections import defaultdict
import sys
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e22_a32_study_trends as e


def main():
    root=e.ROOT; e.verify(root)
    inventory={(r['replicate'],r['condition']):r for r in e.config.load_config(root/'raw-inventory.json')}
    sums=defaultdict(lambda:defaultdict(float)); inputs={}
    for rep in range(e.REPLICATES):
        for job in e.config.load_config(root/f'rep{rep:04d}.json'):
            if job['case']!='kenya' or job['profile'] not in ('default','fixed_curriculum'): continue
            folder=root/'raw'/f'rep{rep:04d}'/job['condition']
            assert e.config.sha256(folder/'complete.json')==inventory[rep,job['condition']]['complete_sha256']
            complete=e.config.load_config(folder/'complete.json')
            def read(name):
                path=folder/(name+'.parquet'); digest=complete['hashes'][path.name]
                assert e.config.sha256(path)==digest
                inputs[str(path.relative_to(e.REPO)).replace('\\','/')]=digest
                return pq.read_table(path).to_pylist()
            exposures={r['event_id']:r for r in read('material_exposure')}
            for r in read('learning_doses'):
                if r['source']!='teacher': continue
                for group in ('low','high'):
                    if r['student'] not in job['groups'][group]: continue
                    key=(job['profile'],job['arm'],group); a=sums[key]; a['count']+=1
                    for field in ('quality','readiness'): a[field]+=exposures[r['event_id']][field]
                    for field in ('processing_probability','attention_probability','effort','dose'): a[field]+=r[field]
            actions=[r for r in read('teacher_actions') if r['action']=='instruction']
            for group in ('low','high'):
                n=len(job['groups'][group])
                a=sums[job['profile'],job['arm'],group]
                a['difficulty_total']+=sum(r['difficulty'] for r in actions)*n
                a['difficulty_weight']+=len(actions)*n
    results=[]
    for key,a in sorted(sums.items()):
        results.append(dict(profile=key[0],arm=key[1],group=key[2],student_lesson_events=int(a['count']),
            **{k:a[k]/a['count'] for k in ('quality','readiness','processing_probability','attention_probability','effort','dose')},
            difficulty=a['difficulty_total']/a['difficulty_weight']))
    out=e.REPO/'docs/reports/E22-lesson-pathway-audit.json'
    if out.exists(): raise ValueError('Preserve existing audit')
    e.config.save_json(out,dict(results=results,raw_file_inputs=inputs,
        design_sha256=e.config.sha256(root/'design-lock.json'),script_sha256=e.config.sha256(Path(__file__)),
        interpretation='Observed pathway summaries, not randomized mediation or human causation.'))
    for r in results: print({k:round(v,4) if isinstance(v,float) else v for k,v in r.items()})


if __name__=='__main__': main()
