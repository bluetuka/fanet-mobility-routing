#!/usr/bin/env python3
"""
analyze.py — Statistics + publication figures for the FANET mobility paper.

Input : all_results.csv (from parse_flowmon.py)
Output:
    summary_stats.csv      mean, std, 95% CI per (protocol, mobility, nodes)
    significance.csv       Mann-Whitney U + Cliff's delta, RWP vs Real
    ranking_table.csv      best protocol per (nodes, mobility) — headline table
    fig_pdr_panels.pdf     PDR vs nodes, one panel per protocol, 95% CI bars
    fig_delay_panels.pdf   same for mean delay

Decision rule (pre-registered, matches the methodology section):
    A mobility-model difference is treated as material if
    p < 0.05 (Mann-Whitney) AND |Cliff's delta| >= 0.33 (medium+).

Usage:
    pip install pandas scipy matplotlib
    python3 analyze.py all_results.csv
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ALPHA = 0.05
DELTA_THRESHOLD = 0.33  # medium effect (Romano et al. interpretation)
METRICS = ["pdr_pct", "mean_delay_ms"]
PROTOCOL_ORDER = ["aodv", "olsr", "dsdv"]
MOBILITY_LABEL = {"rwp": "Random Waypoint", "real": "Realistic (ROS2/Gazebo)"}


def ci95(x: np.ndarray) -> float:
    """Half-width of the 95% CI of the mean (t-distribution)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return 0.0
    return stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))


def cliffs_delta(a, b) -> float:
    """Cliff's delta effect size: P(a>b) - P(a<b)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return (gt - lt) / (len(a) * len(b)) if len(a) and len(b) else 0.0


def main(csv_path: Path) -> None:
    df = pd.read_csv(csv_path)
    needed = {"protocol", "mobility", "nodes", "seed", *METRICS}
    missing = needed - set(df.columns)
    if missing:
        sys.exit(f"Missing columns in {csv_path}: {missing}")

    seeds_per_cfg = df.groupby(["protocol", "mobility", "nodes"])["seed"].nunique()
    if (seeds_per_cfg < 10).any():
        print("[warn] some configurations have <10 seeds — CIs will be wide:")
        print(seeds_per_cfg[seeds_per_cfg < 10].to_string(), "\n")

    # ---------- 1. Summary statistics ----------
    rows = []
    for (p, m, n), g in df.groupby(["protocol", "mobility", "nodes"]):
        for metric in METRICS:
            vals = g[metric].dropna().to_numpy()
            rows.append({
                "protocol": p, "mobility": m, "nodes": n, "metric": metric,
                "n_seeds": len(vals),
                "mean": round(np.mean(vals), 3),
                "std": round(np.std(vals, ddof=1), 3) if len(vals) > 1 else 0,
                "ci95": round(ci95(vals), 3),
            })
    summary = pd.DataFrame(rows)
    summary.to_csv("summary_stats.csv", index=False)

    # ---------- 2. RWP vs Realistic significance ----------
    sig_rows = []
    for (p, n), g in df.groupby(["protocol", "nodes"]):
        a = g.loc[g.mobility == "rwp"]
        b = g.loc[g.mobility == "real"]
        if a.empty or b.empty:
            continue
        for metric in METRICS:
            x, y = a[metric].dropna(), b[metric].dropna()
            if len(x) < 2 or len(y) < 2:
                continue
            u, pval = stats.mannwhitneyu(x, y, alternative="two-sided")
            d = cliffs_delta(y, x)  # positive => Realistic higher
            sig_rows.append({
                "protocol": p, "nodes": n, "metric": metric,
                "rwp_mean": round(x.mean(), 3),
                "real_mean": round(y.mean(), 3),
                "p_value": round(pval, 5),
                "cliffs_delta": round(d, 3),
                "material": bool(pval < ALPHA and abs(d) >= DELTA_THRESHOLD),
            })
    sig = pd.DataFrame(sig_rows)
    sig.to_csv("significance.csv", index=False)

    # ---------- 3. Protocol ranking table (the headline) ----------
    rank_rows = []
    for (m, n), g in summary[summary.metric == "pdr_pct"].groupby(["mobility", "nodes"]):
        best = g.sort_values("mean", ascending=False).iloc[0]
        rank_rows.append({
            "nodes": n, "mobility": m,
            "best_protocol": best.protocol,
            "best_pdr": best["mean"],
        })
    ranking = pd.DataFrame(rank_rows).sort_values(["nodes", "mobility"])
    ranking.to_csv("ranking_table.csv", index=False)

    flips = []
    for n, g in ranking.groupby("nodes"):
        winners = set(g.best_protocol)
        if len(winners) > 1:
            flips.append(n)
    if flips:
        print(f"** RANKING FLIP at nodes={flips} — this is your headline finding **\n")

    # ---------- 4. Figures ----------
    metric_cfg = {
        "pdr_pct": ("Packet Delivery Ratio (%)", "fig_pdr_panels.pdf"),
        "mean_delay_ms": ("Mean End-to-End Delay (ms)", "fig_delay_panels.pdf"),
    }
    for metric, (ylabel, fname) in metric_cfg.items():
        sub = summary[summary.metric == metric]
        protos = [p for p in PROTOCOL_ORDER if p in sub.protocol.unique()]
        fig, axes = plt.subplots(1, len(protos), figsize=(3.2 * len(protos), 3.0),
                                 sharey=True)
        if len(protos) == 1:
            axes = [axes]
        for ax, p in zip(axes, protos):
            for mob, marker in (("rwp", "o"), ("real", "s")):
                g = sub[(sub.protocol == p) & (sub.mobility == mob)].sort_values("nodes")
                if g.empty:
                    continue
                ax.errorbar(g.nodes, g["mean"], yerr=g.ci95, marker=marker,
                            capsize=3, linewidth=1.4,
                            label=MOBILITY_LABEL.get(mob, mob))
            ax.set_title(p.upper(), fontsize=10)
            ax.set_xlabel("Number of nodes")
            ax.set_xticks(sorted(sub.nodes.unique()))
            ax.grid(alpha=0.3)
        axes[0].set_ylabel(ylabel)
        axes[0].legend(fontsize=8, frameon=False)
        fig.tight_layout()
        fig.savefig(fname, bbox_inches="tight")
        plt.close(fig)
        print(f"wrote {fname}")

    print("\nwrote summary_stats.csv, significance.csv, ranking_table.csv")
    print("Materially different configs (p<0.05 AND |delta|>=0.33):")
    mat = sig[sig.material]
    print(mat.to_string(index=False) if not mat.empty else "  none yet")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 analyze.py all_results.csv")
    main(Path(sys.argv[1]))
