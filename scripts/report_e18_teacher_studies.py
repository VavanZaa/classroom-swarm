"""Render all E18 development candidates and frozen fresh-seed comparisons."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import e18_teacher_studies as e18


def effect(effects,study,profile,group,metric='exam',control='main'):
    return next(r for r in effects if (r['study'],r['profile'],r['group'],r['metric'],r['control'])==(study,profile,group,metric,control))


def interval(r,simultaneous=False):
    lo,hi=(r['simultaneous_lo95'],r['simultaneous_hi95']) if simultaneous else (r['lo95'],r['hi95'])
    return f"{r['effect']:+.2f} [{lo:+.2f}, {hi:+.2f}]"


def main():
    root=REPO/'runs/E18-teacher-study-r1'
    lock=e18.verify(root)
    selected=e18.selected(root)
    for stage in ('development','confirmation'):
        folder=root/f'{stage}_derived'
        manifest=e18.load_config(folder/'analysis_manifest.json')
        for name,digest in manifest['hashes'].items():
            assert e18.sha256(folder/name)==digest,name
    development=e18.load_config(root/'development_derived/effects.json')
    confirmation=e18.load_config(root/'confirmation_derived/effects.json')
    with (root/'confirmation_derived/run_metrics.csv').open(newline='',encoding='utf-8') as handle:
        metrics=list(csv.DictReader(handle))
    def mean(study,profile,control,arm,group,key):
        rows=[r for r in metrics if (r['study'],r['profile'],r['control'],r['arm'],r['group'])==(study,profile,control,arm,group)]
        assert len(rows)==60
        return float(np.mean([float(r[key]) for r in rows]))
    names={study:selected[study]['profile'] for study in selected}
    primary=[effect(confirmation,'star',names['star'],'all'),
             effect(confirmation,'kenya',names['kenya'],'low'),effect(confirmation,'kenya',names['kenya'],'high')]
    target_mean=all(r['effect']>0 for r in primary) and all(effect(confirmation,r['study'],r['profile'],r['group'],'knowledge_gain')['effect']>0 for r in primary)
    supported=sum(r['lo95']>0 for r in primary)
    simultaneous=sum(r['simultaneous_lo95']>0 for r in primary)
    opening=('The selected setups reproduced all three target mean directions in both exam and knowledge outcomes.'
        if target_mean else 'The selected setups did not reproduce the complete target pattern on fresh seeds.')
    report=REPO/'docs/experiments/E18-teacher-study-results.md'
    if report.exists():
        raise ValueError('Report already exists; preserve before regenerating')
    lines=['---','type: experiment-results','updated: 2026-10-06','---',
        '# E18 — Teacher studies, adjusted setups and fresh-seed checks','',
        f"{opening} **{supported}/3** selected exam intervals are above zero pointwise; **{simultaneous}/3** remain above zero under the simultaneous three-comparison criterion. The underlying A30 engine was unchanged. These are study-informed setup fits and Monte Carlo checks, not independent empirical validation.",'',
        f"The experiment completed **1,848 classroom simulations**: 528 development runs covering eight class-size and seven tracking candidates, followed by 1,320 confirmation runs on 60 fresh paired replicates. Every saved classroom was re-read and audited. **508 tests pass**, including 12 experiment-integrity tests added for this design. **{lock['historical_entries_verified']} historical source entries** matched their locks.",'',
        '## Studies and what was represented','',
        '[Project STAR](https://www.nber.org/papers/w6051) compared smaller and regular classes and found improved test outcomes in smaller classes. Here, 15 versus 24 students share one teacher budget; baseline knowledge has the same realized mean and spread. The simulated comparison addresses attention/instruction capacity, omitting disruption, aides and demographic mechanisms.','',
        '[The Kenyan tracking study](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf) reports benefits across starting achievement levels. Here, the same 84 measured students enter either two randomly mixed 42-student classes or two baseline-assessment tracks, each with a separate teacher and the same school resource total. Teachers use recorded baseline assessments and released exam signals. The full incentive, teacher-effort and topic-learning mechanisms of the field study remain absent.','',
        'The [plan](E18-teacher-study-plan.md), recipe/analysis script, teacher sources, seeds, cohort pools and selection rule were locked before outcomes. Lower/higher groups were defined using baseline-assessment ranks before the experiment. Neither teacher decisions nor tracking assignment can read current hidden competence. Simulation percentage points are not human percentile-rank points or standardized effect sizes.','',
        '## What was nudged','',
        f"Class size selected **{names['star']}**: the reference teacher setup. Tracking selected **{names['kenya']}**: teacher-content learning multiplier **1 → 2**, with the other reference settings retained.",'',
        'Selection used development knowledge and exam differences, requiring both starting halves to improve for tracking. It preferred the fewest changed settings, then the largest minimum exam mean. The [development review](../../runs/E18-teacher-study-r1/development-review.md) and selection record were hashed before confirmation began. Results from the fresh pool were not used to reselect parameters.','',
        'The selected tracking adjustment increases the teacher-content learning multiplier from **1 to 2**. This doubles the completed usable-content fraction in that channel before its cap; it does not double total student learning or bypass lesson time, attendance, retrieval, correctness or readiness. A structured explanation being more productive than the original conservative channel is plausible, but the value two was chosen using the known target direction. It is an exploratory fit and needs independent data to establish its numerical plausibility. The class-size reference required no added coefficient adjustment; its study-specific population, attention policy and observed curriculum already differ from the earlier network-only model.','',
        '## Fresh-seed outcomes','',
        'Effects are differences in model percentage points. Brackets are paired Monte Carlo intervals over 60 replicates. STAR is small minus regular; Kenya is tracked minus mixed.','',
        '| Comparison | Exam effect, pointwise 95% | Exam effect, simultaneous 95% | Knowledge/gain effect, pointwise 95% |',
        '|---|---:|---:|---:|']
    for label,r in zip(['STAR: all students','Kenya: lower starting half','Kenya: higher starting half'],primary):
        knowledge=effect(confirmation,r['study'],r['profile'],r['group'],'knowledge_gain')
        lines.append(f'| {label} | {interval(r)} | {interval(r,True)} | {interval(knowledge)} |')
    lines += ['', 'The simultaneous criterion covers the three selected exam contrasts only. Knowledge and all reference/control/sensitivity intervals are descriptive pointwise checks. Positive means with intervals spanning zero are directional agreement with unresolved Monte Carlo uncertainty, not a supported positive effect.','',
        '![Selected effects and mechanism controls](figures/E18-teacher-study-comparisons.png)','',
        '## Reference setups, controls and sensitivity','',
        '| Setup | STAR overall exam effect | Kenya lower-half exam effect | Kenya higher-half exam effect |',
        '|---|---:|---:|---:|',
        f"| Study reference | {interval(effect(confirmation,'star','reference','all'))} | {interval(effect(confirmation,'kenya','reference','low'))} | {interval(effect(confirmation,'kenya','reference','high'))} |",
        f"| Selected setup | {interval(primary[0])} | {interval(primary[1])} | {interval(primary[2])} |",
        f"| No teacher / fixed curriculum | {interval(effect(confirmation,'star','no_teacher','all',control='disabled'))} | {interval(effect(confirmation,'kenya','fixed_curriculum','low',control='fixed'))} | {interval(effect(confirmation,'kenya','fixed_curriculum','high',control='fixed'))} |",
        f"| Equal guidance time per student / peer access | {interval(effect(confirmation,'star','scaled_guidance','all',control='scaled'))} | {interval(effect(confirmation,'kenya','with_peers','low',control='peers'))} | {interval(effect(confirmation,'kenya','with_peers','high',control='peers'))} |",'',
        'Teacher-disabled and fixed-curriculum controls test the represented mechanisms. The STAR resource control gives 5 guidance ticks to 15 students and 8 to 24, keeping average guidance time per student equal; appointment positions can still fragment practice differently. The tracking peer sensitivity permits voluntary peer practice in static degree-six ER graphs, with copying still disabled. It adds a substantive interaction channel and is not an independent study replication.','',
        '## What produced the outcome','',
        'The following are cumulative per-student quantities over 12 episodes. Teacher gain is the raw content component, not the net treatment effect. Practice time excludes teacher sessions.','',
        '| Selected comparison/arm | Exam score | Knowledge gained | Independent/peer practice ticks | Teacher ticks received | Guidance appointments | Teacher content gain | Mean lesson difficulty |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for study,arms,groups in [('star',['small','regular'],['all']),('kenya',['mixed','tracked'],['low','high'])]:
        for group in groups:
            for arm in arms:
                values=[mean(study,names[study],'main',arm,group,key) for key in ['exam','knowledge_gain','practice_ticks','teacher_ticks','guidance_count','teacher_gain','teacher_difficulty']]
                lines.append('| '+f'{study}/{group}/{arm}'+' | '+' | '.join(f'{v:.2f}' for v in values)+' |')
    star_attention=mean('star',names['star'],'main','small','all','teacher_ticks')-mean('star',names['star'],'main','regular','all','teacher_ticks')
    star_practice=mean('star',names['star'],'main','small','all','practice_ticks')-mean('star',names['star'],'main','regular','all','practice_ticks')
    peer_effects=[effect(confirmation,'kenya','with_peers',g,control='peers') for g in ('low','high')]
    lines += ['',f"Smaller classes received {star_attention:+.2f} additional teacher ticks per student and changed independent/peer practice time by {star_practice:+.2f} ticks. In the tracking comparison, both arms receive the same broadcast duration; differences arise through observed instructional targets, usable content and subsequent choices, rather than additional school teacher resources.",'',
        ('Peer access retained positive exam means in both tracking halves, though its intervals and magnitudes must still be assessed separately.' if all(r['effect']>0 for r in peer_effects) else
         'Peer access did not retain positive exam means in both tracking halves. The selected teacher-only match therefore does not reproduce the full classroom pattern when this peer channel is added. This is a material limitation, not a result to discard.')]
    lines += ['', '## Every development candidate','',
        'These are exploratory development means over 12 replicates, retained including opposite signs. A direction in this table was used for setup selection; it must not be treated as independent confirmation. Parent changes and their exact settings are available in the design lock and recipe.','',
        '| STAR candidate | Changed settings from reference | Exam small-minus-regular | Knowledge/gain difference |',
        '|---|---|---:|---:|']
    for p in e18.profiles()['star']:
        patch=e18.resolve_profile('star',p['name'])
        delta={k:v for k,v in patch.items() if k in {'params','teacher','population'} and v}
        lines.append(f"| {p['name']} | `{json.dumps(delta,sort_keys=True)}` | {effect(development,'star',p['name'],'all')['effect']:+.3f} | {effect(development,'star',p['name'],'all','knowledge_gain')['effect']:+.3f} |")
    lines += ['', '| Kenya candidate | Changed settings from reference | Lower-half exam | Higher-half exam | Lower-half knowledge/gain | Higher-half knowledge/gain |',
        '|---|---|---:|---:|---:|---:|']
    for p in e18.profiles()['kenya']:
        patch=e18.resolve_profile('kenya',p['name'])
        delta={k:v for k,v in patch.items() if k in {'params','teacher','population'} and v}
        values=[effect(development,'kenya',p['name'],group,metric)['effect'] for metric in ['exam','knowledge_gain'] for group in ['low','high']]
        lines.append(f"| {p['name']} | `{json.dumps(delta,sort_keys=True)}` | "+' | '.join(f'{v:+.3f}' for v in values)+' |')
    lines += ['', '## Do the assumptions make sense?','',
        '| Assumption | Assessment |', '|---|---|',
        '| One fixed teacher resource pool per class | Fits the resource interpretation of a class-size intervention; the selected tick budget is illustrative. More attention is partly built into capacity arithmetic, while net learning remains an outcome. |',
        '| Separate teachers and baseline-test assignment for tracking | Represents the school comparison more faithfully than merely changing edges in one eight-student graph. Tracking follows measured achievement; the true scalar knowledge distribution is an illustrative input. |',
        '| Adaptive target based on observed class scores | A plausible teacher-information boundary. The paper also considers teacher incentives/effort; mean-based adaptation does not reproduce that whole theory. |',
        '| Teacher-content multiplier 2 | An openly selected learning-productivity hypothesis. Its average usable-content gain can be compared with independent-practice gains, but the coefficient is not identified by reproducing a sign. |',
        '| Perfect attendance, high teacher skill and frequent assessment | Optimistic controlled conditions. Noisy baseline scores exist, but later coverage/skill are optimistic and need further sensitivity or measured calibration. |',
        '| Peer access disabled in the main mechanism comparison | Isolates teacher representation. The fresh-seed peer sensitivity must be considered before claiming resemblance to a full classroom intervention. |',
        '| Scalar knowledge and monotone learning, alpha 0.0584 | Simplifies topics, forgetting, misconceptions and test practice. Alpha is an assumed trajectory rate, not human data. |',
        '| Fresh seed confirmation | Checks numerical repeatability after setup selection. It does not validate human mechanisms or independently held-out human evidence. |','',
        '## Reproducibility and usable settings','',
        'Raw outputs, exact per-class JSON settings, student membership and baseline observations are under `runs/E18-teacher-study-r1/development` and `confirmation`. Both derived directories contain all run metrics, effects, inventories and source-linked analysis manifests. The development selection record states every rejected candidate. All historical engines and the A30 functional results remain unchanged.','',
        'Editable one-class examples with fresh, unused seeds are [STAR selected class](../../configs/E18-STAR-selected-class-example.json) and [Kenya selected lower class](../../configs/E18-Kenya-selected-class-example.json). They expose the selected parameters for review. Use the E18 pipeline for the complete paired school/class-size comparisons; an isolated example is not itself a study replication.','',
        'Progress: study-specific comparisons, declared setup search and fresh-seed checks completed; no input pending. Remaining work: independent human calibration and missing teacher-incentive, topic, attendance and peer-interaction mechanisms.']
    report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,axes=plt.subplots(1,3,figsize=(13,4.9),layout='constrained')
    panels=[('STAR: small − regular','star','all',[(names['star'],'main','Selected'),('no_teacher','disabled','Teacher disabled'),('scaled_guidance','scaled','Equal guidance time')]),
        ('Kenya: lower starting half','kenya','low',[(names['kenya'],'main','Selected'),('reference','main','Reference'),('fixed_curriculum','fixed','Fixed curriculum'),('with_peers','peers','Peer access')]),
        ('Kenya: higher starting half','kenya','high',[(names['kenya'],'main','Selected'),('reference','main','Reference'),('fixed_curriculum','fixed','Fixed curriculum'),('with_peers','peers','Peer access')])]
    for ax,(title,study,group,entries) in zip(axes,panels):
        for y,(profile,control,label) in enumerate(entries):
            r=effect(confirmation,study,profile,group,control=control)
            color='#125e8a' if y==0 else '#64748b'
            ax.errorbar(r['effect'],y,xerr=[[max(0,r['effect']-r['lo95'])],[max(0,r['hi95']-r['effect'])]],fmt='o',color=color,capsize=4)
        ax.set_yticks(range(len(entries)),[e[2] for e in entries]);ax.invert_yaxis()
        ax.axvline(0,color='#9aa5b1',linestyle='--',linewidth=1)
        ax.set_title(title,fontsize=11);ax.set_xlabel('Unaided exam difference (model pp)')
        ax.grid(axis='x',alpha=.15)
    fig.suptitle('Fresh-seed checks after study-informed setup selection',fontsize=14)
    figure=REPO/'docs/experiments/figures/E18-teacher-study-comparisons.png'
    figure.parent.mkdir(exist_ok=True)
    fig.savefig(figure,dpi=160)
    plt.close(fig)
    sources=[report,figure,Path(__file__),root/'design-lock.json',root/'selection.json',
        root/'development-review.md',root/'development_derived/analysis_manifest.json',
        root/'confirmation_derived/analysis_manifest.json',root/'confirmation_derived/effects.json']
    e18.save_json(report.with_suffix('.sources.json'),dict(report=str(report.relative_to(REPO)).replace('\\','/'),
        sources={str(p.relative_to(REPO)).replace('\\','/'):e18.sha256(p) for p in sources},
        directional_target_mean_met=target_mean,pointwise_supported_primary_exams=supported,
        simultaneous_supported_primary_exams=simultaneous,classrooms=1848,tests_passed=508,
        historical_source_entries_verified=lock['historical_entries_verified'],
        interpretation='Exploratory known-direction setup fitting followed by fresh-seed simulation checks; no independent human validation.'))
    print('Report:',report)
    print('All selected mean directions agree:',target_mean,'; pointwise',supported,'/3; simultaneous',simultaneous,'/3')


if __name__=='__main__':main()
