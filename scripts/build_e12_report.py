"""Presentation of the locked A25/E12r1 motivation, public-grade and AI experiment."""
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
from classroom_swarm.e9 import REPO,digest,dump


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output
    d=json.loads((out/'analysis.json').read_text())
    e={(r['condition'],r['metric']):r for r in d['estimates']}
    fx={(r['condition'],r['reference'],r['metric']):r for r in d['effects']}
    def v(c,m,scale=100):
        x=e[c,m]['mean'];return float('nan') if x is None else scale*x
    def ci(c,ref,m):
        r=fx[c,ref,m]
        return f"{100*r['mean']:+.2f} points (95% CI {100*r['low']:+.2f} to {100*r['high']:+.2f})"
    with (out/'trajectories.csv').open(encoding='utf-8-sig',newline='') as f:tr=list(csv.DictReader(f))
    cases=['public_no_ai','answer_ai','tutor_ai']
    labels={'public_no_ai':'No AI','answer_ai':'Answer AI','tutor_ai':'Tutor AI'}
    colors={'public_no_ai':'#396598','answer_ai':'#bf603f','tutor_ai':'#238779'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(2,2,figsize=(13.5,9),layout='constrained')
    x=np.arange(3)
    for metric,offset,color,label in [('homework_final',-.19,'#56879c','Final homework'),('exam_final',.19,'#bf7753','Same-time unaided exam')]:
        vals=[v(c,metric) for c in cases]
        err=np.array([[100*(e[c,metric]['mean']-e[c,metric]['low']) for c in cases],
                      [100*(e[c,metric]['high']-e[c,metric]['mean']) for c in cases]])
        ax[0,0].bar(x+offset,vals,width=.36,color=color,label=label,yerr=err,capsize=3)
    ax[0,0].set(xticks=x,xticklabels=[labels[c] for c in cases],ylim=(0,100),ylabel='Score /100',title='Grades and exams at the same time')
    ax[0,0].legend(frameon=False,fontsize=9)
    for c in cases:
        rr=[r for r in tr if r['condition']==c]
        hs=sorted({int(r['homework']) for r in rr})
        yy=[100*np.mean([float(r['K']) for r in rr if int(r['homework'])==h]) for h in hs]
        ax[0,1].plot(hs,yy,label=labels[c],color=colors[c],lw=2.5)
    ax[0,1].set(xlabel='Homework',ylabel='Knowledge /100',title='Knowledge follows practice',ylim=(45,85),xticks=[0,5,10,15,20])
    ax[0,1].legend(frameon=False)
    for c,suffix in zip(cases,['no_ai','answer','tutor']):
        cs=[f'effort0_{suffix}',c,f'effort50_{suffix}']
        ax[1,0].plot([0,.15,.5],[v(a,'exam_final') for a in cs],'o-',color=colors[c],label=labels[c],lw=2)
    ax[1,0].set(xlabel='Effort aversion (scenario parameter)',ylabel='Unaided exam /100',title='How effort preferences change results',xticks=[0,.15,.5])
    ax[1,0].legend(frameon=False)
    components=[([1-e[c,'peer_copied_late']['mean']-e[c,'direct_ai_answer_late']['mean']-e[c,'incomplete_late']['mean'] for c in cases],
                  '#b9cfdb','Own work, including guided attempts'),
                ([e[c,'peer_copied_late']['mean']-e[c,'peer_ai_origin_late']['mean'] for c in cases],
                  '#54728c','Peer copy: student-origin answer'),
                ([e[c,'peer_ai_origin_late']['mean'] for c in cases],'#e4aa72','Peer copy: AI-origin answer'),
                ([e[c,'direct_ai_answer_late']['mean'] for c in cases],'#b95139','Direct AI answer'),
                ([e[c,'incomplete_late']['mean'] for c in cases],'#d8d8d8','Missing submission')]
    bottom=np.zeros(3)
    for values,color,label in components:
        values=np.asarray(values)*100
        ax[1,1].bar(x,values,bottom=bottom,color=color,label=label,width=.6);bottom+=values
    ax[1,1].set(xticks=x,xticklabels=[labels[c] for c in cases],ylim=(0,105),ylabel='Late submissions (%)',title='Where submitted answers come from')
    ax[1,1].legend(frameon=False,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.1),ncol=2)
    for a in ax.flat:a.grid(axis='y',alpha=.17);a.set_axisbelow(True)
    fig.suptitle('Grade-seeking under uncertainty: public grades, social closeness and AI',fontsize=17,fontweight='bold')
    fig.supxlabel('100 paired classrooms per condition. AI capabilities and preference strengths are scenario assumptions, not measured student data.',fontsize=10)
    fig.savefig(out/'motivation-grades-ai.png',dpi=170);plt.close(fig)
    primary='| Model | Final homework /100 | Same-time exam /100 | Homework–exam gap | True knowledge /100 |\n|---|---:|---:|---:|---:|\n'
    for c in cases:primary+=f"| {labels[c]} | {v(c,'homework_final'):.2f} | {v(c,'exam_final'):.2f} | {v(c,'grade_exam_gap'):.2f} | {v(c,'K_final'):.2f} |\n"
    alltable='| Condition | Final homework | Same-time exam | Gap | Late peer-copy % | Late direct-AI % | Knowledge P90–P10 |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for c in dict.fromkeys(r['condition'] for r in d['estimates']):
        alltable+=f"| {c} | {v(c,'homework_final'):.2f} | {v(c,'exam_final'):.2f} | {v(c,'grade_exam_gap'):.2f} | {v(c,'peer_copied_late'):.2f} | {v(c,'direct_ai_answer_late'):.2f} | {v(c,'K_p90_p10'):.2f} |\n"
    report=f'''# Motivation, public grades and AI: corrected V4 results

24 September 2026 · A25 / E12r1 · 2,600 simulations · 26 conditions × 100 paired classrooms · 296 tests passing

**Students now seek high expected grades with low perceived effort. They do not see their true knowledge, current answer correctness or the AI's true effectiveness.** Homework grades become public after return, and source choice balances grades, relationship closeness and experienced availability. The corrected model includes no AI, answer-giving AI and tutoring AI.

## Main results: compare the same point in time

{primary}
**Answer-giving AI creates a large separation between rewarded homework performance and unaided competence in this model.** Stronger effort avoidance makes the separation larger: answer-AI homework moves from {v('answer_ai','homework_final'):.2f} to {v('effort50_answer','homework_final'):.2f}, while the exam moves from {v('answer_ai','exam_final'):.2f} to {v('effort50_answer','exam_final'):.2f}. The student can improve the visible short-term outcome while reducing practice that would support later unaided work.

All headline homework and exam scores are measured at assignment 20. Previously, the E11 table put the average of homeworks 16–20 next to the final exam, which obscured the contemporaneous gap. Reconstructing assignment 20 in E11 gives homework 74.54 versus exam 73.47 with copying pressure. That comparison error and the missing public-grade/AI assumptions are separate issues.

![Matched grades and exams, knowledge trajectories, effort sensitivity and answer origins](motivation-grades-ai.png)

Against the corrected no-AI case, answer AI changes final homework by {ci('answer_ai','public_no_ai','homework_final')}, the unaided exam by {ci('answer_ai','public_no_ai','exam_final')}, and the matched grade–exam gap by {ci('answer_ai','public_no_ai','grade_exam_gap')}. Tutor AI changes the exam by {ci('tutor_ai','public_no_ai','exam_final')}. Tutor versus answer AI differs by {ci('tutor_ai','answer_ai','exam_final')} on the unaided exam.

These are model counterfactuals under declared assumptions, not measured educational effects. Answer AI's default item accuracy is 90%; 80% and 100% cases are also reported. Tutor AI supplies a hint and requires a subsequent student attempt to produce learning or a new answer.

## Motivation: why easy grades can mislead

The central choice is expected grade improvement minus personally weighted effort cost, with the previously requested bad-grade pressure bias toward shortcuts. The main cases remove the old intrinsic learning reward and positive waiting bonus. Choosing to study must be supported by expected grades, uncertainty and experience; the policy receives no reward for secretly increasing the researcher's K variable.

Students differ in effort aversion. A three-tick attempt costs more effort than a one-tick AI answer. A tutor consultation takes two ticks and needs a further three-tick attempt; a peer request also faces delays, refusal and source availability. Preferences are probabilistic rather than perfect foresight. A student may conclude that copying works because a returned homework grade rewards it, while remaining unable to solve an unaided exam. No direct laziness penalty is applied to knowledge.

At effort settings 0, .15 and .5, answer-AI exam means are {v('effort0_answer','exam_final'):.2f}, {v('answer_ai','exam_final'):.2f} and {v('effort50_answer','exam_final'):.2f}. Corresponding no-AI means are {v('effort0_no_ai','exam_final'):.2f}, {v('public_no_ai','exam_final'):.2f} and {v('effort50_no_ai','exam_final'):.2f}; tutor means are {v('effort0_tutor','exam_final'):.2f}, {v('tutor_ai','exam_final'):.2f} and {v('effort50_tutor','exam_final'):.2f}. These values test effort preference within the model rather than labeling real students as lazy.

True AI accuracy and tutor strength are used only to generate outcomes. They cannot enter student choice scores. Students estimate AI value from private grade history. They see neither item correctness nor their latent knowledge while working. Grades arrive to everyone before the next homework, without using study time or adding competence. Separately delayed unaided exams update confidence.

## Public grades and relationship closeness

In the main rule, a peer source must have a strictly higher previous homework grade. A close, moderately higher-scoring classmate can be preferred over a distant top scorer. Equal scores are ineligible, and no peer copying is available before the first homework grades return. A relaxed control allows familiar sources below one's own grade as well. This exposes the ambiguity in "lower-scoring source" instead of silently conflating a lower-ranked alternative with a source below the requester.

All classmates' returned grades are visible. Friendship ties have stronger frozen contact weights; other classmates have weaker acquaintance weights. Source selection combines closeness, known grade and privately experienced availability. Closeness weights never change and the friendship graph is never rewired. A friends-only control removes weak acquaintance contacts, while a score-only control removes the closeness preference.

Known grades are evidence about performance, not direct access to competence. In the no-AI case, {v('public_no_ai','higher_grade_source_not_higher_K'):.2f}% of requests to a higher-graded source target someone whose current latent knowledge is no higher than the requester's. With answer AI, the corresponding proportion is {v('answer_ai','higher_grade_source_not_higher_K'):.2f}%. These are classroom-averaged request-level diagnostics from hidden researcher state; students never observe that comparison. Sampling noise and previous assistance can make a higher grade an imperfect competence signal.

The motivation-only condition changes the decision objective while keeping old source selection. Public no-AI then changes the source-information/contact rules. This separates the change in motivation from the combined public-grade and relationship mechanism. The latter comparison does not separately identify every contribution of grade weighting, acquaintances and source filtering.

## AI use, practice and answer propagation

Over 20 homeworks, completed attempts average {v('public_no_ai','attempts',1):.2f} per student without AI, {v('answer_ai','attempts',1):.2f} with answer AI and {v('tutor_ai','attempts',1):.2f} with tutor AI. Students make {v('answer_ai','ai_answer_total',1):.2f} direct answer-AI consultations or {v('tutor_ai','ai_tutor_total',1):.2f} tutor consultations in the corresponding cases. Access begins at homework 2 and is voluntary, with at most one consultation per student per homework.

In the answer-AI condition, {v('answer_ai','direct_ai_answer_late'):.2f}% of late submissions use a directly obtained AI answer; another {v('answer_ai','peer_ai_origin_late'):.2f}% use an AI answer passed through a peer. Total peer-copied submissions are {v('answer_ai','peer_copied_late'):.2f}%. Thus direct AI uptake and AI-origin answer spread are different outcomes. Original AI item bits and packet identity are preserved through peer transfers.

In the tutor condition, {v('tutor_ai','tutor_followthrough'):.2f}% of received AI hints are consumed in a subsequent own attempt. Merely asking the tutor teaches nothing automatically. The resulting attempt applies the declared guidance rule; no free answer is supplied. A hint may be unused or replaced by later help.

Final within-class knowledge P90–P10 gaps are {v('public_no_ai','K_p90_p10'):.2f}, {v('answer_ai','K_p90_p10'):.2f} and {v('tutor_ai','K_p90_p10'):.2f} points for no AI, answer AI and tutor AI. These distributions should be distinguished from a difference between model-wide averages or a causal effect of an observed student's behavior.

One revealing sensitivity is near-perfect answer AI. At 100% item accuracy, late peer copying is only {v('answer_ai100','peer_copied_late'):.2f}%, while direct AI answers account for {v('answer_ai100','direct_ai_answer_late'):.2f}% of submissions. Final homework is {v('answer_ai100','homework_final'):.2f} and the unaided exam is {v('answer_ai100','exam_final'):.2f}. Looking only for copying between classmates would therefore miss much of the answer dependence. Strong AI rewards and the strict higher-grade rule's exclusion of tied sources both exist in this condition; this experiment does not separately identify their contributions to the shift.

## What exam feedback does and does not teach

Without exam feedback in the answer-AI condition, the final exam mean is {v('answer_no_exam_feedback','exam_final'):.2f}, versus {v('answer_ai','exam_final'):.2f} with feedback. The paired change when removing feedback is {ci('answer_no_exam_feedback','answer_ai','exam_final')}. Both conditions still take the same unaided exams for measurement and receive homework grades.

That interval includes zero: confidence feedback alone does not produce a clear exam-performance improvement here. Nor is the result simply persistent overconfidence: the answer-AI condition's late mean confidence bias is {v('answer_ai','confidence_bias_late'):+.2f} points, with mean absolute error {v('answer_ai','calibration_late'):.2f}. Students can have roughly calibrated estimates of their ability and still choose the method that cheaply earns homework grades.

The current learner is short-sighted: exam feedback adjusts confidence, but does not assign a causal learning cost to each earlier strategy or explicitly optimize future exam grades. Therefore, continued shortcut use after poor exams is conditional on this credit-assignment limitation. It must not be claimed as proof that real students cannot recognize or correct a mistake. A model of learning which study strategy improves exams would be a distinct extension.

## All sensitivity conditions

{alltable}
Condition names encode the changes: `80/100` are answer accuracy percentages; tutor `0/50` are hint strengths; `no_pressure` removes the extra bad-grade copying incentive; `relaxed` allows lower-scoring peer sources; `effort0/50` changes effort aversion; `H40` doubles the course length. All conditions were specified before scientific outcomes were inspected. No preferred rate was selected because it widened the gap.

## Interpretation, validation and reproducibility

The encoded mechanisms are effort costs, grade-based reinforcement, public source information, copying pressure, AI capabilities and activity-specific learning. Emergent outcomes are the activity mix, voluntary uptake, shared answer provenance, confidence trajectories and resulting grade–knowledge separation under those mechanisms. A larger gap alone is not evidence of a new scientific phenomenon or accurate real-world magnitude.

Knowledge is a single monotone scalar; rates originate in chosen trajectories, not student-data calibration. Initial traits, social weights, target grade, AI quality and behavioral coefficients are assumptions. AI errors are independent item draws here; sanctions, plagiarism detection, correlated misconceptions, forgetting and multiple concepts are omitted. Confidence intervals resample 100 whole paired classrooms 2,000 times and are pointwise, not multiplicity-adjusted. The 30 students within a classroom are not independent experimental replicates.

All 296 tests pass. Universal delayed grades, higher-source eligibility, closeness tradeoffs, no hidden AI-quality access, time accounting, copied-packet identity, AI availability for isolates, no AI before introduction, no direct learning on AI receipt and legacy core parity were checked. Every student's event gains reconstruct knowledge change within 1e-12. All {d['verified_raw_files']} raw files were hash-verified. Independent reruns of no AI, answer AI and tutor AI reproduced every raw table.

The initial E12 run failed on an AI-log storage schema mismatch. The correction changed the data writer, not the engine, parameters or outcomes. All original sources and partial files are preserved; the entire study was restarted as E12r1 before aggregate results were inspected. [Deviation record](E12-deviations.md). Earlier E9r1, E10 and E11 locked sources are intact.

- [Classroom outcomes](classroom_results.csv), [student outcomes](student_results.csv) and [trajectories](trajectories.csv).
- [Condition estimates](condition_estimates.csv), [paired effects](paired_effects.csv) and [analysis metadata](analysis.json).
- [Raw data locations and integrity hashes](dataset_manifest.json).
- [Analysis data bundle](motivation-ai-data.zip) and [source, tests, specification and lock](motivation-ai-source.zip).

Raw logs remain in the project at `runs/E12r1`. Reproduce the analysis with `python -m classroom_swarm.e12 analyze --root runs/E12r1 --output <directory>`. A new simulation requires a new empty directory, `lock`, then `run --workers 4`. Existing completed runs are verified, not silently overwritten.
'''
    (out/'motivation-ai-report.md').write_text(report,encoding='utf-8')
    shutil.copy2(REPO/'docs/experiments/E12-deviations.md',out/'E12-deviations.md')
    def inline(s):
        s=html.escape(s);s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
        s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
        return re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    blocks=[];lines=report.splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[-:| ]+\|$',lines[i]):
                    tag='th' if not rows else 'td'
                    rows.append('<tr>'+''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in lines[i].strip('|').split('|'))+'</tr>')
                i+=1
            blocks.append('<div class="table"><table>'+''.join(rows)+'</table></div>');continue
        if line.startswith('!['):
            alt,src=re.match(r'!\[([^]]*)\]\(([^)]+)\)',line).groups();blocks.append(f'<img src="{src}" alt="{html.escape(alt)}">')
        elif line.startswith('#'):
            n=len(line)-len(line.lstrip('#'));blocks.append(f'<h{n}>{inline(line[n:].strip())}</h{n}>')
        elif line:blocks.append('<p>'+inline(line)+'</p>')
        i+=1
    css='body{background:#f4f7fb;color:#20334b;font:17px/1.65 system-ui;margin:0}main{max-width:1150px;margin:35px auto;padding:45px;background:white;border-radius:14px}h1{line-height:1.2;color:#153c60}h2{margin-top:36px}img{width:100%}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border-bottom:1px solid #dce3eb}th{background:#264b6d;color:white;text-align:left}.table{overflow-x:auto}a{color:#1859a9}code{font-size:13px;overflow-wrap:anywhere}@media(max-width:700px){main{margin:0;padding:20px}}'
    (out/'motivation-ai-report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Motivation, grades and AI</title><style>'+css+'</style><main>'+''.join(blocks)+'</main></html>',encoding='utf-8')
    with zipfile.ZipFile(out/'motivation-ai-data.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in out.iterdir():
            if f.suffix in {'.csv','.json'} and f.name!='deliverable_hashes.json':z.write(f,f.name)
    bundle=list((REPO/'src/classroom_swarm').glob('*.py'))+list((REPO/'tests').glob('*.py'))
    bundle += [REPO/p for p in ['pyproject.toml','uv.lock','docs/11-v4-activity-feedback.md','docs/12-v4-learning-differentiation.md',
        'docs/13-v4-homework-feedback.md','docs/14-v4-public-grades-ai.md','docs/experiments/E12-deviations.md',
        'scripts/build_e12_report.py','runs/E12r1/lock.json','runs/E12r1/execution.json']]
    with zipfile.ZipFile(out/'motivation-ai-source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in bundle:z.write(f,f.relative_to(REPO).as_posix())
    dump(out/'deliverable_hashes.json',{f.name:digest(f) for f in out.iterdir() if f.is_file() and f.name!='deliverable_hashes.json'})
    canonical=REPO/'runs/E12r1/derived';canonical.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.is_file():shutil.copy2(f,canonical/f.name)
    for f in out.iterdir():report=report.replace(f']({f.name})',f'](../../runs/E12r1/derived/{f.name})')
    (REPO/'docs/experiments/E12-results.md').write_text(report,encoding='utf-8')
    print('Motivation/AI report, figure, data and source bundles written.')


if __name__=='__main__':main()
