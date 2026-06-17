"""Core deterministic wildfire cellular-automata simulation on a 2D grid.

The grid is a 2D array of integer cell codes (see :data:`BLOCK_NAMES`). Fire
propagates with a Moore neighborhood using block-type-weighted ignition
probabilities. Firefighters are a cellular-automata overlay whose *motion
strategy* is selectable so an external caller (e.g. the analysis pipeline) can
optimize over it. Everything is driven by a single ``numpy.random.Generator``
seeded from :class:`SimulationConfig.seed`, so identical inputs reproduce
identical runs.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Callable

import numpy as np

# --- Cell (block) type codes -------------------------------------------------
# Ordering matches the ListedColormap in visualization.py (index -> color).
MOUNTAIN = 0   # impassable to fire; firefighters traverse slowly (1 cell / 2 turns)
WATER = 1      # non-fuel; impassable to firefighters (cannot cross)
LOW_FUEL = 2   # burnable; burns in 1 turn
HIGH_FUEL = 3  # burnable; burns in 2 turns
FIRE = 4       # actively burning; diminishes as fuel is consumed
DEPLETED = 5   # zero fuel; fire cannot spread here

BLOCK_NAMES = {
    MOUNTAIN: "mountain",
    WATER: "water",
    LOW_FUEL: "low_fuel",
    HIGH_FUEL: "high_fuel",
    FIRE: "fire",
    DEPLETED: "depleted",
}

_FUEL_TYPES = (LOW_FUEL, HIGH_FUEL)
_BURN_TIME = {LOW_FUEL: 1, HIGH_FUEL: 2}

# A pluggable strategy returns the target cell for firefighter ``i`` (or ``None``
# to hold position). The engine handles movement (terrain-costed) and automatic
# extinguishing of adjacent fires.
StrategyFn = Callable[[int, np.ndarray, np.ndarray, np.ndarray, np.random.Generator], "tuple[int, int] | None"]


@dataclass(frozen=True)
class SimulationConfig:
    nx: int = 80
    ny: int = 80
    nt: int = 200
    seed: int = 12345

    # Landscape generation (spatially coherent via Gaussian blobs)
    mountain_fraction: float = 0.10
    water_fraction: float = 0.10
    high_fuel_fraction: float = 0.45
    n_blobs: int = 8
    blob_sigma: float = 7.0

    # Fire dynamics (per-turn probabilities)
    p_ignite_low: float = 0.12
    p_ignite_high: float = 0.35
    p_extinguish: float = 0.6

    # Initial fire / firefighters
    fire_starts: tuple[tuple[int, int], ...] = ()
    firefighter_count: int = 0
    firefighter_starts: tuple[tuple[int, int], ...] = ()
    strategy: str = "greedy-closest"
    waypoints: tuple[tuple[int, int], ...] = ()

    # Optional explicit terrain (overrides generation); used by tests.
    terrain_override: np.ndarray | None = None

    def validate(self) -> None:
        if self.nx <= 0 or self.ny <= 0:
            raise ValueError("Grid dimensions nx and ny must be positive integers.")
        if self.nt < 0:
            raise ValueError("nt must be >= 0.")
        for name, v in {
            "mountain_fraction": self.mountain_fraction,
            "water_fraction": self.water_fraction,
            "high_fuel_fraction": self.high_fuel_fraction,
            "p_ignite_low": self.p_ignite_low,
            "p_ignite_high": self.p_ignite_high,
            "p_extinguish": self.p_extinguish,
        }.items():
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1].")
        if self.blob_sigma <= 0:
            raise ValueError("blob_sigma must be > 0.")
        if self.n_blobs < 0:
            raise ValueError("n_blobs must be >= 0.")
        if self.mountain_fraction + self.water_fraction >= 1.0:
            raise ValueError("mountain_fraction + water_fraction must be < 1 (leave room for fuel).")


# --- Landscape generation ----------------------------------------------------

def _blob_field(rng: np.random.Generator, shape: tuple[int, int], n_blobs: int, sigma: float) -> np.ndarray:
    """Sum of random 2D Gaussian blobs -> a spatially smooth random field."""
    field = np.zeros(shape, dtype=np.float64)
    if n_blobs == 0:
        return field
    yy, xx = np.indices(shape)
    for _ in range(n_blobs):
        cy = rng.uniform(0.0, shape[0])
        cx = rng.uniform(0.0, shape[1])
        amp = rng.uniform(0.6, 1.4)
        field += amp * np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2) / (2.0 * sigma ** 2)))
    return field


def _normalize01(field: np.ndarray) -> np.ndarray:
    lo, hi = float(field.min()), float(field.max())
    if hi - lo < 1e-12:
        return np.zeros_like(field)
    return (field - lo) / (hi - lo)


def generate_landscape(config: SimulationConfig, rng: np.random.Generator) -> np.ndarray:
    """Generate a deterministic, spatially coherent landscape of cell codes."""
    nx, ny = config.nx, config.ny
    elev = _normalize01(_blob_field(rng, (nx, ny), config.n_blobs, config.blob_sigma))
    moist = _normalize01(_blob_field(rng, (nx, ny), config.n_blobs, config.blob_sigma))
    fueltype = _normalize01(_blob_field(rng, (nx, ny), config.n_blobs, config.blob_sigma))

    terrain = np.full((nx, ny), LOW_FUEL, dtype=np.int8)
    mountain = elev >= (1.0 - config.mountain_fraction)
    water = (moist >= (1.0 - config.water_fraction)) & (~mountain)
    terrain[mountain] = MOUNTAIN
    terrain[water] = WATER

    fuel_mask = terrain == LOW_FUEL  # everything not mountain/water is currently low fuel
    if fuel_mask.any() and config.high_fuel_fraction > 0.0:
        vals = fueltype[fuel_mask]
        thresh = np.quantile(vals, 1.0 - config.high_fuel_fraction)
        high = fuel_mask & (fueltype >= thresh)
        terrain[high] = HIGH_FUEL
    return terrain


# --- Geometry helpers (non-periodic) ----------------------------------------

def _moore_neighbor_mask(mask: np.ndarray) -> np.ndarray:
    """True where any of the 8 Moore neighbors is True (non-periodic edges)."""
    nx, ny = mask.shape
    out = np.zeros((nx, ny), dtype=bool)
    padded = np.pad(mask, 1, constant_values=False)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            out |= padded[1 + dr:1 + dr + nx, 1 + dc:1 + dc + ny]
    return out


def _bfs_distances(source: tuple[int, int], passable: np.ndarray) -> np.ndarray:
    """4-neighborhood BFS distances from ``source`` over ``passable`` cells.

    Returns an int32 array with -1 for unreachable cells. Water is the only
    impassable terrain (mountains, fuel, fire and depleted are all walkable).
    """
    nx, ny = passable.shape
    dist = np.full((nx, ny), -1, dtype=np.int32)
    sr, sc = source
    if not (0 <= sr < nx and 0 <= sc < ny) or not passable[sr, sc]:
        return dist
    dist[sr, sc] = 0
    q: deque[tuple[int, int]] = deque([(sr, sc)])
    while q:
        r, c = q.popleft()
        d = dist[r, c]
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < nx and 0 <= nc < ny and passable[nr, nc] and dist[nr, nc] == -1:
                dist[nr, nc] = d + 1
                q.append((nr, nc))
    return dist


def _has_moore_neighbor_fire(pos: tuple[int, int], fire_mask: np.ndarray) -> bool:
    r, c = pos
    nx, ny = fire_mask.shape
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < nx and 0 <= nc < ny and fire_mask[nr, nc]:
                return True
    return False


def _nearest_fire(pos: tuple[int, int], passable: np.ndarray, fire_mask: np.ndarray) -> tuple[int, int] | None:
    dist = _bfs_distances(pos, passable)
    finite = fire_mask & (dist >= 0)
    if not finite.any():
        return None
    rc = np.argwhere(finite)
    d = dist[finite]
    i = int(np.argmin(d))
    return int(rc[i, 0]), int(rc[i, 1])


def _entry_cost(cell: int) -> float:
    """Movement cost to *enter* a cell of the given terrain type."""
    if cell == MOUNTAIN:
        return 2.0           # 1 impassable block per 2 turns
    if cell in (HIGH_FUEL, FIRE):
        return 1.0           # 1 cell per turn
    if cell in (LOW_FUEL, DEPLETED):
        return 0.5           # 2 cells per turn
    return math.inf          # WATER: impassable


# --- Firefighter strategy & movement ----------------------------------------

def _compute_targets(
    strategy,
    ff_pos: np.ndarray,
    terrain: np.ndarray,
    fire_mask: np.ndarray,
    ff_wp_idx: np.ndarray,
    waypoints: tuple[tuple[int, int], ...],
    rng: np.random.Generator,
) -> list[tuple[int, int] | None]:
    """Per-firefighter target cell (or None to hold), based on the strategy."""
    passable = terrain != WATER
    n = ff_pos.shape[0]
    targets: list[tuple[int, int] | None] = [None] * n
    for i in range(n):
        pos = (int(ff_pos[i, 0]), int(ff_pos[i, 1]))
        if callable(strategy):
            targets[i] = strategy(i, ff_pos, terrain, fire_mask, rng)
            continue
        if strategy == "hold":
            targets[i] = pos
        elif strategy == "waypoint":
            if not waypoints:
                targets[i] = pos
            else:
                wp = waypoints[ff_wp_idx[i] % len(waypoints)]
                if pos == wp:
                    ff_wp_idx[i] += 1
                    wp = waypoints[ff_wp_idx[i] % len(waypoints)]
                targets[i] = wp
        else:  # "greedy-closest" (default)
            if _has_moore_neighbor_fire(pos, fire_mask):
                targets[i] = pos  # fire adjacent -> stand and fight
            else:
                nf = _nearest_fire(pos, passable, fire_mask)
                targets[i] = nf if nf is not None else pos
    return targets


def _move_firefighters(
    ff_pos: np.ndarray,
    ff_energy: np.ndarray,
    targets: list[tuple[int, int] | None],
    terrain: np.ndarray,
) -> None:
    """Move each firefighter toward its target, terrain-costed with carryover.

    Each firefighter gains 1.0 energy per turn; entering a cell costs that
    cell's :func:`_entry_cost`. Leftover energy carries to the next turn, so a
    mountain step (cost 2.0) takes two turns to afford.
    """
    passable = terrain != WATER
    nx, ny = terrain.shape
    for i in range(ff_pos.shape[0]):
        ff_energy[i] += 1.0
        target = targets[i]
        if target is None:
            continue
        r, c = int(ff_pos[i, 0]), int(ff_pos[i, 1])
        if (r, c) == target:
            continue
        dist = _bfs_distances(target, passable)
        if dist[r, c] < 0:
            continue  # unreachable (target behind water, etc.)
        while True:
            r, c = int(ff_pos[i, 0]), int(ff_pos[i, 1])
            if (r, c) == target:
                break
            cur_d = dist[r, c]
            best: tuple[int, int] | None = None
            best_d: int | None = None
            for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if not (0 <= nr < nx and 0 <= nc < ny):
                    continue
                if not passable[nr, nc]:
                    continue
                d = int(dist[nr, nc])
                if d < 0:
                    continue
                if best is None or d < best_d:
                    best, best_d = (nr, nc), d
            if best is None or best_d is None or best_d >= cur_d:
                break  # no progress toward target
            cost = _entry_cost(int(terrain[best]))
            if ff_energy[i] >= cost:
                ff_pos[i, 0], ff_pos[i, 1] = best[0], best[1]
                ff_energy[i] -= cost
            else:
                break  # not enough energy this turn; carry it over


# --- One CA turn -------------------------------------------------------------

def _step(state: dict, strategy, config: SimulationConfig, rng: np.random.Generator) -> None:
    terrain: np.ndarray = state["terrain"]
    burn_remaining: np.ndarray = state["burn_remaining"]
    orig_fuel: np.ndarray = state["orig_fuel"]
    ff_pos: np.ndarray = state["ff_pos"]
    ff_energy: np.ndarray = state["ff_energy"]
    ff_wp_idx: np.ndarray = state["ff_wp_idx"]

    fire_mask = terrain == FIRE

    # 1. Firefighters extinguish adjacent fires (chance per adjacent fire cell).
    if ff_pos.shape[0] > 0 and fire_mask.any():
        ff_mask = np.zeros_like(terrain, dtype=bool)
        ff_mask[ff_pos[:, 0], ff_pos[:, 1]] = True
        extinguish_candidates = fire_mask & _moore_neighbor_mask(ff_mask)
        if extinguish_candidates.any():
            rolls = rng.random(terrain.shape)
            ext = extinguish_candidates & (rolls < config.p_extinguish)
            if ext.any():
                terrain[ext] = orig_fuel[ext]   # remaining fuel restored (not depleted)
                burn_remaining[ext] = 0
                fire_mask = terrain == FIRE

    fire_at_start = fire_mask.copy()  # burning cells before this turn's ignitions

    # 2. Firefighters move per the selected strategy.
    if ff_pos.shape[0] > 0:
        targets = _compute_targets(strategy, ff_pos, terrain, fire_mask, ff_wp_idx, config.waypoints, rng)
        _move_firefighters(ff_pos, ff_energy, targets, terrain)

    # 3. Fire spread: Moore neighbors of fire that are fuel ignite with
    #    block-type-weighted probability.
    fuel_mask = (terrain == LOW_FUEL) | (terrain == HIGH_FUEL)
    if fire_mask.any() and fuel_mask.any():
        candidates = fuel_mask & _moore_neighbor_mask(fire_mask)
        if candidates.any():
            p = np.where(terrain == HIGH_FUEL, config.p_ignite_high, config.p_ignite_low)
            rolls = rng.random(terrain.shape)
            ignite = candidates & (rolls < p)
            if ignite.any():
                is_low = ignite & (terrain == LOW_FUEL)
                is_high = ignite & (terrain == HIGH_FUEL)
                orig_fuel[is_low] = LOW_FUEL
                orig_fuel[is_high] = HIGH_FUEL
                terrain[ignite] = FIRE
                burn_remaining[is_low] = _BURN_TIME[LOW_FUEL]
                burn_remaining[is_high] = _BURN_TIME[HIGH_FUEL]

    # 4. Burn-down: only pre-existing fires (not the ones ignited this turn).
    if fire_at_start.any():
        burn_remaining[fire_at_start] -= 1
        done = fire_at_start & (burn_remaining <= 0)
        if done.any():
            terrain[done] = DEPLETED
            burn_remaining[done] = 0


# --- Initialization & driver ------------------------------------------------

def _initialize(config: SimulationConfig, rng: np.random.Generator) -> dict:
    nx, ny = config.nx, config.ny
    if config.terrain_override is not None:
        terrain = np.array(config.terrain_override, dtype=np.int8)
        if terrain.shape != (nx, ny):
            raise ValueError("terrain_override shape must match (nx, ny).")
        terrain = terrain.copy()
    else:
        terrain = generate_landscape(config, rng)

    burn_remaining = np.zeros((nx, ny), dtype=np.int8)
    orig_fuel = terrain.copy()  # for fuel cells this is their type; restored on extinguish

    # Initial fires (must start on low or high fuel).
    fire_starts = list(config.fire_starts)
    if not fire_starts:
        fuel_cells = np.argwhere((terrain == LOW_FUEL) | (terrain == HIGH_FUEL))
        if fuel_cells.size == 0:
            raise ValueError("No fuel cells available to start a fire.")
        pick = fuel_cells[rng.integers(0, len(fuel_cells))]
        fire_starts = [(int(pick[0]), int(pick[1]))]
    for (r, c) in fire_starts:
        if not (0 <= r < nx and 0 <= c < ny):
            raise ValueError(f"Fire start ({r},{c}) is out of bounds.")
        if terrain[r, c] not in _FUEL_TYPES:
            raise ValueError(
                f"Fire start ({r},{c}) must be on low or high fuel (got {BLOCK_NAMES[int(terrain[r, c])]})."
            )
        ft = int(terrain[r, c])
        orig_fuel[r, c] = ft
        terrain[r, c] = FIRE
        burn_remaining[r, c] = _BURN_TIME[ft]

    # Firefighters (overlay; may not start on water).
    ff_starts = list(config.firefighter_starts)
    if not ff_starts and config.firefighter_count > 0:
        valid = np.argwhere(terrain != WATER)
        for _ in range(config.firefighter_count):
            pick = valid[rng.integers(0, len(valid))]
            ff_starts.append((int(pick[0]), int(pick[1])))
    for (r, c) in ff_starts:
        if not (0 <= r < nx and 0 <= c < ny):
            raise ValueError(f"Firefighter start ({r},{c}) is out of bounds.")
        if terrain[r, c] == WATER:
            raise ValueError(f"Firefighter start ({r},{c}) cannot be on water (impassable).")

    n_ff = len(ff_starts)
    ff_pos = np.array(ff_starts, dtype=np.int16).reshape(n_ff, 2) if n_ff else np.empty((0, 2), dtype=np.int16)
    ff_energy = np.zeros(n_ff, dtype=np.float64)
    ff_wp_idx = np.zeros(n_ff, dtype=np.int32)

    return {
        "terrain": terrain,
        "burn_remaining": burn_remaining,
        "orig_fuel": orig_fuel,
        "ff_pos": ff_pos,
        "ff_energy": ff_energy,
        "ff_wp_idx": ff_wp_idx,
    }


def run_simulation(config: SimulationConfig, strategy_fn: StrategyFn | None = None) -> dict[str, np.ndarray]:
    """Run the wildfire CA for ``config.nt`` turns.

    If ``strategy_fn`` is given it overrides ``config.strategy`` (this is the
    pluggable seam the analysis pipeline optimizes over).
    """
    config.validate()
    rng = np.random.default_rng(config.seed)
    state = _initialize(config, rng)
    strategy = strategy_fn if strategy_fn is not None else config.strategy

    nx, ny, nt = config.nx, config.ny, config.nt
    n_ff = state["ff_pos"].shape[0]

    terrain_hist = np.empty((nt + 1, nx, ny), dtype=np.int8)
    ff_pos_hist = np.empty((nt + 1, n_ff, 2), dtype=np.int16)
    terrain_hist[0] = state["terrain"]
    ff_pos_hist[0] = state["ff_pos"]

    burning = np.zeros(nt + 1, dtype=np.int64)
    depleted = np.zeros(nt + 1, dtype=np.int64)
    fuel = np.zeros(nt + 1, dtype=np.int64)
    firefighters = np.zeros(nt + 1, dtype=np.int64)
    burned_total = np.zeros(nt + 1, dtype=np.int64)

    def record(k: int) -> None:
        t = state["terrain"]
        b = int(np.count_nonzero(t == FIRE))
        d = int(np.count_nonzero(t == DEPLETED))
        f = int(np.count_nonzero((t == LOW_FUEL) | (t == HIGH_FUEL)))
        burning[k] = b
        depleted[k] = d
        fuel[k] = f
        firefighters[k] = n_ff
        burned_total[k] = b + d

    record(0)
    for step in range(1, nt + 1):
        _step(state, strategy, config, rng)
        terrain_hist[step] = state["terrain"]
        ff_pos_hist[step] = state["ff_pos"]
        record(step)

    return {
        "terrain": terrain_hist,
        "ff_positions": ff_pos_hist,
        "burning": burning,
        "depleted": depleted,
        "fuel": fuel,
        "firefighters": firefighters,
        "burned_total": burned_total,
        "config": config,
    }