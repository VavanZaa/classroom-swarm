"""Render audited E16 effects without changing models, settings or analyses."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from classroom_swarm.tutoring_config import REPO,load_config,sha256,save_json

ROOT=REPO/'runs/E16-tutoring-r1'
SELECTION=[('lab','mixed_reference','tracked_reference','Mixed − tracked, shared practice'),
    ('lab','mixed_solo','mixed_reference','Shared practice − independent practice'),
    ('composition','high_joint','low_joint','Stronger peers, voluntary practice'),
    ('composition','high_joint_copy','low_joint_copy','Stronger peers, copying available'),
    ('lab','mixed_voluntary','tracked_voluntary','Mixed − tracked, voluntary practice'),
    ('lab','mixed_hard','tracked_hard','Mixed − tracked, difficult content'),
    ('lab','mixed_slow','mixed_reference','Slower − reference shared practice')]


def rows(stage):
    folder=ROOT/(stage+'_derived')
    manifest=load_config(folder/'analysis_manifest.json')
    assert manifest['raw_audits']=='all passed'
    for name,digest in manifest['hashes'].items():assert sha256(folder/name)==digest
    with (folder/'effects.csv').open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))


def get(data,group,a,b,metric,reverse=False):
    found=[r for r in data if r['group']==group and r['condition']==a and r['reference']==b and r['metric']==metric]
    assert len(found)==1,(group,a,b,metric)
    r=found[0];v=[float(r[k]) for k in ['effect','lo95','hi95']]
    return [-v[0],-v[2],-v[1]] if reverse else v


def fmt(v):return f'{v[0]:+.3f} [{v[1]:+.3f}, {v[2]:+.3f}]'


def main():
    dev,val=rows('development'),rows('validation')
    fig,ax=plt.subplots(figsize=(10,5.5))
    for stage,data,offset,color in [('Development (30 replicates)',dev,.12,'#8495a5'),('Validation (100 replicates)',val,-.12,'#006b84')]:
        values=[get(data,g,a,b,'exam',reverse=(a=='mixed_solo')) for g,a,b,_ in SELECTION]
        means=np.array([r[0] for r in values]);err=np.array([[r[0]-r[1] for r in values],[r[2]-r[0] for r in values]])
        ax.errorbar(means,np.arange(len(values))+offset,xerr=err,fmt='o',color=color,label=stage,capsize=3)
    ax.axvline(0,color='#555',lw=.8);ax.set_yticks(range(len(SELECTION)),[r[3] for r in SELECTION]);ax.invert_yaxis()
    ax.set_xlabel('Low starters: final unaided exam difference (percentage points)')
    ax.set_title('Tutoring trends depend on activity, content and copying')
    ax.legend(loc='lower right',fontsize=9);ax.grid(axis='x',alpha=.18)
    fig.text(.5,.015,'Paired pointwise 95% Monte Carlo intervals; uncalibrated numerical model.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.04,1,1]);images=REPO/'docs/experiments/figures';images.mkdir(exist_ok=True)
    fig.savefig(images/'E16-tutoring-trends.png',dpi=180);plt.close(fig)
    lines=['# E16: tutoring content and activity diagnostics','',
        'A29 reproduces similar directions to the peer-teaching lab comparison in the explicitly scheduled shared-practice protocol: mixed groups help low starters more than tracked groups, and shared practice exceeds equal-duration independent practice. Both final unaided exam and latent knowledge-gain means are positive on untouched validation seeds. This is directional correspondence within the assumed model, not empirical validation or effect-size replication.','',
        'All 3,120 runs completed and passed raw audits: 720 development runs (24 conditions × 30 replicates), then 2,400 validation runs (the same 24 conditions × 100 separate replicates). Settings, source code and both seed sets were frozen before development outcomes. No coefficient or engine revision was made after outcomes were inspected.','',
        '## Main effects','',
        'All values below are final-exam percentage-point differences for exogenously defined low starters, with paired pointwise 95% bootstrap Monte Carlo intervals. Intervals describe simulation uncertainty; they do not quantify uncertainty about real classrooms.','',
        '| Comparison | Development | Validation |','|---|---:|---:|']
    for g,a,b,label in SELECTION:
        reverse=a=='mixed_solo'
        lines.append(f'| {label} | {fmt(get(dev,g,a,b,"exam",reverse))} | {fmt(get(val,g,a,b,"exam",reverse))} |')
    lines += ['', f'![E16 tutoring diagnostics](<{(images/"E16-tutoring-trends.png").as_posix()}>)','',
        'For the two primary shared-practice comparisons, validation latent knowledge-gain differences are '+
        fmt(get(val,'lab','mixed_reference','tracked_reference','knowledge_gain'))+' pp (mixed minus tracked) and '+
        fmt(get(val,'lab','mixed_solo','mixed_reference','knowledge_gain',True))+' pp (shared minus independent).','',
        '## Mechanism diagnosis and limits','',
        'The legacy optional-hint path remains available unchanged. Joint practice removes the old request/explanation/optional-practice separation: the learner works during the session and produces its own packet. Correct item content must also be novel and accessible to contribute a learning bonus. Helpers learn from correct completed explanation opportunities, rather than automatically from every delivered hint. Source-quality beliefs are private, directed and based on personally observed worksheet checks; availability remains separate.','',
        'The new voluntary, no-copying composition contrast is positive. The copying-enabled contrast remains negative: stronger sources can improve assisted homework while displacing independent practice. Adding tutoring content does not remove that substitution mechanism, and those contrary arms were retained rather than tuned away.','',
        'Longer scheduled sessions lower exams relative to the reference activity, showing the opportunity cost of time. Very difficult content suppresses usable explanations, and the mixed-versus-tracked advantage need not remain positive. Thus the extension does not enforce one aggregate sign across settings. Zero teaching skill yields exactly zero mixed-minus-tracked effect in this declared probe; disabling all communication also yields exact focal-student nulls.','',
        'Shared teaching versus independent practice partly encodes a benefit through nonnegative content/helper additions during an equal reserved practice block. It must not be presented as an independent discovery. Mixed versus tracked still depends on item content, helper opportunities, subsequent choices and the network assignment. Gain decomposition is a realized-path accounting identity, not independent causal mediation.','',
        'The [Kimbrough, McGee and Shigeoka manuscript](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) uses a common Sudoku task, optional conversation and individual evaluation. A29 represents shared-task opportunities with scheduled practice and sampled peer explanations. It does not model conversational decisions, visible ranks, persistent topic mastery or puzzle-solving speed. These differences limit the comparison, even when signs agree.','',
        'Class size with teacher capacity, adaptive instruction under tracking, and [Wu et al.’s helper-reward intervention](https://www.aeaweb.org/articles?id=10.1257/pol.20200563) require separately specified extensions. This implementation does not reproduce those field interventions. Existing AI paths are preserved; E16 makes no new AI replication claim.','',
        '## Changes, verification and use','',
        '* Added `tutoring_settings.py`, `v4_tutoring.py`, and `tutoring_config.py`, with all A28 parameters plus explicit activity/content coefficients and teaching-skill, source-quality and task-difficulty distributions.',
        '* Added tests for legacy parity, item complementarity, readiness, wrong-content nulls, observable quality, time accounting, complete gain reconstruction, configuration validation and byte-identical interrupted-run recovery.',
        '* Final complete regression suite: 429 tests passed. All 3,120 simulation raw audits and post-run hash checks passed.',
        '* Added `scripts/resume_tutoring_experiment.py`; it checks settings, software/source/raw hashes, preserves incomplete directories, and regenerates only missing or damaged runs.',
        '* All 321 historical source-lock entries checked across A22–A28/E14/E15 matched. Historical code and outputs are preserved.',
        '', f'Editable configuration: [full parameter template](<{(REPO/"configs/A29-tutoring-template.json").as_posix()}>) or [shared-practice comparison](<{(REPO/"configs/A29-shared-practice-example.json").as_posix()}>). Example commands:', '', '```powershell',
        '.venv\\Scripts\\python.exe -m classroom_swarm.tutoring_config validate configs/A29-tutoring-template.json',
        '.venv\\Scripts\\python.exe -m classroom_swarm.tutoring_config run configs/A29-tutoring-template.json --output runs/my-tutoring-experiment',
        '.venv\\Scripts\\python.exe scripts/resume_tutoring_experiment.py runs/my-tutoring-experiment', '```','',
        'Sources and raw records: `runs/E16-tutoring-r1/diagnostic-lock.json`, four runtime locks, per-run completion hashes, and `development_derived`/`validation_derived` effects, replicate metrics, raw inventories and analysis manifests. Initial preflight rejected a distribution contrast incorrectly labeled as a single scalar change; it was declared bundled before any run. The unused `runs/E16-tutoring` directory contains no runs. No outcome-driven model changes occurred.','',
        'Progress: implementation and diagnostics complete; no approval or user input pending. Teacher/instruction and reward interventions remain separately scoped future work.']
    destination=REPO/'docs/experiments/E16-results.md'
    destination.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save_json(ROOT/'report_manifest.json',dict(analysis_manifests={stage:sha256(ROOT/(stage+'_derived')/'analysis_manifest.json') for stage in ['development','validation']},
        report_sha256=sha256(destination),figure_sha256=sha256(images/'E16-tutoring-trends.png'),script_sha256=sha256(Path(__file__))))
    print(destination)


if __name__=='__main__':main()
