# Training

## Running a training session

```bash
docker run -d --name tal-train -p 6080:6080 -v tal-data:/app/Data tal-racing
```

Open `http://localhost:6080/vnc.html` to watch the agent learn in real time.
Training logs stream to the container output:

```
12450::Lap Complete 18 -> FinalR: 1.00 -> LapTime 61.4 -> TotalReward: 99.2 -> Progress: 1.00
12510::Crashed -> FinalR: -1.00 -> LapTime 5.3 -> TotalReward: 4.1 -> Progress: 0.08
```

Check progress at any time:
```bash
docker logs tal-train 2>&1 | grep -E "Lap Complete|Crashed|Finished Training"
```

---

## Config file structure

Config files live in `config/`. Each file defines a sweep of training runs.

```yaml
test_name: "TAL_speeds"       # used as the save directory name

architecture: "fast"          # network architecture (fast = small MLP)
n_scans: 2                    # number of LIDAR scan subsets used as input
train_mode: "Std"
test_mode: "Std"

n: 4                          # number of random seeds to run
set_n: 1                      # set identifier (used in run name)
random_seed: 10000            # base seed; actual seed = random_seed + 10*n

noise_std: 0.1                # Gaussian position noise (metres), 0 to disable
lidar_noise_std: 0.05         # Gaussian LIDAR noise (metres), 0 to disable

n_train_steps: 100000         # training steps per run
n_test_laps: 20               # evaluation laps after training

map_name: "f1_esp"            # fixed map (used when runs vary speed)
reward: "TAL"                 # TAL | Cth | Progress

runs:                         # list of variable parameters across runs
  - max_speed: 4
  - max_speed: 5
  - max_speed: 6
  - max_speed: 7
```

To vary maps instead of speeds:
```yaml
max_speed: 6
runs:
  - map_name: "f1_esp"
  - map_name: "f1_mco"
  - map_name: "f1_aut"
  - map_name: "f1_gbr"
```

---

## Reward functions

| Value | Description |
|---|---|
| `TAL` | Trajectory-Aided Learning — penalises deviation from the optimal racing line. Best overall performance. |
| `Cth` | Cross-track heading reward — penalises lateral error and heading error from the racing line. |
| `Progress` | Pure progress along the track. Simple but struggles at high speeds. |

---

## Available maps

| ID | Circuit |
|---|---|
| `f1_esp` | Circuit de Barcelona-Catalunya (Spain) |
| `f1_mco` | Circuit de Monaco |
| `f1_aut` | Red Bull Ring (Austria) |
| `f1_gbr` | Silverstone (Great Britain) |

---

## Trained model paths

Weights are saved to the Docker volume at:
```
Data/Vehicles/<test_name>/<run_name>/<run_name>_actor.pth
Data/Vehicles/<test_name>/<run_name>/<run_name>_critic.pth
```

The run name encodes all parameters:
```
fast_Std_Std_TAL_f1_esp_6_5_2
 │    │    │   │   │   │ │ └─ seed (n=2)
 │    │    │   │   │   │ └─── set_n
 │    │    │   │   │   └───── max_speed
 │    │    │   │   └───────── map
 │    │    │   └───────────── reward
 │    │    └───────────────── test_mode
 │    └────────────────────── train_mode
 └─────────────────────────── architecture
```

---

## Extended training (all configs)

A `start_train_extended.sh` script runs all configs sequentially:

```bash
docker run -d --name tal-train-ext -p 6080:6080 -v tal-data:/app/Data tal-racing /start_train_extended.sh
```

This trains TAL_speeds (16 runs) then TAL_maps (20 runs) — approximately 18–20 hours on CPU.
