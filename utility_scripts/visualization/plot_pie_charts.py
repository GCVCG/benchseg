#!/usr/bin/env python
"""Generate one pie chart per method from per-image metrics files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

from _scene_metrics import default_bins_for_scale, load_methods, resolve_metric_scale, sanitize_filename


DEFAULT_COLORS = ["#cf252c", "#ea9422", "#ffea40", "#019d4d"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one pie chart per method from per-image metrics files."
    )
    parser.add_argument("--metrics-root", required=True, help="Metrics directory or single metrics file.")
    parser.add_argument(
        "--metrics-glob",
        default="**/*.*",
        help="Glob used when --metrics-root is a directory. Default: %(default)s",
    )
    parser.add_argument("--metric-name", default="AP", help="Metric to visualize. Default: %(default)s")
    parser.add_argument("--object-prefix", default=None, help="Optional metrics key prefix filter.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Default: Visualization/plots/pies",
    )
    parser.add_argument("--bins", nargs="+", type=float, default=None, help="Metric bin edges.")
    parser.add_argument(
        "--metric-scale",
        choices=["auto", "0-1", "0-100"],
        default="auto",
        help="Metric scale used for default bins. Default: %(default)s",
    )
    parser.add_argument(
        "--colors",
        nargs="+",
        default=DEFAULT_COLORS,
        help="Colors for metric bins. Length must be len(bins) - 1.",
    )
    parser.add_argument("--method-label-map", default=None, help="Optional JSON file mapping method names to labels.")
    parser.add_argument("--method-order-file", default=None, help="Optional method order text file.")
    parser.add_argument(
        "--figure-size",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[3.0, 3.0],
        help="Figure size in inches.",
    )
    parser.add_argument(
        "--show-percentages",
        action="store_true",
        help="Show per-bin percentages in a compact legend.",
    )
    parser.add_argument(
        "--legend-marker-size",
        type=float,
        default=8.0,
        help="Marker size for the percentage legend. Default: %(default)s",
    )
    parser.add_argument(
        "--legend-font-size",
        type=float,
        default=10.0,
        help="Font size for the percentage legend. Default: %(default)s",
    )
    parser.add_argument(
        "--output-format",
        choices=["png", "pdf", "both"],
        default="png",
        help="Output file format. Default: %(default)s",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Output resolution in DPI. Default: %(default)s")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.bins is not None:
        if len(args.bins) < 2:
            raise ValueError("--bins must contain at least two values.")
        if sorted(args.bins) != args.bins:
            raise ValueError("--bins must be sorted in ascending order.")
        if len(args.colors) != len(args.bins) - 1:
            raise ValueError("--colors length must equal len(--bins) - 1.")
    if args.dpi < 1:
        raise ValueError("--dpi must be at least 1.")
    if args.legend_marker_size <= 0:
        raise ValueError("--legend-marker-size must be greater than 0.")
    if args.legend_font_size <= 0:
        raise ValueError("--legend-font-size must be greater than 0.")


def add_percentage_legend(
    ax,
    fractions: np.ndarray,
    colors: list[str],
    marker_size: float,
    font_size: float,
) -> None:
    labels = [f"{fraction * 100:.1f}%" if fraction > 0 else "0.0%" for fraction in fractions]
    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=marker_size)
        for color in colors
    ]
    ax.legend(
        handles,
        labels,
        loc="lower right",
        borderaxespad=0,
        frameon=False,
        fontsize=font_size,
        handlelength=1.0,
        handletextpad=0.35,
        labelspacing=0.25,
    )


def resolve_output_dir(output_dir: str | None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    return Path(__file__).resolve().parent / "plots" / "pies"


def save_figure(fig, output_stem: Path, output_format: str, dpi: int) -> list[Path]:
    saved_paths = []
    formats = ["png", "pdf"] if output_format == "both" else [output_format]
    for fmt in formats:
        output_path = output_stem.with_suffix(f".{fmt}")
        fig.savefig(output_path, format=fmt, dpi=dpi, bbox_inches="tight")
        saved_paths.append(output_path)
    return saved_paths


def main() -> int:
    args = parse_args()
    validate_args(args)

    methods = load_methods(
        metrics_root=args.metrics_root,
        metrics_glob=args.metrics_glob,
        metric_name=args.metric_name,
        object_prefix=args.object_prefix,
        method_label_map=args.method_label_map,
        method_order_file=args.method_order_file,
    )
    metric_scale = resolve_metric_scale(args.metric_scale, methods)
    bins = list(args.bins) if args.bins is not None else default_bins_for_scale(metric_scale)
    if len(args.colors) != len(bins) - 1:
        raise ValueError("--colors length must equal len(bins) - 1.")

    output_dir = resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating pie charts in {output_dir}")
    for method in methods:
        counts, _ = np.histogram(method.values, bins=bins)
        if counts.sum() == 0:
            print(f"  skipping {method.raw_name}: no values after binning")
            continue

        fractions = counts / counts.sum()
        nonzero = fractions > 0

        fig, ax = plt.subplots(figsize=tuple(args.figure_size))
        ax.pie(
            fractions[nonzero],
            colors=np.array(args.colors)[nonzero],
            startangle=90,
            counterclock=False,
        )

        if args.show_percentages:
            add_percentage_legend(
                ax=ax,
                fractions=fractions,
                colors=args.colors,
                marker_size=args.legend_marker_size,
                font_size=args.legend_font_size,
            )

        output_stem = output_dir / f"pie_{sanitize_filename(method.raw_name)}"
        fig.tight_layout()
        saved_paths = save_figure(fig, output_stem, args.output_format, args.dpi)
        plt.close(fig)
        print(f"  saved {', '.join(str(path) for path in saved_paths)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
