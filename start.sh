#!/bin/bash
set -e

# Start virtual display
Xvfb :99 -screen 0 1280x800x24 &
sleep 1

# Start VNC server (no password for local dev)
x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -noxdamage &
sleep 1

# Start noVNC web server on port 6080
websockify --web /usr/share/novnc 6080 localhost:5900 &
sleep 1

echo "================================================"
echo "  noVNC ready at http://localhost:6080/vnc.html"
echo "================================================"

# Run training (must run from repo root so config/ and maps/ are found)
cd /app
python3 TrajectoryAidedLearning/TrainAgents.py
