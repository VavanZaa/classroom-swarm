"""Read-only E17 report; verify saved evidence before producing prose and figure."""
from pathlib import Path
import csv
import json
import numpy as np
import e17_tutoring_robustness as study
from classroom_swarm.tutoring_config import REPO,load_config,save_json,sha256

LABELS={
    'reference':'Reference (20 episodes)', 'skill75':'Teaching skill 0.75',
    'skill50':'Teaching skill 0.50','heterogeneous':'Skill uniform [0.5, 1]',
    'partial_checks':'25% check coverage','no_checks':'No quality checks',
    'frozen_quality':'Frozen quality beliefs','no_quality_target':'No quality-based targeting',
    'prior_low':'Quality prior 0.2','prior_high':'Quality prior 0.8',
    'slow':'Five-tick practice','voluntary':'Voluntary (20 episodes)',
    'single_scheduled':'Single scheduled episode','single_voluntary':'Single voluntary episode'}


def read_verified(root,stage):
    folder=root/f'{stage}_derived';manifest=load_config(folder/'analysis_manifest.json')
    assert manifest['design_lock_sha256']==sha256(root/'design-lock.json')
    for name,digest in manifest['hashes'].items():assert sha256(folder/name)==digest,name
    with (folder/'effects.csv').open(encoding='utf-8',newline='') as handle:effects=list(csv.DictReader(handle))
    with (folder/'run_metrics.csv').open(encoding='utf-8',newline='') as handle:metrics=list(csv.DictReader(handle))
    return effects,metrics,manifest


def find(rows,variant,reference='tracked',group='low',metric='exam',arm='mixed'):
    return next(r for r in rows if (r['condition'],r['reference'],r['group'],r['metric'])==
                (f'{arm}_{variant}',f'{reference}_{variant}',group,metric))


def formatted(r,family=False):
    lo,hi=('simultaneous_lo95','simultaneous_hi95') if family else ('lo95','hi95')
    def fmt(value):
        value=float(value)
        if abs(value)<1e-9:value=0.
        return f'{value:+.3f}'
    return f"{fmt(r['effect'])} [{fmt(r[lo])}, {fmt(r[hi])}]"


def mean(metrics,condition,group,metric):
    values=[float(r[metric]) for r in metrics if r['condition']==condition and r['group']==group]
    return float(np.mean(values))


def build(root):
    lock=study.verify(root)
    dev,_,dm=read_verified(root,'development');rows,metrics,cm=read_verified(root,'confirmation')
    before=sha256(root/'design-lock.json')
    variants=[v for v,_,_ in study.VARIANTS]
    # Sign correspondence is separate from strength of Monte Carlo evidence.
    positive=[];clear=[]
    for v in variants:
        probes=[find(rows,v,ref,metric=m) for ref in ('tracked','solo') for m in ('exam','knowledge_gain')]
        if all(float(r['effect'])>0 for r in probes):positive.append(v)
        # A zero bootstrap endpoint can carry roundoff (~1e-17 pp); it is not positive evidence.
        if all(float(r['lo95'])>1e-9 for r in probes):clear.append(v)
    no_check=[r for r in metrics if r['condition'].endswith(('_no_checks','_frozen_quality'))]
    assert all(float(r['quality_update_fraction'])==0 for r in no_check)
    solo=[r for r in metrics if r['condition'].startswith('solo_')]
    assert all(float(r['guided_sessions_per_episode'])==float(r['content_gain'])==float(r['helper_gain'])==0 for r in solo)
    scheduled=[v for v,patch,_ in study.VARIANTS if patch.get('tutoring_activity','shared_practice')=='shared_practice']
    assert all(float(find(rows,v,metric='guided_sessions_per_episode')['effect'])==0 for v in scheduled)
    figpath=REPO/'docs/experiments/figures/E17-tutoring-robustness.png'
    figpath.parent.mkdir(parents=True,exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,7.8),sharey=True)
    for ax,reference,title in zip(axes,('tracked','solo'),('Mixed minus tracked','Mixed minus independent')):
        values=[find(rows,v,reference) for v in variants]
        y=np.arange(len(values));effects=np.array([float(r['effect']) for r in values])
        lower=np.array([float(r['lo95']) for r in values]);upper=np.array([float(r['hi95']) for r in values])
        ax.errorbar(effects,y,xerr=np.vstack([effects-lower,upper-effects]),fmt='o',color='#246b8e',capsize=3)
        ax.axvline(0,color='#888888',linewidth=1)
        ax.set_title(title);ax.set_xlabel('Unaided exam difference (percentage points)')
        ax.grid(axis='x',alpha=.2)
    axes[0].set_yticks(np.arange(len(variants)),[LABELS[v] for v in variants]);axes[0].invert_yaxis()
    fig.suptitle('E17: low starters, 60 fresh paired classrooms per condition',fontsize=14)
    fig.text(.5,.01,'Pointwise 95% Monte Carlo intervals; model assumptions and protocols vary. No human effect sizes fitted.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.95));fig.savefig(figpath,dpi=160);plt.close(fig)
    lines=[
        '# E17 results: tutoring robustness and study-pattern comparison','',
        f"Completed {dm['total_runs']+cm['total_runs']:,} simulations: {dm['total_runs']:,} development and {cm['total_runs']:,} untouched-seed confirmation. All saved raw hashes and numerical audits passed. No learning coefficients or engine rules were changed after outcomes.",'',
        f"**Result:** {len(positive)}/{len(variants)} declared variants reproduce both positive low-starter mean directions (mixed–tracked and mixed–independent) in both unaided exam and competence gain. {len(clear)}/{len(variants)} have all four pointwise intervals above zero. This count describes this declared sensitivity grid, not a probability that the model is valid. The complete behavioral/protocol pattern must be assessed separately below.",'',
        '**The complete study pattern is not reproduced.** The reference mixed–tracked exam difference is +0.222 pp, but its simultaneous interval includes zero. Mixed–independent is +0.611 pp with a positive simultaneous interval. At teaching skill .5, mixed tutoring instead lowers low-starter exams by 0.403 pp versus independent practice. In the single voluntary episode, both exam contrasts include zero, and the low mixed–tracked competence contrast is also uncertain. Scheduled teaching frequency cannot respond to tracking; voluntary frequency and ability-group results vary with the schedule.','',
        '## What was tested','',
        'Existing A29 features: teaching-skill distributions, check coverage, quality priors/updating/targeting, practice duration and scheduled/voluntary tutoring. All initial competence and preferences were paired across arms. The schedule was also adjusted from 20 episodes to one, declared before outcomes. Noisy or delayed worksheet checks, persistent topics, teachers, rewards and evolving relationships remain planned features.','',
        'The [peer-teaching study](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) used one practice block with optional communication and public prior-performance information. Its Sudoku results linked tracking to weaker teaching benefits and less teaching; gains were concentrated among lower performers. Here the final test measures numerical competence, and a guided session is only a teaching proxy. Our one-episode variants improve schedule correspondence but do not implement the full human protocol.','',
        '## Low-starter results on fresh seeds','',
        'All entries are model percentage points with pointwise 95% Monte Carlo bootstrap intervals. Competence gain is latent model state, not a measured human outcome. Interval endpoints within 1e-9 pp of zero are treated as zero when counting positive intervals; this avoids interpreting floating-point roundoff as evidence.','',
        '| Variant | Mixed–tracked exam | Mixed–independent exam | Mixed–tracked competence gain | Tracked–independent exam |',
        '|---|---|---|---|---|']
    for v in variants:
        lines.append(f"| {LABELS[v]} | {formatted(find(rows,v))} | {formatted(find(rows,v,'solo'))} | {formatted(find(rows,v,metric='knowledge_gain'))} | {formatted(find(rows,v,'solo',arm='tracked'))} |")
    lines+=['','![Low-starter robustness comparisons](figures/E17-tutoring-robustness.png)','',
        'Nine prespecified low-starter exam comparisons also receive simultaneous 95% intervals across the family. These wider intervals address multiplicity within that family; all other sensitivity comparisons remain exploratory.','',
        '| Prespecified variant | Mixed–tracked | Mixed–independent | Tracked–independent |','|---|---|---|---|']
    for v in ('reference','single_scheduled','single_voluntary'):
        lines.append(f"| {LABELS[v]} | {formatted(find(rows,v),True)} | {formatted(find(rows,v,'solo'),True)} | {formatted(find(rows,v,'solo',arm='tracked'),True)} |")
    lines+=['','## Teaching activity and ability groups','',
        'Scheduled tutoring has equal explanation frequency across mixed and tracked groups by construction. Any scheduled outcome agreement cannot explain the study’s endogenous teaching-frequency change. Voluntary sessions provide a more relevant behavioral probe but still lack the study’s public baseline ranks and task/payment structure.','',
        '| Protocol | Mixed–tracked low exam | Mixed–tracked high exam | High-minus-low exam effect | Mixed low sessions/episode | Tracked low sessions/episode | Mixed high sessions/episode | Tracked high sessions/episode |',
        '|---|---|---|---|---|---|---|---|']
    for v in ('reference','voluntary','single_scheduled','single_voluntary'):
        vals=[mean(metrics,f'{arm}_{v}',group,'guided_sessions_per_episode') for group in ('low','high') for arm in ('mixed','tracked')]
        lines.append(f"| {LABELS[v]} | {formatted(find(rows,v))} | {formatted(find(rows,v,group='high'))} | {formatted(find(rows,v,group='high_minus_low'))} | "+' | '.join(f'{x:.3f}' for x in vals)+' |')
    lines+=['','Differences above compare exogenous initial-ability groups. Low versus high treatment heterogeneity is evaluated as a paired effect difference; a nonsignificant high-group result alone does not demonstrate a smaller high-group effect. Model session counts are not the human coded teaching statements.','',
        '## Assumption diagnostics and adjustments','',
        '| Diagnostic | Fresh-seed change in low mixed-group exam versus matched reference | Interpretation |',
        '|---|---|---|']
    interpretations={
        'skill75':'Delivery reliability, with content and practice held fixed.',
        'skill50':'Larger loss of conditional explanation delivery.',
        'heterogeneous':'Delivery heterogeneity changes family/support together; not a pure mean contrast.',
        'partial_checks':'Partial observed feedback, still accurate and immediate.',
        'no_checks':'No quality learning from worksheet checks.',
        'frozen_quality':'Checks arrive but cannot update quality beliefs.',
        'no_quality_target':'Removes targeting weight; perceived homework value still uses quality.',
        'prior_low':'Initial private source-quality assumption.',
        'prior_high':'Initial private source-quality assumption.',
        'slow':'Longer exposure has the old base-learning rule and greater time cost.',
        'voluntary':'Optional commitment changes opportunity and helper costs.',
        'single_scheduled':'One episode plus final-exam scheduling is an inseparable schedule bundle.',
        'single_voluntary':'Voluntary versus scheduled within the one-episode schedule.'}
    for v in variants[1:]:
        ref='single_scheduled' if v=='single_voluntary' else 'reference'
        r=next(r for r in rows if (r['condition'],r['reference'],r['group'],r['metric'])==
            (f'mixed_{v}',f'mixed_{ref}','low','exam'))
        lines.append(f"| {LABELS[v]} | {formatted(r)} | {interpretations[v]} |")
    lines+=['',
        '**Adjustments completed:** the predeclared experiment changes explanation reliability and feedback availability, examines alternative private priors, and uses voluntary and single-episode schedules. These are declared controls and protocol probes, not coefficients chosen because they produced a favorable outcome. Original defaults are retained.','',
        'Removing checks increases the low mixed-group exam by +0.319 pp [0.139, 0.528] versus the reference. Own practice increases by +0.093 ticks per student per episode [0.066, 0.122]. The competence-gain difference is +0.379 pp: practice contributes +0.401 pp, content -0.077 pp and helper learning +0.054 pp, up to rounding. This is a raw-log accounting decomposition, not independent causal mediation. More accurate private source judgments are not guaranteed to improve learning when decisions primarily value homework grades and effort; they can also change how much additional practice occurs. These diagnostics do not justify removing real-world feedback.','',
        '**What these tests cannot fix:** partial coverage does not test noisy/delayed signals. A single scalar retrieval draw does not represent persistent Sudoku strategy mastery. Guaranteed sessions cannot generate less conversation under tracking. If those mismatches persist, the next model revision should implement F02 optional explanatory activity and F03 topic/helper consolidation, with F01 feedback realism. Raising a peer-benefit coefficient would not repair the missing behavioral mechanisms.','',
        'A mechanical explanation for tracked-group gains is already visible in the content rule. At starting learner competence .35, skill 1 and uniform difficulty [0,1], independent learner/provider retrieval gives an expected usable-content fraction of about .1253 from another .35 provider, versus .2302 from a .75 provider (numerical integration of the declared retrieval/readiness rule). Thus two equally weak students still have complementary item knowledge. These are model expectations at the initial state, not human measurements or a causal estimate from the treatment comparison. Persistent shared gaps in strategy knowledge could behave differently; that is a hypothesis for F03.','',
        'Teacher-capacity/class-size, instructional tracking, rewarded seating, university peer mean–spread interactions and the AI learning objective were not rerun in E17. Their feature gaps remain separate; this experiment provides no new claims of agreement with those studies.','',
        '## Reproducibility and claim boundaries','',
        'Raw logs reconstruct all gains and outcomes. No-check/frozen-quality arms had exactly zero quality updates; independent arms had zero tutoring content and content/helper gains. All scheduled mixed–tracked session-frequency contrasts were exactly zero, as encoded. Historical E16 source hashes were verified unchanged.','',
        'Development and confirmation used the same locked 42-condition design, different predeclared seeds, and paired replicate-level bootstrap intervals (3,000 resamples). The development review was saved before confirmation began. These intervals describe simulation variability; they do not include uncertainty about assumed coefficients, missing mechanisms or the human study.','',
        'Any claim of qualitative agreement must specify the variant, subgroup and outcome and acknowledge the protocol and behavioral mismatches. Matching a sign does not identify the human causal mechanism or independently validate the simulator. Equal scheduled base practice plus nonnegative bonuses partly encodes a teaching benefit; it is not an empirical discovery.','',
        'Project files: [preregistration](E17-preregistration.md), [feature backlog](../19-feature-backlog.md), [previous study review](../reports/Classroom-study-comparison-and-assumption-review-2026-10-01.md), [editable single-practice configuration](../../configs/E17-single-practice-example.json). The editable example has a new seed and has not been run; the reported single-practice evidence comes from the locked E17 stages.','',
        'Saved data: `runs/E17-tutoring-robustness-r1/design-lock.json`, stage configs and reviews, raw run folders, and `development_derived` / `confirmation_derived` effects, replicate metrics, raw inventories and analysis manifests.','',
        'Progress: E17 experiments and evidence report complete; no input pending. Next: specify the remaining behavioral and feedback mechanisms rather than tune to a desired sign.','']
    report=REPO/'docs/experiments/E17-results.md';report.write_text('\n'.join(lines),encoding='utf-8')
    evidence=[root/'design-lock.json',root/'development-review.md',
        root/'development_derived/analysis_manifest.json',root/'confirmation_derived/analysis_manifest.json',
        root/'confirmation_derived/effects.csv',root/'confirmation_derived/run_metrics.csv',Path(__file__),report,figpath]
    save_json(report.with_suffix('.sources.json'),dict(primary_study='https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf',
        hashes={str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in evidence},
        matching_positive_variants=positive,all_four_pointwise_intervals_positive=clear))
    assert sha256(root/'design-lock.json')==before
    print(report)
    print(json.dumps(dict(positive=positive,clear=clear),indent=2))


if __name__=='__main__':build(REPO/'runs/E17-tutoring-robustness-r1')
