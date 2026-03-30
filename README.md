# Trajectory-Aided Learning — Extended Fork

Based on the paper [High-speed Autonomous Racing using Trajectory-Aided Deep Reinforcement Learning](https://ieeexplore.ieee.org/document/10182327) (Evans et al., IEEE RA-L 2023).

This fork extends the original with:
- **Dockerised environment** — runs on any machine with Docker, visualised in a browser via noVNC
- **Observation noise** — Gaussian noise on position and LIDAR readings for robust controller training
- **Interactive GUI** — browser-based test runner with live metrics and lap log

---

## How it works

TAL trains a TD3 agent to race at high speed by incorporating the optimal racing line into the reward signal. Rather than rewarding raw progress, the agent is penalised for deviating from the trajectory and rewarded for completing laps fast.

![TAL reward visualisation](Data/tal_calculation.png)

TAL significantly outperforms baseline rewards at high speeds where pure progress rewards fail.

![TAL vs baseline](Data/TAL_vs_baseline_reward.png)

---

## Quick start

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/GreyViperTooth/TrajectoryAidedLearning.git
cd TrajectoryAidedLearning

docker build -t tal-racing .
```

### Train
```bash
docker run -d --name tal-train -p 6080:6080 -v tal-data:/app/Data tal-racing
```

### Test (interactive GUI)
```bash
docker run --rm --name tal-test -p 6080:6080 -v tal-data:/app/Data tal-racing /start_test.sh
```

Open **`http://localhost:6080/vnc.html`** and click Connect.
The training/test simulation appears as a live window in the browser.

> **Note:** `-v tal-data:/app/Data` mounts a named Docker volume so trained weights persist across container restarts.

---

## Training configurations

| Config file | What it trains | Maps | Speeds |
|---|---|---|---|
| `TAL_speeds.yaml` | Speed sensitivity study | Spain (f1_esp) | 4, 5, 6, 7 m/s |
| `TAL_maps.yaml` | Cross-track generalisation | Spain, Monaco, Austria, GB | 6 m/s |
| `Cth_speeds.yaml` | CTH baseline (comparison) | Spain | 4–8 m/s |

Each config runs 4–5 random seeds for statistical robustness. Training one full config takes ~8–10 hours on CPU.

See [`docs/training.md`](docs/training.md) for configuration options and how to add new tracks or speeds.

---

## Observation noise

This fork adds configurable sensor noise to train more robust controllers:

| Parameter | Default | Effect |
|---|---|---|
| `noise_std` | `0.1 m` | Gaussian noise on x/y position estimate |
| `lidar_noise_std` | `0.05 m` | Gaussian noise on each LIDAR range reading |

Noise is active during both training and evaluation. Set either to `0` in the config YAML to disable. See [`docs/noise.md`](docs/noise.md).

---

## GUI test controller

After training, launch `/start_test.sh` to open the interactive controller in the browser:

- Select map and max speed from dropdowns
- Set number of test laps
- Start / Stop the agent mid-run
- Live metrics: current lap time, best/avg lap, completion rate, crash count
- Scrolling lap log with ✓/✗ per lap

See [`docs/gui.md`](docs/gui.md) for details.

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
