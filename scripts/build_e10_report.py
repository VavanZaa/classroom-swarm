"""Presentation only; all measurements come from the locked E10 analysis."""
import argparse
import csv
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from classroom_swarm.e9 import REPO, digest, dump


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output
    data=json.loads((out/'analysis.json').read_text())
    e={(r['condition'],r['metric']):r for r in data['estimates']}
    fx={(r['condition'],r['metric']):r for r in data['effects']}
    def val(c,m,scale=100):
        return e[c,m]['mean']*scale
    def ci(c,m):
        r=fx[c,m]
        return f"{100*r['mean']:+.2f} points (95% CI {100*r['low']:+.2f} to {100*r['high']:+.2f})"
    with (out/'trajectories.csv').open(encoding='utf-8-sig', newline='') as f:
        tr=list(csv.DictReader(f))
    colors={'reference':'#385a88','check0':'#bb563b'}
    names={'reference':'Original checking','check0':'Score-only checking'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.titleweight':'bold'})
    fig,ax=plt.subplots(2,2,figsize=(13,8.6),layout='constrained')
    for c in colors:
        rows=[r for r in tr if r['condition']==c]
        hs=sorted({int(r['homework']) for r in rows})
        for metric,axis in [('K',ax[0,0]),('K_p90_p10',ax[0,1])]:
            ys=[100*np.mean([float(r[metric]) for r in rows if int(r['homework'])==h]) for h in hs]
            axis.plot(hs,ys,lw=2.5,label=names[c],color=colors[c])
        for metric,style,label in [('high_K','-','Early high-attempt'),('low_K','--','Early low-attempt')]:
            ys=[100*np.mean([float(r[metric]) for r in rows if int(r['homework'])==h]) for h in hs]
            ax[1,1].plot(hs,ys,style,lw=2,label=names[c]+': '+label,color=colors[c])
    ax[0,0].set(title='Average knowledge falls',ylabel='Knowledge /100',ylim=(45,82))
    ax[0,1].set(title='Overall spread widens relative to the original',ylabel='Within-class P90 minus P10',ylim=(0,27))
    ax[1,1].set(title='Early activity groups do not pull farther apart',ylabel='Knowledge /100',ylim=(45,82))
    bottoms=np.zeros(2)
    for metric,color,label in [('attempt_gain','#31918b','Own attempts'),('check_gain','#d49a44','Checking'),('help_hint_gain','#8470a6','Explaining to peers')]:
        ys=[val(c,metric) for c in colors]
        ax[1,0].bar(range(2),ys,bottom=bottoms,color=color,label=label,width=.55)
        bottoms+=ys
    ax[1,0].set(title='Where knowledge gains come from',ylabel='Accumulated gain /100',xticks=[0,1],xticklabels=list(names.values()),ylim=(0,32))
    for axis in [ax[0,0],ax[0,1],ax[1,1]]:
        axis.set_xlabel('Homework'); axis.set_xticks([0,5,10,15,20])
    for axis in ax.flat:
        axis.grid(axis='y',alpha=.18); axis.set_axisbelow(True); axis.legend(fontsize=8,frameon=False)
    fig.suptitle('Activity-specific learning: a wider spread, but no persistent behavioral split',fontsize=17,fontweight='bold')
    fig.supxlabel('Means of 100 paired classrooms. Groups fixed from original-model attempts in homeworks 1–5; descriptive, not causal.',fontsize=10)
    fig.savefig(out/'learning-gap.png',dpi=170)
    plt.close(fig)
    labels={'reference':'Original (100% check learning)','check25':'25% check learning','check10':'10% check learning',
            'check0':'Score-only check (0%)','check0_unaligned':'0%, original choice values','no_check':'Checking unavailable',
            'H40_reference':'40 homeworks: original','H40_check0':'40 homeworks: score-only',
            'ER_reference':'ER network: original','ER_check0':'ER network: score-only'}
    table='| Condition | Mean knowledge /100 | P90–P10 gap | Early-group final gap | Late copied submissions |\n|---|---:|---:|---:|---:|\n'
    for c,label in labels.items():
        table+=f"| {label} | {val(c,'K_final'):.2f} | {val(c,'K_p90_p10'):.2f} | {val(c,'group_gap_K_final'):.2f} | {val(c,'copy_late'):.2f}% |\n"
    report=f'''# Learning activities and the knowledge gap

24 September 2026 · V4.2-L / A23 · E10 · 1,000 simulations · 100 independent paired classrooms × 10 conditions

**Implemented and tested: score inspection now informs beliefs without automatically adding competence. This widens the overall final knowledge spread modestly, but does not establish a stronger, persistent split between students' learning behaviors.** The original V4.1/V4.2 engines and E9 results are preserved.

## What changed

Originally a two-tick check revealed an answer packet's exact score and also gained knowledge at half the rate of a three-tick independent attempt. The new default gives this **score-only check** no direct knowledge increment. It still takes time, supplies information, updates confidence and affects later choices. Students learn when they actually attempt work or explain to peers; a hint boosts a subsequent attempt. Copying retains zero direct learning. No copying penalty, assigned student type, larger general learning rate or target gap was added.

The check's expected intrinsic learning value changes consistently; its information value remains. A separate condition keeps the original choice values to isolate this change. Checking-learning strengths of 0%, 10%, 25% and 100% of the original are all reported, without choosing a winning value after inspecting outcomes. The zero default describes score inspection; it does **not** claim that effortful checking, error correction or self-explanation cannot teach.

## Main findings

The class mean falls from **{val('reference','K_final'):.2f} to {val('check0','K_final'):.2f}**. The within-class 90th–10th percentile gap rises from **{val('reference','K_p90_p10'):.2f} to {val('check0','K_p90_p10'):.2f}**: {ci('check0','K_p90_p10')}. This is about an 11% wider final spread relative to the original rule, not a claim of real-world accuracy.

**Both models still compress the initial spread**, which averages {val('reference','K0_p90_p10'):.2f} points. Learning remains monotone and proportional to remaining headroom, `(1-K)`. Given comparable learning exposure and rates, lower knowledge leaves more room to gain and students approach the same ceiling. The intervention reduces this convergence rather than producing divergence from the initial classroom.

![Learning trajectories, within-class spread, learning decomposition and early activity groups](learning-gap.png)

## Do different activity patterns now create a clearer lasting gap?

Not convincingly in this test. We fixed the top and bottom thirds of each reference classroom using **completed attempts in the first five homeworks**, then followed the same students across paired conditions. Their final knowledge gap is {val('reference','group_gap_K_final'):.2f} points originally and {val('check0','group_gap_K_final'):.2f} with score-only checking. The paired change is {ci('check0','group_gap_K_final')}. Their initial gap was already {val('reference','group_gap_K0'):.2f} points; these are not randomly assigned strategies.

After homework 5, the high-minus-low attempt-rate difference is just {val('reference','group_gap_later_attempts',1):.3f} attempts per homework originally and {val('check0','group_gap_later_attempts',1):.3f} with score-only checking. Early behavior predicts little sustained difference in later attempt frequency. Integer attempt counts also tie frequently: on average {val('reference','boundary_ties',1):.2f} of the two group boundaries are tied; student ID resolves ties. These groups are a limited descriptive diagnostic, not distinct stable student types or a causal estimate of an activity's benefit.

The high-attempt group gains {val('check0','group_gap_gain'):.2f} points more over the full course, but {abs(val('check0','group_gap_later_gain')):.2f} points less after homework 5. This is compatible with catch-up and regression toward typical activity rates; it is not evidence of a self-reinforcing learning divide.

## Behavioral responses and mechanisms

Removing automatic check learning reduces that contribution from {val('reference','check_gain'):.2f} to zero knowledge points. Own-attempt gains rise from {val('reference','attempt_gain'):.2f} to {val('check0','attempt_gain'):.2f}; explanation gains rise from {val('reference','help_hint_gain'):.2f} to {val('check0','help_hint_gain'):.2f}. Lower K increases learning headroom as well as changing behavior, so this decomposition must not all be attributed to additional attempts.

Completed attempts increase only from {val('reference','attempts',1):.2f} to {val('check0','attempts',1):.2f} per student across 20 homeworks. Checks decrease from {val('reference','checks',1):.2f} to {val('check0','checks',1):.2f}. Students continue checking frequently for its modeled informational value. Late copied submissions increase from {val('reference','copy_late'):.2f}% to {val('check0','copy_late'):.2f}%; both defaults complete all homework. Knowledge and behavioral change are therefore not interchangeable.

When checking is entirely unavailable, mean knowledge is {val('no_check','K_final'):.2f}, versus {val('check0','K_final'):.2f} with score-only checking available. Attempts increase to {val('no_check','attempts',1):.2f}. Within this model, a useful information-seeking activity can consume time that would otherwise produce competence. This is a counterfactual model result, not a recommendation to stop checking real work.

## All conditions

{table}
The wider overall spread persists on ER networks ({ci('ER_check0','K_p90_p10')}) and at 40 homeworks ({ci('H40_check0','K_p90_p10')}). Nevertheless, the absolute spread is smaller at 40 than at 20 homeworks. More time alone does not generate persistent divergence.

## What is encoded, what emerges, and what to change next

An attempt teaching more than passive score inspection is **encoded**, so this difference is not a discovered phenomenon. The observed activity substitution, continued checking, weak persistence of early attempt differences, and partial compensation are responses produced by the coupled decision and learning system. This study does not establish a scientifically unique form of emergence.

The next useful target is **persistence and learning content**, rather than another increase in activity multipliers. Candidate mechanisms are habit reinforcement from privately observed effort and outcomes, and separate concept skills with prerequisite difficulty and transfer tests. These could let repeated practice build useful capability while repeated answer access preserves grades without equivalent unaided performance. They require separate evidence, ablations and an explicit design; neither is implemented here. They should also permit recovery, strategy switching and null results.

For now, V4.2-L is a clearer operational distinction between information and competence. It succeeds in widening overall spread modestly, but **does not yet achieve a robust knowledge divide associated with persistent activity styles**. We retained that result rather than tuning until a larger divide appeared.

## Evidence and limitations

[Karpicke and Blunt (2011)](https://pubmed.ncbi.nlm.nih.gov/21252317/) found benefits of retrieval practice on conceptual assessments relative to elaborative concept-mapping study. This motivates distinguishing reconstructive activity from receipt of information, but does not supply the model's numerical learning rates or prove that every attempt is effective.

[Smith and colleagues (2009)](https://pubmed.ncbi.nlm.nih.gov/19119232/) found improvement on related concept questions after peer discussion. This supports retaining a route from discussion to learning, not treating all assistance as copying. These studies do not validate the simulated gap or the score-only zero-learning assumption.

All rates remain assumptions; alpha comes from a chosen trajectory, not educational data. This is an exploratory extension motivated by E9 results, with the E10 design and source hashes fixed before its runs. Uncertainty intervals resample 100 whole paired classrooms, 2,000 times; they are pointwise, not multiplicity-adjusted. Thirty students per classroom are not treated as independent experimental replicates. Initial skills, heterogeneous rates and choices confound activity-group comparisons. One scalar K cannot represent separate concepts, misconceptions, forgetting or transfer.

## Verification and reproducibility

261 tests pass, including exact historical parity at original checking strength, information updates without automatic competence, activity-time accounting and event-level learning equations. All {data['verified_raw_files']} raw data files were hash-verified. Every student's accumulated event gains reconstruct total knowledge change within 1e-12. Independent reruns of the reference and score-only condition reproduced every raw table. All E9 locked source hashes remain unchanged.

- [All classroom outcomes](classroom_results.csv)
- [All student outcomes and fixed early-group labels](student_results.csv)
- [Trajectories](trajectories.csv)
- [Condition estimates](condition_estimates.csv) and [paired effects](paired_effects.csv)
- [Analysis metadata](analysis.json) and [raw dataset locations and hashes](dataset_manifest.json)
- [Analysis data bundle](learning-gap-data.zip)
- [Source, tests, specification and run lock](learning-gap-source.zip)

Raw logs stay in the project at `runs/E10`. Reproduce with `python -m classroom_swarm.e10 analyze --root runs/E10 --output <directory>`. For a new simulation, use `lock` on a new empty directory, then `run --workers 4`. An existing completed run is verified rather than overwritten. E9 remains the historical baseline.
'''
    (out/'learning-gap-report.md').write_text(report,encoding='utf-8')
    def inline(s):
        s=html.escape(s)
        s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
        s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
        return re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    blocks=[]; lines=report.splitlines(); i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[-:| ]+\|$',lines[i]):
                    tag='th' if not rows else 'td'
                    rows.append('<tr>'+''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in lines[i].strip('|').split('|'))+'</tr>')
                i+=1
            blocks.append('<div class="table"><table>'+''.join(rows)+'</table></div>'); continue
        if line.startswith('!['):
            alt,src=re.match(r'!\[([^]]*)\]\(([^)]+)\)',line).groups()
            blocks.append(f'<img src="{src}" alt="{html.escape(alt)}">')
        elif line.startswith('#'):
            level=len(line)-len(line.lstrip('#')); blocks.append(f'<h{level}>{inline(line[level:].strip())}</h{level}>')
        elif line:
            blocks.append('<p>'+inline(line)+'</p>')
        i+=1
    css='body{background:#f4f7fb;color:#20334b;font:17px/1.65 system-ui;margin:0}main{max-width:1100px;margin:35px auto;padding:45px;background:white;border-radius:14px}h1{line-height:1.2;color:#153c60}h2{margin-top:36px}img{width:100%}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border-bottom:1px solid #dce3eb}th{background:#264b6d;color:white;text-align:left}.table{overflow-x:auto}a{color:#1859a9}code{font-size:13px;overflow-wrap:anywhere}@media(max-width:700px){main{margin:0;padding:20px}}'
    (out/'learning-gap-report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Learning activities and the knowledge gap</title><style>'+css+'</style><main>'+''.join(blocks)+'</main></html>',encoding='utf-8')
    with zipfile.ZipFile(out/'learning-gap-data.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in out.iterdir():
            if f.suffix in {'.csv','.json'} and f.name!='deliverable_hashes.json':
                z.write(f,f.name)
    bundle=list((REPO/'src/classroom_swarm').glob('*.py'))+list((REPO/'tests').glob('*.py'))
    bundle += [REPO/p for p in ['pyproject.toml','uv.lock','docs/11-v4-activity-feedback.md','docs/12-v4-learning-differentiation.md',
        'scripts/build_e10_report.py','runs/E10/lock.json','runs/E10/execution.json']]
    with zipfile.ZipFile(out/'learning-gap-source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in bundle:
            z.write(f,f.relative_to(REPO).as_posix())
    dump(out/'deliverable_hashes.json',{f.name:digest(f) for f in out.iterdir() if f.is_file() and f.name!='deliverable_hashes.json'})
    canonical=REPO/'runs/E10/derived'; canonical.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.is_file(): shutil.copy2(f,canonical/f.name)
    for f in out.iterdir():
        report=report.replace(f']({f.name})',f'](../../runs/E10/derived/{f.name})')
    (REPO/'docs/experiments/E10-results.md').write_text(report,encoding='utf-8')
    print('Report, figure, data and source bundles written.')


if __name__=='__main__':
    main()
