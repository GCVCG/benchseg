"""Unit tests for the Stage 3 fusion rule Phi and re-seed schedule (CPU, no GPU).

Run: python -m pytest tests/test_fusion.py -q
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from fusion import fuse, iou, reseed_frames, FUSIONS, DEFAULT_TAU  # noqa: E402


def _sq(top, left, size, H=20, W=20):
    m = np.zeros((H, W), np.uint8)
    m[top:top + size, left:left + size] = 1
    return m


def test_iou_disjoint_overlap_empty():
    a, b = _sq(0, 0, 4), _sq(10, 10, 4)
    assert iou(a, b) == 0.0
    assert iou(a, a) == 1.0
    # half-overlap: A=[0:4,0:4], B=[2:6,0:4] -> inter 2 rows, union 6 rows of 4 cols
    A, B = _sq(0, 0, 4), _sq(2, 0, 4)
    assert abs(iou(A, B) - (2 * 4) / (6 * 4)) < 1e-9
    # empty vs empty -> identical (1.0) so the gate keeps propagated
    assert iou(np.zeros((5, 5)), np.zeros((5, 5))) == 1.0


def test_fuse_output_is_uint8_0_255():
    P, F = _sq(0, 0, 4), _sq(0, 0, 4)
    for rule in FUSIONS:
        out = fuse(P, F, rule)
        assert out.dtype == np.uint8
        assert set(np.unique(out)).issubset({0, 255})


def test_keep_propagated_returns_propagated():
    P, F = _sq(0, 0, 4), _sq(10, 10, 4)
    out = fuse(P, F, "keep_propagated")
    assert np.array_equal(out > 0, P > 0)


def test_accept_fresh_returns_fresh():
    P, F = _sq(0, 0, 4), _sq(10, 10, 4)
    out = fuse(P, F, "accept_fresh")
    assert np.array_equal(out > 0, F > 0)


def test_union():
    P, F = _sq(0, 0, 4), _sq(10, 10, 4)
    out = fuse(P, F, "union")
    assert np.array_equal(out > 0, (P > 0) | (F > 0))
    assert int(np.count_nonzero(out)) == int(np.count_nonzero(P)) + int(np.count_nonzero(F))


def test_overlap_gated_keeps_on_high_overlap_accepts_on_low():
    # identical masks -> IoU 1.0 >= tau -> keep propagated
    P = _sq(0, 0, 8)
    assert np.array_equal(fuse(P, P.copy(), "overlap_gated", tau=DEFAULT_TAU) > 0, P > 0)
    # disjoint masks -> IoU 0 < tau -> accept fresh
    F = _sq(10, 10, 4)
    assert np.array_equal(fuse(P, F, "overlap_gated", tau=DEFAULT_TAU) > 0, F > 0)
    # borderline: choose tau below and above the actual IoU and check the switch
    A, B = _sq(0, 0, 4), _sq(2, 0, 4)  # IoU = 1/3
    j = iou(A, B)
    assert np.array_equal(fuse(A, B, "overlap_gated", tau=j - 0.01) > 0, A > 0)  # keep
    assert np.array_equal(fuse(A, B, "overlap_gated", tau=j + 0.01) > 0, B > 0)  # accept


def test_reseed_schedule():
    avail = list(range(0, 100))  # every frame has a fresh mask
    assert reseed_frames(avail, 0, 0) == [0]        # K<=0 -> no re-seed
    assert reseed_frames(avail, None, 5) == [5]     # None -> no re-seed
    assert reseed_frames(avail, 30, 0) == [0, 30, 60, 90]
    assert reseed_frames(avail, 30, 5) == [5, 35, 65, 95]
    # sparse fresh masks: only some frames carry a non-empty mask
    sparse = [0, 30, 61, 90]  # 60 missing -> skipped, 61 not on grid -> skipped
    assert reseed_frames(sparse, 30, 0) == [0, 30, 90]
    # first always present; 37 not available and 40 is off the K-grid -> just [7]
    assert reseed_frames([7, 40], 30, 7) == [7]


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["python", "-m", "pytest", __file__, "-q"]))
