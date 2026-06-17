"""Visualization helpers for the wildfire cellular-automata simulation.

Renders the terrain (mountains / water / low & high fuel / fire / depleted) with
a discrete colormap and overlays firefighters as markers, animating the fire
moving through the landscape. The animation can be saved to a GIF (openable
directly in the VS Code preview pane) or shown interactively.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.colors import BoundaryNorm, ListedColormap

# Codes mirror simulation.py (kept in sync by index).
_MOUNTAIN, _WATER, _LOW_FUEL, _HIGH_FUEL, _FIRE, _DEPLETED = 0, 1, 2, 3, 4, 5

_COLORS = [
    "#6b6b6b",  # mountain  (gray)
    "#2f7fe2",  # water     (blue)
    "#c7e086",  # low fuel  (light green)
    "#2e8b3d",  # high fuel (dark green)
    "#ff5a08",  # fire      (orange-red)
    "#5b4636",  # depleted  (charred brown)
]
_CMAP = ListedColormap(_COLORS)
_BOUNDS = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
_NORM = BoundaryNorm(_BOUNDS, _CMAP.N)


def create_animation(
    terrain: np.ndarray,
    ff_positions: np.ndarray,
    burning: np.ndarray,
    depleted: np.ndarray,
    fuel: np.ndarray,
    interval_ms: int = 120,
    frame_stride: int = 1,
) -> FuncAnimation:
    """Build a matplotlib animation of the wildfire simulation.

    Parameters
    ----------
    terrain : (T, nx, ny) int array of cell codes
    ff_positions : (T, n_ff, 2) int array of firefighter (row, col) per step
    burning, depleted, fuel : (T,) per-step statistics for the title
    """
    if frame_stride <= 0:
        raise ValueError("frame_stride must be a positive integer.")
    if terrain.ndim != 3:
        raise ValueError("terrain must have shape (T, nx, ny).")

    nx, ny = terrain.shape[1], terrain.shape[2]
    n_ff = ff_positions.shape[1]
    frame_indices = np.arange(0, terrain.shape[0], frame_stride)

    fig, ax = plt.subplots(figsize=(7.2, 7.0), constrained_layout=True)
    im = ax.imshow(terrain[0], cmap=_CMAP, norm=_NORM, origin="lower", interpolation="nearest")

    # Legend mapping each color to its block type.
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor=_COLORS[0], label="Mountain"),
        Patch(facecolor=_COLORS[1], label="Water"),
        Patch(facecolor=_COLORS[2], label="Low fuel"),
        Patch(facecolor=_COLORS[3], label="High fuel"),
        Patch(facecolor=_COLORS[4], label="Fire"),
        Patch(facecolor=_COLORS[5], label="Depleted"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
              frameon=False, fontsize=8, title="Blocks")

    # Firefighter overlay (white-edged navy triangles).
    scatter = None
    if n_ff > 0:
        pos0 = ff_positions[0]
        scatter = ax.scatter(pos0[:, 1], pos0[:, 0], marker="^", s=70,
                             facecolor="#0b2b6b", edgecolor="white", linewidth=0.8, zorder=5)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_xticks([])
    ax.set_yticks([])
    title = ax.set_title("")

    def update(frame: int):
        step = int(frame_indices[frame])
        im.set_data(terrain[step])
        if scatter is not None:
            pos = ff_positions[step]
            scatter.set_offsets(np.column_stack([pos[:, 1], pos[:, 0]]))
        title.set_text(
            f"step={step}  burning={int(burning[step])}  depleted={int(depleted[step])}"
            f"  fuel={int(fuel[step])}  firefighters={n_ff}"
        )
        return (im, scatter, title) if scatter is not None else (im, title)

    return FuncAnimation(
        fig,
        update,
        frames=frame_indices.size,
        interval=interval_ms,
        blit=False,
        repeat=False,
    )


def render_animation(anim: FuncAnimation, save_path: str | None, show: bool) -> None:
    if save_path:
        target = Path(save_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        anim.save(str(target), dpi=120)
    if show:
        plt.show()
    else:
        plt.close(anim._fig)