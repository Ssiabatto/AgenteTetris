import sys
import os
from datetime import datetime

# ensure repo root is on sys.path so `src` package can be imported
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

from src.video.video import threshold_image, resize_image, to_matrix
from src.video.boardcapture import WindowCapture as b_Cap
from src.video.nextcapture import WindowCapture as n_Cap
from src.tetris.tetris import Tetris
import cv2 as cv
import time
import csv
# analysis and slow frame helpers are imported lazily when RUN_AND_ANALYZE is enabled
import pyautogui


def run_loop(iterations=None, csv_path=None, run_and_analyze=True,
             out_base_dir=None, run_timestamp=None,
             slow_threshold=0.05, slow_profile=False):
    boardcap = b_Cap()
    writer = None
    if csv_path:
        # sanitize path and ensure parent directory exists
        csv_path = csv_path.strip()
        parent = os.path.dirname(csv_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        f = open(csv_path, 'w', newline='', encoding='utf-8')
        writer = csv.writer(f)
        writer.writerow(['timestamp', 't_capture', 't_preprocess', 't_decision', 't_total'])

    i = 0
    # Lazy imports: import heavy helpers only if analysis is enabled
    iterations_analysis = None
    slow_frames = None
    if run_and_analyze:
        from src.tools import iterations_analysis as iterations_analysis
        from src.tools import slow_frames as slow_frames

    try:
        while True:
            t0 = time.perf_counter()
            img = boardcap.get_screenshot()
            t1 = time.perf_counter()

            proc = threshold_image(img)
            proc = resize_image(proc, 10, 22)
            matrix = to_matrix(proc)
            t2 = time.perf_counter()

            game = Tetris(matrix)
            game.process_current_state()
            t3 = time.perf_counter()

            if writer:
                writer.writerow([time.time(), t1 - t0, t2 - t1, t3 - t2, t3 - t0])

            # if analysis is enabled, check for slow decision frames and log them
            if run_and_analyze and out_base_dir and run_timestamp:
                if (t3 - t2) >= slow_threshold:
                    out_folder = os.path.join(out_base_dir, run_timestamp)
                    # optionally profile the decision callable if requested
                    if slow_profile:
                        prof_dir = os.path.join(out_folder, 'slow_frames_prof')
                        dest_prof = os.path.join(prof_dir, f'frame_{i}_{int(time.time())}.prof')
                        # profile the expensive part (re-run process_current_state under profiler)
                        try:
                            slow_frames.profile_decision_callable(game.process_current_state, dest_prof)
                        except Exception:
                            # If profiling re-running causes issues, fall back to logging only
                            pass
                    # log stack and meta info
                    slow_frames.log_slow_frame(out_folder, i, t1 - t0, t2 - t1, t3 - t2, t3 - t0,
                                               stack=True, profile=slow_profile,
                                               profile_dir=os.path.join(out_folder, 'slow_frames_prof'))

            i += 1
            if iterations and i >= iterations:
                break
    finally:
        if writer:
            f.close()


if __name__ == "__main__":
    # control via env vars: ITERATIONS, TIMINGS_CSV
    # Default iterations (modify this variable or set the ITERATIONS env var)
    DEFAULT_ITERATIONS = 3000

    it = os.environ.get('ITERATIONS')
    csvp = os.environ.get('TIMINGS_CSV')
    iterations = int(it) if it else DEFAULT_ITERATIONS

    # RUN_AND_ANALYZE: env toggle (default True)
    RUN_AND_ANALYZE = os.environ.get('RUN_AND_ANALYZE', '1') != '0'
    # SLOW_FRAME_THRESHOLD (seconds) - when exceeded, a short stack + optional profile is saved
    SLOW_FRAME_THRESHOLD = float(os.environ.get('SLOW_FRAME_THRESHOLD', '0.05'))
    SLOW_FRAME_PROFILE = os.environ.get('SLOW_FRAME_PROFILE', '0') == '1'

    # If no CSV path provided, when analysis is enabled write directly into the
    # dated run folder so analysis can find slow_frames.log and produce the PDF.
    base_dir = os.path.join(root, 'IterationsTimings')
    os.makedirs(base_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_folder = os.path.join(base_dir, timestamp)
    if not csvp:
        if RUN_AND_ANALYZE:
            os.makedirs(out_folder, exist_ok=True)
            csvp = os.path.join(out_folder, 'timings.csv')
        else:
            csvp = os.path.join(base_dir, f'timings_{timestamp}.csv')

    # optional override to disable PyAutoGUI failsafe (not recommended)
    disable_failsafe = os.environ.get('DISABLE_PYAUTOGUI_FAILSAFE') == '1'
    if disable_failsafe:
        print('Warning: DISABLE_PYAUTOGUI_FAILSAFE=1 set. PyAutoGUI failsafe disabled.')
        pyautogui.FAILSAFE = False

    # Run the loop and, if enabled, analyze afterwards. Keep main minimal: instrumentation
    # for slow-frames will be performed inside the loop via the slow_frames helper.
    run_exception = None
    try:
        run_loop(iterations=iterations, csv_path=csvp,
                 run_and_analyze=RUN_AND_ANALYZE,
                 out_base_dir=base_dir,
                 run_timestamp=timestamp,
                 slow_threshold=SLOW_FRAME_THRESHOLD,
                 slow_profile=SLOW_FRAME_PROFILE)
    except pyautogui.FailSafeException:
        print('PyAutoGUI fail-safe triggered (mouse moved to a screen corner). Stopping run.')
    except Exception as e:
        run_exception = e

    # If analysis is enabled, run it now (ensures PDF and summary are generated even on fail-safe)
    if RUN_AND_ANALYZE:
        try:
            from src.tools import iterations_analysis
            result = iterations_analysis.analyze_and_save(csvp, out_folder)
            print('Analysis written:', result)
        except Exception as e:
            print('Error while running analysis:', e)

    if run_exception:
        # Re-raise after attempting analysis
        raise run_exception
