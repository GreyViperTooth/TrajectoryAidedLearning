#!/bin/bash
set -e

# Start virtual display
Xvfb :99 -screen 0 1280x800x24 &
sleep 1

# Start VNC server
x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -noxdamage &
sleep 1

# Start noVNC web server on port 6080
websockify --web /usr/share/novnc 6080 localhost:5900 &
sleep 1

echo "================================================"
echo "  noVNC ready at http://localhost:6080/vnc.html"
echo "================================================"

# Run test evaluation with visualization enabled
# RUN_FILE can be overridden at runtime: docker run -e RUN_FILE=TAL_speeds ...
RUN_FILE="${RUN_FILE:-Cth_speeds}"

cd /app
python3 - <<EOF
import TrajectoryAidedLearning.TestSimulation as ts
ts.SHOW_TEST = True
from TrajectoryAidedLearning.TestSimulation import TestSimulation
sim = TestSimulation("${RUN_FILE}")
sim.run_testing_evaluation()
EOF
