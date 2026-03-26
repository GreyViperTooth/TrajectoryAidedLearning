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

cd /app

# Extended training: TAL reward across multiple speeds AND multiple tracks.
# This gives a controller that is robust at speeds 4-7 m/s across 4 F1 maps.
#
#   TAL_speeds : speeds 4, 5, 6, 7  on f1_esp  (4 seeds each = 16 runs)
#   TAL_maps   : maps  esp, mco, aut, gbr at speed 6 (5 seeds each = 20 runs)
#
# Total: ~36 training runs × ~15 min each on CPU ≈ 9 hours.
# Models are saved to the mounted Data volume after every run.

python3 - <<'PYEOF'
import sys, os
sys.path.insert(0, "/app")

import TrajectoryAidedLearning.TrainAgents as ta
import TrajectoryAidedLearning.TestSimulation as ts

# Enable visualisation so you can watch progress in the browser
ta.SHOW_TRAIN = True
ts.SHOW_TEST  = True

from TrajectoryAidedLearning.TrainAgents import TrainSimulation

CONFIGS = [
    "TAL_speeds",   # speed sweep on Spain track (4, 5, 6, 7 m/s)
    "TAL_maps",     # map sweep at speed 6 (Spain, Monaco, Austria, GB)
]

for cfg in CONFIGS:
    print(f"\n{'='*60}")
    print(f"  Starting config: {cfg}")
    print(f"{'='*60}\n")
    try:
        sim = TrainSimulation(cfg)
        sim.run_training_evaluation()
    except Exception as e:
        print(f"[ERROR] Config {cfg} failed: {e}", flush=True)
        import traceback; traceback.print_exc()
        print("Continuing with next config...", flush=True)

print("\nAll extended training complete.")
PYEOF
