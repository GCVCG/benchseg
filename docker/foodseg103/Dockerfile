# Specify base image
ARG  PYTORCH=1.13.1
ARG  CUDA=11.6
ARG  CUDNN=8
FROM pytorch/pytorch:${PYTORCH}-cuda${CUDA}-cudnn${CUDNN}-devel

# Set the working directory in the container
WORKDIR /workspace

RUN python -m pip install --no-cache-dir opencv-python-headless Pillow==9.2.0

# Copy the application files into the container
COPY . /workspace

# Qt dependencies
RUN apt-get update && apt-get install -y build-essential libgl1 libglib2.0-0 libxkbcommon-x11-0 '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev libfontconfig libdbus-1-3 mesa-utils libgl1-mesa-glx

RUN apt-get -y update && apt-get install -y wget imagemagick parallel

RUN pip install mmcv-full==1.7.0 -f https://download.openmmlab.com/mmcv/dist/cu116/torch1.13/index.html
RUN pip install opencv-python==4.8.0.76
RUN pip install timm==0.9.5
RUN pip install terminaltables==3.1.10
RUN pip install matplotlib==3.5.3
RUN pip install fvcore==0.1.5.post20221221
RUN pip install cloudpickle==2.2.1
RUN pip install omegaconf==2.3.0
RUN pip install pycocotools==2.0.6
RUN pip install pillow==9.1.0
RUN pip install werkzeug==2.2.3
RUN pip install chardet