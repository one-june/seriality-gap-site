"""Build the rollout-5 report tables and figures from saved results."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


ASSETS = Path(__file__).resolve().parent
GUIDANCE = ASSETS.parent
REPORT_DATA = GUIDANCE / "guidance-experiments-report" / "REPORT_DATA.json"
SCORES = ASSETS / "original_rollouts.json"

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "figure.dpi": 160,
    "savefig.dpi": 180,
    "svg.fonttype": "none",
})


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(ASSETS / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(ASSETS / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_csv(name: str, rows: list[dict]) -> None:
    with (ASSETS / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


report = json.loads(REPORT_DATA.read_text())
score_document = json.loads(SCORES.read_text())
scores = score_document["videos"]


def r5(path: str) -> float:
    return scores[path]["rollout_h5_error"]


# 1. Initial holdout matrix. Values are already computed with the repository's
# original rollout_h5_error and averaged over reverse steps 50, 100, and 200.
condition_labels = {
    "1ball-25f": "1 ball\n25 frames",
    "1ball-49f": "1 ball\n49 frames",
    "5ball-25f": "5 balls\n25 frames",
    "5ball-33f": "5 balls\n33 frames",
    "5ball-41f": "5 balls\n41 frames",
    "5ball-49f": "5 balls\n49 frames",
}
method_labels = {
    "gaussian": "Gaussian control",
    "absolute": "Absolute rollout target",
    "delta": "Physics-delta target",
    "oracle": "Exact-future oracle",
}
initial_rows = []
for condition in report["conditions"]:
    for method in method_labels:
        initial_rows.append({
            "condition": condition,
            "method": method,
            "relative_improvement_percent": report["stable_improvement_percent"][condition][method]["rollout_h5_error_mean"],
        })
write_csv("initial_matrix_original.csv", initial_rows)

fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8), gridspec_kw={"width_ratios": [1.55, 1]})
x = np.arange(len(report["conditions"]))
width = 0.25
colors = {"gaussian": "#8a94a6", "absolute": "#dc6b57", "delta": "#3d7ea6", "oracle": "#27ae60"}
for i, method in enumerate(("gaussian", "absolute", "delta")):
    vals = [report["stable_improvement_percent"][c][method]["rollout_h5_error_mean"] for c in report["conditions"]]
    axes[0].bar(x + (i - 1) * width, vals, width, label=method_labels[method], color=colors[method])
axes[0].axhline(0, color="#333333", lw=0.8)
axes[0].set_xticks(x, [condition_labels[c] for c in report["conditions"]], fontsize=8)
axes[0].set_ylabel("Original rollout-5 improvement (%)")
axes[0].set_title("Rollout-derived targets remain near diffusion")
axes[0].legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
oracle = [report["stable_improvement_percent"][c]["oracle"]["rollout_h5_error_mean"] for c in report["conditions"]]
axes[1].bar(x, oracle, color=colors["oracle"])
axes[1].axhline(0, color="#333333", lw=0.8)
axes[1].set_xticks(x, [condition_labels[c] for c in report["conditions"]], fontsize=8)
axes[1].set_ylabel("Original rollout-5 improvement (%)")
axes[1].set_title("The exact-future oracle improves every condition")
for ax in axes:
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Initial holdout matrix, mean over 50/100/200 reverse steps", y=0.99, fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "01_initial_matrix_original")


# 2. Strength sweep on four matched 5-ball, 49-frame generations.
sources = ["037", "164", "828", "871"]
scales = [0.003, 0.01, 0.03, 0.05, 0.1, 0.3]
strength_rows = []
baseline_paths = [f"guidance-experiments-report/qualitative/runs/5ball-49f/diffusion/videos/00000/{s}.mp4" for s in sources]
baseline_mean = float(np.mean([r5(p) for p in baseline_paths]))
for method in ("absolute", "delta"):
    for scale in scales:
        token = {0.003: "0p003", 0.01: "0p01", 0.03: "0p03", 0.05: "0p05", 0.1: "0p10", 0.3: "0p30"}[scale]
        values = [r5(f"guidance-experiments-report/qualitative/strength-sweep-5ball-49f/{method}-s{token}/videos/00000/{s}.mp4") for s in sources]
        strength_rows.append({"method": method, "scale": scale, "mean_original_rollout_h5": float(np.mean(values))})
write_csv("strength_sweep_original.csv", strength_rows)

fig, ax = plt.subplots(figsize=(7.2, 4.4))
for method, color, marker in [("absolute", colors["absolute"], "o"), ("delta", colors["delta"], "s")]:
    rows = [r for r in strength_rows if r["method"] == method]
    ax.plot([r["scale"] for r in rows], [r["mean_original_rollout_h5"] for r in rows], marker=marker, color=color, lw=2, label=method_labels[method])
ax.axhline(baseline_mean, color="#222222", ls="--", lw=1.4, label=f"Diffusion ({baseline_mean:.3f})")
ax.set_xscale("log")
ax.set_xticks(scales, [str(s) for s in scales])
ax.set_xlabel("Guidance strength")
ax.set_ylabel("Mean original rollout-5 error")
ax.set_title("Stronger rollout guidance does not repair the target direction", fontweight="bold")
ax.grid(alpha=0.2)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False)
fig.tight_layout()
save(fig, "02_strength_sweep_original")


# 3. Successive reference and acceptance changes, using the saved matched videos.
progress_specs = [
    ("Cleaned stitched\nendpoints", "cleaned-rollout5-baseline", "cleaned-rollout5-s0p10", ["164", "828", "037", "871"]),
    ("Continuous local\ntrajectory", "continuous-window-full/baseline", "continuous-window-full/guided", sources),
]
progress_rows = []
for label, baseline_group, guided_group, ids in progress_specs:
    for source in ids:
        if "continuous" in baseline_group:
            b = f"guidance-experiments-report/qualitative/{baseline_group}/videos/00000/{source}.mp4"
            g = f"guidance-experiments-report/qualitative/{guided_group}/videos/00000/{source}.mp4"
        else:
            shard = ids.index(source)
            b = f"guidance-experiments-report/qualitative/{baseline_group}/shard-{shard}/videos/00000/{source}.mp4"
            g = f"guidance-experiments-report/qualitative/{guided_group}/shard-{shard}/videos/00000/{source}.mp4"
        progress_rows.append({"method": label.replace("\n", " "), "case": source, "baseline": r5(b), "guided": r5(g), "guided_minus_baseline": r5(g) - r5(b)})
for seed in (0, 1):
    b = f"continuous-window-accept-case1-v1/case1-source164-baseline-seed{seed}/videos/00000/164.mp4"
    g = f"continuous-window-accept-case1-v1/case1-source164-guided-seed{seed}/videos/00000/164.mp4"
    progress_rows.append({"method": "Score-checked updates", "case": f"seed {seed}", "baseline": r5(b), "guided": r5(g), "guided_minus_baseline": r5(g) - r5(b)})
write_csv("construction_progression_original.csv", progress_rows)

progress_labels = ["Cleaned stitched\nendpoints", "Continuous local\ntrajectory", "Score-checked\nupdates"]
fig, ax = plt.subplots(figsize=(7.4, 4.5))
for i, label in enumerate(progress_labels):
    key = label.replace("\n", " ")
    rows = [r for r in progress_rows if r["method"] == key]
    jitter = np.linspace(-0.08, 0.08, len(rows))
    vals = [r["guided_minus_baseline"] for r in rows]
    ax.scatter(np.full(len(rows), i) + jitter, vals, color="#356fa3", s=42, zorder=3)
    mean = float(np.mean(vals))
    ax.plot([i - 0.20, i + 0.20], [mean, mean], color="#d35400", lw=3, zorder=4)
    mean_text = f"mean {mean:+.4f}" if abs(mean) < 0.001 else f"mean {mean:+.3f}"
    ax.text(i, mean + (0.014 if mean >= 0 else -0.014), mean_text, ha="center", va="bottom" if mean >= 0 else "top", fontsize=9)
ax.axhline(0, color="#222222", lw=1)
ax.set_xticks(range(3), progress_labels)
ax.set_ylabel("Guided − baseline original rollout-5 error")
ax.set_title("Reference fixes and score checking do not yield a stable gain", fontweight="bold")
ax.grid(axis="y", alpha=0.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "03_construction_progression_original")


# 4. Late, every-window variants on the same five generations.
late_specs = [
    ("Delta, full window", "late-all-window-local-5cases", report["late_all_window_cases"]),
    ("Delta, endpoint", "late-endpoint-local-5cases", report["late_endpoint_cases"]),
    ("Delta, full + strict validity", "late-extra-invalid-full-window-5cases", report["extra_ball_invalid_cases"]["full_window"]),
    ("Delta, endpoint + strict validity", "late-extra-invalid-endpoint-5cases", report["extra_ball_invalid_cases"]["endpoint_only"]),
    ("Direct target, full window", "late-absolute-full-window-5cases", report["absolute_physics_target_cases"]["full_window"]),
    ("Direct target, endpoint", "late-absolute-endpoint-5cases", report["absolute_physics_target_cases"]["endpoint_only"]),
]
late_rows = []
for label, group, old_data in late_specs:
    for case in range(1, 6):
        base = "late-all-window-accept-case1-v1" if group == "late-all-window-local-5cases" and case == 1 else f"{group}/case-{case}"
        old_case = next(r for r in old_data["cases"] if r["case"] == case)
        late_rows.append({
            "method": label,
            "case": case,
            "baseline_original_rollout_h5": r5(f"{base}/vanilla-diffusion.mp4"),
            "guided_original_rollout_h5": r5(f"{base}/guided-final.mp4"),
            "guided_minus_baseline": r5(f"{base}/guided-final.mp4") - r5(f"{base}/vanilla-diffusion.mp4"),
            "baseline_scorable_pairs": round(old_case["control"]["rollout_h5_scorable_fraction"] * 220),
            "guided_scorable_pairs": round(old_case["guided"]["rollout_h5_scorable_fraction"] * 220),
            "accepted_updates": old_case["accepted_updates"],
        })
write_csv("late_five_case_original.csv", late_rows)

matrix = np.array([[r["guided_minus_baseline"] for r in late_rows if r["method"] == label] for label, _, _ in late_specs])
matrix_with_mean = np.column_stack([matrix, matrix.mean(axis=1)])
limit = float(np.max(np.abs(matrix_with_mean)))
fig, ax = plt.subplots(figsize=(9.4, 5.1))
im = ax.imshow(matrix_with_mean, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
for i in range(matrix_with_mean.shape[0]):
    for j in range(matrix_with_mean.shape[1]):
        value = matrix_with_mean[i, j]
        ax.text(j, i, f"{value:+.3f}", ha="center", va="center", fontsize=9, color="white" if abs(value) > limit * 0.55 else "#222222")
ax.set_xticks(range(6), ["Case 1", "Case 2", "Case 3", "Case 4", "Case 5", "Mean"])
ax.set_yticks(range(6), [x[0] for x in late_specs])
ax.set_title("Every late-guidance variant raises mean original rollout-5 error", fontweight="bold")
cb = fig.colorbar(im, ax=ax, shrink=0.83)
cb.set_label("Guided − baseline original rollout-5 error")
fig.tight_layout()
save(fig, "04_late_five_case_original")


# 5. The separate validity tracker explains why historical acceptance and the
# original score can disagree. Each point is a five-case aggregate.
validity_rows = []
for label, _, _ in late_specs:
    rows = [r for r in late_rows if r["method"] == label]
    validity_rows.append({
        "method": label,
        "original_rollout_h5_change": float(np.mean([r["guided_minus_baseline"] for r in rows])),
        "scorable_pair_change": sum(r["guided_scorable_pairs"] - r["baseline_scorable_pairs"] for r in rows),
        "guided_scorable_pairs": sum(r["guided_scorable_pairs"] for r in rows),
        "baseline_scorable_pairs": sum(r["baseline_scorable_pairs"] for r in rows),
    })
write_csv("late_validity_vs_original.csv", validity_rows)

fig, ax = plt.subplots(figsize=(7.5, 5.0))
for i, row in enumerate(validity_rows):
    marker = "s" if row["method"].startswith("Direct") else "o"
    ax.scatter(row["scorable_pair_change"], row["original_rollout_h5_change"], s=70, marker=marker, color=plt.cm.tab10(i), zorder=3)
    ax.annotate(row["method"], (row["scorable_pair_change"], row["original_rollout_h5_change"]), xytext=(5, 4), textcoords="offset points", fontsize=8)
ax.axhline(0, color="#333333", lw=0.9)
ax.axvline(0, color="#333333", lw=0.9)
ax.set_xlabel("Change in scorable ball/frame pairs (out of 1,100)")
ax.set_ylabel("Change in mean original rollout-5 error")
ax.set_title("Better validity does not lower the original rollout-5 mean", fontweight="bold")
ax.grid(alpha=0.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "05_validity_vs_original")


# 6. Surviving videos from the focused Case 2 horizon-5 sweep.
case2_names = ["vanilla", "h5-best-visual", "h5-best-penalized"]
case2_labels = ["Vanilla", "Visual\nbalance", "Historical\nselection"]
case2_validity = [55, 204, 220]
case2_rows = []
for name, label, valid in zip(case2_names, case2_labels, case2_validity):
    path = f"guidance-experiments-report/rollout-smallest-error-results-so-far-assets/{name}.mp4"
    row = scores[path]
    case2_rows.append({"output": label.replace("\n", " "), "original_rollout_h5": row["rollout_h5_error"], "original_rollout_h5_p95": row["rollout_h5_p95"], "original_rollout_h5_max": row["rollout_h5_max"], "scorable_pairs": valid})
write_csv("case2_selected_original.csv", case2_rows)

fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.3), gridspec_kw={"width_ratios": [1.6, 1]})
vals = [r["original_rollout_h5"] for r in case2_rows]
bar_colors = ["#7f8c8d", "#2b78b8", "#d9822b"]
bars = axes[0].bar(range(3), vals, color=bar_colors)
axes[0].set_xticks(range(3), case2_labels)
axes[0].set_ylabel("Original rollout-5 error")
axes[0].set_title("Physical consistency")
axes[0].bar_label(bars, fmt="%.3f", padding=3)
axes[0].set_ylim(0, max(vals) * 1.18)
coverage = axes[1].bar(range(3), case2_validity, color=bar_colors)
axes[1].set_xticks(range(3), case2_labels)
axes[1].set_ylabel("Scorable ball/frame pairs (out of 220)")
axes[1].set_title("Separate validity tracker")
axes[1].bar_label(coverage, padding=3)
axes[1].set_ylim(0, 245)
for ax in axes:
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("Focused Case 2 sweep: the historical rankings change under the original metric", fontsize=12.5, fontweight="bold")
fig.tight_layout()
save(fig, "06_case2_selected_original")


# 7. Actual decoded frames for the three Case 2 videos.
frame_indices = [5, 16, 27, 38, 48]


def read_frames(path: Path) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(path))
    frames = []
    wanted = set(frame_indices)
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index in wanted:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        index += 1
    cap.release()
    assert len(frames) == len(frame_indices), (path, len(frames))
    return frames


fig, axes = plt.subplots(3, 5, figsize=(10.7, 6.3))
for row_index, (name, label) in enumerate(zip(case2_names, ["Vanilla", "Visual-balance selection", "Historical score selection"])):
    path = GUIDANCE / f"guidance-experiments-report/rollout-smallest-error-results-so-far-assets/{name}.mp4"
    for column, (frame_index, frame) in enumerate(zip(frame_indices, read_frames(path))):
        axes[row_index, column].imshow(frame)
        axes[row_index, column].set_xticks([])
        axes[row_index, column].set_yticks([])
        if row_index == 0:
            axes[row_index, column].set_title(f"Frame {frame_index}")
        if column == 0:
            axes[row_index, column].set_ylabel(label, rotation=0, ha="right", va="center", labelpad=8)
fig.suptitle("Saved Case 2 outputs", fontsize=13, fontweight="bold")
fig.tight_layout()
save(fig, "07_case2_video_frames")


figure_data = {
    "metric": score_document["definition"],
    "initial_matrix": initial_rows,
    "strength_sweep": strength_rows,
    "strength_sweep_diffusion_mean": baseline_mean,
    "construction_progression": progress_rows,
    "late_five_case": late_rows,
    "late_validity_vs_original": validity_rows,
    "case2_selected": case2_rows,
}
(ASSETS / "figure_data.json").write_text(json.dumps(figure_data, indent=2) + "\n")
print(json.dumps({"figures": 7, "tables": 6, "metric": "original rollout-5"}, indent=2))
