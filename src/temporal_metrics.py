"""Temporal stability metrics for per-frame IoU sequences.

These metrics summarise how a method's per-frame foreground IoU behaves *along a
scene* (an ordered sequence of frames belonging to the same video/scene). They
are computed from a 1-D sequence of per-frame IoU values ``IoU_1 .. IoU_T`` and
are deliberately decoupled from how those IoU values are produced.

Definitions (T = number of frames in the scene, denominator T-1 over adjacent
pairs):

    continuity  C_gamma  = (1/(T-1)) * sum_{t=2..T} 1[IoU_{t-1} >= gamma AND IoU_t >= gamma]
    flicker     FR_delta = (1/(T-1)) * sum_{t=2..T} 1[IoU_{t-1} - IoU_t > delta]
    drift       dIoU     = (1/(T-1)) * sum_{t=2..T} |IoU_t - IoU_{t-1}|
    volatility  sigma    = sample standard deviation (ddof=1) of {IoU_1 .. IoU_T}

Defaults: gamma = 0.5, delta = 0.2. Both are read from config/args, never
hard-coded at the call site.

Scenes with T < 2 have no adjacent pairs: continuity/flicker/drift are
*undefined* and returned as ``None`` (so callers exclude them from the
macro-average) rather than being silently reported as 1.0/100%. Volatility of a
single frame is also undefined (``None``).

The module also exposes ``continuity_buggy`` which reproduces the aggregation
bug Reviewer 4 flagged: it counts only *above->below* transitions, so a scene
whose IoU is below gamma at *every* frame records zero transitions and returns
~100% continuity instead of 0. It exists solely so the unit tests can pin the
bug and prove the corrected function differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

DEFAULT_GAMMA = 0.5
DEFAULT_DELTA = 0.2


@dataclass(frozen=True)
class TemporalConfig:
    """Thresholds for the temporal metrics, read from config/args."""

    gamma: float = DEFAULT_GAMMA
    delta: float = DEFAULT_DELTA

    @classmethod
    def from_mapping(cls, mapping: Optional[dict] = None) -> "TemporalConfig":
        mapping = mapping or {}
        return cls(
            gamma=float(mapping.get("gamma", DEFAULT_GAMMA)),
            delta=float(mapping.get("delta", DEFAULT_DELTA)),
        )


def _as_array(ious: Sequence[float]) -> np.ndarray:
    arr = np.asarray(list(ious), dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"IoU sequence must be 1-D, got shape {arr.shape}")
    return arr


def continuity(ious: Sequence[float], gamma: float = DEFAULT_GAMMA) -> Optional[float]:
    """Fraction of adjacent frame pairs where BOTH frames have IoU >= gamma.

    Returns 0.0 when no adjacent pair qualifies (e.g. every IoU < gamma), and
    ``None`` when T < 2 (undefined, excluded from aggregation).
    """
    arr = _as_array(ious)
    T = arr.size
    if T < 2:
        return None
    prev_ok = arr[:-1] >= gamma
    curr_ok = arr[1:] >= gamma
    return float(np.count_nonzero(prev_ok & curr_ok) / (T - 1))


def flicker(
    ious: Sequence[float],
    delta: float = DEFAULT_DELTA,
    symmetric: bool = False,
) -> Optional[float]:
    """Flicker rate over adjacent frame pairs.

    Manuscript definition (``symmetric=False``): fraction of pairs with a downward
    IoU *drop* strictly greater than delta (``IoU_{t-1} - IoU_t > delta``).

    Shipped-code behaviour (``symmetric=True``): fraction of pairs whose absolute
    change exceeds delta (``|IoU_t - IoU_{t-1}| > delta``) -- counts both upward
    and downward jumps. Recovered by reverse-engineering tab:temporal_styled.
    """
    arr = _as_array(ious)
    T = arr.size
    if T < 2:
        return None
    if symmetric:
        changes = np.abs(arr[1:] - arr[:-1])
    else:
        changes = arr[:-1] - arr[1:]
    return float(np.count_nonzero(changes > delta) / (T - 1))


def drift(ious: Sequence[float]) -> Optional[float]:
    """Mean absolute frame-to-frame IoU change."""
    arr = _as_array(ious)
    T = arr.size
    if T < 2:
        return None
    return float(np.mean(np.abs(np.diff(arr))))


def volatility(ious: Sequence[float]) -> Optional[float]:
    """Sample standard deviation (ddof=1) of the IoU sequence."""
    arr = _as_array(ious)
    T = arr.size
    if T < 2:
        return None
    return float(np.std(arr, ddof=1))


def scene_metrics(
    ious: Sequence[float], config: Optional[TemporalConfig] = None
) -> dict:
    """Compute all four temporal metrics for one scene's IoU sequence."""
    cfg = config or TemporalConfig()
    return {
        "continuity": continuity(ious, cfg.gamma),
        "flicker": flicker(ious, cfg.delta),
        "drift": drift(ious),
        "sigma": volatility(ious),
        "n_frames": int(_as_array(ious).size),
    }


def macro_average(scene_values: Sequence[dict]) -> dict:
    """Macro-average per-scene metrics across scenes, skipping undefined (None) scenes.

    Aggregation policy: compute each metric per scene first, then take the mean
    across scenes (each scene weighted equally). Scenes for which a metric is
    undefined (T < 2) are excluded from that metric's average.
    """
    keys = ("continuity", "flicker", "drift", "sigma")
    out: dict = {}
    for key in keys:
        vals = [s[key] for s in scene_values if s.get(key) is not None]
        out[key] = float(np.mean(vals)) if vals else None
    out["n_scenes"] = int(len(scene_values))
    out["n_scenes_used"] = int(
        sum(1 for s in scene_values if s.get("continuity") is not None)
    )
    return out


# ---------------------------------------------------------------------------
# Buggy reference implementation (the R4.2 bug) — kept ONLY for regression tests.
# Do not use in production aggregation.
# ---------------------------------------------------------------------------
def continuity_buggy(ious: Sequence[float], gamma: float = DEFAULT_GAMMA) -> float:
    """Reproduces the SHIPPED bug: continuity computed as 1 - drift, ignoring gamma.

    Reverse-engineered from the published Table~\\ref{tab:temporal_styled}: for
    every method and partition the reported continuity equals ``100 - drift``
    (i.e. ``1 - mean|IoU_t - IoU_{t-1}|``) and its per-scene std equals the drift
    std. The threshold ``gamma`` is never used, so a flat-but-bad sequence
    (FoodLMM on FKit: IoU == 0 at every frame -> drift 0) reports 1.0 (~100%)
    continuity even though no adjacent pair clears gamma. ``gamma`` is accepted
    only to mirror the corrected signature; it is intentionally unused here.
    """
    arr = _as_array(ious)
    T = arr.size
    if T < 2:
        return 1.0  # the buggy default: undefined treated as perfect continuity
    drift_val = float(np.mean(np.abs(np.diff(arr))))
    return 1.0 - drift_val
