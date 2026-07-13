#!/usr/bin/env python3
"""
parse_flowmon.py — Parse ns-3 FlowMonitor XML files into one tidy CSV.

Expects filenames produced by run_batch.sh:
    flowmon_{protocol}_{mobility}_n{nodes}_s{seed}.xml

Output: one row per run with network-level aggregates:
    protocol, mobility, nodes, seed,
    pdr_pct, mean_delay_ms, mean_jitter_ms,
    tx_packets, rx_packets, lost_packets, throughput_kbps

Usage:
    python3 parse_flowmon.py results/ -o all_results.csv
"""
import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FNAME_RE = re.compile(
    r"flowmon_(?P<protocol>\w+)_(?P<mobility>\w+)_n(?P<nodes>\d+)_s(?P<seed>\d+)\.xml$"
)


def parse_time_ns(value: str) -> float:
    """FlowMonitor times look like '+9.2e+09ns' — return nanoseconds as float."""
    return float(value.replace("ns", "").replace("+", ""))


def parse_one(path: Path) -> dict | None:
    m = FNAME_RE.search(path.name)
    if not m:
        print(f"[warn] filename not recognized, skipping: {path.name}", file=sys.stderr)
        return None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        print(f"[warn] XML parse error in {path.name}: {e}", file=sys.stderr)
        return None

    tx = rx = lost = 0
    delay_ns = jitter_ns = 0.0
    rx_bytes = 0
    t_first = float("inf")
    t_last = 0.0

    for flow in root.iter("Flow"):
        # FlowMonitor's <FlowStats> children carry these attributes
        if "txPackets" not in flow.attrib:
            continue
        tx += int(flow.attrib["txPackets"])
        rx += int(flow.attrib["rxPackets"])
        lost += int(flow.attrib.get("lostPackets", 0))
        delay_ns += parse_time_ns(flow.attrib.get("delaySum", "0ns"))
        jitter_ns += parse_time_ns(flow.attrib.get("jitterSum", "0ns"))
        rx_bytes += int(flow.attrib.get("rxBytes", 0))
        if "timeFirstTxPacket" in flow.attrib:
            t_first = min(t_first, parse_time_ns(flow.attrib["timeFirstTxPacket"]))
        if "timeLastRxPacket" in flow.attrib:
            t_last = max(t_last, parse_time_ns(flow.attrib["timeLastRxPacket"]))

    if tx == 0:
        print(f"[warn] no transmitted packets in {path.name}", file=sys.stderr)
        return None

    duration_s = (t_last - t_first) / 1e9 if t_last > t_first else 0.0
    return {
        "protocol": m["protocol"],
        "mobility": m["mobility"],
        "nodes": int(m["nodes"]),
        "seed": int(m["seed"]),
        "pdr_pct": round(100.0 * rx / tx, 3),
        "mean_delay_ms": round(delay_ns / rx / 1e6, 3) if rx else None,
        "mean_jitter_ms": round(jitter_ns / rx / 1e6, 3) if rx else None,
        "tx_packets": tx,
        "rx_packets": rx,
        "lost_packets": lost,
        "throughput_kbps": round(rx_bytes * 8 / duration_s / 1e3, 2) if duration_s else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results_dir", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("all_results.csv"))
    args = ap.parse_args()

    rows = []
    for path in sorted(args.results_dir.glob("flowmon_*.xml")):
        row = parse_one(path)
        if row:
            rows.append(row)

    if not rows:
        sys.exit("No valid FlowMonitor files found.")

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n_cfg = len({(r["protocol"], r["mobility"], r["nodes"]) for r in rows})
    print(f"Parsed {len(rows)} runs across {n_cfg} configurations -> {args.output}")
    print("Next: python3 analyze.py all_results.csv")


if __name__ == "__main__":
    main()
