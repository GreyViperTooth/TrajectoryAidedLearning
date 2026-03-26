FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_GL_VERSION_OVERRIDE=3.3

RUN apt-get update && apt-get install -y \
    python3 python3-pip git \
    xvfb x11vnc novnc websockify \
    libgl1-mesa-glx libgl1-mesa-dri libgles2-mesa libglu1-mesa libosmesa6 \
    libxrandr2 libxi6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/GreyViperTooth/TrajectoryAidedLearning.git . && \
    mkdir -p Data/Vehicles && \
    sed -i 's/"_actor\.pth")/"_actor.pth", weights_only=False)/g' TrajectoryAidedLearning/Planners/AgentPlanners.py && \
    sed -i 's/^SHOW_TRAIN = False/SHOW_TRAIN = True/' TrajectoryAidedLearning/TrainAgents.py && \
    sed -i 's/if run\.noise_std > 0:/if getattr(run, "noise_std", 0) > 0:/g' TrajectoryAidedLearning/TestSimulation.py

RUN pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip3 install numpy "gym==0.21.0" Pillow "pyglet==1.5.27" matplotlib scipy pyyaml numba && \
    pip3 install -e .

COPY start.sh /start.sh
COPY start_test.sh /start_test.sh
COPY start_train_extended.sh /start_train_extended.sh
RUN chmod +x /start.sh /start_test.sh /start_train_extended.sh

EXPOSE 6080

CMD ["/start.sh"]
