#!/usr/bin/env bash
# Runs BOTH parallel benchmarks of the cost study (v1.1) with the corrected program (fanet-compare-simpat):
#   1) full matrix: 300 runs, P = 1 and 6
#   2) subset: n = 100, 50, seeds 1-5 (60 runs), P = 1, 2, 4, 6
# Total roughly 2-2.5 h. Keep the machine otherwise idle while it runs (timing!).
# Same steps as the script used for the manuscript; only the paths were made relative to this repository.
# Usage: NS3_DIR=/path/to/ns-3-dev bash scripts/parallel_benchmark/run_all_parallel_simpat.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
NS3="${NS3_DIR:-$HOME/Documents/Code/ns-3-dev}"
S="$HERE/run_parallel_benchmark_simpat.sh"
cd "$NS3" || exit 1
FULL=$NS3/benchmark_parallel_full_simpat
PILOT=$NS3/benchmark_parallel_pilot_simpat
NS3_DIR=$NS3 NODES_LIST="100 50 20 10 5" SEED_LIST="1 2 3 4 5 6 7 8 9 10" PS_LIST="1 6" BENCH_DIR=$FULL bash "$S" || exit 1
NS3_DIR=$NS3 BENCH_DIR=$PILOT bash "$S" || exit 1
for B in $FULL $PILOT; do
  echo "== summary $B"; python3 "$HERE/summarize_parallel_benchmark.py" "$B"
  dest="$REPO/results/$(basename $B)"
  mkdir -p "$dest"
  cp "$B/batch_summary.csv" "$B/speedup_summary.csv" "$B/per_run_all.csv" "$dest/"
done
echo "ALL PARALLEL DONE"
