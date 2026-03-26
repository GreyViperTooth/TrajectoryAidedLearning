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

# Discover all trained models in the Data volume and only test those.
# Creates a temporary config so we never crash on missing weights.
python3 - <<'PYEOF'
import os, yaml, glob

import TrajectoryAidedLearning.TestSimulation as ts
ts.SHOW_TEST = True
from TrajectoryAidedLearning.TestSimulation import TestSimulation

# Find every actor checkpoint that actually exists
# Path structure: Data/Vehicles/<config>/<run_name>/<run_name>_actor.pth
trained = glob.glob("/app/Data/Vehicles/*/*/*_actor.pth")
if not trained:
    print("No trained models found in Data/Vehicles/. Run training first.")
    exit(1)

print(f"Found {len(trained)} trained model(s):")
for p in trained:
    print(" ", p)

# Load the base config and filter runs to only those with saved weights
base_cfg_name = os.environ.get("RUN_FILE", "Cth_speeds")
cfg_path = f"/app/config/{base_cfg_name}.yaml"
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)

# Build a set of run_names that have weights
trained_names = set()
for path in trained:
    # path is like Data/Vehicles/Cth_speeds/fast_Std_Std_Cth_f1_esp_7_1_0/..._actor.pth
    trained_names.add(os.path.basename(os.path.dirname(path)))

print(f"\nTesting {len(trained_names)} run(s): {trained_names}\n")

# Write a temporary filtered config
tmp_cfg = dict(cfg)
original_runs = cfg.get("Runs", [{"max_speed": cfg.get("max_speed")}])
original_n    = cfg.get("n", 1)

# Try all speed/n combos and keep only what's trained
from types import SimpleNamespace
arch   = cfg.get("Architecture", "fast")
mode   = cfg.get("Training_mode", "Std")
tmode  = cfg.get("Test_mode", "Std")
reward = cfg.get("Reward", "Cth")
map_n  = cfg.get("Map", "f1_esp")
set_n  = cfg.get("Set", 1)

filtered_runs = []
filtered_ns   = []
for run in original_runs:
    speed = run.get("max_speed", cfg.get("max_speed"))
    for ni in range(original_n):
        run_name = f"{arch}_{mode}_{tmode}_{reward}_{map_n}_{speed}_{set_n}_{ni}"
        if run_name in trained_names:
            filtered_runs.append(run)
            filtered_ns.append(ni)
            break  # one match per speed is enough

if not filtered_runs:
    # Fall back: just run the first trained model directly
    first = sorted(trained_names)[0]
    print(f"Could not match config automatically. Running {first} directly.\n")
    tmp_cfg["Runs"] = [original_runs[0]]
    tmp_cfg["n"] = 1
else:
    tmp_cfg["Runs"] = filtered_runs
    tmp_cfg["n"] = 1  # one seed per speed

tmp_path = "/app/config/_test_trained.yaml"
tmp_cfg["Test"] = "_test_trained"
with open(tmp_path, "w") as f:
    yaml.dump(tmp_cfg, f)

sim = TestSimulation("_test_trained")
sim.run_testing_evaluation()
PYEOF
