"""Score the report's saved videos with the original rollout-1 and rollout-5.

Usage: python out/guidance/rollout1-report-assets/score_original_rollouts.py
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

ASSETS = Path(__file__).resolve().parent
GUIDANCE = ASSETS.parent
ROOT = GUIDANCE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cv2
import numpy as np
import torch
from sshv2.simulation.diff import Difference
from sshv2.simulation.rollout import rollout
from sshv2.simulation.utils import InitialCondition, Simulation

torch.set_num_threads(1)
cv2.setNumThreads(1)


def score(payload):
    video_text, source = payload
    video = GUIDANCE / video_text
    simulation_path = (ROOT / "data/bounce/eval_49f_5n_0c" / source).with_suffix(".npz")
    # Read the same initial conditions and task metadata as Simulation.from_file,
    # without loading the unrelated pickled event arrays in the dataset archive.
    with np.load(simulation_path, allow_pickle=False) as data:
        centers, velocities = data["centers"][0], data["velocities"][0]
        conditions = [InitialCondition(
            radius=float(radius), color=tuple(int(c) for c in color),
            position=tuple(float(v) for v in position),
            velocity=tuple(float(v) for v in velocity),
        ) for radius, color, position, velocity in zip(
            data["index_to_radius"], data["index_to_color"], centers, velocities)]
        world_size = tuple(float(v) for v in data["world_size"])
        fps = float(data["fps"][0])
        radii_delta = float(data["radii_delta"][0])
    generated = Simulation.from_video(
        video, conditions, world_size=world_size, fps=fps, clipped=True,
        radii_delta=radii_delta,
    )
    assert len(generated) == 49, video
    metrics = {}
    for horizon in (1, 5):
        difference = Difference.from_simulations(generated, rollout(generated, horizon=horizon))
        value = difference.avg_center_error((5, None))
        assert np.isfinite(value), (video, horizon, value)
        errors = np.linalg.norm(difference.centers_error[5:], axis=-1)
        metrics.update({f"rollout_h{horizon}_error": value,
                        f"rollout_h{horizon}_p95": float(np.percentile(errors, 95)),
                        f"rollout_h{horizon}_max": float(errors.max())})
    return dict(video=video_text, source_video=source,
                **metrics, observed_frames=5, frames=49,
                video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                simulation_metadata=str(simulation_path.relative_to(ROOT)))


def collect_videos():
    jobs = {}
    def add(path, source):
        assert path.is_file(), path
        jobs[str(path.relative_to(GUIDANCE))] = source
    for p in sorted((GUIDANCE / "best-rollout1-matched-10samples-5steps-v1").glob("case-*/steps-*/run.json")):
        source = json.loads(p.read_text())["source"]
        for video in ("vanilla-diffusion.mp4", "guided-final.mp4"):
            add(p.parent / video, source)
    for p in sorted((GUIDANCE / "rollout1-single-source-5cases").glob("case-*/run.json")):
        source = json.loads(p.read_text())["source"]
        for video in ("vanilla-diffusion.mp4", "guided-final.mp4"):
            add(p.parent / video, source)
    for video in ("vanilla-diffusion.mp4", "guided-final.mp4"):
        add(GUIDANCE / "rollout1-all-ball-tracker-case2-full-trace-v3" / video, "00000/828.mp4")
    add(GUIDANCE / "guidance-experiments-report/rollout-smallest-error-results-so-far-assets/h1-best.mp4", "00000/828.mp4")
    for name in ("ground-truth", "vanilla"):
        add(GUIDANCE / f"guidance-experiments-report/rollout-smallest-error-results-so-far-assets/{name}.mp4", "00000/828.mp4")
    for cap in (75, 100, 200, 500):
        add(GUIDANCE / f"smallest-error-rollout-case2/h1-best-u{cap}/guided-final.mp4", "00000/828.mp4")
    for path in sorted((GUIDANCE / "smallest-error-rollout-case2/stopped-2026-09-03").glob("h1-*/guided-final.mp4")):
        add(path, "00000/828.mp4")
    return sorted(jobs.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=len(os.sched_getaffinity(0)))
    args = parser.parse_args()
    jobs = collect_videos()
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs)),
                             mp_context=multiprocessing.get_context("fork")) as pool:
        results = list(pool.map(score, jobs))
    reference = json.loads((GUIDANCE / "guidance-experiments-report/REPORT_DATA.json").read_text())["ar_bidi_qualitative"]["cases"]
    differences = {1: [], 5: []}
    for row in results:
        path = Path(row["video"])
        if path.parts[0] == "best-rollout1-matched-10samples-5steps-v1" and path.name == "vanilla-diffusion.mp4":
            case = path.parts[1].split("-")[1]
            steps = path.parts[2].split("-")[1]
            for horizon in (1, 5):
                key = f"rollout_h{horizon}_error"
                expected = reference[case]["steps"][steps]["bidirectional"]["metrics"][key]
                differences[horizon].append(abs(row[key] - expected))
    assert all(len(v) == 50 for v in differences.values())
    # The stored baseline evaluations and NPZ task metadata differ at floating
    # point precision. Require agreement well below the report's four decimals.
    assert max(max(v) for v in differences.values()) < 1e-5, differences
    source_files = ["utils.py", "vid_to_sim.py", "fix.py", "run.py", "rollout.py", "diff.py"]
    data = dict(
        metrics=["rollout_h1_error", "rollout_h5_error"],
        definition="Difference.from_simulations(sim_out, rollout(sim_out, horizon=h)).avg_center_error((5, None)), h in (1, 5)",
        tail_statistics="p95/max of Euclidean center errors over the same 220 ball/frame pairs; no historical success thresholds applied",
        tracker="Simulation.from_video with repository defaults (fix=True, mode=color, color_tolerance=32)",
        validation={f"rollout_h{h}": dict(saved_baselines_compared=50, maximum_absolute_difference=max(v)) for h, v in differences.items()},
        implementation_sha256={name: hashlib.sha256((ROOT / "src/sshv2/simulation" / name).read_bytes()).hexdigest() for name in source_files},
        videos={row["video"]: row for row in results},
    )
    (ASSETS / "original_rollouts.json").write_text(json.dumps(data, indent=2) + "\n")
    with (ASSETS / "original_rollouts.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps(dict(videos_scored=len(results), validation=data["validation"]), indent=2))


if __name__ == "__main__":
    main()
