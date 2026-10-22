"""Build user-facing E9 report from the completed locked analysis."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

from classroom_swarm.e9 import REPO, digest, dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    data = json.loads((out / "analysis.json").read_text())
    mechs = json.loads((out / "mechanism_checks.json").read_text())
    e = {(r["condition"], r["metric"]): r for r in data["estimates"]}
    m = {(r["condition"], r["metric"]): r for r in mechs["estimates"]}
    effects = {(r["condition"], r["reference"], r["metric"]): r for r in data["effects"]}
    def val(name, metric, places=2):
        x = e[(name, metric)]["mean"]
        return "not applicable" if x is None else f"{100*x:.{places}f}"
    def ci(a, b, metric):
        r = effects[(a, b, metric)]
        return f"{100*r['mean']:+.3f} points [95% CI {100*r['low']:+.3f}, {100*r['high']:+.3f}]"
    labels = {"v3_reference": "V3 historical reference", "v41": "V4.1: activities/time",
              "v42_no_feedback": "V4.2: self-assessment only", "v42_recalibrate": "V4.2: exam recalibration",
              "constructive": "Constructive exam response", "withdrawal": "Withdrawal-capable response"}
    table = "| Model | Final knowledge /100 | Final unaided exam /100 | Late homework /100 | Answer-backed submissions | Self-assessment error /100 |\n|---|---:|---:|---:|---:|---:|\n"
    for name, label in labels.items():
        table += f"| {label} | {val(name,'K_final')} | {val(name,'exam_final')} | {val(name,'grade_late')} | {val(name,'copy_late')}% | {val(name,'calibration_late')} |\n"
    alltable = "| Condition | Final knowledge /100 | Unaided exam /100 | Answer-backed % | Incomplete % |\n|---|---:|---:|---:|---:|\n"
    for name in dict.fromkeys(r["condition"] for r in data["estimates"]):
        alltable += f"| {name} | {val(name,'K_final')} | {val(name,'exam_final')} | {val(name,'copy_late')} | {val(name,'incomplete_late',3)} |\n"
    uptake = m[("v42_recalibrate", "hint_consumed_share")]
    report = f"""# V4.1/V4.2 results: adaptation without a learning breakthrough

24 September 2026 · E9r1 · 2,600 simulations · 26 conditions · 100 paired classrooms per condition

**Implemented and tested. Students now change activities during homework, share limited time, and respond to delayed assessments. The clearest result is behavioral substitution: less answer copying and better self-assessment do not automatically produce more knowledge.** No large withdrawal cascade, tipping point or new universal law was established.

## What was implemented

V4.1 permits attempts, requests for explanations or answers, checking, waiting and submission. Human help requires consent and time; a delivered explanation does not automatically generate learning. V4.2 adds private self-assessment and delayed exam feedback, with recalibration-only, constructive and withdrawal-capable response rules. The graph stays fixed. There are no assigned cheater/helper types, AI agents, forgetting or changing friendships in this experiment.

V1–V3 and E8 engines were preserved. The historical V3 path is tested for exact delegation. **245 tests pass**, including timing, non-overlap, packet identity, local information, feedback delays and raw-log reconstruction. All 2,600 final runs passed integrity checks. Analysis rehashed **2,200 raw/manifest files**, and an independent scientific rerun reproduced every raw table exactly.

An initial run found a one-ULP roundoff error in inactive knowledge. It was corrected without changing parameters, and every condition was rerun under a new source lock. The first logs remain at runs/E9; results here use runs/E9r1 only. The deviation is documented.

## Main results

{table}

Knowledge is a latent probability scaled to 100, not an observed percentage of students who mastered a curriculum. Late means the final five homeworks. Answer-backed means the final submitted packet came from answer transfer, even if the student also attempted or checked. It is not the fraction of students assigned a copying identity. Self-assessment error is mean absolute C minus K, using the absolute value for each student. V3's confidence variable has a different meaning, so its error is not compared.

The V3 row is a descriptive reference, not an isolated causal estimate: V4 changes the activity menu, time structure and learning opportunities together. V3's larger grade–exam gap cannot be credited to one V4 mechanism.

![Trajectories of knowledge, behavior and self-assessment](v4-trajectories.png)

### 1. Behavior reorganized while knowledge stayed almost unchanged

V4.1 to V4.2 recalibration reduced answer-backed submissions from {val('v41','copy_late')}% to {val('v42_recalibrate','copy_late')}%. The paired difference was {ci('v42_recalibrate','v41','copy_late')}. Final knowledge changed by {ci('v42_recalibrate','v41','K_final')}.

Raw-event decomposition explains the cancellation. Compared with V4.1, V4.2 gained approximately 0.28 additional knowledge points through attempts, lost 0.26 points of checking-related learning, and lost 0.03 points of learning while explaining to others. The net difference was approximately zero. Students reallocated activity; they did not simply add more learning when they copied less.

The large improvement in calibration is partly expected by construction: V4.1 freezes self-assessment at its initial value. The more informative exam-only comparison is recalibration versus self-assessment without exam feedback: calibration error changed by {ci('v42_recalibrate','v42_no_feedback','calibration_late')}, copying by {ci('v42_recalibrate','v42_no_feedback','copy_late')}, and knowledge by {ci('v42_recalibrate','v42_no_feedback','K_final')}.

At 40 homeworks, V4.2 still copied less than its matched V4.1 control, but had {ci('H40_v42','H40_v41','K_final')} less knowledge. The decomposition again shows extra attempt learning offset by less checking and explaining. This is a small model-dependent tradeoff, not evidence that real assessment feedback harms learning.

### 2. Receiving help did not ensure using it

Only **{100*uptake['mean']:.1f}%** of delivered hints were consumed in a subsequent completed guided attempt before the homework ended (classroom-mean 95% CI {100*uptake['low']:.1f}–{100*uptake['high']:.1f}%). Some students instead checked or submitted existing work, waited, sought other help, or ran out of time. This result comes from an explicitly exploratory analysis of actual receipt and attempt events; it is not inferred merely from requesting a hint.

Removing explanation requests increased answer-backed submissions by {ci('no_hint','v42_recalibrate','copy_late')}, but changed final knowledge by only {ci('no_hint','v42_recalibrate','K_final')}. More independent attempts and checking offset the missing explanation activity under these rules.

This **help-utilization bottleneck** is a useful new pattern expressed by V4: delivery, engagement and learning are different events. Its magnitude is sensitive to the model's scheduling and one-shot activity choices. It does not show that real peer explanation is ineffective.

### 3. Help was concentrated, but stable helper identities were weak

In the recalibration condition, the most-used 20% of students supplied {val('v42_recalibrate','source_top20')}% of successful late help. Yet degree-adjusted early/late helper persistence was only {e[('v42_recalibrate','source_persistence')]['mean']:.3f} (95% CI {e[('v42_recalibrate','source_persistence')]['low']:.3f}–{e[('v42_recalibrate','source_persistence')]['high']:.3f}).

Freezing access beliefs reduced this persistence by {effects[('frozen_access','v42_recalibrate','source_persistence')]['mean']:.3f}, while barely changing copying or knowledge. Thus private experience modestly stabilizes helper activity in this model, without determining the class-wide copying rate.

These are descriptive helper statistics, not the stricter V3 root-source test. Unequal traffic can arise from finite event counts and unequal opportunities; this experiment does not establish strong source identities independent of all traits and opportunities. “Temporary concentration” is more defensible than “permanent brokers emerged.”

![Help success, concentration and descriptive persistence](v4-help-network.png)

### 4. Time and checking dominated the tested knowledge changes

Relative to recalibration, the short deadline changed final knowledge by {ci('deadline8','v42_recalibrate','K_final')}; the long deadline changed it by {ci('deadline16','v42_recalibrate','K_final')}. Short deadlines also sharply reduced explanation requests. They did not produce more copied submissions here: less time restricts opportunities to obtain help as well as opportunities to practice.

Removing checking changed knowledge by {ci('no_check','v42_recalibrate','K_final')}, even though students attempted more. This is partly a direct consequence of the model: checking provides reliable correctness information and an explicit practice increment. The emergent part is the compensating activity allocation, which did not fully replace that loss. This condition removes checking information, time use and practice together; it cannot isolate their individual contributions.

Removing the helper's time cost increased knowledge by only {ci('helper_time_free','v42_recalibrate','K_final')}. Limited time matters, but the tested helper burden did not generate a major congestion crisis. The control is deliberately unrealistic: helpers can work and help concurrently.

![Paired counterfactual effects](v4-counterfactuals.png)

### 5. The withdrawal-capable rule did not generate a withdrawal regime

About {100*m[('withdrawal','positive_surprise')]['mean']:.1f}% of released assessments in that condition exceeded students' prior predictions. Average controllability rose from 0.50 to {e[('withdrawal','control_late')]['mean']:.3f}. Most students were underconfident as competence improved, so the same rule that permits discouragement also permitted recovery.

Constructive and withdrawal-capable responses changed final knowledge by only {ci('constructive','v42_recalibrate','K_final')} and {ci('withdrawal','v42_recalibrate','K_final')}, respectively. We should not tune these coefficients until a dramatic collapse appears. These scenarios simply did not create the repeated unexpected failures needed for that aggregate pattern.

## How strong are the findings?

The five preregistered primary contrasts were assessed on five primary outcomes. All 25 pointwise intervals remained within their declared practical-effect boundaries: 1 point of knowledge, 3 points for exam/behavior and 2 points for calibration. This means the primary design found **small effects**, even where a pointwise interval excluded zero. Larger changes came from additional sensitivity conditions, particularly deadline and checking changes.

Initial benefit expectations remain important: answer-backed submissions ranged from {val('prior25','copy_late')}% with a .25 prior to {val('prior75','copy_late')}% with a .75 prior. Argmax choice produced {val('argmax_v42','copy_late')}% versus {val('v42_recalibrate','copy_late')}% with the baseline stochastic rule. There is no single empirically established copying forecast.

V4.2's late mixed-activity share was {val('v42_recalibrate','mixed_late')}%. This verifies that the new activity system is being used; the mere ability to mix activities was designed in and is not itself a discovery. Incompletion was almost absent, which also limits conclusions about disengagement or deadline failure. Availability of dynamic rules does not guarantee meaningful stress or instability.

## What emergence can be claimed?

The best-supported new system-level observation is **compensation between learning activities**: changes in answer use and self-assessment can be absorbed by changes in attempts, checking and helping, leaving overall competence nearly unchanged. The raw-event decomposition verifies the cancellation.

A second useful observation is **delivered help without follow-through**. Making explanation available is insufficient when participation competes with other activities and time. A third is **concentrated but weakly persistent help traffic**, with modest stabilization from private source learning.

These are conditional patterns within this new model, not claims of uniqueness across the scientific literature. We found no evidence establishing bistability, hysteresis, phase transitions, large withdrawal cascades or strong permanent broker roles. No numerical outcome is calibrated to a real school.

## Assumptions that most limit interpretation

- Fixed standard-difficulty items, one latent skill, monotone learning and no forgetting. There is no demanding new-topic shock to generate persistent setbacks.
- Checking reveals the actual packet grade using an assumed reliable rubric and also grants practice. Real self-checking may be fallible; this assumption deserves its own future experiment.
- Initial self-assessment equals initial latent knowledge, then V4.1 holds it fixed. Much of the V4.1 calibration gap is a designed benchmark effect.
- Choices are short-horizon scores; explanations are numerical scaffolds, not simulated dialogue. Grade benefits use coarse episode-level credit assignment.
- Removing an action changes both opportunities and the feasible choice set. Those contrasts do not identify a single psychological cause.
- Most deadlines still allow at least one packet, and automatic deadline submission makes noncompletion uncommon.
- Feedback response rules are hypotheses. Their immediate direction is encoded; their aggregate magnitude and interactions are the outcomes.
- Pointwise 95% intervals describe Monte Carlo uncertainty across independent classrooms, not real-student uncertainty or familywise-confirmed discoveries. Supplemental gain decomposition and hint uptake were exploratory after primary outcome inspection.

## Full condition table

{alltable}

## Data and reproduction

- [Classroom results](classroom_results.csv): one row per simulation, all available outcomes.
- [Trajectories](classroom_trajectories.csv): one row per simulation/homework.
- [Condition estimates](condition_estimates.csv): means, SDs, estimable classroom counts and intervals.
- [Paired effects](paired_effects.csv): matched classroom differences, including null results.
- [Exploratory mechanism data](mechanism_classrooms.csv): learning decomposition and actual hint consumption.
- [Analysis metadata](analysis.json) and [mechanism checks](mechanism_checks.json).
- [Source and reproducibility bundle](V4-source-and-reproducibility.zip): implementation, tests, specification, preregistration, deviation record and source lock.

Complete raw logs remain in `D:\\3D Project\\AI Student classroom Socio graph multiagent simulation\\runs\\E9r1` (approximately 816.5 MiB before adding derived outputs). The delivered tables are derived from these logs. The raw dataset is not duplicated inside the source bundle. [Dataset location and integrity manifest](dataset_manifest.json) records its location and hashes.

Within the project environment, reproduce analysis with `python -m classroom_swarm.e9 analyze --root runs/E9r1 --output <directory>`. Re-running `run --root runs/E9r1` verifies completed shards; to conduct a new complete run, lock a new empty output directory first. Do not edit the locked model to improve the observed story.

The recommended next scientific step is to challenge the checking/learning and difficulty assumptions, not immediately add more psychological states. Keep this result as a transparent baseline, including its small effects and absent crises.
"""
    (out / "V4-results-report.md").write_text(report, encoding="utf-8")
    # Small renderer for the report's deliberately simple Markdown subset; no extra dependencies.
    def inline(text):
        escaped = html.escape(text)
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        return escaped
    blocks = []
    lines = report.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-:| ]+\|$", lines[i]):
                    cells = lines[i].strip("|").split("|")
                    tag = "th" if not rows else "td"
                    rows.append("<tr>" + "".join(f"<{tag}>{inline(c.strip())}</{tag}>" for c in cells) + "</tr>")
                i += 1
            blocks.append('<div class="table"><table>' + "".join(rows) + "</table></div>")
            continue
        if line.startswith("!["):
            alt, src = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line).groups()
            blocks.append(f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}"></figure>')
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line.startswith("- "):
            blocks.append('<p class="bullet">• ' + inline(line[2:]) + "</p>")
        elif line:
            blocks.append("<p>" + inline(line) + "</p>")
        i += 1
    css = """body{margin:0;background:#f4f7fb;color:#17243a;font:17px/1.65 system-ui,sans-serif}
main{max-width:1140px;margin:40px auto;background:white;padding:50px 60px;border-radius:16px}
h1{font-size:38px;line-height:1.2;max-width:850px;color:#122d57}h2{margin-top:44px;font-size:25px;color:#163f70}
h3{margin-top:30px;font-size:21px}a{color:#1859b7}p{max-width:1000px}.table{overflow-x:auto;margin:24px 0}
table{border-collapse:collapse;width:100%;font-size:14px}th{background:#163f70;color:white;text-align:left}
th,td{padding:10px 12px;border-bottom:1px solid #dce4ef}tr:nth-child(odd) td{background:#f5f8fc}
figure{margin:28px -20px}img{width:100%;height:auto}code{font-size:13px;background:#eef2f8;overflow-wrap:anywhere}
.bullet{margin:7px 0}@media(max-width:750px){main{padding:22px;margin:0}h1{font-size:29px}figure{margin:20px 0}}
@media print{main{padding:0;margin:0}figure,table{break-inside:avoid}body{font-size:11px;background:white}}
"""
    (out / "V4-results-report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V4.1/V4.2 results</title><style>' + css + '</style><main>' + "\n".join(blocks) + "</main></html>", encoding="utf-8")
    raw = REPO / "runs" / "E9r1"
    raw_hashes = {}
    for complete in sorted((raw / "raw").glob("*/complete.json")):
        record = json.loads(complete.read_text())
        raw_hashes.update({str(complete.parent / name): value for name, value in record["hashes"].items()})
    dump(out / "dataset_manifest.json", dict(raw_root=str(raw), raw_hashes=raw_hashes,
        lock_sha256=digest(raw / "lock.json"), files_verified=data["verified_files"],
        records="2600 simulations; 100 independent paired classrooms; 26 conditions"))
    bundle_files = list((REPO / "src" / "classroom_swarm").glob("*.py")) + list((REPO / "tests").glob("*.py"))
    bundle_files += [REPO / x for x in ("pyproject.toml", "uv.lock", "docs/11-v4-activity-feedback.md",
        "docs/experiments/E9-preregistration.md", "docs/experiments/E9-deviations.md",
        "scripts/analyze_e9_mechanisms.py", "scripts/build_e9_report.py")]
    bundle_files += [raw / "lock.json", raw / "execution.json"]
    with zipfile.ZipFile(out / "V4-source-and-reproducibility.zip", "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file in bundle_files:
            z.write(file, file.relative_to(REPO).as_posix())
    canonical = raw / "derived"
    canonical.mkdir(exist_ok=True)
    for file in out.iterdir():
        if file.is_file():
            shutil.copy2(file, canonical / file.name)
    repo_report = report
    for filename in [f.name for f in out.iterdir() if f.is_file()]:
        repo_report = repo_report.replace(f"]({filename})", f"](../../runs/E9r1/derived/{filename})")
    (REPO / "docs" / "experiments" / "E9-results.md").write_text(repo_report, encoding="utf-8")
    dump(out / "deliverable_hashes.json", {f.name: digest(f) for f in out.iterdir() if f.is_file() and f.name != "deliverable_hashes.json"})
    print("Report, source bundle, dataset manifest and canonical derived copies written.")


if __name__ == "__main__":
    main()
