"""E22b: fix a duplicated setup cost, preserving E22 and paired semantic draws."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e22_a32_study_trends as e

ROOT=e.REPO/'runs/E22b-teacher-access-r1'
PLAN=e.REPO/'docs/experiments/E22b-teacher-access-plan.md'
original_jobs=e.build_jobs
original_comparisons=e.comparisons


def corrected_jobs(rep):
    jobs=[j for j in original_jobs(rep) if j['case']=='teacher_rewards']
    for job in jobs:
        if job['resolved']['extensions']['test_preparation']['participation']:
            job['resolved']['extensions']['test_preparation']['participation_cost']=0.
    return jobs


def contrasts(): return [s for s in original_comparisons() if s['case']=='teacher_rewards']


def prepare():
    e.build_jobs=corrected_jobs; e.comparisons=contrasts
    e.prepare(ROOT)
    # Extend the source lock before any E22b simulation; E22's lock is untouched.
    lock=e.config.load_config(ROOT/'design-lock.json')
    for p in (Path(__file__),PLAN,e.REPO/'tests/test_e22_teacher_access_correction.py'):
        lock['sources'][str(p.relative_to(e.REPO)).replace('\\','/')]=e.config.sha256(p)
    lock.update(correction='Remove duplicated general .6 cost; retain per-design .6 cost. Source inspection before aggregate E22 outcomes.',
        paired_to='runs/E22-A32-study-trends-r1',same_student_draws=True)
    e.config.save_json(ROOT/'design-lock.json',lock)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('command',choices=['prepare','run','analyze','verify']); p.add_argument('--workers',type=int,default=2)
    a=p.parse_args(); e.build_jobs=corrected_jobs; e.comparisons=contrasts
    if a.command=='prepare': prepare()
    elif a.command=='run': e.run(ROOT,a.workers)
    elif a.command=='analyze': e.analyze(ROOT)
    else: e.verify(ROOT); print('E22b source and design hashes passed.')


if __name__=='__main__': main()
