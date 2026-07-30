"""Stage 3 fusion rule Phi and the re-seeding schedule K for the hybrid pipeline.

This makes explicit the two Stage 3 controls that Reviewer 1 asked us to ablate.
Both act ONLY at re-seed frames; between re-seeds the tracker propagates as before.

Fusion rule Phi(P, F) -> the mask emitted (and re-seeded) at a re-seed frame,
given the propagated mask P (tracker estimate at that frame) and the fresh
per-frame segmentor mask F:

    overlap_gated  : F if IoU(P, F) < tau else P   (accept fresh only on disagreement)
    keep_propagated: P                             (never accept fresh == no fusion)
    accept_fresh   : F                             (always replace with the fresh mask)
    union          : P | F                         (elementwise union)

Re-seed schedule for interval K, starting from the first seeded frame f0:

    {f0, f0+K, f0+2K, ...}   (K <= 0 or None -> {f0} only, i.e. no re-seeding)

`keep_propagated` and `K<=0` both reduce to the current single-seed pipeline, so
the default behaviour is recoverable exactly (see track_pipeline_reseed.py, which
short-circuits keep_propagated to the untouched track_pipeline.py path).

Masks are accepted as bool or uint8 (0/255) arrays of equal shape; fuse() returns
uint8 in {0, 255} to match every other mask written in this repo.
"""
import numpy as np

FUSIONS = ("overlap_gated", "keep_propagated", "accept_fresh", "union")
DEFAULT_TAU = 0.5


def _b(m):
    return np.asarray(m) > 0


def iou(a, b):
    """Binary foreground IoU. Empty-vs-empty is treated as identical (1.0),
    matching per_frame_iou.iou_binary's empty-union convention only inverted for
    the gate: two empty masks agree, so the gate should keep the propagated one."""
    a, b = _b(a), _b(b)
    inter = int(np.count_nonzero(a & b))
    union = int(np.count_nonzero(a | b))
    return inter / union if union else 1.0


def fuse(propagated, fresh, rule="keep_propagated", tau=DEFAULT_TAU):
    """Combine a propagated mask and a fresh mask under rule Phi. Returns uint8 0/255."""
    P, F = _b(propagated), _b(fresh)
    if P.shape != F.shape:
        raise ValueError(f"mask shape mismatch: propagated {P.shape} vs fresh {F.shape}")
    if rule == "keep_propagated":
        out = P
    elif rule == "accept_fresh":
        out = F
    elif rule == "union":
        out = P | F
    elif rule == "overlap_gated":
        out = F if iou(P, F) < tau else P
    else:
        raise ValueError(f"unknown fusion rule {rule!r}; choose from {FUSIONS}")
    return out.astype(np.uint8) * 255


def reseed_frames(available, k, first):
    """Frame indices to re-seed at: {first, first+k, first+2k, ...} kept to those
    that actually carry a non-empty fresh mask (`available`, any iterable of ints).

    k None or <= 0 -> [first] (no re-seeding). `first` is always included."""
    avail = set(int(i) for i in available)
    if first not in avail:
        # first must be a real seed frame; caller guarantees it, guard anyway
        avail.add(int(first))
    if not k or k <= 0:
        return [int(first)]
    hi = max(avail)
    out, f = [], int(first)
    while f <= hi:
        if f in avail:
            out.append(f)
        f += k
    return out
