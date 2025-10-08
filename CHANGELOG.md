# Changelog

All notable changes to this project will be documented in this file.

<a name="v1_1_0"></a>
## [1.1.0] - 2025-10-08
### Added
- Per-iteration timing instrumentation and CSV output (t_capture, t_preprocess, t_decision, t_total).
- Slow-frame tracer (stack trace) and optional per-slow-frame cProfile dumps under `IterationsTimings/<timestamp>/slow_frames_prof/`.
- `src/tools/iterations_analysis.py` produces `dataprocess.pdf` (multi-page) and `summary.txt` inside the dated run folder.
- `src/tools/slow_frames.py` helper for logging slow frames and profiling.

### Changed
- Runner behavior: when `RUN_AND_ANALYZE=1` the CSV and analysis artifacts are saved in `IterationsTimings/<timestamp>/`.
- `main.py` imports analysis tooling lazily to avoid overhead when analysis is disabled.
 - Code cleanup and reorganization: refactored capture modules, consolidated analysis tooling into `src/tools/`, removed several wildcard/duplicate imports and simplified `main.py` to be minimal and lazy-load analysis helpers.

---

<a name="v1_0_0"></a>
## [1.0.0] - 2024-11-04
### Added
- Initial project code: `src/tetris/`, `src/video/`, `src/matrix/`, and `src/AIBot/`.
- Main runners: `main.py` (live capture and processing) and `__main_.py` (offline move scoring debug helper).

### Notes
- This is the first functional version delivered: core capture, board-to-matrix conversion, and heuristic state scoring are implemented and working in a basic form.
- Core heuristics and helper functions are implemented in `src/tetris/tetris.py` and `src/tetris/pieza.py`.

---