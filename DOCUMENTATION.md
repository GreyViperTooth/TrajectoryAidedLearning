# TAL Racing — Project Documentation

**Based on:** [High-speed Autonomous Racing using Trajectory-Aided Deep Reinforcement Learning](https://ieeexplore.ieee.org/document/10182327) — Evans et al., IEEE RA-L 2023

**Fork:** [github.com/GreyViperTooth/TrajectoryAidedLearning](https://github.com/GreyViperTooth/TrajectoryAidedLearning)

---

## What is this?

TAL trains a reinforcement learning agent (TD3 algorithm) to race an F1-scale car at high speed around real F1 circuits. The key idea is incorporating the optimal racing line into the reward signal — the agent is rewarded for following the racing line quickly rather than just making raw forward progress. This results in realistic racing behaviour: braking into corners, carrying speed on straights.

This fork adds:
- **Docker environment** — runs anywhere with Docker, visualised in a browser via noVNC
- **Observation noise** — Gaussian noise on position and LIDAR for robust controller training
- **Interactive GUI** — browser-based test runner with live metrics

---

## Setup

### Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux)

### Build once
```bash
git clone https://github.com/GreyViperTooth/TrajectoryAidedLearning.git
cd TrajectoryAidedLearning
docker build -t tal-racing .
```

The build clones the repo inside the image, installs all Python dependencies, and sets up the virtual display stack. Takes ~10–15 minutes the first time.

### Named volume for persistence
All trained weights are stored in a Docker named volume. Always include `-v tal-data:/app/Data` so weights survive container restarts:
```bash
docker volume create tal-data   # only needed once
```

---

## Running

### Train an agent
```bash
docker run -d --name tal-train -p 6080:6080 -v tal-data:/app/Data tal-racing
```
Watch training live at `http://localhost:6080/vnc.html`.

### Extended training (all configs)
```bash
docker run -d --name tal-train-ext -p 6080:6080 -v tal-data:/app/Data tal-racing /start_train_extended.sh
```
Runs TAL_speeds (16 runs) then TAL_maps (20 runs) — ~18–20 hours on CPU.

### Test with GUI controller
```bash
docker run --rm --name tal-test -p 6080:6080 -v tal-data:/app/Data tal-racing /start_test.sh
```
Open `http://localhost:6080/vnc.html` → click **Connect**.

### Monitor training logs
```bash
docker logs tal-train 2>&1 | grep -E "Lap Complete|Crashed|Finished Training"
```

---

## Training

### How training works
Each run trains a fresh TD3 agent for 100,000 steps. After training, the agent is evaluated over 20 laps and the completion rate is recorded. Multiple random seeds are used per config to get statistically reliable results.

Training output per step:
```
12450::Lap Complete 18 -> FinalR: 1.00 -> LapTime 61.4 -> TotalReward: 99.2 -> Progress: 1.00
12510::Crashed       -> FinalR: -1.00 -> LapTime 5.3  -> TotalReward: 4.1  -> Progress: 0.08
```

### Config files (`config/`)

| File | Purpose | Maps | Speeds |
|---|---|---|---|
| `TAL_speeds.yaml` | Speed sensitivity study | Spain only | 4, 5, 6, 7 m/s |
| `TAL_maps.yaml` | Cross-track generalisation | All 4 maps | 6 m/s |
| `Cth_speeds.yaml` | CTH baseline for comparison | Spain only | 4–8 m/s |

### Config file format
```yaml
test_name: "TAL_speeds"       # save directory name

architecture: "fast"          # network size (fast = small MLP)
n_scans: 2                    # LIDAR scan subsets used as input
train_mode: "Std"
test_mode: "Std"

n: 4                          # number of random seeds
set_n: 1                      # set identifier (part of run name)
random_seed: 10000            # base seed; actual = random_seed + 10*n

noise_std: 0.1                # position noise in metres (0 = off)
lidar_noise_std: 0.05         # LIDAR noise in metres (0 = off)

n_train_steps: 100000
n_test_laps: 20

map_name: "f1_esp"            # fixed map (when runs vary speed)
reward: "TAL"                 # TAL | Cth | Progress

runs:
  - max_speed: 4
  - max_speed: 5
  - max_speed: 6
  - max_speed: 7
```

To vary maps instead of speeds, swap the `runs` block:
```yaml
max_speed: 6
runs:
  - map_name: "f1_esp"
  - map_name: "f1_mco"
  - map_name: "f1_aut"
  - map_name: "f1_gbr"
```

### Reward functions

| Value | Description |
|---|---|
| `TAL` | Trajectory-Aided Learning — penalises deviation from the optimal racing line. Best overall. |
| `Cth` | Cross-track heading — penalises lateral and heading error. Good baseline. |
| `Progress` | Raw track progress. Simple but fails at high speeds. |

### Available maps

| ID | Circuit |
|---|---|
| `f1_esp` | Circuit de Barcelona-Catalunya (Spain) |
| `f1_mco` | Circuit de Monaco |
| `f1_aut` | Red Bull Ring (Austria) |
| `f1_gbr` | Silverstone (Great Britain) |

### Trained model paths
Weights are saved inside the `tal-data` volume at:
```
Data/Vehicles/<test_name>/<run_name>/<run_name>_actor.pth
```

The run name encodes all parameters:
```
fast_Std_Std_TAL_f1_esp_6_5_2
 │    │    │   │   │   │ │ └── seed (n=2)
 │    │    │   │   │   │ └──── set_n
 │    │    │   │   │   └────── max_speed
 │    │    │   │   └────────── map
 │    │    │   └────────────── reward
 │    │    └────────────────── test_mode
 │    └─────────────────────── train_mode
 └──────────────────────────── architecture
```

---

## Observation Noise

Noise is applied at every simulation step during both training and evaluation, forcing the agent to learn a policy robust to sensor uncertainty.

### Position noise (`noise_std`)
Gaussian noise on the x/y position estimate:
```
pose_x = true_x + N(0, noise_std)
pose_y = true_y + N(0, noise_std)
```
Simulates GPS or localisation drift. Default: **0.1 m**.

### LIDAR noise (`lidar_noise_std`)
Independent Gaussian noise on every beam of the LIDAR scan:
```
scan = clip(scan + N(0, lidar_noise_std, size=n_beams), 0, 30)
```
LIDAR is the primary sensor input, so this has the most impact. Simulates real rangefinder noise. Default: **0.05 m**.

### Configuring noise
In any config YAML:
```yaml
noise_std: 0.1        # set to 0 to disable
lidar_noise_std: 0.05 # set to 0 to disable
```
Configs without either key default to 0 — old configs remain compatible.

---

## GUI Test Controller

### Launch
```bash
docker run --rm --name tal-test -p 6080:6080 -v tal-data:/app/Data tal-racing /start_test.sh
```
Open `http://localhost:6080/vnc.html` → Connect.

Two windows appear in the browser:
- **Control panel** — map/speed picker, metrics, lap log
- **Simulation window** — live racing view, opens when you hit Start

### Controls

| Control | Description |
|---|---|
| **Map** | Select the circuit. Options with no trained model are still shown but will error gracefully. |
| **Max Speed** | Speed cap in m/s. Filtered to only show trained speeds for the selected map. |
| **Test Laps** | Number of laps before auto-stop (1–50). |
| **▶ START TEST** | Loads the best available seed and starts evaluation. |
| **■ STOP** | Stops after the current lap finishes. |

### Live metrics

| Metric | Description |
|---|---|
| Status | Idle / Starting / Running / Done / Stopped / Error |
| Lap | Current lap out of total (e.g. `4 / 10`) |
| Cur Time | Elapsed time in the current lap |
| Last Lap | Time of the most recently finished lap |
| Best Lap | Fastest completed lap so far |
| Avg Lap | Mean of all completed lap times |
| Completed | Laps finished without crashing |
| Crashes | Laps that ended in collision |
| Completion Rate | Completed / Total as %, shown on a progress bar |

The **Lap Log** records each lap with ✓ (complete) or ✗ (crash) and the lap time.

### Available map/speed combinations

| Map | Available speeds |
|---|---|
| Spain (f1_esp) | 4, 5, 6, 7 m/s |
| Monaco (f1_mco) | 6 m/s |
| Austria (f1_aut) | 6 m/s |
| Great Britain (f1_gbr) | 6 m/s |

Only Spain has multi-speed models because `TAL_speeds` was trained on Spain only.

---

## Trained Models Summary

37 models total across 3 training runs.

### TAL_speeds — Spain, 4 speeds × 4 seeds (16 models)

| Speed | Seed 0 | Seed 1 | Seed 2 | Seed 3 |
|---|---|---|---|---|
| 4 m/s | 95% | 90% | 20% | 100% |
| 5 m/s | 90% | 95% | 100% | 60% |
| 6 m/s | 100% | 85% | 95% | 100% |
| 7 m/s | 90% | 95% | 0% | 90% |

### TAL_maps — All 4 circuits, 6 m/s, 5 seeds (20 models)

| Map | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Seed 4 |
|---|---|---|---|---|---|
| Spain | — | — | 95% | 55% | 95% |
| Monaco | — | — | 70% | 70% | 100% |
| Austria | — | — | 95% | 85% | 100% |
| Great Britain | — | — | 100% | 85% | 100% |

### Cth_speeds — legacy baseline (1 model)
`fast_Std_Std_Cth_f1_esp_7_1_0` — CTH reward, Spain, 7 m/s, seed 0.

---

## Migrating to a New Machine

### Transfer trained weights (Docker volume)

**Export from source machine:**
```bash
# Windows (Command Prompt)
docker run --rm -v tal-data:/data -v "C:/Users/<username>/Desktop:/backup" ubuntu tar czf /backup/tal-data.tar.gz -C /data .

# Linux/Mac
docker run --rm -v tal-data:/data -v ~/Desktop:/backup ubuntu tar czf /backup/tal-data.tar.gz -C /data .
```

**Import on target machine:**
```bash
docker volume create tal-data
docker run --rm -v tal-data:/data -v ~/Desktop:/backup ubuntu tar xzf /backup/tal-data.tar.gz -C /data
```

**Verify:**
```bash
docker run --rm -v tal-data:/data ubuntu find /data/Vehicles -name "*_actor.pth" | wc -l
# Should print 37
```

### Fresh Ubuntu 22.04 setup
```bash
# Install Docker
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
sudo usermod -aG docker $USER && newgrp docker

# Install VS Code
sudo snap install --classic code

# Clone and build
git clone https://github.com/GreyViperTooth/TrajectoryAidedLearning.git
cd TrajectoryAidedLearning
code .                        # open in VS Code
docker build -t tal-racing .  # ~10-15 min first time

# Run demo
docker run --rm --name tal-demo -p 6080:6080 -v tal-data:/app/Data tal-racing /start_test.sh
# Open http://localhost:6080/vnc.html
```

> On Linux you can skip noVNC entirely and pass the host display directly:
> `docker run ... -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix tal-racing /start_test.sh`
> This gives a native window instead of a browser tab.

---

## Architecture Overview

```
TrajectoryAidedLearning/
├── TrainAgents.py          # Training entry point — select config here
├── TestSimulation.py       # Base simulation loop, observation builder, noise
├── Planners/
│   ├── AgentPlanners.py    # TD3 agent wrappers (trainer + tester)
│   └── PurePursuit.py      # Classical baseline controller
├── Utils/
│   ├── TD3.py              # TD3 algorithm (actor, critic, replay buffer)
│   ├── RewardSignals.py    # TAL, CTH, Progress reward implementations
│   ├── StdTrack.py         # Racing line representation and progress calc
│   ├── RacingTrack.py      # Track geometry utilities
│   └── utils.py            # Config loading, run list setup
└── f110_gym/               # Bundled F1Tenth simulator
    ├── f110_env.py         # OpenAI Gym environment
    ├── dynamic_models.py   # Vehicle physics
    ├── laser_models.py     # LIDAR simulation
    └── rendering.py        # Pyglet visualisation

config/                     # Training configuration YAML files
gui_test.py                 # Interactive browser GUI controller
Dockerfile                  # Ubuntu 22.04 container definition
start.sh                    # Container startup for training
start_test.sh               # Container startup for GUI test
start_train_extended.sh     # Container startup for full training sweep
```

---

## Citation

```bibtex
@ARTICLE{10182327,
    author={Evans, Benjamin David and Engelbrecht, Herman Arnold and Jordaan, Hendrik Willem},
    journal={IEEE Robotics and Automation Letters},
    title={High-Speed Autonomous Racing Using Trajectory-Aided Deep Reinforcement Learning},
    year={2023},
    volume={8},
    number={9},
    pages={5353-5359},
    doi={10.1109/LRA.2023.3295252}
}
```
