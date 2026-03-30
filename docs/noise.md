# Observation Noise

Training with noise forces the agent to develop a robust policy that tolerates sensor uncertainty, rather than memorising exact trajectories.

## What is noised

### Position noise (`noise_std`)
Gaussian noise applied to the x/y position estimate at every simulation step:

```python
pose_x = true_x + N(0, noise_std)
pose_y = true_y + N(0, noise_std)
```

This simulates GPS or localisation drift. The agent must learn to act correctly even when its position estimate is slightly off.

### LIDAR noise (`lidar_noise_std`)
Independent Gaussian noise applied to every beam of the LIDAR scan:

```python
scan = clip(scan + N(0, lidar_noise_std, size=n_beams), 0, 30)
```

LIDAR is the primary sensor input, so this is the more impactful of the two. It simulates real-world rangefinder noise (~1–5 cm is typical for physical sensors).

## Default values

| Parameter | Default | Rationale |
|---|---|---|
| `noise_std` | `0.1 m` | 10 cm position uncertainty — realistic for indoor localisation |
| `lidar_noise_std` | `0.05 m` | 5 cm range noise — slightly above physical sensor specs for robustness margin |

## Configuring noise

In any config YAML:
```yaml
noise_std: 0.1        # set to 0 to disable position noise
lidar_noise_std: 0.05 # set to 0 to disable LIDAR noise
```

Configs without either key default to `0` (no noise), so older configs remain compatible.

## Effect on training

The agent sees noisy observations during both training and evaluation. This means:
- It cannot rely on precise position feedback to time braking points
- It must learn a policy with enough margin to handle perception errors
- Completion rates are slightly lower during early training but the final policy generalises better to real sensor conditions
