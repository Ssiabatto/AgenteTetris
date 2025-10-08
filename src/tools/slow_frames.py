import os
import time
import traceback
import cProfile
import pstats
from pathlib import Path


def ensure_dir(p):
	os.makedirs(p, exist_ok=True)


def short_stack(limit=20):
	# return a shortened formatted stack (exclude current frame)
	stack = traceback.format_stack()[:-2]
	if len(stack) > limit:
		stack = stack[-limit:]
	return ''.join(stack)


def log_slow_frame(out_folder, iteration, t_capture, t_preprocess, t_decision, t_total, stack=True,
				   profile=False, profile_dir=None):
	"""Append a slow-frame log entry. Optionally write a cProfile snapshot.

	out_folder: path to the dated run folder (IterationsTimings/<timestamp>)
	"""
	ensure_dir(out_folder)
	log_path = os.path.join(out_folder, 'slow_frames.log')
	ts = time.time()
	with open(log_path, 'a', encoding='utf-8') as f:
		f.write(f'[{ts}] iter={iteration} t_capture={t_capture:.6f} t_preprocess={t_preprocess:.6f} '
				f't_decision={t_decision:.6f} t_total={t_total:.6f}\n')
		if stack:
			f.write('STACK:\n')
			f.write(short_stack())
			f.write('\n')

	# optionally run a quick profile snapshot of the current thread (caller must provide profiler func)
	if profile and profile_dir:
		ensure_dir(profile_dir)
		prof_file = os.path.join(profile_dir, f'slow_frame_{iteration}_{int(ts)}.prof')
		# The caller can call cProfile.runctx to profile a function; here we only create a placeholder file
		# to indicate where a profile should be saved. Providing full per-frame profiling requires
		# the caller to execute the profiled function under cProfile; instead, callers can use
		# the `profile_decision_callable` helper below.
		with open(prof_file, 'w', encoding='utf-8') as pf:
			pf.write(f'profiling-placeholder for iteration {iteration} at {ts}\n')


def profile_decision_callable(decision_callable, dest_prof_path, *args, **kwargs):
	"""Run decision_callable under cProfile and save stats to dest_prof_path."""
	ensure_dir(os.path.dirname(dest_prof_path))
	pr = cProfile.Profile()
	pr.enable()
	try:
		res = decision_callable(*args, **kwargs)
	finally:
		pr.disable()
		ps = pstats.Stats(pr)
		ps.dump_stats(dest_prof_path)
	return res

