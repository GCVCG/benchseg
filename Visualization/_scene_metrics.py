"""Shared helpers for scene metrics visualization scripts."""

from __future__ import annotations

import csv
import glob
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class SceneData:
    camera_centers: np.ndarray
    rotations: np.ndarray
    image_names: list[str]
    points: np.ndarray
    point_colors: np.ndarray


@dataclass
class MethodMetrics:
    raw_name: str
    label: str
    path: Path
    values_by_key: dict[str, float]

    @property
    def values(self) -> np.ndarray:
        return np.array(list(self.values_by_key.values()), dtype=float)


DEFAULT_BINS_0_1 = [0.0, 0.5, 0.75, 0.95, 1.01]
DEFAULT_BINS_0_100 = [0.0, 50.0, 75.0, 95.0, 100.000001]


def quat_to_rotmat(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    q = np.array([qw, qx, qy, qz], dtype=float)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )


def parse_images_txt(images_path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    camera_centers = []
    rotations = []
    image_names = []

    with images_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 10:
                continue

            try:
                int(parts[0])
            except ValueError:
                continue

            qw, qx, qy, qz = map(float, parts[1:5])
            tx, ty, tz = map(float, parts[5:8])
            image_name = parts[9]

            rotation = quat_to_rotmat(qw, qx, qy, qz)
            translation = np.array([tx, ty, tz], dtype=float)
            camera_center = -rotation.T @ translation

            camera_centers.append(camera_center)
            rotations.append(rotation)
            image_names.append(image_name)

    return np.array(camera_centers), np.array(rotations), image_names


def parse_points3d_txt(points_path: Path) -> tuple[np.ndarray, np.ndarray]:
    coords = []
    colors = []

    with points_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 7:
                continue

            try:
                x, y, z = map(float, parts[1:4])
                r, g, b = map(int, parts[4:7])
            except ValueError:
                continue

            coords.append([x, y, z])
            colors.append([r / 255.0, g / 255.0, b / 255.0])

    return np.array(coords), np.array(colors)


def load_scene(images_path: str, points_path: str) -> SceneData:
    camera_centers, rotations, image_names = parse_images_txt(Path(images_path))
    points, point_colors = parse_points3d_txt(Path(points_path))
    if points.size == 0:
        raise ValueError(f"No 3D points were loaded from {points_path}")
    if camera_centers.size == 0:
        raise ValueError(f"No camera poses were loaded from {images_path}")
    return SceneData(
        camera_centers=camera_centers,
        rotations=rotations,
        image_names=image_names,
        points=points,
        point_colors=point_colors,
    )


def discover_metric_files(metrics_root: str, metrics_glob: str) -> list[Path]:
    metrics_path = Path(metrics_root)
    if metrics_path.is_file():
        if metrics_path.suffix.casefold() != ".csv":
            raise ValueError(f"Metrics input must be a CSV file: {metrics_path}")
        return [metrics_path]

    pattern = str(metrics_path / metrics_glob)
    files = [Path(path) for path in glob.glob(pattern, recursive=True)]
    files = [
        path
        for path in files
        if path.is_file() and path.suffix.casefold() == ".csv"
    ]
    if not files:
        raise FileNotFoundError(
            f"No CSV metrics files found under {metrics_root!r} with glob {metrics_glob!r}"
        )
    return sorted(files)


def normalize_metric_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def candidate_metric_names(metric_name: str) -> set[str]:
    normalized = normalize_metric_name(metric_name)
    names = {normalized}
    aliases = {
        "ap": {"map"},
        "map": {"ap"},
    }
    names.update(aliases.get(normalized, set()))
    return names


def load_methods_from_long_csv(
    metrics_path: Path,
    metric_name: str,
    key_prefix: str | None,
) -> list[MethodMetrics]:
    with metrics_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        lowered = {name.casefold(): name for name in fieldnames}

        method_column = lowered.get("method")
        frame_column = lowered.get("frame")
        if method_column is None or frame_column is None:
            return []

        metric_candidates = candidate_metric_names(metric_name)
        metric_column = next(
            (
                column
                for column in fieldnames
                if normalize_metric_name(column) in metric_candidates
            ),
            None,
        )
        if metric_column is None:
            return []

        methods: dict[str, dict[str, float]] = {}
        for row in reader:
            method_name = row.get(method_column, "").strip()
            frame_text = row.get(frame_column, "").strip()
            metric_text = row.get(metric_column, "").strip()
            if not method_name or not frame_text or not metric_text:
                continue

            try:
                frame_index = int(float(frame_text))
                metric_value = float(metric_text)
            except ValueError:
                continue

            key = f"{frame_index:03d}"
            if key_prefix:
                key = f"{key_prefix}_{frame_index:03d}"

            methods.setdefault(method_name, {})[key] = metric_value

    return [
        MethodMetrics(
            raw_name=method_name,
            label=method_name,
            path=metrics_path,
            values_by_key=values_by_key,
        )
        for method_name, values_by_key in methods.items()
        if values_by_key
    ]


def derive_method_name(metrics_path: Path) -> str:
    if metrics_path.stem == "metrics":
        return metrics_path.parent.name
    return metrics_path.stem


def load_label_map(path: str | None) -> dict[str, str]:
    if path is None:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(key): str(value) for key, value in payload.items()}


def load_method_order(path: str | None) -> list[str] | None:
    if path is None:
        return None
    entries = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                entries.append(line)
    return entries


def sort_methods(
    methods: list[MethodMetrics], method_order: list[str] | None
) -> list[MethodMetrics]:
    if not method_order:
        return sorted(methods, key=lambda method: method.label.casefold())

    rank = {entry: idx for idx, entry in enumerate(method_order)}

    def order_key(method: MethodMetrics) -> tuple[int, str]:
        if method.raw_name in rank:
            return rank[method.raw_name], method.label.casefold()
        if method.label in rank:
            return rank[method.label], method.label.casefold()
        return len(rank) + 1, method.label.casefold()

    return sorted(methods, key=order_key)


def load_methods(
    metrics_root: str,
    metrics_glob: str,
    metric_name: str,
    object_prefix: str | None,
    method_label_map: str | None,
    method_order_file: str | None,
) -> list[MethodMetrics]:
    label_map = load_label_map(method_label_map)
    methods = []

    for metrics_path in discover_metric_files(metrics_root, metrics_glob):
        csv_methods = load_methods_from_long_csv(
            metrics_path=metrics_path,
            metric_name=metric_name,
            key_prefix=object_prefix,
        )
        if not csv_methods:
            print(
                f"Skipping {metrics_path}: no long-form CSV values matched "
                f"metric '{metric_name}'."
            )
            continue
        for method in csv_methods:
            method.label = label_map.get(method.raw_name, method.raw_name)
        methods.extend(csv_methods)

    if not methods:
        raise ValueError(
            f"No methods with metric '{metric_name}' were found under {metrics_root}."
        )

    return sort_methods(methods, load_method_order(method_order_file))


def build_metric_key_candidates(
    image_name: str,
    prefix: str | None,
    template: str,
    index_width: int,
) -> list[str]:
    path = Path(image_name)
    stem = path.stem
    name = path.name
    digits_match = re.search(r"(\d+)$", stem)
    index = int(digits_match.group(1)) if digits_match else None

    if template != "auto":
        context = {
            "prefix": prefix or "",
            "index": index if index is not None else 0,
            "stem": stem,
            "name": name,
        }
        try:
            return [template.format(**context)]
        except Exception as exc:
            raise ValueError(f"Failed to format metric key template {template!r}: {exc}") from exc

    candidates = [stem, name]
    if index is not None:
        candidates.append(str(index))
        candidates.append(f"{index:0{index_width}d}")
        if prefix:
            candidates.append(f"{prefix}_{index}")
            candidates.append(f"{prefix}_{index:0{index_width}d}")

    if prefix and stem.startswith(f"{prefix}_"):
        candidates.append(stem)

    unique = []
    seen = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            unique.append(candidate)
            seen.add(candidate)
    return unique


def resolve_metric_value_for_image(
    image_name: str,
    values_by_key: dict[str, float],
    prefix: str | None,
    template: str,
    index_width: int,
) -> float | None:
    for candidate in build_metric_key_candidates(
        image_name=image_name,
        prefix=prefix,
        template=template,
        index_width=index_width,
    ):
        if candidate in values_by_key:
            return values_by_key[candidate]
    return None


def compute_centered_scene(scene: SceneData) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    center = scene.points.mean(axis=0)
    return center, scene.points - center, scene.camera_centers - center


def compute_axis_limits(
    points_centered: np.ndarray, cameras_centered: np.ndarray, margin_ratio: float
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    scene_coords = np.vstack([points_centered, cameras_centered])
    mins = scene_coords.min(axis=0)
    maxs = scene_coords.max(axis=0)
    spans = maxs - mins
    spans[spans == 0] = 1.0
    margin = spans * margin_ratio
    mins -= margin
    maxs += margin
    return (mins[0], maxs[0]), (mins[1], maxs[1]), (mins[2], maxs[2])


def metric_to_color(
    value: float | None, bins: list[float], colors: list[str], missing_color: str
) -> str:
    if value is None:
        return missing_color
    for idx in range(len(bins) - 1):
        if bins[idx] <= value < bins[idx + 1]:
            return colors[idx]
    if value == bins[-1]:
        return colors[-1]
    return missing_color


def infer_metric_scale(methods: list[MethodMetrics]) -> str:
    max_value = max(float(np.max(method.values)) for method in methods if method.values.size > 0)
    return "0-100" if max_value > 1.0 + 1e-9 else "0-1"


def resolve_metric_scale(requested_scale: str, methods: list[MethodMetrics]) -> str:
    if requested_scale == "auto":
        return infer_metric_scale(methods)
    return requested_scale


def default_bins_for_scale(metric_scale: str) -> list[float]:
    if metric_scale == "0-100":
        return list(DEFAULT_BINS_0_100)
    return list(DEFAULT_BINS_0_1)


def build_bin_labels(metric_name: str, bins: list[float]) -> list[str]:
    labels = []
    for idx in range(len(bins) - 1):
        left = bins[idx]
        right = bins[idx + 1]
        if idx == 0:
            labels.append(f"{metric_name} < {right:g}")
        elif idx == len(bins) - 2:
            labels.append(f"{metric_name} >= {left:g}")
        else:
            labels.append(f"{left:g}-{right:g}")
    return labels


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", name)
