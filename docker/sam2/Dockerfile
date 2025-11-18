FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* && git lfs install

# Install SAM2 OUTSIDE the bind mount so it won't be shadowed
WORKDIR /opt
RUN git clone https://github.com/facebookresearch/sam2.git

# Install the package (non-editable to avoid path issues)
RUN pip install --upgrade pip && \
    pip install /opt/sam2 && \
    pip install opencv-python-headless==4.10.* decord

# Work from your project root when you bind-mount
WORKDIR /workspace
CMD ["/bin/bash"]
