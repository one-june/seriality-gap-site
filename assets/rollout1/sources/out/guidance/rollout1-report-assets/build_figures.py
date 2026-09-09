"""Build report figures with the original rollout-1 and rollout-5 metrics."""
from __future__ import annotations
import csv, gzip, json, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

ASSETS = Path(__file__).resolve().parent
GUIDANCE = ASSETS.parent
OLD = GUIDANCE / "guidance-experiments-report"
SWEEP = GUIDANCE / "smallest-error-rollout-case2"
ARCHIVE = SWEEP / "stopped-2026-09-03"
MATCHED = GUIDANCE / "best-rollout1-matched-10samples-5steps-v1"
BLUE, GREEN, GRAY = "#2463a6", "#247c65", "#687582"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 12,
    "axes.labelcolor": "#273342", "text.color": "#273342",
    "axes.edgecolor": "#b5bec6", "grid.color": "#e0e5e9",
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "svg.fonttype": "none", "svg.hashsalt": "rollout1-original-metrics",
})

def read(path):
    return json.loads(path.read_text())

def relative(path):
    return str(path.relative_to(GUIDANCE))

def diagnostic_header(path):
    opener = gzip.open(path, "rt") if path.suffix == ".gz" else path.open()
    with opener as f:
        prefix = f.read(150000)
    q, _ = json.JSONDecoder().raw_decode(prefix.split('"quantitative":', 1)[1].lstrip())
    guide = prefix.split('"guidance":', 1)[1].split('"steps":', 1)[0]
    counters = {k: int(re.search(r'"' + k + r'":\s*(\d+)', guide)[1])
                for k in ("num_applied_updates", "num_gradient_calls", "num_model_calls")}
    return q, counters

def save(fig, name):
    for extension in ("svg", "png"):
        fig.savefig(ASSETS / f"{name}.{extension}", dpi=180, bbox_inches="tight")
    plt.close(fig)

def write_csv(name, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (ASSETS / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

original = read(ASSETS / "original_rollouts.json")

def original_metrics(video):
    return {k: v for k, v in original["videos"][relative(video)].items() if k.startswith("rollout_h")}

def report_metrics(saved, video):
    # Error values use only the original metric; validity is a separate diagnostic.
    return original_metrics(video) | {
        "scorable_ball_transitions": saved.get("rollout_h1_scored_ball_frames", saved.get("scored_ball_frames")),
        "missing_ball_frames": saved.get("missing_ball_frames"),
        "wrong_color_ball_frames": saved.get("color_changed_ball_frames", saved.get("wrong_color_ball_frames")),
        "extra_ball_frames": saved.get("extra_ball_frames"),
        "metric_video": relative(video),
    }

saved_pilot = read(OLD / "ROLLOUT1_SINGLE_SOURCE_REPORT_DATA.json")
pilot = []
for c in saved_pilot["cases"]:
    directory = GUIDANCE / "rollout1-single-source-5cases" / f"case-{c['case']}"
    pilot.append({k: c[k] for k in ("case", "source", "accepted_updates")} | {
        m: report_metrics(c[m], directory / filename)
        for m, filename in (("vanilla", "vanilla-diffusion.mp4"), ("guided", "guided-final.mp4"))})
pilot_aggregate = {f"{m}_rollout_h{h}_error": float(np.mean([c[m][f"rollout_h{h}_error"] for c in pilot]))
                   for m in ("vanilla", "guided") for h in (1, 5)}
for h in (1, 5):
    pilot_aggregate[f"improved_cases_h{h}"] = sum(c["guided"][f"rollout_h{h}_error"] < c["vanilla"][f"rollout_h{h}_error"] for c in pilot)
for m in ("vanilla", "guided"):
    pilot_aggregate[f"{m}_scorable"] = sum(c[m]["scorable_ball_transitions"] for c in pilot)
pilot_aggregate["accepted_updates"] = sum(c["accepted_updates"] for c in pilot)
write_csv("five_video_results.csv", [{k: c[k] for k in ("case", "source", "accepted_updates")} |
          {f"{m}_{k}": v for m in ("vanilla", "guided") for k, v in c[m].items()} for c in pilot])

best_video = OLD / "rollout-smallest-error-results-so-far-assets/h1-best.mp4"
best = dict(run="h1-run-29-sqrt-start0p7", **report_metrics(
    {"scored_ball_frames": 220, "missing_ball_frames": 0, "wrong_color_ball_frames": 0, "extra_ball_frames": 0}, best_video))
case2_control = original_metrics(OLD / "rollout-smallest-error-results-so-far-assets/vanilla.mp4")
revised = {m: report_metrics(saved_pilot["case2_full_trace"]["quantitative"][m],
           GUIDANCE / "rollout1-all-ball-tracker-case2-full-trace-v3" / filename)
           for m, filename in (("vanilla_diffusion", "vanilla-diffusion.mp4"), ("guided", "guided-final.mp4"))}

# Do not substitute archived error values for original metrics when videos are absent.
evaluations = []
for path in sorted(SWEEP.glob("h1-*/success-evaluation.json")) + sorted(ARCHIVE.glob("*/success-evaluation.json")):
    saved = read(path)
    config = read(path.parent / "run.json")["guidance_config"]
    video = path.parent / "guided-final.mp4"
    row = dict(run=path.parent.name, source=relative(path), original_metrics_available=relative(video) in original["videos"],
               scorable_ball_transitions=saved["scored_ball_frames"],
               missing_ball_frames=saved["missing_ball_frames"], wrong_color_ball_frames=saved["wrong_color_ball_frames"],
               extra_ball_frames=saved["extra_ball_frames"], **{"config_" + k: v for k, v in config.items()})
    if row["original_metrics_available"]:
        row.update(original_metrics(video))
        row["metric_video"] = relative(video)
    evaluations.append(row)
assert len(evaluations) == 34
archived = {r["run"]: r for r in evaluations if "stopped-2026" in r["source"]}
assert len(archived) == 21 and all(r["original_metrics_available"] for r in archived.values())
write_csv("case2_saved_evaluations.csv", evaluations)

caps = []
for cap in (48, 49, 50, 51, 75, 100, 200, 500):
    if cap == 50:
        row = dict(best, cap=50, updates=1250)
    else:
        directory = ARCHIVE / f"h1-update-cap-{cap}" if cap < 52 else SWEEP / f"h1-best-u{cap}"
        path = directory / ("diagnostics.json.gz" if cap < 52 else "diagnostics.json")
        q, counter = diagnostic_header(path)
        row = dict(cap=cap, updates=counter["num_applied_updates"], source=relative(path),
                   **report_metrics(q["guided"], directory / "guided-final.mp4"))
    caps.append(row)
write_csv("case2_update_caps.csv", caps)

def matched_row(path):
    run = read(path.parent / "run.json")
    q, counters = diagnostic_header(path)
    assert run["guidance_config"]["max_guidance_updates_per_step"] == 75
    assert run["guidance_config"]["guide_start_step"] == 25
    return dict(case=run["case"], video=run["source"], steps=run["num_inference_steps"], source=relative(path),
                **counters, vanilla=report_metrics(q["vanilla_diffusion"], path.parent / "vanilla-diffusion.mp4"),
                guided=report_metrics(q["guided"], path.parent / "guided-final.mp4"))

with ThreadPoolExecutor(max_workers=8) as pool:
    matched = sorted(pool.map(matched_row, sorted(MATCHED.glob("case-*/steps-*/diagnostics.json"))),
                     key=lambda r: (r["steps"], r["case"]))
assert len(matched) == 50
assert all(r["num_applied_updates"] == 0 for r in matched if r["steps"] < 25)
write_csv("ten_video_results.csv", [{k: v for k, v in r.items() if k not in ("vanilla", "guided")} |
          {f"{m}_{k}": v for m in ("vanilla", "guided") for k, v in r[m].items()} for r in matched])
aggregate = []
for steps in (10, 20, 50, 100, 200):
    rows = [r for r in matched if r["steps"] == steps]
    a = dict(steps=steps, samples=10, updates_min=min(r["num_applied_updates"] for r in rows),
             updates_max=max(r["num_applied_updates"] for r in rows))
    for h in (1, 5):
        for m in ("vanilla", "guided"):
            a[f"{m}_rollout_h{h}_error"] = float(np.mean([r[m][f"rollout_h{h}_error"] for r in rows]))
        a[f"improved_cases_h{h}"] = sum(r["guided"][f"rollout_h{h}_error"] < r["vanilla"][f"rollout_h{h}_error"] for r in rows)
    for m in ("vanilla", "guided"):
        a[f"{m}_scorable"] = sum(r[m]["scorable_ball_transitions"] for r in rows)
    aggregate.append(a)
write_csv("ten_video_aggregate.csv", aggregate)
source_data = dict(metric_definitions={"h1": "original rollout_h1_error", "h5": "original rollout_h5_error",
                   "scorable_ball_transitions": "separate validity count from the saved newer tracker"},
                   original_metric_source="rollout1-report-assets/original_rollouts.json",
                   best_case2=best, case2_control=case2_control, pilot_cases=pilot, pilot_aggregate=pilot_aggregate,
                   revised_tracker_case2=revised, case2_caps=caps, case2_archive=list(archived.values()),
                   ten_video_aggregate=aggregate)
(ASSETS / "figure_data.json").write_text(json.dumps(source_data, indent=2) + "\n")

def format_axes(axes, labels, xlabel):
    for ax in axes:
        ax.set_xticks(range(len(labels)), labels)
        ax.set_xlabel(xlabel)
        ax.grid(axis="y", alpha=.6)
        ax.set_axisbelow(True)

# Both original metrics and separate validity counts.
fig, axes = plt.subplots(1, 3, figsize=(15, 4.1), layout="constrained")
for i, key in enumerate(("rollout_h1_error", "rollout_h5_error", "scorable_ball_transitions")):
    for m, label, color, shift in (("vanilla", "Vanilla", GRAY, -.18), ("guided", "Score-checked guidance", BLUE, .18)):
        bars = axes[i].bar(np.arange(5) + shift, [c[m][key] for c in pilot], .36, label=label, color=color)
        axes[i].bar_label(bars, fmt="%.2f" if i < 2 else "%.0f", fontsize=8, padding=3)
    axes[i].set_ylim(0, max(c[m][key] for c in pilot for m in ("vanilla", "guided")) * 1.3)
axes[0].set(ylabel="Rollout-1 error", title="Original one-frame metric")
axes[1].set(ylabel="Rollout-5 error", title="Original five-frame metric")
axes[2].set(ylabel="Scorable ball-transitions / 220", title="Separate validity measurement", ylim=(0, 245))
axes[2].axhline(220, color=GRAY, ls="--", lw=1)
axes[0].legend(frameon=False, fontsize=8)
format_axes(axes, [str(i) for i in range(1, 6)], "Video case")
save(fig, "01_five_video_pilot_original")

fig, axes = plt.subplots(1, 3, figsize=(15, 4.1), layout="constrained")
for i, key in enumerate(("rollout_h1_error", "rollout_h5_error", "scorable_ball_transitions")):
    vals = [r[key] for r in caps]
    bars = axes[i].bar(range(len(caps)), vals, color=[GREEN if c["cap"] == 50 else BLUE for c in caps], width=.68)
    axes[i].bar_label(bars, fmt="%.3f" if i < 2 else "%.0f", fontsize=8, padding=3)
    axes[i].set_ylim(0, max(vals) * 1.2)
axes[0].set(ylabel="Rollout-1 error", title="Cap 51 improves slightly on cap 50")
axes[1].set(ylabel="Rollout-5 error", title="Caps 75–500 do not improve on 50")
axes[2].set(ylabel="Scorable ball-transitions / 220", title="Only cap 50 has complete coverage", ylim=(0, 245))
axes[2].axhline(220, color=GREEN, ls="--", lw=1)
format_axes(axes, [str(c["cap"]) for c in caps], "Allowed updates per denoising step")
save(fig, "02_update_cap_sweep_original")

groups = [
    ("Tie-breaking seed", ["0", "1", "2", "3", "4", "5", "6"],
     [best] + [archived[f"h1-selection-seed-{i}"] for i in range(1, 7)]),
    ("Last active denoising step", ["46", "47", "48", "49"],
     [archived[f"h1-guide-end-step-{i}"] for i in (46, 47, 48)] + [best]),
    ("Strength at step 49", [".05", ".10", ".15", ".18", ".195", ".20", ".205", ".210", ".22", ".25"],
     [archived["h1-final-scale-" + i] if i != "baseline" else best
      for i in ("0p05", "0p10", "0p15", "0p18", "0p195", "baseline", "0p205", "0p210", "0p22", "0p25")]),
]
fig, axes = plt.subplots(3, 1, figsize=(12, 7.4), layout="constrained")
for ax, (title, labels, rows) in zip(axes, groups):
    colors = np.tile(np.array([[[.96, .97, .98]]]), (3, len(rows), 1))
    for j, row in enumerate(rows):
        if row is best:
            colors[:, j] = [.82, .9, .97]
    ax.imshow(colors, aspect="auto")
    for i, key in enumerate(("rollout_h1_error", "rollout_h5_error", "scorable_ball_transitions")):
        for j, row in enumerate(rows):
            ax.text(j, i, str(int(row[key])) if i == 2 else f"{row[key]:.3f}",
                    ha="center", va="center", fontsize=10)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(3), ["Rollout-1 error", "Rollout-5 error", "Scorable / 220"])
    ax.set_title(title, loc="left", pad=8)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
fig.suptitle("Nearby settings under the original rollout metrics\nBlue columns = historically selected reference configuration", fontsize=13)
save(fig, "03_final_batch_original")

active = [a for a in aggregate if a["steps"] >= 50]
fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), layout="constrained")
for i, suffix in enumerate(("rollout_h1_error", "rollout_h5_error", "scorable")):
    for m, label, color, shift in (("vanilla", "Matched vanilla control", GRAY, -.18), ("guided", "Guidance (cap 75)", BLUE, .18)):
        values = [a[f"{m}_{suffix}"] * (100 / 2200 if i == 2 else 1) for a in active]
        bars = axes[i].bar(np.arange(3) + shift, values, .36, color=color, label=label)
        axes[i].bar_label(bars, fmt="%.3f" if i < 2 else "%.1f%%", fontsize=9, padding=3)
    axes[i].set_ylim(0, max(p.get_height() for p in axes[i].patches) * 1.3)
axes[0].set(ylabel="Mean rollout-1 error over 10 videos", title="One-frame error worsened")
axes[1].set(ylabel="Mean rollout-5 error over 10 videos", title="Five-frame error worsened")
axes[2].set(ylabel="Scorable ball-transitions (%)", title="Guided outputs lost validity", ylim=(0, 110))
axes[0].legend(frameon=False, fontsize=8)
format_axes(axes, [str(a["steps"]) for a in active], "Total denoising steps")
save(fig, "04_ten_video_aggregate_original")

lookup = {(r["case"], r["steps"]): r for r in matched}
steps = (50, 100, 200)
fig, axes = plt.subplots(1, 3, figsize=(15, 6.8), layout="constrained")
for i, horizon in enumerate((1, 5)):
    key = f"rollout_h{horizon}_error"
    delta = np.array([[lookup[c, s]["guided"][key] - lookup[c, s]["vanilla"][key]
                       for s in steps] for c in range(1, 11)])
    limit = float(np.max(np.abs(delta)))
    im = axes[i].imshow(delta, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), aspect="auto")
    for r in range(10):
        for c in range(3):
            axes[i].text(c, r, f"{delta[r,c]:+.3f}", ha="center", va="center",
                         color="white" if abs(delta[r,c]) > .6 * limit else "#17212b")
    axes[i].set_title(f"Guided − vanilla rollout-{horizon}\nPositive = worse with guidance")
    fig.colorbar(im, ax=axes[i], fraction=.035, pad=.025, label="Error difference")
coverage = np.array([[lookup[c, s]["guided"]["scorable_ball_transitions"] for s in steps] for c in range(1, 11)])
axes[2].imshow(coverage, cmap="Blues", vmin=0, vmax=220, aspect="auto")
for r in range(10):
    for c in range(3):
        axes[2].text(c, r, str(coverage[r,c]), ha="center", va="center",
                     color="white" if coverage[r,c] > 125 else "#17212b")
axes[2].set_title("Guided scorable transitions\nOut of 220 per video")
for ax in axes:
    ax.set_xticks(range(3), steps)
    ax.set_yticks(range(10), [f"Case {c}" for c in range(1, 11)])
    ax.set_xlabel("Total denoising steps")
    ax.tick_params(length=0)
save(fig, "05_ten_video_cases_original")

# 6. Unaltered decoded frames from the saved experiment videos.
video_root = OLD / "rollout-smallest-error-results-so-far-assets"
videos = [("Ground truth", video_root / "ground-truth.mp4"),
          ("Case 2 sweep: vanilla", video_root / "vanilla.mp4"),
          ("Case 2 sweep: cap 50", video_root / "h1-best.mp4"),
          ("Case 2 sweep: cap 500", video_root / "h1-u500.mp4"),
          ("Follow-up: vanilla, 50 steps", MATCHED / "case-2/steps-50/vanilla-diffusion.mp4"),
          ("Follow-up: cap 75, 50 steps", MATCHED / "case-2/steps-50/guided-final.mp4")]
frames = (5, 16, 27, 38, 48)
fig, axes = plt.subplots(len(videos), len(frames), figsize=(10, 11.7), layout="constrained")
for i, (label, path) in enumerate(videos):
    video = cv2.VideoCapture(str(path))
    assert video.isOpened(), path
    assert int(video.get(cv2.CAP_PROP_FRAME_COUNT)) == 49, path
    for j, frame in enumerate(frames):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, pixels = video.read()
        assert ok, (path, frame)
        axes[i, j].imshow(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
        axes[i, j].set_xticks([])
        axes[i, j].set_yticks([])
        for spine in axes[i, j].spines.values(): spine.set_visible(False)
        if i == 0: axes[i, j].set_title(f"Frame {frame}")
        if j == 0: axes[i, j].set_ylabel(label, fontsize=9, rotation=0, ha="right", va="center", labelpad=12)
    video.release()
save(fig, "06_case2_video_frames")

print(json.dumps({"pilot": pilot_aggregate, "follow_up": aggregate}, indent=2))
