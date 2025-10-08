# AgenteTetris

## Version
Version: 1.1.0 — 2025-10-08

## Author - Sergio Nicolás Siabatto Cleves
Original authors: Sergio Nicolás Siabatto Cleves and Jhon Silva

It started as a small college project and evolved into an experiment in AI and game-state processing.

AgenteTetris is a lightweight Tetris state processor with basic video-capture utilities that read the game screen and evaluate candidate moves. Recorded test runs are in `DemoVideos/`.

## Quick facts

- Main runner: `main.py` — captures the board, converts it to a matrix, and calls `Tetris.process_current_state()`.
- Alternate test runner: `__main_.py` — offline helper to score and print possible piece landings for debugging.
- Source code: `src/` (packages: `tetris`, `video`, `matrix`, `AIBot`).
- Test videos are included in `DemoVideos/` (see `DemoVideos/v1_0_0.mp4`, recorded 2024-11-04).

## Repository structure

```
AgenteTetris/
├─ main.py                 # Primary entry point: capture → preprocess → Tetris processor (minimal runner)
├─ requirements.txt        # Python dependencies
├─ CHANGELOG.md            # Release history
├─ README.md               # Project overview (this file)
├─ DemoVideos/             # Demo recordings (e.g. v1_0_0.mp4)
├─ IterationsTimings/      # Timestamped profiling and run outputs (CSV, PDF, logs)
└─ src/                    # Source packages
   ├─ tetris/              # Core Tetris logic (pieces, board, heuristics)
   ├─ video/               # Screen capture & preprocessing
   ├─ matrix/              # Image → numeric matrix utilities
   └─ tools/               # Analysis and profiling helpers (iterations_analysis, slow_frames)
```

## Dependencies

Install required packages (recommended to use a virtual environment). The project was developed and tested on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Note: `requirements.txt` includes `numpy` and `opencv-python`.

## How to run (Windows / cmd.exe)

1. Ensure Python 3.8+ is installed and a virtual environment is active.
2. Install dependencies:

```cmd
pip install -r requirements.txt
```

3. Run the main capture-and-process loop:

```cmd
python main.py
```

4. For offline testing of the move-scoring helper in `__main_.py`:

```cmd
python __main_.py
```

When running `main.py`, a window named "Board" will appear showing the thresholded board image. The code resizes and converts that image to a 22×10 matrix and calls `Tetris.process_current_state()`.

## Notes about the code

- The `src/tetris` package implements pieces (`Pieza`), board (`Tablero`), and scoring heuristics (`Tetris` class). Functions such as `Tetris.bumpiness`, `Tetris.complete_lines`, `Tetris.holes` and `Tetris.aggregate_height` are used by the agent to evaluate states.
- `src/video` contains capture utilities that use `opencv-python` to grab a region of the screen and convert it to a binary (thresholded) image.
- `__main_.py` is a useful script to inspect how rotated pieces would land and to print possible final grids for debugging and development.

## Demo & release videos

Recorded demo runs are stored in `DemoVideos/`. The included demo for this release is `DemoVideos/v1_0_0.mp4` (recorded 2024-11-04).

See the changelog entry for v1.0.0 for more context: [CHANGELOG](CHANGELOG.md#v1_0_0)

<video controls width="640">
	<source src="DemoVideos/v1_0_0.mp4" type="video/mp4">
	Your browser does not support the video tag. You can download or open the file directly: [DemoVideos/v1_0_0.mp4](DemoVideos/v1_0_0.mp4)
</video>

Example (local preview):

```powershell
# Play the v1.0.0 demo (Windows, uses default app mapping)
start "" DemoVideos\v1_0_0.mp4
```

## Changelog

See [CHANGELOG](CHANGELOG.md) for version history.

Recent changes in v1.1.0 (2025-10-08) include run profiling and analysis support.

Code cleanup and structure

- This release included a cleanup and reorganization of the project to improve readability and maintainability:
   - Consolidated analysis/profiling helpers into `src/tools/`.
   - Simplified and cleaned `main.py` so it remains a small runner and imports heavy tooling only when needed.
   - Removed several duplicate/wildcard imports and unused functions across modules.

## Next steps (improvement checklist)

### Minimum contract (inputs / outputs / success criteria)

- Inputs: screenshot (or internal game state), piece info (current, next, hold), simulated actions (left/right/rotate/soft/hard/hold)
- Outputs: sequence of actions to place each piece
- Success criteria: reduce average time to clear 40 lines (measure with 100 deterministic episodes) and/or consistently beat the baseline time for 40 lines

### Quick high-level goals

- Optimize vision + capture pipeline
- Reduce control latency with macro-actions and a move generator
- Improve decision policy (heuristic → search → ML)
- Train with RL/IL in an accelerated (headless) environment where possible

### Performance optimization (reduce current ~38s)

Tasks:

1. Profile the loop (capture, preprocess, decide, input)
   - Add timers or use `cProfile` to measure: screenshot, preprocessing, decision, input sending
   - Inspect results with `snakeviz` or `pstats`

2. Optimize screenshot capture
   - Capture only the ROI; ensure `get_screenshot()` crops precisely
   - Use contiguous buffers (e.g. `np.ascontiguousarray`) and avoid unnecessary color conversions
   - Downscale resolution/depth if it preserves required info

3. Move expensive work out of the per-frame loop
   - Precompute templates/masks, vectorize with NumPy, avoid Python loops
   - Keep image ops in uint8 whenever possible

4. Convert decisions to macro-actions
   - For each piece, generate the full key-sequence (rotations + shifts + hard-drop) and execute it; decide once per piece instead of per frame

5. Implement a move-generator using a bitboard model
   - Represent the board as 20x10 bits (e.g. `uint16` per row)
   - Simulate all legal placements (rotations + x) quickly and evaluate with a vectorized heuristic

6. Simulate input behavior (DAS/ARR) in software
   - Compute the minimal key sequence to move/rotate and send it; prefer hard-drop when appropriate

7. Batch / parallelize heavy evaluations
   - Use NumPy, Numba or C for bulk evaluation of placements

Estimated impact: move-generator + bitboard + macro-actions should reduce decision time to ~1–10 ms per piece and can cut total time substantially (example: ~38s → ~10–20s depending on hardware and policy)

### Policy and algorithm improvements (heuristics → ML)

Tasks:

- Implement an improved heuristic (features: lines, holes, aggregate height, bumpiness, wells, transitions) and tune weights (grid/random search)
- Add depth-limited search (N=2..4) with pruning and beam search
- Generate dataset from heuristic and train a supervised policy (IL) on bitboard inputs
- Continue to RL fine-tuning (PPO or DQN/Rainbow) using macro-actions and compact observations

### Training environment design

Tasks:

- Build a Gym-like API wrapper: `observation`, `step(action)`, `reset()`
  - Observation: bitboard (20x10), piece id, next N, hold bit
  - Action: place at column X with rotation R (+ hold)
  - `step(action)` should simulate the result instantly in logic (no screen)
  - Reward: reward for lines, combo/back-to-back, penalty for losing

- If internal state isn't available: implement a lightweight headless Tetris simulator and train on it (sim2real)

Recommended PPO params (stable-baselines3 starter):

```text
n_steps = 2048
batch_size = 64
n_epochs = 10
gamma = 0.99
gae_lambda = 0.95
lr = 2.5e-4
clip_range = 0.2
```

### Reward design (ideas)

- Reward per line: `+1.0 * lines_cleared` (or `lines_cleared**2`)
- Combo bonus: `+0.5` per consecutive combo
- Back-to-back Tetris bonus: `+1.0`
- Penalize holes: `-0.1 * num_holes`
- Time penalty: `-0.01` per step to encourage speed
- Terminal penalty: `-5` or `-100` on loss

### Network architectures

- Input: bitboard 20x10 + one-hot piece ids for current+next
- Quick model: Flatten → MLP (512→256) → policy + value
- Better model: small CNN → MLP → policy + value
- Output for macro-actions: softmax over (columns * rotations * hold options)

### Metrics and evaluation

- Key metrics: average time to 40 lines, lines/minute, failure rate, sample efficiency
- Validate with deterministic seeds and run A/B tests (heuristic vs policy vs policy+search)

### Profiling checklist

- Measure per-piece timing: `T_capture`, `T_preprocess`, `T_decision`, `T_input`
- Insert the following in the loop to log timings:

```python
import time
t0 = time.perf_counter()
img = wc.get_screenshot()
t1 = time.perf_counter()
board = process(img)
t2 = time.perf_counter()
action = policy(board)
t3 = time.perf_counter()
send_action(action)
t4 = time.perf_counter()
print('capture',t1-t0,'proc',t2-t1,'dec',t3-t2,'input',t4-t3)
```

Tools: `cProfile`, `line_profiler`, `pyinstrument`

### Edge cases & risks

- Noisy vision: mis-detected board → add sanity checks and validation
- Input timing limits: game may ignore or throttle inputs → add robust timing/retry logic
- Overfitting to heuristic in IL: combine IL pretraining with RL fine-tuning
- Compute needs: RL training benefits from GPU/strong CPU

---