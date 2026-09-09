import numpy as np

from sshv2.simulation.fix import fix_simulation
from sshv2.simulation.run import build_simulation
from sshv2.simulation.utils import InitialCondition, Simulation


def rollout(
    simulation: Simulation,
    horizon: int,
    *,
    fix: bool = False,
) -> Simulation:
    horizon = max(int(horizon), 1)
    num_frames = len(simulation)
    if num_frames == 0:
        return Simulation(
            centers=np.empty_like(simulation.centers),
            velocities=np.empty_like(simulation.velocities),
            world_size=simulation.world_size,
            duration=simulation.duration,
            fps=simulation.fps,
            dt=simulation.dt,
            events=list(simulation.events),
            id_to_index=dict(simulation.id_to_index),
            index_to_color=list(simulation.index_to_color),
            index_to_radius=list(simulation.index_to_radius),
            radii_delta=simulation.radii_delta,
        )

    base_sim = fix_simulation(simulation) if fix else simulation
    num_objects = simulation.centers.shape[1]

    pred_centers = np.zeros_like(simulation.centers)
    pred_velocities = np.zeros_like(simulation.velocities)

    pred_centers[0] = simulation.centers[0]
    pred_velocities[0] = base_sim.velocities[0]

    for frame_idx in range(1, num_frames):
        start_idx = max(frame_idx - horizon, 0)
        steps = frame_idx - start_idx

        start_positions = simulation.centers[start_idx]
        start_velocities = base_sim.velocities[start_idx]

        initial_conditions = [
            InitialCondition(
                radius=simulation.index_to_radius[obj_idx],
                color=simulation.index_to_color[obj_idx],
                position=tuple(start_positions[obj_idx]),
                velocity=tuple(start_velocities[obj_idx]),
            )
            for obj_idx in range(num_objects)
        ]

        segment = build_simulation(
            initial_conditions,
            duration=steps * simulation.dt,
            fps=simulation.fps,
            world_size=simulation.world_size,
            radii_delta=simulation.radii_delta,
        )
        pred_centers[frame_idx] = segment.centers[-1]
        pred_velocities[frame_idx] = segment.velocities[-1]

    return Simulation(
        centers=pred_centers,
        velocities=pred_velocities,
        world_size=simulation.world_size,
        duration=simulation.duration,
        fps=simulation.fps,
        dt=simulation.dt,
        events=list(base_sim.events),
        id_to_index=dict(simulation.id_to_index),
        index_to_color=list(simulation.index_to_color),
        index_to_radius=list(simulation.index_to_radius),
        radii_delta=simulation.radii_delta,
    )
