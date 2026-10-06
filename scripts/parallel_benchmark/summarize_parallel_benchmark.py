#!/usr/bin/env python3
"""Speedup / efficiency table and determinism check for the parallel benchmark."""
import csv, glob, os, sys, collections

d = sys.argv[1] if len(sys.argv) > 1 else "benchmark_parallel"
rows = list(csv.DictReader(open(os.path.join(d, "batch_summary.csv"))))
rows = [r for r in rows]
base = next((r for r in rows if r["P"] == "1"), None)
if base is None:
    sys.exit("P=1 baseline missing")
T1 = float(base["makespan_s"])

out = [["P", "runs", "failed", "makespan_s", "speedup", "efficiency_pct", "mean_run_s", "slowdown_vs_P1_per_run"]]
m1 = float(base["mean_run_s"])
for r in rows:
    P = int(r["P"]); T = float(r["makespan_s"])
    S = T1 / T
    out.append([P, r["runs"], r["failed"], f"{T:.1f}", f"{S:.2f}", f"{100*S/P:.1f}",
                f"{float(r['mean_run_s']):.2f}", f"{float(r['mean_run_s'])/m1:.2f}"])
w = [max(len(str(x[i])) for x in out) for i in range(len(out[0]))]
for line in out:
    print("  ".join(str(c).rjust(w[i]) for i, c in enumerate(line)))
with open(os.path.join(d, "speedup_summary.csv"), "w", newline="") as f:
    csv.writer(f).writerows(out)

# determinism: the results row of each configuration must be identical for every P
res = collections.defaultdict(dict)
for path in glob.glob(os.path.join(d, "P*", "runs", "*", "results.csv")):
    P = path.split(os.sep)[-4]; tag = path.split(os.sep)[-2]
    res[tag][P] = open(path).read().strip()
bad = [t for t, v in res.items() if len(set(v.values())) > 1]
print(f"\nconfigurations compared across P: {len(res)}; differing results rows: {len(bad)}")
for t in bad[:10]:
    print("  differs:", t)
