#!/usr/bin/env python3
"""Run matched best-rollout-1 generations for the report's ten examples."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/guidance/best-rollout1-matched-10samples-5steps-v1"
BASELINE = ROOT / "out/guidance/missing-ball-aware-rollout5-5ball49f-d-oracle-v1/d/5ball-49f/holdout"
LABELS = ROOT / "data/bounce/eval_49f_5n_0c_seriality_guidance/holdout.csv"
DATASET = ROOT / "data/bounce/eval_49f_5n_0c"
GUIDANCE = ROOT / "configs/guidance/smallest_error_rollout_h1_best_u75.yaml"
SOURCES = (
    "00000/164.mp4", "00000/828.mp4", "00000/037.mp4", "00000/871.mp4",
    "00000/066.mp4", "00000/704.mp4", "00000/967.mp4", "00001/016.mp4",
    "00000/927.mp4", "00000/221.mp4",
)
STEPS = (10, 20, 50, 100, 200)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--gpus", nargs="+", default=["0", "1", "2", "3"])
    parser.add_argument("--workers-per-gpu", type=int, default=2)
    parser.add_argument("--only", help="Run one case and step, formatted CASE:STEP")
    parser.add_argument("--skip-complete", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def baseline_details(source: str, steps: int, global_index: int) -> tuple[Path, int, int]:
    matches = sorted(BASELINE.glob(
        f"holdout-d-steps{steps}-seed0-shard*of*/videos/{source}"
    ))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one baseline for {source} at {steps} steps; found {len(matches)}")
    video = matches[0]
    run_dir = video.parents[2]
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    total = sum(1 for _ in csv.DictReader(LABELS.open(encoding="utf-8")))
    shard = int(run["shard_index"])
    num_shards = int(run["num_shards"])
    start = total * shard // num_shards
    stop = total * (shard + 1) // num_shards
    position = global_index - start
    if not 0 <= position < stop - start:
        raise RuntimeError(f"{source} is outside its reported shard")
    if int(run["batch_size"]) < stop - start:
        raise RuntimeError("This launcher assumes each baseline shard contains one batch")
    return video, stop - start, position


def prepare_job(case: int, steps: int, out_dir: Path, indices: dict[str, int]) -> dict:
    source = SOURCES[case - 1]
    vanilla, replay_batch_size, replay_position = baseline_details(
        source, steps, indices[source]
    )
    job_dir = out_dir / f"case-{case}" / f"steps-{steps}"
    control_dir = out_dir / "controls" / f"case-{case}" / f"steps-{steps}"
    control_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DATASET / source, control_dir / "ground-truth.mp4")
    shutil.copy2(vanilla, control_dir / "vanilla-diffusion.mp4")
    (control_dir / "run.json").write_text(json.dumps({
        "source": source,
        "seed": 0,
        "num_inference_steps": steps,
        "baseline_video": str(vanilla),
        "replay_noise_batch_size": replay_batch_size,
        "replay_noise_position": replay_position,
    }, indent=2) + "\n", encoding="utf-8")
    return {
        "case": case,
        "steps": steps,
        "source": source,
        "out_dir": job_dir,
        "control_dir": control_dir,
        "replay_batch_size": replay_batch_size,
        "replay_position": replay_position,
    }


def run_job(job: dict, gpu: str, dry_run: bool, skip_complete: bool) -> str:
    out_dir = job["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    if skip_complete and (out_dir / "diagnostics.json").exists():
        return f"case {job['case']}, steps {job['steps']}: already complete"
    command = [
        sys.executable, str(ROOT / "scripts/sshv2/run_rollout1_single_source_case.py"),
        "--source", job["source"], "--case", str(job["case"]),
        "--num-inference-steps", str(job["steps"]),
        "--out-dir", str(out_dir), "--control-dir", str(job["control_dir"]),
        "--guidance-config", str(GUIDANCE),
        "--replay-noise-batch-size", str(job["replay_batch_size"]),
        "--replay-noise-position", str(job["replay_position"]),
    ]
    if dry_run:
        return f"GPU {gpu}: {' '.join(command)}"
    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = gpu
    paths = [str(ROOT / "src"), str(ROOT / "lib/diffsynth")]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["OMP_NUM_THREADS"] = "8"
    with (out_dir / "run.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, cwd=ROOT, env=environment, stdout=log,
            stderr=subprocess.STDOUT, check=False,
        )
    if result.returncode:
        raise RuntimeError(f"case {job['case']}, steps {job['steps']} failed; see {out_dir / 'run.log'}")
    return f"case {job['case']}, steps {job['steps']}: GPU {gpu} complete"


def main() -> None:
    args = parse_args()
    if not args.gpus:
        raise ValueError("At least one GPU is required")
    if args.workers_per_gpu < 1:
        raise ValueError("workers-per-gpu must be positive")
    rows = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    indices = {row["video"]: index for index, row in enumerate(rows)}
    requested = [(case, steps) for case in range(1, 11) for steps in STEPS]
    if args.only:
        case_text, step_text = args.only.split(":", 1)
        requested = [(int(case_text), int(step_text))]
    jobs = [prepare_job(case, steps, args.out_dir, indices) for case, steps in requested]
    # Longest-processing-time scheduling keeps the four GPUs balanced.
    jobs.sort(key=lambda job: (max(0, job["steps"] - 25) * 75 + job["steps"]), reverse=True)
    worker_gpus = [gpu for gpu in args.gpus for _ in range(args.workers_per_gpu)]
    queues: list[list[dict]] = [[] for _ in worker_gpus]
    loads = [0 for _ in worker_gpus]
    for job in jobs:
        target = min(range(len(loads)), key=loads.__getitem__)
        queues[target].append(job)
        loads[target] += max(0, job["steps"] - 25) * 75 + job["steps"]
    with ThreadPoolExecutor(max_workers=len(worker_gpus)) as executor:
        futures = [
            executor.submit(
                lambda gpu=gpu, queue=queue: [
                    run_job(job, gpu, args.dry_run, args.skip_complete) for job in queue
                ]
            )
            for gpu, queue in zip(worker_gpus, queues) if queue
        ]
        for future in as_completed(futures):
            for status in future.result():
                print(status, flush=True)


if __name__ == "__main__":
    main()
