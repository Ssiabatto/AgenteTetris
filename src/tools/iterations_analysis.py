import os
import csv
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import re


_SLOW_LOG_RE = re.compile(r"^\[.*\]\s+iter=(?P<iter>\d+)\s+t_capture=(?P<tcap>[0-9.]+)\s+t_preprocess=(?P<tpre>[0-9.]+)\s+t_decision=(?P<tdec>[0-9.]+)\s+t_total=(?P<ttot>[0-9.]+)")


def read_timings(csv_path, skip_first=20):
	rows = []
	with open(csv_path, 'r', encoding='utf-8') as f:
		reader = csv.DictReader(f)
		for r in reader:
			rows.append(r)
	rows = rows[skip_first:]
	cols = ['t_capture', 't_preprocess', 't_decision', 't_total']
	data = {c: np.array([float(r[c]) for r in rows]) for c in cols}
	return data


def compute_summary(data):
	def s(arr):
		return {
			'count': int(len(arr)),
			'mean': float(np.mean(arr)),
			'median': float(np.median(arr)),
			'stdev': float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
			'min': float(np.min(arr)),
			'max': float(np.max(arr)),
			'p90': float(np.percentile(arr, 90)),
			'p95': float(np.percentile(arr, 95)),
			'p99': float(np.percentile(arr, 99)),
		}

	return {k: s(v) for k, v in data.items()}


def make_plots(data):
	# Create 4 subplots: histograms, time series of total, mean contributions bar, pie chart
	t_total = data['t_total']
	capture = data['t_capture']
	pre = data['t_preprocess']
	dec = data['t_decision']

	fig = plt.figure(figsize=(8, 11))
	gs = fig.add_gridspec(4, 2)

	ax_hist = fig.add_subplot(gs[0, :])
	ax_time = fig.add_subplot(gs[1, :])
	ax_bar = fig.add_subplot(gs[2, 0])
	ax_pie = fig.add_subplot(gs[2, 1])

	# Histograms (log-scaled xaxis for clarity on heavy tails)
	ax_hist.hist([capture, pre, dec, t_total], bins=60, label=['capture', 'preprocess', 'decision', 'total'], stacked=False)
	ax_hist.set_title('Timing histograms')
	ax_hist.set_xlabel('seconds')
	ax_hist.legend()

	# Time series for total
	ax_time.plot(t_total, linewidth=0.6)
	ax_time.set_title('t_total over iterations')
	ax_time.set_xlabel('iteration')
	ax_time.set_ylabel('seconds')

	# Mean contribution bar
	means = [float(np.mean(capture)), float(np.mean(pre)), float(np.mean(dec))]
	total_mean = float(np.mean(t_total))
	pct = [m / total_mean * 100 if total_mean else 0.0 for m in means]
	ax_bar.bar(['capture', 'preprocess', 'decision'], pct, color=['#4c72b0', '#55a868', '#c44e52'])
	ax_bar.set_title('Mean contribution to mean total (%)')
	ax_bar.set_ylabel('%')

	# Pie chart (mean-time shares)
	labels = ['capture', 'preprocess', 'decision']
	ax_pie.pie(pct, labels=labels, autopct='%1.1f%%', colors=['#4c72b0', '#55a868', '#c44e52'])
	ax_pie.set_title('Mean time share')

	plt.tight_layout()
	return fig


def parse_slow_frames_log(log_path):
	"""Parse slow_frames.log entries and return a list of dicts with iter and times and stack."""
	entries = []
	if not os.path.exists(log_path):
		return entries
	with open(log_path, 'r', encoding='utf-8') as f:
		lines = f.readlines()
	i = 0
	while i < len(lines):
		m = _SLOW_LOG_RE.match(lines[i].strip())
		if m:
			entry = {
				'iter': int(m.group('iter')),
				't_capture': float(m.group('tcap')),
				't_preprocess': float(m.group('tpre')),
				't_decision': float(m.group('tdec')),
				't_total': float(m.group('ttot')),
				'stack': ''
			}
			# read subsequent lines until blank or next entry -> treat as stack
			j = i + 1
			stack_lines = []
			while j < len(lines) and not lines[j].startswith('['):
				stack_lines.append(lines[j])
				j += 1
			entry['stack'] = ''.join(stack_lines).strip()
			entries.append(entry)
			i = j
		else:
			i += 1
	return entries


def make_slow_frames_page(slow_entries):
	# Create a figure summarizing slow-frame stats and top entries
	fig = plt.figure(figsize=(8, 11))
	ax_hist = fig.add_subplot(211)
	ax_text = fig.add_subplot(212)
	ax_text.axis('off')
	if not slow_entries:
		ax_hist.text(0.5, 0.5, 'No slow-frame entries found', ha='center', va='center')
		return fig

	tdec = np.array([e['t_decision'] for e in slow_entries])
	ax_hist.hist(tdec, bins=40, color='#c44e52')
	ax_hist.set_title('Slow-frame decision time histogram')
	ax_hist.set_xlabel('seconds')
	# Top 10 slow frames
	top = sorted(slow_entries, key=lambda e: e['t_decision'], reverse=True)[:10]
	text_lines = [f'Total slow frames: {len(slow_entries)}', 'Top slow frames (iter, t_decision):']
	for e in top:
		text_lines.append(f"iter={e['iter']}, t_decision={e['t_decision']:.6f}")
	# add sample stacks for top 3
	text_lines.append('\nSample stacks for top 3:')
	for e in top[:3]:
		stack = e.get('stack', '').strip()
		if stack:
			snippet = '\n'.join(stack.splitlines()[-10:])
			text_lines.append(f"iter={e['iter']} stack:\n{snippet}\n")
	ax_text.text(0, 1, '\n'.join(text_lines), va='top', family='monospace', fontsize=8)
	plt.tight_layout()
	return fig


def analyze_and_save(csv_input_path, output_folder):
	os.makedirs(output_folder, exist_ok=True)
	data = read_timings(csv_input_path)
	summary = compute_summary(data)

	# save summary as a small text file
	summary_txt = os.path.join(output_folder, 'summary.txt')
	with open(summary_txt, 'w', encoding='utf-8') as f:
		f.write(f'Analysis for {csv_input_path}\n')
		f.write(f'Generated: {datetime.now().isoformat()}\n\n')
		for k, v in summary.items():
			f.write(f"{k}:\n")
			for kk, vv in v.items():
				f.write(f"  {kk}: {vv}\n")
			f.write('\n')

	# create multipage PDF: main plots + optional slow-frames page
	out_pdf = os.path.join(output_folder, 'dataprocess.pdf')
	with PdfPages(out_pdf) as pdf:
		fig = make_plots(data)
		pdf.savefig(fig)
		plt.close(fig)

		# include slow-frames page if available
		slow_log = os.path.join(output_folder, 'slow_frames.log')
		slow_entries = parse_slow_frames_log(slow_log)
		if slow_entries:
			fig2 = make_slow_frames_page(slow_entries)
			pdf.savefig(fig2)
			plt.close(fig2)

	# move csv into folder named 'timings.csv'
	dest_csv = os.path.join(output_folder, 'timings.csv')
	if os.path.abspath(csv_input_path) != os.path.abspath(dest_csv):
		# copy file
		from shutil import copyfile
		copyfile(csv_input_path, dest_csv)

	return {'summary_txt': summary_txt, 'pdf': out_pdf, 'csv': dest_csv}

