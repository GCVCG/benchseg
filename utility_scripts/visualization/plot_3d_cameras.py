#!/usr/bin/env python
"""Generate 3D camera plots colored by per-image metric values."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

from _scene_metrics import (
    compute_axis_limits,
    compute_centered_scene,
    default_bins_for_scale,
    load_methods,
    load_scene,
    metric_to_color,
    resolve_metric_value_for_image,
    resolve_metric_scale,
    sanitize_filename,
)


DEFAULT_COLORS = ["#cf252c", "#ea9422", "#ffea40", "#019d4d"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one 3D camera plot per method from COLMAP scene files and metrics."
    )
    parser.add_argument("--metrics-root", required=True, help="Metrics directory or single metrics file.")
    parser.add_argument(
        "--metrics-glob",
        default="**/*.*",
        help="Glob used when --metrics-root is a directory. Default: %(default)s",
    )
    parser.add_argument("--metric-name", default="AP", help="Metric to visualize. Default: %(default)s")
    parser.add_argument("--object-prefix", default=None, help="Optional metrics key prefix.")
    parser.add_argument("--images-path", required=True, help="COLMAP images.txt path.")
    parser.add_argument("--points-path", required=True, help="COLMAP points3D.txt path.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Default: Visualization/plots/3d",
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
        "--metric-key-template",
        default="auto",
        help="Template for mapping image names to metrics keys. Default: auto",
    )
    parser.add_argument("--index-width", type=int, default=3, help="Zero-padding width for numeric image ids.")
    parser.add_argument("--elev", type=float, default=None, help="3D view elevation.")
    parser.add_argument("--azim", type=float, default=None, help="3D view azimuth.")
    parser.add_argument(
        "--axis-margin-ratio",
        type=float,
        default=0.05,
        help="Margin ratio around the point cloud bounds.",
    )
    parser.add_argument(
        "--view-preset",
        choices=["auto", "sample-scene"],
        default="auto",
        help="Optional fixed view preset. Default: %(default)s",
    )
    parser.add_argument(
        "--xlim",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=None,
        help="Fixed X axis limits. Overrides auto-fit and presets.",
    )
    parser.add_argument(
        "--ylim",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=None,
        help="Fixed Y axis limits. Overrides auto-fit and presets.",
    )
    parser.add_argument(
        "--zlim",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=None,
        help="Fixed Z axis limits. Overrides auto-fit and presets.",
    )
    parser.add_argument(
        "--figure-size",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[4.0, 4.0],
        help="Figure size in inches.",
    )
    parser.add_argument("--point-size", type=float, default=0.05, help="Point cloud marker size.")
    parser.add_argument("--camera-base", type=float, default=0.3, help="Camera frustum half-width.")
    parser.add_argument("--camera-height", type=float, default=0.6, help="Camera frustum height.")
    parser.add_argument("--missing-color", default="gray", help="Color used when a metric is missing.")
    parser.add_argument(
        "--output-rotation",
        type=int,
        choices=[0, 90, 180, 270],
        default=None,
        help=(
            "Rotate the rendered image before saving. If omitted, sample-scene "
            "uses 180 and other presets use 0."
        ),
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
    if args.index_width < 1:
        raise ValueError("--index-width must be at least 1.")
    if args.dpi < 1:
        raise ValueError("--dpi must be at least 1.")
    if args.point_size <= 0:
        raise ValueError("--point-size must be greater than 0.")


def plot_camera_frustum(
    ax,
    center: np.ndarray,
    rotation: np.ndarray,
    scale_base: float,
    height: float,
    color: str,
    linewidth: float = 0.1,
) -> None:
    p0 = np.array([0.0, 0.0, 0.0])
    p1 = np.array([scale_base, scale_base, height])
    p2 = np.array([scale_base, -scale_base, height])
    p3 = np.array([-scale_base, -scale_base, height])
    p4 = np.array([-scale_base, scale_base, height])
    frustum = np.stack([p0, p1, p2, p3, p4])
    world = (rotation @ frustum.T).T + center

    side_faces = [
        [world[0], world[1], world[2]],
        [world[0], world[2], world[3]],
        [world[0], world[3], world[4]],
        [world[0], world[4], world[1]],
    ]
    base_face = [[world[1], world[2], world[3], world[4]]]

    ax.add_collection3d(
        Poly3DCollection(
            side_faces,
            facecolors=color,
            edgecolors=color,
            linewidths=linewidth,
            alpha=0.8,
        )
    )
    ax.add_collection3d(
        Poly3DCollection(
            base_face,
            facecolors=color,
            edgecolors=color,
            linewidths=linewidth,
            alpha=0.9,
        )
    )

    edges = [
        [world[0], world[1]],
        [world[0], world[2]],
        [world[0], world[3]],
        [world[0], world[4]],
        [world[1], world[2]],
        [world[2], world[3]],
        [world[3], world[4]],
        [world[4], world[1]],
    ]
    ax.add_collection3d(Line3DCollection(edges, colors=color, linewidths=linewidth))


def resolve_axis_limits(
    args: argparse.Namespace,
    points_centered: np.ndarray,
    cameras_centered: np.ndarray,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    preset_limits = {
        "sample-scene": (
            (-17.51, 33.30),
            (-9.09, 41.72),
            (-62.31, -11.50),
        )
    }

    if args.view_preset in preset_limits:
        xlim, ylim, zlim = preset_limits[args.view_preset]
    else:
        xlim, ylim, zlim = compute_axis_limits(
            points_centered, cameras_centered, args.axis_margin_ratio
        )

    if args.xlim is not None:
        xlim = tuple(args.xlim)
    if args.ylim is not None:
        ylim = tuple(args.ylim)
    if args.zlim is not None:
        zlim = tuple(args.zlim)

    return xlim, ylim, zlim


def resolve_view_angles(args: argparse.Namespace) -> tuple[float, float]:
    preset_angles = {
        "auto": (34.087629330952225, 99.98761354356844),
        "sample-scene": (34.087629330952225, 99.98761354356844),
    }
    elev, azim = preset_angles.get(args.view_preset, preset_angles["auto"])
    if args.elev is not None:
        elev = args.elev
    if args.azim is not None:
        azim = args.azim
    return elev, azim


def resolve_output_rotation(args: argparse.Namespace) -> int:
    if args.output_rotation is not None:
        return args.output_rotation
    if args.view_preset == "sample-scene":
        return 180
    return 0


def resolve_output_dir(output_dir: str | None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    return Path(__file__).resolve().parent / "plots" / "3d"


def render_figure_image(fig, rotation: int, dpi: int) -> np.ndarray:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0)
    buffer.seek(0)
    image = mpimg.imread(buffer)
    if rotation == 0:
        return image
    return np.rot90(image, k=rotation // 90)


def save_rotated_pdf(image: np.ndarray, output_path: Path, dpi: int) -> None:
    height, width = image.shape[:2]
    fig_width = 4.0
    fig_height = fig_width * height / width
    image_fig, image_ax = plt.subplots(figsize=(fig_width, fig_height))
    image_ax.imshow(image)
    image_ax.axis("off")
    image_fig.savefig(output_path, format="pdf", dpi=dpi, bbox_inches="tight", pad_inches=0)
    plt.close(image_fig)


def save_figure(fig, output_stem: Path, rotation: int, output_format: str, dpi: int) -> list[Path]:
    saved_paths = []
    formats = ["png", "pdf"] if output_format == "both" else [output_format]
    rendered_image = None

    for fmt in formats:
        output_path = output_stem.with_suffix(f".{fmt}")
        if fmt == "png":
            if rotation == 0:
                fig.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0)
            else:
                rendered_image = render_figure_image(fig, rotation, dpi)
                mpimg.imsave(output_path, rendered_image)
        elif fmt == "pdf":
            if rotation == 0:
                fig.savefig(output_path, format="pdf", dpi=dpi, bbox_inches="tight", pad_inches=0)
            else:
                if rendered_image is None:
                    rendered_image = render_figure_image(fig, rotation, dpi)
                save_rotated_pdf(rendered_image, output_path, dpi)
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
    scene = load_scene(args.images_path, args.points_path)
    metric_scale = resolve_metric_scale(args.metric_scale, methods)
    bins = list(args.bins) if args.bins is not None else default_bins_for_scale(metric_scale)
    if len(args.colors) != len(bins) - 1:
        raise ValueError("--colors length must equal len(bins) - 1.")

    output_dir = resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _, points_centered, cameras_centered = compute_centered_scene(scene)
    xlim, ylim, zlim = resolve_axis_limits(args, points_centered, cameras_centered)
    elev, azim = resolve_view_angles(args)
    output_rotation = resolve_output_rotation(args)

    print(f"Generating 3D camera plots in {output_dir}")
    for method in methods:
        method_colors = [
            metric_to_color(
                resolve_metric_value_for_image(
                    image_name=image_name,
                    values_by_key=method.values_by_key,
                    prefix=args.object_prefix,
                    template=args.metric_key_template,
                    index_width=args.index_width,
                ),
                bins=bins,
                colors=args.colors,
                missing_color=args.missing_color,
            )
            for image_name in scene.image_names
        ]

        fig = plt.figure(figsize=tuple(args.figure_size))
        ax = fig.add_subplot(111, projection="3d")
        ax.scatter(
            points_centered[:, 0],
            points_centered[:, 1],
            points_centered[:, 2],
            c=scene.point_colors,
            marker=".",
            s=args.point_size,
            alpha=1.0,
        )

        for idx, camera_center in enumerate(cameras_centered):
            plot_camera_frustum(
                ax=ax,
                center=camera_center,
                rotation=scene.rotations[idx],
                scale_base=args.camera_base,
                height=args.camera_height,
                color=method_colors[idx],
            )

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_zlim(zlim)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()

        output_stem = output_dir / f"3D_{sanitize_filename(method.raw_name)}"
        saved_paths = save_figure(fig, output_stem, output_rotation, args.output_format, args.dpi)
        plt.close(fig)
        print(f"  saved {', '.join(str(path) for path in saved_paths)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
