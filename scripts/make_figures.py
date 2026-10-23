#!/usr/bin/env python3
"""Regenerates Figures 3, 4 and 5 of the JPDC 2026 paper
"Computational Cost of UAV Network Co-Simulation: Scalability, Topology Churn,
and Routing Protocol Effects".

Data sources (version 1.1, Oct 2026; all measured on the lab machine):
  * simpat_rerun_2026-10/timing_simpat_300runs.csv - per-run wall-clock time, peak RSS,
      link breaks and node degree of the 300 runs (fanet-compare-simpat, binary timed directly)
      columns: protocol,mobility,nNodes,seed,wallClockSec,peakRssKB,cpuPct,exitStatus,
               linkBreaks,avgNodeDegree,pdr
  * (optional) parallel_benchmark_full_simpat/per_run_all.csv - sequential (P=1) re-run of
      the same 300 configurations from the parallel benchmark
  * Table 1 of the paper - embedded below (mean +- sd of wall-clock time)

Output: one vector PDF per panel (Figure_3_wallclock_{Realistic,RWP}.pdf,
Figure_4_memory_{Realistic,RWP}.pdf, Figure_5_breaks_vs_time.pdf), fonts embedded,
no title inside the image (put the panel titles in the LaTeX subcaptions).

Figure 3: wall-clock time vs n, drawn from the Table 1 values (so the figure and
          the table are identical by construction).
Figure 4: peak RSS vs n, mean +- sd over 10 seeds, from the 300-run CSV.
Figure 5: wall-clock time vs link breaks per run, both from the 300-run CSV
          (optionally, with --perrun, the P=1 benchmark durations instead).

Version 1.0 used results/jpdc2026_timing_300runs.csv, which was produced with the
RWP generator bug described in the README; do not use it for the RWP condition.

Usage:
  python3 make_figures.py --timing results/simpat_rerun_2026-10/timing_simpat_300runs.csv --out figs/
"""
import argparse
import csv
import os
import statistics as st
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

NS = [5, 10, 20, 50, 100]
STYLE = {"AODV": ("#d62728", "o"), "OLSR": ("#1f77b4", "s"), "DSDV": ("#2ca02c", "^")}

# Table 1: (mean, sd) of wall-clock seconds per run, 10 seeds, n = 5,10,20,50,100
# Version 1.1 (Oct 2026): computed from results/simpat_rerun_2026-10/timing_simpat_300runs.csv
# (fanet-compare-simpat, binary timed directly; values rounded half-up to 2 decimals).
TABLE1 = {
    ("AODV", "RWP"):       [(0.48, .08), (1.49, .31), (5.32, 1.09), (22.45, 3.10), (85.03, 14.86)],
    ("AODV", "Realistic"): [(0.57, .07), (1.11, .11), (4.31, .68), (26.79, 2.62), (69.85, 7.30)],
    ("OLSR", "RWP"):       [(0.43, .09), (1.19, .24), (2.78, .37), (8.09, 1.03),  (25.69, 2.99)],
    ("OLSR", "Realistic"): [(0.44, .09), (1.02, .08), (2.81, .27), (8.96, .84),   (16.89, 1.32)],
    ("DSDV", "RWP"):       [(0.45, .09), (1.12, .23), (2.98, .48), (10.12, .47),  (43.64, 2.07)],
    ("DSDV", "Realistic"): [(0.52, .09), (1.06, .08), (2.74, .27), (11.53, 1.21), (32.95, 2.24)],
}


matplotlib.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,          # embed fonts (Elsevier: vector, fonts embedded)
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
})
FIGSIZE = (3.5, 2.7)   # single column (~89 mm); one panel per file, no title inside the image
MOBS = ["Realistic", "RWP"]


def setup(ax, ylabel, logy, ylim):
    ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.set_xticks(NS)
    ax.set_xticklabels(NS)
    ax.minorticks_off()
    ax.set_ylim(*ylim)
    ax.set_xlabel("Number of UAV nodes ($n$)")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=.3, which="both" if logy else "major")
    ax.legend(title="Routing protocol", fontsize=7, title_fontsize=7, loc="upper left")


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, name + ".pdf"))
    plt.close(fig)


def pair(out, stem, series, ylabel, logy):
    """series[(p, mob)] = (means, sds). Two separate files with identical y-limits."""
    lo = min(m - e for v in series.values() for m, e in zip(*v))
    hi = max(m + e for v in series.values() for m, e in zip(*v))
    ylim = (max(lo * 0.8, 1e-2) if logy else 0, hi * (1.5 if logy else 1.08))
    for mob in MOBS:
        fig, ax = plt.subplots(figsize=FIGSIZE)
        for p, (c, mk) in STYLE.items():
            y, e = series[(p, mob)]
            ax.errorbar(NS, y, yerr=e, color=c, marker=mk, ms=4, lw=1.3, capsize=2, label=p)
        setup(ax, ylabel, logy, ylim)
        save(fig, out, f"{stem}_{mob}")


def fig3(out):
    series = {k: ([x for x, _ in v], [e for _, e in v]) for k, v in TABLE1.items()}
    pair(out, "Figure_3_wallclock", series, "Wall-clock simulation time (s, log scale)", True)


def fig4(rows, out):
    d = collections.defaultdict(list)
    for r in rows:
        d[(int(r["nNodes"]), r["protocol"], r["mobility"])].append(int(r["peakRssKB"]) / 1024)
    series = {(p, mob): ([st.mean(d[(n, p, mob)]) for n in NS], [st.stdev(d[(n, p, mob)]) for n in NS])
              for p in STYLE for mob in MOBS}
    pair(out, "Figure_4_memory", series, "Peak memory (MB)", False)


def fig5(rows, perrun_path, out):
    """x = link breaks per run (+1), y = wall-clock time per run.
    By default y is wallClockSec of the 300-run CSV (the values behind Table 1, as stated
    in the paper's caption). With --perrun, y is the sequential (P=1) duration from the
    parallel benchmark instead (version 1.0 behaviour)."""
    breaks = {(r["protocol"], r["mobility"], int(r["nNodes"]), int(r["seed"])): int(r["linkBreaks"])
              for r in rows}
    pts = []
    if perrun_path:
        for r in csv.DictReader(open(perrun_path)):
            if r["P"] != "1":
                continue
            k = (r["protocol"], r["mobility"], int(r["nNodes"]), int(r["seed"]))
            pts.append((k[0], k[1], breaks[k] + 1, float(r["duration_s"])))
    else:
        for r in rows:
            pts.append((r["protocol"], r["mobility"], int(r["linkBreaks"]) + 1, float(r["wallClockSec"])))
    assert len(pts) == 300, f"expected 300 runs, got {len(pts)}"
    fig, a = plt.subplots(figsize=FIGSIZE)
    for p, (c, _) in STYLE.items():
        for mob, mk in [("Realistic", "o"), ("RWP", "^")]:
            xs = [x for q, m, x, y in pts if q == p and m == mob]
            ys = [y for q, m, x, y in pts if q == p and m == mob]
            a.scatter(xs, ys, c=c, marker=mk, s=14, alpha=.7)
    a.set_xscale("log")
    a.set_yscale("log")
    a.grid(alpha=.3, which="both")
    a.set_xlabel("Link breaks per run (log scale; +1 offset)")
    a.set_ylabel("Wall-clock simulation time (s, log scale)")
    h = [Line2D([], [], marker="o", ls="", color=c, label=p) for p, (c, _) in STYLE.items()]
    h += [Line2D([], [], marker="o", ls="", color="gray", label="Realistic"),
          Line2D([], [], marker="^", ls="", color="gray", label="RWP")]
    a.legend(handles=h, fontsize=6, loc="lower right")
    save(fig, out, "Figure_5_breaks_vs_time")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timing", required=True)
    ap.add_argument("--perrun", default=None,
                    help="optional: use P=1 benchmark durations for Figure 5 instead of wallClockSec")
    ap.add_argument("--out", default="figs")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = list(csv.DictReader(open(a.timing)))
    assert len(rows) == 300, f"expected 300 rows, got {len(rows)}"
    fig3(a.out)
    fig4(rows, a.out)
    fig5(rows, a.perrun, a.out)
    print("wrote 5 vector PDFs (Figures 3-5) to", a.out)


if __name__ == "__main__":
    main()
