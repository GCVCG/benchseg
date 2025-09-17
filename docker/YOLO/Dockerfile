# FROM ultralytics/ultralytics:8.3.65-cuda12
FROM ultralytics/ultralytics:8.3.158

# ---- Python layer (single RUN) ----
RUN pip install --no-cache-dir \
        "numpy<2.0" \
        opencv-python-headless==4.10.0.82 \
        scikit-learn matplotlib albumentations==1.4.3 \
        torchmetrics

# ---- System layer ----
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nano && \
    rm -rf /var/lib/apt/lists/*

# ---- Ultralytics settings ----
WORKDIR /workspace

RUN yolo settings runs_dir=/workspace/runs

ENTRYPOINT ["/bin/bash","-l", "-c"]
