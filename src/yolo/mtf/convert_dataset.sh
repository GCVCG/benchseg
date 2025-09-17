#!/usr/bin/env bash
set -euo pipefail

rm -rf /workspace/data/mtf_yolo

DATA="/workspace/data/mtf_full"
OUT="/workspace/data/mtf_yolo"

mkdir -p "$OUT"/{images,binary-masks}

python /workspace/src/yolo_flatten.py "$DATA" "$OUT"

echo "Flattening done – $(ls "$OUT"/images | wc -l) images copied."

python /workspace/src/splits.py

mkdir -p "$OUT"/labels/{train, test, val}

python /workspace/src/to_yolo_seg.py