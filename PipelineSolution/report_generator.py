"""Report generator: text and PDF outputs for the strategy optimization."""
from __future__ import annotations

import os
import sys
from datetime import datetime

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from DevelopmentSolution.simulation import SimulationConfig

# Terrain colormap (kept in sync with DevelopmentSolution/visualization.py).
_COLORS = ["#6b6b6b", "#2f7fe2", "#c7e086", "#2e8b3d", "#ff5a08", "#5b4636"]


class TextReportGenerator:
    @staticmethod
    def generate_text(optimization: dict, validation_result: tuple[bool, str] | None = None) -> str:
        cfg: SimulationConfig = optimization["config"]
        best = optimization["best_metrics"]
        ranking = optimization["ranking"]
        results = optimization["best_results"]

        lines = []
        lines.append("=" * 72)
        lines.append("WILDFIRE FIREFIGHTING STRATEGY OPTIMIZATION REPORT")
        lines.append("=" * 72)
        lines.append("")
        lines.append("CONFIGURATION")
        lines.append("-" * 72)
        lines.append(f"Grid:                {cfg.nx} x {cfg.ny}")
        lines.append(f"Turns:               {cfg.nt}")
        lines.append(f"Seed:                {cfg.seed}")
        lines.append(f"Firefighters:        {optimization['best_metrics']['firefighters']}")
        lines.append(f"p_ignite_low/high:   {cfg.p_ignite_low} / {cfg.p_ignite_high}")
        lines.append(f"p_extinguish:        {cfg.p_extinguish}")
        lines.append(f"Fire starts:         {cfg.fire_starts if cfg.fire_starts else 'auto (1)'}")
        lines.append("")
        lines.append(f"OBJECTIVE: minimize burned area (final burned_total)")
        lines.append("")
        lines.append("RECOMMENDED STRATEGY")
        lines.append("-" * 72)
        lines.append(f"  Strategy:          {optimization['best_name']}")
        lines.append(f"  Final burned:      {best['final_burned']}")
        lines.append(f"  Fuel remaining:    {best['final_fuel']}")
        lines.append(f"  Depleted:          {best['final_depleted']}")
        lines.append(f"  Peak burning:      {best['peak_burning']} (step {best['peak_step']})")
        lines.append("")
        lines.append("STRATEGY COMPARISON (ranked by final burned area)")
        lines.append("-" * 72)
        lines.append(f"  {'#':<3}{'Strategy':<42}{'burned':>8}{'fuel':>8}{'depl':>8}{'peak':>8}")
        for i, r in enumerate(ranking, 1):
            lines.append(f"  {i:<3}{r['name']:<42}{r['final_burned']:>8}{r['final_fuel']:>8}"
                         f"{r['final_depleted']:>8}{r['peak_burning']:>8}")
        lines.append("")
        lines.append("BEST-RUN TRAJECTORY")
        lines.append("-" * 72)
        lines.append(f"  Initial fuel:      {int(results['fuel'][0])}")
        lines.append(f"  Peak burning:      {best['peak_burning']} at step {best['peak_step']}")
        lines.append(f"  Final burning:     {best['final_burning']}")
        lines.append(f"  Final burned total:{best['final_burned']}")
        lines.append("")

        if validation_result is not None:
            lines.append("VALIDATION")
            lines.append("-" * 72)
            passed, message = validation_result
            lines.append(f"  Status: {'PASSED' if passed else 'FAILED'}")
            lines.append(f"  {message}")
            lines.append("")

        lines.append("=" * 72)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 72)
        return "\n".join(lines)


class PDFReportGenerator:
    @staticmethod
    def generate_pdf(optimization: dict, output_path: str) -> None:
        with PdfPages(output_path) as pdf:
            PDFReportGenerator._page_summary(pdf, optimization)
            PDFReportGenerator._page_trajectories(pdf, optimization)
            PDFReportGenerator._page_final_terrain(pdf, optimization)
        print(f"✓ PDF report generated: {output_path}")

    @staticmethod
    def _page_summary(pdf, optimization):
        cfg = optimization["config"]
        best = optimization["best_metrics"]
        ranking = optimization["ranking"]
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")
        ax.text(0.5, 0.96, "Wildfire Firefighting Strategy Optimization", ha="center",
                fontsize=15, weight="bold", transform=ax.transAxes)
        ax.text(0.5, 0.92, "Objective: minimize burned area", ha="center", fontsize=11,
                style="italic", transform=ax.transAxes)

        y = 0.86
        ax.text(0.1, y, "CONFIGURATION", fontsize=12, weight="bold", transform=ax.transAxes)
        for label, val in [
            ("Grid", f"{cfg.nx} x {cfg.ny}"),
            ("Turns", str(cfg.nt)),
            ("Seed", str(cfg.seed)),
            ("Firefighters", str(best["firefighters"])),
            ("p_ignite low/high", f"{cfg.p_ignite_low} / {cfg.p_ignite_high}"),
            ("p_extinguish", str(cfg.p_extinguish)),
            ("Fire starts", str(cfg.fire_starts) if cfg.fire_starts else "auto (1)"),
        ]:
            y -= 0.035
            ax.text(0.12, y, label, fontsize=10, transform=ax.transAxes)
            ax.text(0.55, y, str(val), fontsize=10, family="monospace", transform=ax.transAxes)

        y -= 0.05
        ax.text(0.1, y, "RECOMMENDED STRATEGY", fontsize=12, weight="bold", transform=ax.transAxes)
        y -= 0.035
        ax.text(0.12, y, optimization["best_name"], fontsize=11, family="monospace",
                color="#2e8b3d", weight="bold", transform=ax.transAxes)
        for label, val in [
            ("Final burned", str(best["final_burned"])),
            ("Fuel remaining", str(best["final_fuel"])),
            ("Depleted", str(best["final_depleted"])),
            ("Peak burning", f"{best['peak_burning']} @ step {best['peak_step']}"),
        ]:
            y -= 0.03
            ax.text(0.12, y, label, fontsize=9, transform=ax.transAxes)
            ax.text(0.55, y, str(val), fontsize=9, family="monospace", transform=ax.transAxes)

        y -= 0.05
        ax.text(0.1, y, "STRATEGY COMPARISON (ranked)", fontsize=12, weight="bold", transform=ax.transAxes)
        y -= 0.03
        ax.text(0.12, y, "#  Strategy                                   burned   fuel  depl  peak",
                fontsize=8, family="monospace", transform=ax.transAxes)
        for i, r in enumerate(ranking, 1):
            y -= 0.028
            ax.text(0.12, y,
                    f"{i:<2} {r['name']:<41} {r['final_burned']:>6} {r['final_fuel']:>6}"
                    f" {r['final_depleted']:>5} {r['peak_burning']:>5}",
                    fontsize=8, family="monospace", transform=ax.transAxes)

        ax.text(0.5, 0.02, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ha="center", fontsize=8, style="italic", transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    @staticmethod
    def _page_trajectories(pdf, optimization):
        fig, ax = plt.subplots(figsize=(8.5, 6))
        best_name = optimization["best_name"]
        for name, traj in optimization["trajectories"].items():
            style = dict(linewidth=2.6) if name == best_name else dict(linewidth=1.3, alpha=0.7)
            ax.plot(np.arange(len(traj)), traj, label=name, **style)
        ax.set_xlabel("Turn")
        ax.set_ylabel("Burned area (cells)")
        ax.set_title("Burned Area Over Time by Strategy", weight="bold")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    @staticmethod
    def _page_final_terrain(pdf, optimization):
        from matplotlib.colors import BoundaryNorm, ListedColormap
        from matplotlib.patches import Patch
        results = optimization["best_results"]
        terrain = results["terrain"]
        ff = results["ff_positions"]
        cmap = ListedColormap(_COLORS)
        norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5], cmap.N)

        fig, ax = plt.subplots(figsize=(7.2, 7.0))
        ax.imshow(terrain[-1], cmap=cmap, norm=norm, origin="lower", interpolation="nearest")
        if ff.shape[1] > 0:
            pos = ff[-1]
            ax.scatter(pos[:, 1], pos[:, 0], marker="^", s=70,
                       facecolor="#0b2b6b", edgecolor="white", linewidth=0.8, zorder=5)
        ax.set_title(f"Final landscape under recommended strategy\n({optimization['best_name']})",
                     weight="bold", fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
        handles = [Patch(facecolor=_COLORS[i], label=n) for i, n in enumerate(
            ["Mountain", "Water", "Low fuel", "High fuel", "Fire", "Depleted"])]
        handles.append(plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#0b2b6b",
                                  markeredgecolor="white", markersize=9, label="Firefighter"))
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
                  frameon=False, fontsize=8)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)