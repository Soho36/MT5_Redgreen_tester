"""Plot the completed fixed-grid NQ experiment with matplotlib.

Requires the complete contrast.csv produced by analyze_granularity.py. Each
facet shows RTL and market-control expectancy, their paired contrast and its
95% interval, and every individual grid origin. The default outputs are PNG
and SVG beside the study documentation.

Usage: python plot_granularity.py [Reports/granularity_20261009]
       python plot_granularity.py --csv input.csv --output output.png
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, StrMethodFormatter
import numpy as np
import pandas as pd

from project_paths import PROJECT_ROOT as ROOT

DEFAULT_RUN = ROOT / "Reports" / "granularity_20261009"
DEFAULT_OUTPUT = ROOT / "docs" / "baseline" / "granularity" / "expectancy-by-grid.png"
PERIODS = (("2010-15", "2010-2015"), ("2016-19", "2016-2019"),
           ("2020-26", "2020-2026"))
GRIDS = np.array([0.25, 0.5, 1.0, 2.0])
COLORS = {"rtl": "#178879", "control": "#B46A28", "contrast": "#264D82", "origin": "#718DAF"}
REQUIRED = {"scope", "period", "grid_points", "k", "origin_ticks", "rtl_gross_R",
            "control_gross_R", "contrast_R", "contrast_R_lo", "contrast_R_hi"}


def _read(csv):
    csv = Path(csv)
    if not csv.is_file():
        raise FileNotFoundError(f"Completed experiment CSV is not available: {csv}")
    data = pd.read_csv(csv)
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"contrast.csv is missing columns: {sorted(missing)}")
    facets = []
    numeric = ["grid_points", "k", "rtl_gross_R", "control_gross_R",
               "contrast_R", "contrast_R_lo", "contrast_R_hi"]
    for period, title in PERIODS:
        mean = data[(data.scope == "equal_origin_mean") & (data.period == period)].sort_values("grid_points")
        origins = data[(data.scope == "origin") & (data.period == period)].sort_values(["grid_points", "origin_ticks"])
        if len(mean) != len(GRIDS) or not np.allclose(mean.grid_points.to_numpy(), GRIDS, rtol=0, atol=1e-12):
            raise ValueError(f"Period {period} needs one equal-origin mean for every grid")
        if not np.isfinite(mean[numeric].to_numpy(dtype=float)).all():
            raise ValueError(f"Period {period} has invalid mean or interval values")
        if (mean.contrast_R_lo > mean.contrast_R_hi).any():
            raise ValueError(f"Period {period} has reversed interval endpoints")
        if not np.allclose(mean.rtl_gross_R - mean.control_gross_R, mean.contrast_R, rtol=0, atol=1e-9):
            raise ValueError(f"Period {period} contrast does not reconcile to RTL minus control")
        for grid in GRIDS:
            subset = origins[np.isclose(origins.grid_points, grid, rtol=0, atol=1e-12)]
            expected = int(round(grid / 0.25))
            if len(subset) != expected or set(subset.origin_ticks) != set(range(expected)):
                raise ValueError(f"Period {period}, grid {grid:g}, does not contain all {expected} origins")
            if not np.isfinite(subset[numeric + ["origin_ticks"]].to_numpy(dtype=float)).all():
                raise ValueError(f"Period {period}, grid {grid:g}, has invalid origin values")
            average = mean.loc[np.isclose(mean.grid_points, grid), "contrast_R"].iloc[0]
            if not np.isclose(subset.contrast_R.mean(), average, rtol=0, atol=1e-9):
                raise ValueError(f"Period {period}, grid {grid:g}, origin average does not reconcile")
        facets.append((title, mean, origins))
    return facets


def plot(csv, output=DEFAULT_OUTPUT):
    """Validate complete results and write a static PNG plus matching SVG."""
    facets = _read(csv)
    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ValueError("Output must name a .png file; matching .svg is written automatically")
    bounds = []
    for _, mean, origins in facets:
        bounds.extend(mean[["rtl_gross_R", "control_gross_R", "contrast_R_lo", "contrast_R_hi"]].to_numpy().ravel())
        bounds.extend(origins.contrast_R.to_numpy())
    low, high = min(0, min(bounds)), max(0, max(bounds))
    padding = max((high - low) * 0.10, 0.015)
    style = {"font.family": "DejaVu Sans", "font.size": 10,
             "axes.labelsize": 11, "axes.titlesize": 12,
             "axes.spines.top": False, "axes.spines.right": False,
             "axes.edgecolor": "#A5ADB5", "xtick.color": "#4D5863", "ytick.color": "#4D5863",
             "svg.fonttype": "none"}
    with plt.rc_context(style):
        fig, axes = plt.subplots(1, 3, figsize=(13.2, 5.3), sharey=True)
        fig.subplots_adjust(left=0.085, right=0.985, top=0.72, bottom=0.25, wspace=0.12)
        positions = np.arange(len(GRIDS), dtype=float)
        for ax, (title, mean, origins) in zip(axes, facets):
            ax.axhline(0, color="#84909C", lw=1.1, zorder=1)
            ax.grid(axis="y", color="#E7EBEF", lw=0.7, zorder=0)
            for grid, subset in origins.groupby("grid_points", sort=True):
                center = float(np.log2(grid / 0.25))
                offsets = np.linspace(-0.15, 0.15, len(subset)) if len(subset) > 1 else np.array([0.0])
                ax.scatter(center + offsets, subset.contrast_R, s=20, marker="o",
                           color=COLORS["origin"], alpha=0.65, edgecolors="none", zorder=3)
            ax.plot(positions, mean.rtl_gross_R, color=COLORS["rtl"], marker="s",
                    markersize=4.8, lw=1.9, zorder=4)
            ax.plot(positions, mean.control_gross_R, color=COLORS["control"], marker="^",
                    markersize=5, lw=1.9, zorder=4)
            # Draw exact interval endpoints; percentile intervals need not contain the point estimate.
            ax.vlines(positions, mean.contrast_R_lo, mean.contrast_R_hi,
                      color=COLORS["contrast"], lw=1.25, zorder=4)
            for x, lo, hi in zip(positions, mean.contrast_R_lo, mean.contrast_R_hi):
                ax.hlines([lo, hi], x - 0.045, x + 0.045, color=COLORS["contrast"], lw=1.25, zorder=4)
            ax.plot(positions, mean.contrast_R, color=COLORS["contrast"], marker="o",
                    markersize=5.2, lw=2.25, zorder=5)
            ax.set_title(title, fontweight="bold", pad=12)
            ax.set_xticks(positions, ["0.25\n1x native", "0.50\n2x", "1.00\n4x", "2.00\n8x"])
            ax.set_xlim(-0.32, 3.32)
            ax.set_ylim(low - padding, high + padding)
            ax.yaxis.set_major_formatter(StrMethodFormatter("{x:+.2f}"))
            if high - low <= 0.4:
                ax.yaxis.set_major_locator(MultipleLocator(0.05))
            ax.tick_params(axis="x", length=0, pad=8)
        axes[0].set_ylabel("Mean gross R per trade", labelpad=10)
        fig.suptitle("NQ RTL expectancy versus price-data resolution", x=0.085, y=0.965,
                     ha="left", fontsize=17, fontweight="bold", color="#1F2D3B")
        fig.text(0.085, 0.905, "Means give each grid origin equal weight; bars show paired-day 95% intervals for RTL minus control.",
                 ha="left", fontsize=10.5, color="#566372")
        handles = [
            Line2D([], [], color=COLORS["rtl"], marker="s", lw=1.9, label="RTL"),
            Line2D([], [], color=COLORS["control"], marker="^", lw=1.9, label="Market control"),
            Line2D([], [], color=COLORS["contrast"], marker="o", lw=2.25, label="RTL minus control"),
            Line2D([], [], color=COLORS["origin"], marker="o", lw=0, markersize=4.5, alpha=0.65, label="Individual origin"),
        ]
        fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.08, 0.875),
                   ncol=4, frameon=False, columnspacing=2, handlelength=2)
        fig.text(0.535, 0.095, "Price grid in points (multiple of the native 0.25-point grid)",
                 ha="center", fontsize=11, color="#263747")
        fig.text(0.085, 0.03, "Gross results exclude costs. Small origin points use a slight horizontal offset for visibility.",
                 ha="left", fontsize=9, color="#66727F")
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=180, facecolor="white")
        fig.savefig(output.with_suffix(".svg"), facecolor="white")
        plt.close(fig)
    print(f"Wrote {output}")
    print(f"Wrote {output.with_suffix('.svg')}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--csv", type=Path, help="Override the completed contrast CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    plot(args.csv if args.csv is not None else args.run_dir / "contrast.csv", args.output)


if __name__ == "__main__":
    main()
