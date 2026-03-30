#!/usr/bin/env python3
"""TAL Racing Controller — interactive GUI test runner."""

import os, sys, threading, queue, time
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

sys.path.insert(0, "/app")

import TrajectoryAidedLearning.TestSimulation as _ts_mod
_ts_mod.SHOW_TEST = True
from TrajectoryAidedLearning.TestSimulation import TestSimulation
from TrajectoryAidedLearning.Utils.utils import load_conf

# ─── model registry ──────────────────────────────────────────────────────────

MAP_LABELS = {
    "f1_esp": "Spain  (Barcelona)",
    "f1_mco": "Monaco",
    "f1_aut": "Austria  (Red Bull Ring)",
    "f1_gbr": "Great Britain  (Silverstone)",
}

AVAILABLE_SPEEDS = {
    "f1_esp": [4, 5, 6, 7],
    "f1_mco": [6],
    "f1_aut": [6],
    "f1_gbr": [6],
}

# (map_name, speed) → (test_name, set_n, n_seeds)
_REGISTRY = {
    ("f1_esp", 4): ("TAL_speeds",   1, 4),
    ("f1_esp", 5): ("TAL_speeds",   1, 4),
    ("f1_esp", 6): ("TAL_mapsTest", 5, 5),
    ("f1_esp", 7): ("TAL_speeds",   1, 4),
    ("f1_mco", 6): ("TAL_mapsTest", 5, 5),
    ("f1_aut", 6): ("TAL_mapsTest", 5, 5),
    ("f1_gbr", 6): ("TAL_mapsTest", 5, 5),
}

DATA_ROOT = "/app/Data/Vehicles"


def _run_name(map_name, speed, set_n, seed):
    return f"fast_Std_Std_TAL_{map_name}_{speed}_{set_n}_{seed}"


def find_best_seed(map_name, speed):
    """Return (seed, test_name, set_n) for the first available trained model."""
    key = (map_name, speed)
    if key not in _REGISTRY:
        return None
    test_name, set_n, n_seeds = _REGISTRY[key]
    for seed in range(n_seeds):
        rn = _run_name(map_name, speed, set_n, seed)
        path = os.path.join(DATA_ROOT, test_name, rn, f"{rn}_actor.pth")
        if os.path.exists(path):
            return seed, test_name, set_n
    return None


def build_run(map_name, speed, n_laps, seed, test_name, set_n):
    rn = _run_name(map_name, speed, set_n, seed)
    return SimpleNamespace(
        max_speed=speed,
        test_name=test_name,
        architecture="fast",
        n_scans=2,
        train_mode="Std",
        test_mode="Std",
        n=seed,
        set_n=set_n,
        random_seed=10000,
        noise_std=0.1,
        lidar_noise_std=0.05,
        n_train_steps=100000,
        n_test_laps=n_laps,
        map_name=map_name,
        reward="TAL",
        run_name=rn,
        path=f"{test_name}/",
    )


# ─── instrumented simulation ──────────────────────────────────────────────────

class GUISim(TestSimulation):
    """TestSimulation that emits metrics to a queue and respects a stop flag."""

    def __init__(self, run, conf, metrics_q, stop_evt):
        # Bypass file-based init; set fields directly
        self.run_data = [run]
        self.conf = conf
        self.env = None
        self.planner = None
        self.n_test_laps = None
        self.lap_times = []
        self.completed_laps = 0
        self.prev_obs = None
        self.prev_action = None
        self.std_track = None
        self.map_name = None
        self.reward = None
        self.noise_rng = None
        self.noise_std = 0
        self.lidar_noise_std = 0
        self.vehicle_state_history = None
        self._crashes = 0
        self._q = metrics_q
        self._stop = stop_evt

    def _put(self, msg):
        try:
            self._q.put_nowait(msg)
        except queue.Full:
            pass

    def run_testing(self):
        assert self.env is not None
        for i in range(self.n_test_laps):
            if self._stop.is_set():
                break
            obs = self.reset_simulation()
            while not obs['colision_done'] and not obs['lap_done']:
                if self._stop.is_set():
                    break
                action = self.planner.plan(obs)
                obs = self.run_step(action)
                if _ts_mod.SHOW_TEST:
                    self.env.render('human_fast')
                self._put({"t": "tick", "lap": i + 1,
                           "cur": obs['current_laptime'],
                           "done": self.completed_laps,
                           "crash": self._crashes})

            self.planner.lap_complete()
            if obs['lap_done']:
                self.lap_times.append(obs['current_laptime'])
                self.completed_laps += 1
                status = "✓"
            else:
                self._crashes += 1
                status = "✗"

            avg  = sum(self.lap_times) / len(self.lap_times) if self.lap_times else 0
            best = min(self.lap_times) if self.lap_times else 0
            self._put({"t": "lap", "lap": i + 1, "status": status,
                       "lt": obs['current_laptime'],
                       "done": self.completed_laps, "crash": self._crashes,
                       "avg": avg, "best": best, "total": self.n_test_laps})

        rate = self.completed_laps / self.n_test_laps * 100 if self.n_test_laps else 0
        avg  = sum(self.lap_times) / len(self.lap_times) if self.lap_times else 0
        best = min(self.lap_times) if self.lap_times else 0
        self._put({"t": "done", "done": self.completed_laps,
                   "crash": self._crashes, "rate": rate, "avg": avg, "best": best})
        return {"success_rate": rate, "avg_times": avg, "std_dev": 0}


def _sim_worker(map_name, speed, n_laps, metrics_q, stop_evt):
    result = find_best_seed(map_name, speed)
    if result is None:
        metrics_q.put({"t": "error",
                       "msg": f"No trained model found for {map_name} @ {speed} m/s"})
        return
    seed, test_name, set_n = result
    conf = load_conf("config_file")
    run  = build_run(map_name, speed, n_laps, seed, test_name, set_n)
    sim  = GUISim(run, conf, metrics_q, stop_evt)
    try:
        sim.run_testing_evaluation()
    except Exception as exc:
        metrics_q.put({"t": "error", "msg": str(exc)})


# ─── GUI ──────────────────────────────────────────────────────────────────────

BG     = "#0f0f1a"
PANEL  = "#1a1a2e"
ACCENT = "#e94560"
GREEN  = "#27ae60"
RED    = "#c0392b"
TEXT   = "#f0f0f0"
SUB    = "#7f8c8d"
FONT   = "Helvetica"


class RacingGUI:
    def __init__(self, root):
        self.root = root
        root.title("TAL Racing Controller")
        root.configure(bg=BG)
        root.resizable(False, False)

        self._stop    = threading.Event()
        self._q       = queue.Queue(maxsize=500)
        self._thread  = None
        self._running = False

        self._build_ui()
        self._poll()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _lbl(self, parent, text, size=7, bold=False, fg=TEXT, **grid):
        w = tk.Label(parent, text=text, bg=parent["bg"], fg=fg,
                     font=(FONT, size, "bold" if bold else "normal"))
        if grid:
            w.grid(**grid)
        return w

    def _metric(self, parent, label, var, row, col):
        self._lbl(parent, label, fg=SUB, row=row, column=col, sticky="w")
        tk.Label(parent, textvariable=var, bg=PANEL, fg=TEXT,
                 font=(FONT, 7, "bold"), anchor="w",
                 width=7).grid(row=row, column=col+1, sticky="w", padx=(3, 12))

    # ── layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=ACCENT, pady=5)
        hdr.pack(fill="x")
        tk.Label(hdr, text="TAL Racing Controller", bg=ACCENT, fg="white",
                 font=(FONT, 8, "bold")).pack()

        # Config section
        cfg = tk.Frame(self.root, bg=PANEL, padx=9, pady=7)
        cfg.pack(fill="x", padx=4, pady=4)

        self._lbl(cfg, "Map", fg=SUB, row=0, column=0, sticky="w")
        map_keys = list(MAP_LABELS.keys())
        self._map_keys = map_keys
        self.map_var = tk.StringVar()
        self.map_combo = ttk.Combobox(
            cfg, textvariable=self.map_var,
            values=[f"{k}  —  {MAP_LABELS[k]}" for k in map_keys],
            state="readonly", width=23)
        self.map_combo.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(1, 5))
        self.map_combo.current(0)
        self.map_combo.bind("<<ComboboxSelected>>", self._on_map_change)

        self._lbl(cfg, "Max Speed (m/s)", fg=SUB, row=2, column=0, sticky="w")
        self.speed_var = tk.IntVar(value=6)
        self.speed_combo = ttk.Combobox(
            cfg, textvariable=self.speed_var,
            values=[4, 5, 6, 7], state="readonly", width=5)
        self.speed_combo.grid(row=3, column=0, sticky="w", pady=(1, 5))

        self._lbl(cfg, "Test Laps", fg=SUB, row=2, column=1, sticky="w", padx=(13, 0))
        self.laps_var = tk.IntVar(value=10)
        tk.Spinbox(cfg, from_=1, to=50, textvariable=self.laps_var,
                   width=3, bg=BG, fg=TEXT, buttonbackground=PANEL,
                   font=(FONT, 7)).grid(row=3, column=1, sticky="w", padx=(13, 0))

        # Start / Stop button
        self.btn = tk.Button(
            self.root, text="▶  START TEST",
            font=(FONT, 8, "bold"), bg=GREEN, fg="white",
            activebackground="#2ecc71", relief="flat",
            padx=7, pady=6, command=self._toggle)
        self.btn.pack(fill="x", padx=4, pady=(0, 4))

        # Live metrics
        met = tk.Frame(self.root, bg=PANEL, padx=9, pady=7)
        met.pack(fill="x", padx=4, pady=(0, 4))

        self._lbl(met, "LIVE METRICS", bold=True, fg=SUB,
                  row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        self.v_status = tk.StringVar(value="Idle")
        self.v_lap    = tk.StringVar(value="— / —")
        self.v_cur    = tk.StringVar(value="—")
        self.v_last   = tk.StringVar(value="—")
        self.v_best   = tk.StringVar(value="—")
        self.v_avg    = tk.StringVar(value="—")
        self.v_done   = tk.StringVar(value="0")
        self.v_crash  = tk.StringVar(value="0")
        self.v_rate   = tk.StringVar(value="—")

        self._metric(met, "Status",    self.v_status, row=1, col=0)
        self._metric(met, "Lap",       self.v_lap,    row=2, col=0)
        self._metric(met, "Cur Time",  self.v_cur,    row=3, col=0)
        self._metric(met, "Last Lap",  self.v_last,   row=4, col=0)
        self._metric(met, "Best Lap",  self.v_best,   row=1, col=2)
        self._metric(met, "Avg Lap",   self.v_avg,    row=2, col=2)
        self._metric(met, "Completed", self.v_done,   row=3, col=2)
        self._metric(met, "Crashes",   self.v_crash,  row=4, col=2)

        self._lbl(met, "Completion Rate", fg=SUB,
                  row=5, column=0, columnspan=2, sticky="w", pady=(7, 1))
        self.pbar = ttk.Progressbar(met, length=220, mode="determinate", maximum=100)
        self.pbar.grid(row=6, column=0, columnspan=4, sticky="ew")
        tk.Label(met, textvariable=self.v_rate, bg=PANEL, fg=ACCENT,
                 font=(FONT, 8, "bold")).grid(row=7, column=0, columnspan=4, pady=(3, 0))

        # Lap log
        log_frame = tk.Frame(self.root, bg=PANEL, padx=9, pady=5)
        log_frame.pack(fill="both", expand=True, padx=4, pady=(0, 5))
        self._lbl(log_frame, "LAP LOG", bold=True, fg=SUB).pack(anchor="w")
        self.log = tk.Text(log_frame, bg=BG, fg=TEXT, font=(FONT, 6),
                           height=5, state="disabled", relief="flat",
                           insertbackground=TEXT)
        self.log.pack(fill="both", expand=True, pady=(3, 0))

        self._on_map_change()

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_map_change(self, *_):
        idx = self.map_combo.current()
        map_key = self._map_keys[max(idx, 0)]
        speeds = AVAILABLE_SPEEDS.get(map_key, [6])
        self.speed_combo["values"] = speeds
        if self.speed_var.get() not in speeds:
            self.speed_var.set(speeds[-1])

    def _toggle(self):
        if self._running:
            self._stop.set()
            self.v_status.set("Stopping…")
            self.btn.config(state="disabled")
        else:
            self._start()

    def _start(self):
        idx      = self.map_combo.current()
        map_name = self._map_keys[max(idx, 0)]
        speed    = self.speed_var.get()
        n_laps   = self.laps_var.get()

        self._stop.clear()
        self._clear_log()
        for v in (self.v_cur, self.v_last, self.v_best, self.v_avg):
            v.set("—")
        self.v_status.set("Starting…")
        self.v_lap.set(f"0 / {n_laps}")
        self.v_done.set("0")
        self.v_crash.set("0")
        self.v_rate.set("—")
        self.pbar["value"] = 0

        self.btn.config(text="■  STOP", bg=RED, activebackground="#e74c3c",
                        state="normal")
        self._running = True

        self._thread = threading.Thread(
            target=_sim_worker,
            args=(map_name, speed, n_laps, self._q, self._stop),
            daemon=True)
        self._thread.start()

    def _reset_btn(self):
        self._running = False
        self.btn.config(text="▶  START TEST", bg=GREEN,
                        activebackground="#2ecc71", state="normal")

    # ── metrics loop ──────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                self._handle(self._q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _handle(self, msg):
        t      = msg["t"]
        n_laps = self.laps_var.get()

        if t == "tick":
            self.v_status.set("Running")
            self.v_lap.set(f"{msg['lap']} / {n_laps}")
            self.v_cur.set(f"{msg['cur']:.1f}s")
            self.v_done.set(str(msg["done"]))
            self.v_crash.set(str(msg["crash"]))

        elif t == "lap":
            self.v_last.set(f"{msg['lt']:.2f}s")
            self.v_avg.set(f"{msg['avg']:.2f}s"  if msg["avg"]  else "—")
            self.v_best.set(f"{msg['best']:.2f}s" if msg["best"] else "—")
            rate = msg["done"] / n_laps * 100
            self.pbar["value"] = rate
            self.v_rate.set(f"{rate:.0f}%")
            icon = "✓" if msg["status"] == "✓" else "✗"
            self._log(f"  Lap {msg['lap']:>2}  {icon}  {msg['lt']:.2f}s")

        elif t == "done":
            stopped = self._stop.is_set()
            self.v_status.set("Stopped" if stopped else "Done ✓")
            self.v_rate.set(f"{msg['rate']:.1f}%")
            self.pbar["value"] = msg["rate"]
            self._log(
                f"\n  ── {msg['done']}/{n_laps} laps · "
                f"{msg['rate']:.0f}% · best {msg['best']:.2f}s ──")
            self._reset_btn()

        elif t == "error":
            self.v_status.set("Error ✗")
            self._log(f"\n  ERROR: {msg['msg']}")
            self._reset_btn()

    def _log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")


# ─── entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir("/app")
    root = tk.Tk()
    # Pin to top-right so the sim window opens to the left without covering the panel
    root.update_idletasks()
    root.geometry(f"+{root.winfo_screenwidth() - 275}+0")
    root.attributes("-topmost", True)   # always on top of pyglet window
    RacingGUI(root)
    root.mainloop()
