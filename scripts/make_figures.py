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
TITLE = {"Realistic": "Realistic (Gazebo-derived) mobility", "RWP": "Random Waypoint (RWP)"}

# Table 1: (mean, sd) of wall-clock seconds per run, 10 seeds, n = 5,10,20,50,100
TABLE1 = {
    ("AODV", "RWP"):       [(0.58, .05), (1.42, .13), (4.50, .75), (24.03, 5.79), (71.47, 9.61)],
    ("AODV", "Realistic"): [(0.62, .04), (1.31, .09), (4.61, .75), (28.28, 2.94), (73.83, 8.17)],
    ("OLSR", "RWP"):       [(0.56, .05), (1.30, .12), (3.09, .41), (9.24, .76),  (24.84, 1.51)],
    ("OLSR", "Realistic"): [(0.59, .04), (1.15, .09), (2.98, .28), (9.36, .90),  (17.43, 1.38)],
    ("DSDV", "RWP"):       [(0.56, .04), (1.34, .16), (3.72, .79), (11.82, 1.20), (47.72, 2.57)],
    ("DSDV", "Realistic"): [(0.61, .04), (1.15, .07), (2.93, .34), (12.15, 1.31), (35.14, 2.51)],
}


def two_panel():
    return plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True, dpi=200)


def finish(fig, ax, ylabel, logy):
    """Axis setup is applied AFTER plotting (keeps the autoscaled limits)."""
    for a, mob in zip(ax, ["Realistic", "RWP"]):
        a.set_xscale("log")
        if logy:
            a.set_yscale("log")
        a.set_xticks(NS)
        a.set_xticklabels(NS)
        a.minorticks_off()
        a.set_title(TITLE[mob], fontsize=8)
        a.set_xlabel("Number of UAV nodes ($n$)", fontsize=8)
        a.grid(alpha=.3, which="both" if logy else "major")
        a.tick_params(labelsize=7)
    ax[0].set_ylabel(ylabel, fontsize=8)
    ax[0].legend(title="Routing protocol", fontsize=7, title_fontsize=7, loc="upper left")
    fig.tight_layout()


def fig3(out):
    fig, ax = two_panel()
    for a, mob in zip(ax, ["Realistic", "RWP"]):
        for p, (c, m) in STYLE.items():
            v = TABLE1[(p, mob)]
            a.errorbar(NS, [x for x, _ in v], yerr=[e for _, e in v], color=c,
                       marker=m, ms=4, lw=1.3, capsize=2, label=p)
    finish(fig, ax, "Wall-clock simulation time (s, log scale)", True)
    fig.savefig(os.path.join(out, "scalability_wallclock.png"))


def fig4(rows, out):
    d = collections.defaultdict(list)
    for r in rows:
        d[(int(r["nNodes"]), r["protocol"], r["mobility"])].append(int(r["peakRssKB"]) / 1024)
    fig, ax = two_panel()
    for a, mob in zip(ax, ["Realistic", "RWP"]):
        for p, (c, m) in STYLE.items():
            y = [st.mean(d[(n, p, mob)]) for n in NS]
            e = [st.stdev(d[(n, p, mob)]) for n in NS]
            a.errorbar(NS, y, yerr=e, color=c, marker=m, ms=4, lw=1.3, capsize=2, label=p)
    finish(fig, ax, "Peak memory (MB)", False)
    fig.savefig(os.path.join(out, "scalability_memory.png"))


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
    fig, a = plt.subplots(figsize=(3.6, 3.2), dpi=200)
    for p, (c, _) in STYLE.items():
        for mob, mk in [("Realistic", "o"), ("RWP", "^")]:
            xs = [x for q, m, x, y in pts if q == p and m == mob]
            ys = [y for q, m, x, y in pts if q == p and m == mob]
            a.scatter(xs, ys, c=c, marker=mk, s=14, alpha=.7)
    a.set_xscale("log")
    a.set_yscale("log")
    a.grid(alpha=.3, which="both")
    a.tick_params(labelsize=7)
    a.set_xlabel("Link breaks per run (topology churn, log scale; +1 offset)", fontsize=7)
    a.set_ylabel("Wall-clock simulation time (s, log scale)", fontsize=7)
    a.set_title("Simulation cost vs. topology churn, by routing protocol", fontsize=8)
    h = [Line2D([], [], marker="o", ls="", color=c, label=p) for p, (c, _) in STYLE.items()]
    h += [Line2D([], [], marker="o", ls="", color="gray", label="Realistic"),
          Line2D([], [], marker="^", ls="", color="gray", label="RWP")]
    a.legend(handles=h, fontsize=6, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "scalability_breaks_vs_time.png"))


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
    print("wrote 3 figures to", a.out)


if __name__ == "__main__":
    main()
