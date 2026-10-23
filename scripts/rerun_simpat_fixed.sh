#!/usr/bin/env bash
# Cost-study batch, v1.1: runs the 300 configurations with the corrected RWP program (fanet-compare-simpat).
# Same design as the v1.0 batch: 3 protocols x 2 mobility x 5 scales x 10 seeds = 300 runs,
# sequential, same loop order. Differences: times the ns-3 binary DIRECTLY (not through ./ns3 run),
# so /usr/bin/time measures only the simulation process; keeps every run's stdout; can resume.
#
# Usage:
#   bash rerun_simpat_fixed.sh test     # one run only (AODV, RWP, n=100, seed 1) to check timing/RSS
#   bash rerun_simpat_fixed.sh          # full 300-run batch (skips runs already done)
# NS3_DIR and OUTDIR can be overridden from the environment (defaults: paths on the original machine).
# Run "./ns3 build" in NS3_DIR first; waypoints_independent/ must be in NS3_DIR.
NS3_DIR="${NS3_DIR:-$HOME/Documents/Code/ns-3-dev}"
SCENARIO="fanet-compare-simpat"
BIN="$NS3_DIR/build/scratch/ns3-dev-${SCENARIO}-default"
OUTDIR="${OUTDIR:-$HOME/Documents/Coupling_UAV_Mobility_Routing_FANET/repo/results/rerun_simpat_2026-10-23}"
LOGDIR="$OUTDIR/logs"
CSV="$OUTDIR/timing_simpat_300runs.csv"
set -u

[ -x "$BIN" ] || { echo "binary not found: $BIN"; exit 1; }
[ -x /usr/bin/time ] || { echo "/usr/bin/time not found"; exit 1; }
mkdir -p "$LOGDIR"
[ -f "$CSV" ] || echo "protocol,mobility,nNodes,seed,wallClockSec,peakRssKB,cpuPct,exitStatus,linkBreaks,avgNodeDegree,pdr" > "$CSV"
cd "$NS3_DIR" || exit 1          # same working directory as the original batch (waypoints_independent, results.csv)

run_one() {   # protocol mobility nodes seed
  local p=$1 m=$2 n=$3 s=$4
  local tag="${p}_${m}_n${n}_s${s}"
  local log="$LOGDIR/$tag.out" tlog="$LOGDIR/$tag.time"
  if [ -f "$tlog" ] && grep -q "Exit status: 0" "$tlog"; then return 0; fi
  /usr/bin/time -v -o "$tlog" "$BIN" --protocol=$p --mobility=$m --nNodes=$n --RngRun=$s > "$log" 2>&1
  local wall rss cpu ex breaks deg pdr
  wall=$(awk -F': ' '/Elapsed \(wall clock\)/{print $2}' "$tlog" | awk -F: '{if(NF==3)print $1*3600+$2*60+$3; else print $1*60+$2}')
  rss=$(awk -F': ' '/Maximum resident set size/{print $2}' "$tlog")
  cpu=$(awk -F': ' '/Percent of CPU/{gsub("%","",$2);print $2}' "$tlog")
  ex=$(awk -F': ' '/Exit status/{print $2}' "$tlog")
  breaks=$(grep -oP '^Link Breaks: \K[0-9]+' "$log" | head -1)
  deg=$(grep -oP '^Avg Node Degree: \K[0-9.]+' "$log" | head -1)
  pdr=$(grep -oP '^PDR: \K[0-9.]+' "$log" | head -1)
  echo "$p,$m,$n,$s,$wall,$rss,$cpu,$ex,$breaks,$deg,$pdr" >> "$CSV"
  echo "$(date +%H:%M:%S) $tag wall=${wall}s rss=${rss}KB breaks=$breaks deg=$deg exit=$ex"
}

if [ "${1:-}" = "test" ]; then
  rm -f "$LOGDIR/AODV_RWP_n100_s1."*        # always redo the test run
  run_one AODV RWP 100 1
  exit 0
fi

for p in AODV OLSR DSDV; do for m in Realistic RWP; do for n in 5 10 20 50 100; do for s in $(seq 1 10); do
  run_one $p $m $n $s
done; done; done; done
echo "ALL DONE: $(($(wc -l < "$CSV")-1)) rows in $CSV"
