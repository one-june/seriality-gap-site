"""Score the report's saved videos with the original rollout-5.

Usage: python out/guidance/rollout5-report-assets/score_original_rollouts.py
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
    for horizon in (5,):
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
    groups = ["late-all-window-local-5cases", "late-endpoint-local-5cases",
              "late-extra-invalid-full-window-5cases", "late-extra-invalid-endpoint-5cases",
              "late-absolute-full-window-5cases", "late-absolute-endpoint-5cases"]
    for group in groups:
        paths = sorted((GUIDANCE / group).glob("case-*/run.json"))
        if group == "late-all-window-local-5cases":
            paths.insert(0, GUIDANCE / "late-all-window-accept-case1-v1/run.json")
        assert len(paths) == 5, group
        for path in paths:
            run = json.loads(path.read_text())
            assert run["guidance_config"]["horizon"] == 5
            for name in ("vanilla-diffusion.mp4", "guided-final.mp4"):
                add(path.parent / name, run["source"])
    for path in sorted((GUIDANCE / "continuous-window-accept-case1-v1").glob("*/videos/00000/164.mp4")):
        add(path, "00000/164.mp4")
    for name in ("ground-truth", "vanilla", "h5-best-penalized", "h5-best-visual"):
        add(GUIDANCE / f"guidance-experiments-report/rollout-smallest-error-results-so-far-assets/{name}.mp4", "00000/828.mp4")
    qualitative = GUIDANCE / "guidance-experiments-report/qualitative"
    for group in ("runs/5ball-49f/diffusion", "strength-sweep-5ball-49f",
                  "cleaned-rollout5-baseline", "cleaned-rollout5-s0p10", "continuous-window-full"):
        for path in sorted((qualitative / group).glob("**/videos/00000/*.mp4")):
            if path.name in {"164.mp4", "828.mp4", "037.mp4", "871.mp4"}:
                add(path, "00000/" + path.name)
    return sorted(jobs.items())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=len(os.sched_getaffinity(0)))
    args = parser.parse_args()
    jobs = collect_videos()
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs)),
                             mp_context=multiprocessing.get_context("fork")) as pool:
        results = list(pool.map(score, jobs))
    reference = json.loads((GUIDANCE / "rollout1-report-assets/original_rollouts.json").read_text())
    reference_by_hash = {v["video_sha256"]: v for v in reference["videos"].values()}
    differences = []
    for row in results:
        if row["video_sha256"] in reference_by_hash:
            expected = reference_by_hash[row["video_sha256"]]["rollout_h5_error"]
            differences.append(abs(row["rollout_h5_error"] - expected))
    assert len(differences) >= 30
    assert max(differences) < 1e-5, differences
    source_files = ["utils.py", "vid_to_sim.py", "fix.py", "run.py", "rollout.py", "diff.py"]
    data = dict(
        metrics=["rollout_h5_error"],
        definition="Difference.from_simulations(sim_out, rollout(sim_out, horizon=h)).avg_center_error((5, None)), h=5",
        tail_statistics="p95/max of Euclidean center errors over the same 220 ball/frame pairs; no historical success thresholds applied",
        tracker="Simulation.from_video with repository defaults (fix=True, mode=color, color_tolerance=32)",
        validation=dict(reference="rollout1-report-assets/original_rollouts.json (validated against original saved evaluations)", identical_video_files_compared=len(differences), maximum_absolute_difference=max(differences)),
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
