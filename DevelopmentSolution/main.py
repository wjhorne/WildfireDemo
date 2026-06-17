"""CLI entry point for the deterministic 2D wildfire cellular-automata simulation."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

from simulation import SimulationConfig, run_simulation
from visualization import create_animation, render_animation


def _parse_pairs(s: str) -> list[tuple[int, int]]:
    """Parse a string like '35,25 10,10' into a list of (row, col) tuples."""
    pairs: list[tuple[int, int]] = []
    for tok in s.split():
        a, b = tok.split(",")
        pairs.append((int(a), int(b)))
    return pairs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="2D wildfire cellular-automata simulation")

    parser.add_argument("--nx", type=int, default=80, help="Grid x-size (rows)")
    parser.add_argument("--ny", type=int, default=80, help="Grid y-size (cols)")
    parser.add_argument("--nt", type=int, default=200, help="Number of time steps")
    parser.add_argument("--seed", type=int, default=12345, help="Deterministic RNG seed")

    parser.add_argument("--mountain-fraction", type=float, default=0.10)
    parser.add_argument("--water-fraction", type=float, default=0.10)
    parser.add_argument("--high-fuel-fraction", type=float, default=0.45)
    parser.add_argument("--n-blobs", type=int, default=8)
    parser.add_argument("--blob-sigma", type=float, default=7.0)

    parser.add_argument("--p-ignite-low", type=float, default=0.12, help="Per-turn ignition prob for low fuel")
    parser.add_argument("--p-ignite-high", type=float, default=0.35, help="Per-turn ignition prob for high fuel")
    parser.add_argument("--p-extinguish", type=float, default=0.6, help="Per-turn extinguish prob per adjacent fire")

    parser.add_argument("--fire-start", action="append", default=[], metavar="R,C",
                        help="Initial fire cell (repeatable); must be on low/high fuel. Default: auto-place 1.")
    parser.add_argument("--firefighters", type=int, default=0, help="Number of firefighters (if no explicit starts)")
    parser.add_argument("--firefighter-starts", type=str, default=None,
                        help="Firefighter starts as 'R,C R,C ...' (non-water cells)")
    parser.add_argument("--strategy", type=str, default="greedy-closest",
                        choices=["greedy-closest", "hold", "waypoint"],
                        help="Firefighter motion strategy (the seam the analysis pipeline optimizes over)")
    parser.add_argument("--waypoints", type=str, default=None, help="Waypoints for 'waypoint' strategy: 'R,C R,C ...'")

    parser.add_argument("--save-animation", type=str, default=None, help="Optional file path to save animation (gif/mp4)")
    parser.add_argument("--output-csv", type=str, default=None, help="Optional path to save per-step statistics CSV")
    parser.add_argument("--frame-stride", type=int, default=1, help="Use every Nth step for animation frames")
    parser.add_argument("--interval-ms", type=int, default=120, help="Milliseconds between animation frames")
    parser.add_argument("--no-show", action="store_true", help="Do not open a matplotlib window")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    fire_starts: tuple[tuple[int, int], ...] = tuple(_parse_pairs(" ".join(args.fire_start))) if args.fire_start else ()
    firefighter_starts: tuple[tuple[int, int], ...] = ()
    if args.firefighter_starts:
        firefighter_starts = tuple(_parse_pairs(args.firefighter_starts))
    waypoints: tuple[tuple[int, int], ...] = ()
    if args.waypoints:
        waypoints = tuple(_parse_pairs(args.waypoints))

    config = SimulationConfig(
        nx=args.nx,
        ny=args.ny,
        nt=args.nt,
        seed=args.seed,
        mountain_fraction=args.mountain_fraction,
        water_fraction=args.water_fraction,
        high_fuel_fraction=args.high_fuel_fraction,
        n_blobs=args.n_blobs,
        blob_sigma=args.blob_sigma,
        p_ignite_low=args.p_ignite_low,
        p_ignite_high=args.p_ignite_high,
        p_extinguish=args.p_extinguish,
        fire_starts=fire_starts,
        firefighter_count=args.firefighters,
        firefighter_starts=firefighter_starts,
        strategy=args.strategy,
        waypoints=waypoints,
    )

    try:
        results = run_simulation(config)
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    burning = results["burning"]
    depleted = results["depleted"]
    fuel = results["fuel"]
    ff = results["firefighters"]

    for step in range(len(burning)):
        print(f"step={step} burning={burning[step]} depleted={depleted[step]} "
              f"fuel={fuel[step]} firefighters={ff[step]} burned={burning[step] + depleted[step]}")

    if args.output_csv:
        out = Path(args.output_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["step", "burning", "depleted", "fuel", "firefighters", "burned_total"])
            for step in range(len(burning)):
                writer.writerow([step, int(burning[step]), int(depleted[step]),
                                 int(fuel[step]), int(ff[step]), int(burning[step] + depleted[step])])
        print(f"wrote stats -> {out}", file=sys.stderr)

    show = not args.no_show
    if show or args.save_animation:
        anim = create_animation(
            results["terrain"],
            results["ff_positions"],
            results["burning"],
            results["depleted"],
            results["fuel"],
            interval_ms=args.interval_ms,
            frame_stride=args.frame_stride,
        )
        render_animation(anim, save_path=args.save_animation, show=show)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())