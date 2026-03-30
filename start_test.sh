#!/bin/bash
set -e

Xvfb :99 -screen 0 1280x900x24 &
sleep 1

x11vnc -display :99 -nopw -listen 0.0.0.0 -xkb -noxdamage &
sleep 1

websockify --web /usr/share/novnc 6080 localhost:5900 &
sleep 1

echo "================================================"
echo "  noVNC ready at http://localhost:6080/vnc.html"
echo "================================================"

cd /app
python3 /app/gui_test.py
