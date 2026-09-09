import os
import json
import wandb
import torch
import shutil
import tempfile
from tqdm import tqdm
from pathlib import Path
from typing import Literal
import torch.nn.functional as F
import torch.distributed as dist
from accelerate import Accelerator
from torch.utils.data import Dataset, DataLoader

from sshv2.simulation.diff import Difference
from sshv2.simulation.rollout import rollout
from sshv2.simulation.reliable_rollout import (
    RolloutTaskSpec,
    corrected_rollout_metrics,
    project_reliable_rollouts,
    track_video_reliably,
)
from sshv2.simulation.quality import Quality
from sshv2.simulation.utils import Simulation
from sshv2.simulation.sim_to_tensor import tensor_to_sim
from sshv2.utils.bounce.configs import BounceTrainingConfig
from sshv2.diffsynth.utils.interface import infer_video_size
from sshv2.diffsynth.pipelines.wan_video import WanVideoPipeline
from sshv2.diffsynth.utils.interface import save_video, video_to_tensor


class Metrics:
    def __init__(
        self,
        l2: float,
        gt_error: float,
        rollout_error: dict[int: float],
        iou: float,
        corrected_rollout: dict[str, float | int | None] | None = None,
        id: str | None = None
    ):
        self.l2 = l2
        self.gt_error = gt_error
        self.rollout_error = rollout_error
        self.iou = iou
        self.corrected_rollout = corrected_rollout or {}
        self.id = id

    @classmethod
    def get(
        cls,
        vid_in: str | os.PathLike | Path,
        vid_out: str | os.PathLike | Path,
        sim_in: Simulation,
        sim_out: Simulation,
        *,
        id: str | None = None,
        size: tuple[int, int] | None = None,
        horizons: tuple[int] = (1, 5),
        num_condition_frames: int = 0,
    ):
        vid_in = Path(vid_in)
        vid_out = Path(vid_out)

        vid_in_tensor = video_to_tensor(vid_in, size=size)
        vid_out_tensor = video_to_tensor(vid_out, size=size)

        num_frames = min(vid_in_tensor.shape[2], vid_out_tensor.shape[2])
        vid_in_tensor = vid_in_tensor[:, :, num_condition_frames:num_frames]
        vid_out_tensor = vid_out_tensor[:, :, num_condition_frames:num_frames]

        l2 = F.mse_loss(vid_in_tensor, vid_out_tensor).item()

        frame_range = (num_condition_frames, None)
        diff = Difference.from_simulations(sim_in, sim_out)
        gt_error = diff.avg_center_error(frame_range)

        rollout_error = {}
        for h in horizons:
            roll_sim = rollout(sim_out, horizon=h)
            roll_diff = Difference.from_simulations(sim_out, roll_sim)
            rollout_error[h] = roll_diff.avg_center_error(frame_range)

        quality = Quality.from_video(
            vid_out,
            sim_in.to_initial_conditions(),
            sim=sim_out,
            world_size=sim_in.world_size,
            clipped=True,
            radii_delta=sim_in.radii_delta
        )

        corrected_rollout: dict[str, float | int | None] = {}
        reliable_horizons = sorted(set(horizons) & {1, 5})
        if reliable_horizons:
            task_spec = RolloutTaskSpec(
                colors=tuple(sim_in.index_to_color),
                radii=tuple(float(value) for value in sim_in.index_to_radius),
                world_size=tuple(float(value) for value in sim_in.world_size),
                fps=float(sim_in.fps),
                radii_delta=float(sim_in.radii_delta),
            )
            reliable_track = track_video_reliably(vid_out, task_spec)
            for horizon in reliable_horizons:
                projection = project_reliable_rollouts(
                    reliable_track, task_spec, horizon=horizon,
                )
                corrected_rollout.update(corrected_rollout_metrics(
                    reliable_track,
                    projection,
                    task_spec,
                    observed_frames=num_condition_frames,
                    horizon=horizon,
                ).to_dict(
                    prefix=f"rollout_h{horizon}",
                    include_tracking_metrics=(horizon == 5 or 5 not in reliable_horizons),
                ))

        return Metrics(
            l2=l2,
            gt_error=gt_error,
            rollout_error=rollout_error,
            iou=quality.avg_iou(frame_range),
            corrected_rollout=corrected_rollout,
            id=id
        )


class Log:
    def __init__(self):
        self.metrics: list[Metrics] = []
        self.failed: int = 0
        self.total: int = 0

    def append(self, metrics: Metrics):
        self.metrics.append(metrics)

    def to_file(self, path: str | os.PathLike | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.summary, f, indent=2)

    @property
    def summary(self):
        if not self.metrics:
            return {"failed": self.failed, "total": self.total}

        def _avg(values):
            values = [v for v in values if v is not None]
            return sum(values) / len(values) if values else None

        horizons = set()
        for m in self.metrics:
            horizons.update(m.rollout_error.keys())

        result = {
            "l2": _avg([m.l2 for m in self.metrics]),
            "gt_error": _avg([m.gt_error for m in self.metrics]),
            "iou": _avg([m.iou for m in self.metrics]),
            "failed": self.failed,
            "total": self.total,
        }
        for h in sorted(horizons):
            result[f"rollout_h{h}_error"] = _avg([m.rollout_error.get(h) for m in self.metrics])
            result[f"legacy_rollout_h{h}_error"] = result[f"rollout_h{h}_error"]
        corrected_keys = sorted({key for metric in self.metrics for key in metric.corrected_rollout})
        for key in corrected_keys:
            result[key] = _avg([metric.corrected_rollout.get(key) for metric in self.metrics])
        return result

    @property
    def wandb(self):
        if not self.metrics:
            return {}

        def _avg(values):
            values = [v for v in values if v is not None]
            return sum(values) / len(values) if values else None

        horizons = set()
        for m in self.metrics:
            horizons.update(m.rollout_error.keys())

        payload = {
            "val/l2": _avg([m.l2 for m in self.metrics]),
            "val/gt_error": _avg([m.gt_error for m in self.metrics]),
            "val/iou": _avg([m.iou for m in self.metrics]),
            "val/failed": self.failed,
            "val/total": self.total,
        }

        for h in sorted(horizons):
            payload[f"val/rollout_h{h}_error"] = _avg([m.rollout_error.get(h) for m in self.metrics])
            payload[f"val/legacy_rollout_h{h}_error"] = payload[f"val/rollout_h{h}_error"]
        corrected_keys = sorted({key for metric in self.metrics for key in metric.corrected_rollout})
        for key in corrected_keys:
            payload[f"val/{key}"] = _avg([metric.corrected_rollout.get(key) for metric in self.metrics])

        return payload


def collate_fn(data):
    result = {
        "video": [s["video"] for s in data],
        "source": [s["source"] for s in data],
        "log_as_video": [s.get("log_as_video", False) for s in data],
    }
    if any("initial_state" in sample for sample in data):
        if not all("initial_state" in sample for sample in data):
            raise ValueError("Either every evaluation sample must have initial_state or none may have it.")
        result["initial_state"] = torch.stack([sample["initial_state"] for sample in data])
    return result


def eval(
    pipe: WanVideoPipeline,
    dataset: Dataset,
    dataset_dir: str | os.PathLike | Path,
    return_fn: bool = False,
    height: int = 256,
    width: int = 256,
    num_frames: int = 33,
    format: Literal["pixels", "features"] = "pixels",
    num_condition_frames: int = 2,
    num_inference_steps: int = 50,
    batch_size: int = 1,
    num_workers: int = 8,
    pre_encoded: bool = False,
    save_videos: bool = False,
    out_dir: str | os.PathLike | Path | None = None,
    wandb_run: wandb.Run | None = None,
    config: BounceTrainingConfig | None = None,
    skip: bool = False,
    seed: int | None = None,
):
    if config is not None:
        height, width = config.val_data.size
        num_frames = config.val_data.num_frames
        format = config.val_data.format
        num_condition_frames = config.model.num_condition_frames
        num_inference_steps = config.model.dit.num_inference_steps
        batch_size = config.loader.val_batch_size
        num_workers = config.loader.val_num_workers
        pre_encoded = config.val_data.encoded
        if config.log is not None:
            save_videos = config.log.save_videos
            out_dir = config.log.out_dir
    
    dataset_dir = Path(dataset_dir)
    out_dir = None if out_dir is None else Path(out_dir)
    base_pipe = pipe

    @torch.no_grad()
    def _run(
        accelerator: Accelerator,
        pipe: WanVideoPipeline | None = None,
        step: int | None = None,
        model_tag: str | None = None,
        **kwargs,
    ):
        pipe = pipe or base_pipe

        def num_condition_video_frames():
            if num_condition_frames <= 0:
                return 0
            if hasattr(pipe.vae, "to_num_frames"):
                return pipe.vae.to_num_frames(num_condition_frames)
            return num_condition_frames * 4 - 3

        def sync_accelerator():
            if accelerator.device.type == "cuda":
                torch.cuda.synchronize(accelerator.device)
            accelerator.wait_for_everyone()

        train_pre_encoded = pipe.pre_encoded
        pipe.pre_encoded_(pre_encoded)
        pipe.train(False)

        dataloader = DataLoader(
            dataset=dataset,
            batch_size=batch_size,
            shuffle=False,
            collate_fn=collate_fn,
            num_workers=num_workers
        )

        dataloader = accelerator.prepare(dataloader)
        log = Log()
        save_dir = None
        if save_videos and out_dir is not None:
            if step is not None:
                dir_name = f"{model_tag}-step-{step}" if model_tag else f"step-{step}"
            else:
                dir_name = f"{model_tag}" if model_tag else f"default"
            save_dir = out_dir / dir_name
            save_dir.mkdir(parents=True, exist_ok=True)

        for data in tqdm(dataloader, desc="Validation", disable=(not accelerator.is_main_process)):

            save_paths = []
            for src in data["source"]:
                sp = (save_dir / Path(src)).with_suffix(".mp4") if save_dir is not None else None
                save_paths.append(sp)

            all_exist = skip and all(sp is not None and sp.exists() for sp in save_paths)

            if not all_exist:
                input_kwargs = {
                    "height": height,
                    "width": width,
                    "num_frames": num_frames,
                    "num_condition_frames": num_condition_frames,
                    "num_inference_steps": num_inference_steps,
                    "num_samples": len(data["video"]),
                    "seed": seed,
                    "return_as_tensor": format == "features",
                    "progress_bar_cmd": lambda x: x
                }
                if num_condition_frames > 0:
                    input_kwargs["condition_frames"] = data["video"]
                if "initial_state" in data:
                    input_kwargs["initial_state"] = data["initial_state"]
                out = pipe(**input_kwargs)
            else:
                out = None

            out_iter = out if out is not None else [None] * len(data["video"])
            for src, pred, log_as_video, save_path in zip(
                data["source"], out_iter, data["log_as_video"], save_paths
            ):
                log.total += 1
                tmp_path = None

                try:
                    vid_in = (dataset_dir / src).with_suffix(".mp4")
                    sim_in = Simulation.from_file((dataset_dir / src).with_suffix(".npz"))
                    init_cond = sim_in.to_initial_conditions()

                    # TODO: --skip with features fails
                    if skip and save_path is not None and save_path.exists():
                        vid_out = save_path
                    else:
                        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                        vid_out = Path(tmp.name)
                        tmp.close()
                        tmp_path = vid_out

                        if format == "features":
                            sim_out = tensor_to_sim(
                                data=pred,
                                fps=sim_in.fps,
                                world_size=sim_in.world_size,
                                index_to_radius=sim_in.index_to_radius,
                                index_to_color=sim_in.index_to_color,
                                id_to_index=sim_in.id_to_index,
                                radii_delta=sim_in.radii_delta,
                                restore=True
                            )
                            pred = sim_out.to_video(
                                fps=sim_in.fps,
                                resolution=infer_video_size(vid_in, (128, 128)),
                                world_size=sim_in.world_size,
                                radii_delta=sim_in.radii_delta,
                                return_pil=True
                            )
                        save_video(pred, vid_out, fps=sim_in.fps)
                        if save_path is not None:
                            save_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(vid_out, save_path)

                    if format != "features":
                        sim_out = Simulation.from_video(
                            video=vid_out,
                            initial_conditions=init_cond,
                            fix=("initial_state" not in data),
                            world_size=sim_in.world_size,
                            fps=sim_in.fps,
                            radii_delta=sim_in.radii_delta,
                        )

                    metric_size = None if format == "features" else (height, width)
                    cond_frames_px = num_condition_video_frames()
                    log.append(Metrics.get(
                        vid_in=vid_in, vid_out=vid_out,
                        sim_in=sim_in, sim_out=sim_out,
                        size=metric_size,
                        num_condition_frames=cond_frames_px,
                    ))
                except Exception as e:
                    log.failed += 1
                finally:
                    if tmp_path is not None:
                        tmp_path.unlink(missing_ok=True)

        if accelerator.num_processes > 1:
            sync_accelerator()
            payload = {
                "metrics": log.metrics,
                "failed": log.failed,
                "total": log.total,
            }
            
            entries = [None for _ in range(accelerator.num_processes)]
            dist.all_gather_object(entries, payload)

            if accelerator.is_main_process:
                merged = Log()
                for entry in entries:
                    merged.metrics.extend(entry["metrics"])
                    merged.failed += entry["failed"]
                    merged.total += entry["total"]
                log = merged
            else:
                log = Log()

        pipe.pre_encoded_(train_pre_encoded)
        pipe.scheduler.set_timesteps(pipe.scheduler.num_train_timesteps, training=True)
        pipe.train(True)

        sync_accelerator()
        if accelerator.is_main_process and save_dir is not None:
            log.to_file(save_dir / "metrics.json")
        sync_accelerator()

        if return_fn:
            return log.wandb if accelerator.is_main_process else {}
        return log if accelerator.is_main_process else Log()

    if return_fn:
        return _run
    return _run()


if __name__ == "__main__":
    import argparse
    from sshv2.diffsynth.trainers.wan_video_train import WanTrainingModule

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--ckpt", type=Path, default=None)
    parser.add_argument("--name", type=str, default="default")
    parser.add_argument("--labels", type=Path, default=None)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--num-inference-steps", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--skip", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    cfg = BounceTrainingConfig.from_file(args.config)

    if args.ckpt is not None:
        cfg.model.dit.ckpt_file = args.ckpt

    if cfg.val_data is None:
        raise ValueError("Config has no val_data section")

    if args.labels is not None:
        cfg.val_data.labels = args.labels

    if args.dataset is not None:
        cfg.val_data.dataset = args.dataset

    if args.batch_size is not None:
        cfg.loader.val_batch_size = args.batch_size

    if args.out_dir is not None and cfg.log is not None:
        cfg.log.out_dir = args.out_dir

    accelerator = Accelerator()

    val_dataset = cfg.val_data.build()

    if args.num_inference_steps is not None:
        cfg.model.dit.num_inference_steps = args.num_inference_steps
    num_inference_steps = cfg.model.dit.num_inference_steps

    model = WanTrainingModule(
        dit_config=cfg.model.dit,
        vae_config=cfg.model.vae,
        no_encoding=cfg.val_data.encoded,
        num_condition_frames=cfg.model.num_condition_frames,
        num_inference_steps=num_inference_steps,
        pipeline_type=cfg.model.pipe,
        pipeline_kwargs=cfg.model.pipe_kwargs
    )
    model.to(accelerator.device)

    out_dir = cfg.log.out_dir if cfg.log is not None else None

    run_eval = eval(
        pipe=model.pipe,
        dataset=val_dataset,
        dataset_dir=cfg.val_data.dataset,
        save_videos=True,
        out_dir=out_dir,
        config=cfg,
        return_fn=True,
        skip=args.skip,
        seed=args.seed,
    )

    run_eval(accelerator=accelerator, model_tag=args.name)
