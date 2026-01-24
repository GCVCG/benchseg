# syntax=docker/dockerfile:1

# Modern PyTorch/CUDA so NVRTC knows newer GPU archs (Ada/Hopper)
ARG BASE_IMAGE=pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime
FROM ${BASE_IMAGE} AS xmem2-base-inference

WORKDIR /app

# Build tooling
RUN python -m pip install --upgrade --no-cache-dir pip setuptools wheel

# Headless OpenCV + Pillow (keeps your pin)
RUN python -m pip install --no-cache-dir opencv-python-headless Pillow==9.2.0

# ---- Dependencies from the repo's requirements.txt (but ignore torch pins)
# The paths on the left of COPY are relative to the *build context* (the repo root),
# not to the Dockerfile location.
COPY requirements.txt /tmp/requirements.txt
RUN awk '!/^(torch|torchvision|torchaudio)([=<>].*)?$/' /tmp/requirements.txt > /tmp/requirements.notorch.txt && \
    python -m pip install --no-cache-dir -r /tmp/requirements.notorch.txt

# Copy the whole repo into the image
COPY . /app

# (Optional) If you want to predefine GPU archs for any native extensions:
# ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

# ---------------- GUI stage ----------------
FROM xmem2-base-inference AS xmem2-gui

# Qt / GUI dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential libgl1 libglib2.0-0 libxkbcommon-x11-0 '^libxcb.*-dev' \
      libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev \
      libxkbcommon-dev libxkbcommon-x11-dev libfontconfig libdbus-1-3 \
      mesa-utils libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

RUN /bin/bash -c 'gcc --version'

# Install demo deps but avoid re-pinning torch here as well
COPY requirements_demo.txt /tmp/requirements_demo.txt
RUN awk '!/^(torch|torchvision|torchaudio)([=<>].*)?$/' /tmp/requirements_demo.txt > /tmp/requirements_demo.notorch.txt && \
    python -m pip install --no-cache-dir -r /tmp/requirements_demo.notorch.txt

# To avoid error messages when launching PyQT
ENV LIBGL_ALWAYS_INDIRECT=1
