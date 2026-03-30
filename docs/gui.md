# GUI Test Controller

The interactive test controller lets you run a trained agent and watch it race, with live metrics in a browser window.

## Launching

```bash
docker run --rm --name tal-test -p 6080:6080 -v tal-data:/app/Data tal-racing /start_test.sh
```

Open `http://localhost:6080/vnc.html` and click **Connect**.

Two windows appear in the browser:
- **Control panel** (top-right) — map/speed picker, start/stop, metrics
- **Simulation window** — live racing visualisation, opens when you hit Start

## Controls

| Field | Description |
|---|---|
| **Map** | Select the circuit. Only maps with trained models available. |
| **Max Speed** | Speed cap in m/s. Options filtered by map — only trained speeds shown. |
| **Test Laps** | How many laps to evaluate before stopping automatically. |
| **▶ START TEST** | Loads the best available seed for the selected config and starts evaluation. |
| **■ STOP** | Stops the current run after the active lap finishes. |

## Metrics panel

| Metric | Description |
|---|---|
| **Status** | Idle / Starting / Running / Done / Stopped / Error |
| **Lap** | Current lap number out of total (e.g. `4 / 10`) |
| **Cur Time** | Elapsed time in the current lap |
| **Last Lap** | Time of the most recently completed lap |
| **Best Lap** | Fastest completed lap so far |
| **Avg Lap** | Mean of all completed lap times |
| **Completed** | Count of laps completed without crashing |
| **Crashes** | Count of laps that ended in a collision |
| **Completion Rate** | `Completed / Total` as a percentage, shown on a progress bar |

The **Lap Log** at the bottom records each lap with a ✓ (completed) or ✗ (crash) and the lap time.

## Seed selection

The GUI automatically picks the first available trained seed for the selected map/speed. Seed priority is `0 → 1 → 2 → ...`. If no model is found a clear error is shown rather than crashing.

## Available map/speed combinations

| Map | Available speeds |
|---|---|
| Spain (f1_esp) | 4, 5, 6, 7 m/s |
| Monaco (f1_mco) | 6 m/s |
| Austria (f1_aut) | 6 m/s |
| Great Britain (f1_gbr) | 6 m/s |

Only Spain has multi-speed models because `TAL_speeds` was trained on Spain only. All four maps have 6 m/s models from `TAL_maps`.
