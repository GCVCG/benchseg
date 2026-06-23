"""Unit tests for temporal stability metrics.

Encodes the correct definitions of continuity (C_gamma), flicker (FR_delta),
drift (dIoU) and volatility (sigma-IoU), and pins the R4.2 aggregation bug:
a scene whose per-frame IoU is below gamma at EVERY frame must have continuity
exactly 0, but the buggy aggregator returns ~1.0 (100%).

Run: python -m pytest tests/test_temporal_metrics.py -v
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from temporal_metrics import (  # noqa: E402
    TemporalConfig,
    continuity,
    continuity_buggy,
    drift,
    flicker,
    macro_average,
    scene_metrics,
    volatility,
)

GAMMA = 0.5
DELTA = 0.2


# ---------------------------------------------------------------------------
# Case (i): all-zero IoU sequence -> continuity 0, flicker 0, drift 0, std 0
# ---------------------------------------------------------------------------
def test_all_zero_sequence_correct():
    ious = [0.0, 0.0, 0.0, 0.0]
    assert continuity(ious, GAMMA) == 0.0
    assert flicker(ious, DELTA) == 0.0
    assert drift(ious) == 0.0
    assert volatility(ious) == 0.0


def test_all_below_gamma_sequence_continuity_zero():
    # Every frame is below gamma=0.5 (the FoodLMM situation).
    ious = [0.10, 0.20, 0.15, 0.30, 0.05]
    assert continuity(ious, GAMMA) == 0.0


# ---------------------------------------------------------------------------
# The bug: buggy aggregator returns ~1.0 (100%) for an all-below-gamma scene.
# This test documents/repro-duces R4.2 and proves the corrected fn differs.
# ---------------------------------------------------------------------------
def test_bug_reproduction_all_zero_returns_one():
    ious = [0.0, 0.0, 0.0, 0.0]
    # Buggy implementation: ~100% continuity for a scene that never exceeds gamma.
    assert continuity_buggy(ious, GAMMA) == 1.0
    # Corrected implementation: exactly 0.
    assert continuity(ious, GAMMA) == 0.0
    assert continuity(ious, GAMMA) != continuity_buggy(ious, GAMMA)


def test_bug_reproduction_low_iou_method():
    # FoodLMM-on-FKit: IoU flat and below gamma -> buggy reports ~100%, correct 0%.
    flat_low = [0.1, 0.1, 0.1, 0.1]
    assert continuity_buggy(flat_low, GAMMA) == pytest.approx(1.0)  # 1 - drift(=0)
    assert continuity(flat_low, GAMMA) == 0.0
    # Even a noisy-but-low sequence reads far too high under the bug.
    noisy_low = [0.10, 0.18, 0.12, 0.20, 0.15]
    assert continuity_buggy(noisy_low, GAMMA) > 0.85  # bug: ignores gamma
    assert continuity(noisy_low, GAMMA) == 0.0         # correct: nothing clears gamma


def test_bug_is_one_minus_drift():
    # The shipped bug == 1 - drift exactly (the tab:temporal_styled identity).
    ious = [0.9, 0.8, 0.3, 0.7, 0.6]
    assert continuity_buggy(ious, GAMMA) == pytest.approx(1.0 - drift(ious))  # 0.725
    assert continuity(ious, GAMMA) == pytest.approx(0.50)  # correct, differs


# ---------------------------------------------------------------------------
# Case (ii): all IoU = 0.9 -> continuity 100%, flicker 0
# ---------------------------------------------------------------------------
def test_all_high_sequence():
    ious = [0.9, 0.9, 0.9, 0.9, 0.9]
    assert continuity(ious, GAMMA) == 1.0
    assert flicker(ious, DELTA) == 0.0
    assert drift(ious) == 0.0
    assert volatility(ious) == 0.0


# ---------------------------------------------------------------------------
# Case (iii): hand-checked mixed sequence with known answers.
#   ious = [0.9, 0.8, 0.3, 0.7, 0.6], gamma=0.5, delta=0.2, T=5, T-1=4
#   continuity: pairs both>=0.5 -> (0.9,0.8) yes, (0.8,0.3) no,
#               (0.3,0.7) no, (0.7,0.6) yes  => 2/4 = 0.50
#   flicker:    drops>0.2 -> 0.1 no, 0.5 yes, -0.4 no, 0.1 no => 1/4 = 0.25
#   drift:      |0.1|,|0.5|,|0.4|,|0.1| = 1.1 / 4 = 0.275
#   sigma:      sample std (ddof=1) of the 5 values, mean 0.66 => sqrt(0.212/4)
# ---------------------------------------------------------------------------
def test_mixed_sequence_hand_checked():
    ious = [0.9, 0.8, 0.3, 0.7, 0.6]
    assert continuity(ious, GAMMA) == pytest.approx(0.50)
    assert flicker(ious, DELTA) == pytest.approx(0.25)
    assert drift(ious) == pytest.approx(0.275)
    assert volatility(ious) == pytest.approx(math.sqrt(0.212 / 4))  # ~0.230217


# ---------------------------------------------------------------------------
# Thresholds: strict inequalities at the boundary.
# ---------------------------------------------------------------------------
def test_continuity_boundary_inclusive():
    # IoU exactly == gamma counts as "qualifying" (>=).
    assert continuity([0.5, 0.5], GAMMA) == 1.0


def test_flicker_strict_inequality():
    # A drop of exactly delta does NOT count (strictly greater than).
    assert flicker([0.5, 0.3], DELTA) == 0.0  # drop == 0.2, not > 0.2
    assert flicker([0.6, 0.3], DELTA) == 1.0  # drop == 0.3 > 0.2


# ---------------------------------------------------------------------------
# T < 2 guard: undefined -> None (excluded), not 1.0/100%.
# ---------------------------------------------------------------------------
def test_single_frame_is_undefined_not_one():
    assert continuity([0.9], GAMMA) is None
    assert flicker([0.9], DELTA) is None
    assert drift([0.9]) is None
    assert volatility([0.9]) is None
    # The buggy version returns 1.0 here too -- another way it inflates results.
    assert continuity_buggy([0.9], GAMMA) == 1.0


def test_empty_sequence_is_undefined():
    assert continuity([], GAMMA) is None
    assert volatility([]) is None


# ---------------------------------------------------------------------------
# Config-driven thresholds.
# ---------------------------------------------------------------------------
def test_config_defaults():
    cfg = TemporalConfig()
    assert cfg.gamma == 0.5
    assert cfg.delta == 0.2


def test_config_from_mapping():
    cfg = TemporalConfig.from_mapping({"gamma": 0.7, "delta": 0.1})
    assert cfg.gamma == 0.7
    assert cfg.delta == 0.1
    # continuity with a higher gamma excludes the 0.6 frame.
    assert continuity([0.9, 0.8, 0.6], cfg.gamma) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Macro-average excludes undefined scenes rather than scoring them 100%.
# ---------------------------------------------------------------------------
def test_macro_average_excludes_undefined_scenes():
    scenes = [
        scene_metrics([0.0, 0.0, 0.0], TemporalConfig()),  # continuity 0
        scene_metrics([0.9, 0.9, 0.9], TemporalConfig()),  # continuity 1
        scene_metrics([0.9], TemporalConfig()),            # undefined -> excluded
    ]
    agg = macro_average(scenes)
    assert agg["continuity"] == pytest.approx(0.5)  # mean(0, 1) over 2 used scenes
    assert agg["n_scenes"] == 3
    assert agg["n_scenes_used"] == 2
