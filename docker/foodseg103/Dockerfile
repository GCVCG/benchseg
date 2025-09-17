########  Base image  ########
ARG PYTORCH=1.13.1    # default build-time vars
ARG CUDA=11.8
ARG CUDNN=8

FROM nvidia/cuda:${CUDA}.0-cudnn${CUDNN}-devel-ubuntu22.04

# ── Redeclare args so they’re in-scope for this stage ──
ARG PYTORCH
ARG CUDA
ARG CUDNN

########  1 • Add Python & pip  ########
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

########  2 • Install PyTorch/cu118 wheels  ########
RUN pip install --no-cache-dir \
        torch==${PYTORCH}+cu117 \
        torchvision==0.14.1+cu117 \
        torchaudio==0.13.1 \
        --index-url https://download.pytorch.org/whl/cu117

########  3 • Your original layers  ########
WORKDIR /workspace
COPY . /workspace

# Qt & system deps (unchanged)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 libxkbcommon-x11-0 \
        '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev \
        libxi-dev libxkbcommon-dev libxkbcommon-x11-dev libfontconfig \
        libdbus-1-3 mesa-utils libgl1-mesa-glx libgl1-mesa-dev wget \
        imagemagick parallel && \
    rm -rf /var/lib/apt/lists/*

# Python deps (deduplicated)
RUN pip install --no-cache-dir \
        numpy==1.26.4 \
        opencv-python-headless==4.8.0.76 \
        Pillow==9.2.0 \
        mmcv-full==1.7.0 -f https://download.openmmlab.com/mmcv/dist/cu117/torch1.13/index.html \
        timm==0.9.5 terminaltables==3.1.10 matplotlib==3.5.3 \
        fvcore==0.1.5.post20221221 cloudpickle==2.2.1 \
        omegaconf==2.3.0 pycocotools==2.0.6 \
        werkzeug==2.2.3 chardet "pandas<2.2.2" \
        scikit-image
