#!/usr/bin/env python3
"""Regenerates Figures 3, 4 and 5 of the JPDC 2026 paper
"Computational Cost of UAV Network Co-Simulation: Scalability, Topology Churn,
and Routing Protocol Effects".

Data sources (all measured on the lab machine, 2026-10):
  * jpdc2026_timing_300runs.csv  - per-run peak RSS and link breaks (300 runs)
      columns: protocol,mobility,nNodes,seed,wallClockSec,peakRssKB,linkBreaks,avgNodeDegree
  * per_run_all.csv              - sequential (P=1) re-run of the same 300
      configurations from the parallel benchmark (benchmark_parallel_full/)
  * Table 1 of the paper         - embedded below (mean +- sd of wall-clock time)

Output: one vector PDF per panel (Figure_3_wallclock_{Realistic,RWP}.pdf,
Figure_4_memory_{Realistic,RWP}.pdf, Figure_5_breaks_vs_time.pdf), fonts embedded,
no title inside the image (put the panel titles in the LaTeX subcaptions).

Figure 3: wall-clock time vs n, drawn from the Table 1 values (so the figure and
          the table are identical by construction).
Figure 4: peak RSS vs n, mean +- sd over 10 seeds, from the 300-run CSV.
Figure 5: wall-clock time (P=1 re-run) vs link breaks per run (300-run CSV),
          joined on (protocol, mobility, n, seed).

Note: the wall-clock column of jpdc2026_timing_300runs.csv is NOT used for the
paper figures: for n=5 and n=10 under realistic mobility it contains values from
an earlier, load-affected re-run that do not match Table 1.

Usage:
  python3 make_figures.py --timing jpdc2026_timing_300runs.csv \
                          --perrun per_run_all.csv --out figs/
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
TABLE1 = {
    ("AODV", "RWP"):       [(0.58, .05), (1.42, .13), (4.50, .75), (24.03, 5.79), (71.47, 9.61)],
    ("AODV", "Realistic"): [(0.62, .04), (1.31, .09), (4.61, .75), (28.28, 2.94), (73.83, 8.17)],
    ("OLSR", "RWP"):       [(0.56, .05), (1.30, .12), (3.09, .41), (9.24, .76),  (24.84, 1.51)],
    ("OLSR", "Realistic"): [(0.59, .04), (1.15, .09), (2.98, .28), (9.36, .90),  (17.43, 1.38)],
    ("DSDV", "RWP"):       [(0.56, .04), (1.34, .16), (3.72, .79), (11.82, 1.20), (47.72, 2.57)],
    ("DSDV", "Realistic"): [(0.61, .04), (1.15, .07), (2.93, .34), (12.15, 1.31), (35.14, 2.51)],
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
    breaks = {(r["protocol"], r["mobility"], int(r["nNodes"]), int(r["seed"])): int(r["linkBreaks"])
              for r in rows}
    pts = []
    for r in csv.DictReader(open(perrun_path)):
        if r["P"] != "1":
            continue
        k = (r["protocol"], r["mobility"], int(r["nNodes"]), int(r["seed"]))
        pts.append((k[0], k[1], breaks[k] + 1, float(r["duration_s"])))
    assert len(pts) == 300, f"expected 300 P=1 runs, got {len(pts)}"
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
    ap.add_argument("--perrun", required=True)
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
