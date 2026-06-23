# syntax=docker/dockerfile:1
# Build context: tracking_models/sam3 (the SAM3 submodule)

FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# SAM3 requires PyTorch 2.7+ / CUDA 12.6+. The cu128 wheel bundles CUDA libs.
RUN pip install --upgrade pip && \
    pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128

# Install SAM3 from the submodule root (COPY . is the build context)
COPY . /opt/sam3
RUN pip install /opt/sam3 && \
    pip install opencv-python-headless einops pycocotools psutil

WORKDIR /workspace
CMD ["/bin/bash"]
