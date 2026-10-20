#!/usr/bin/env bash
# =====================================================================
# instrumented_run_batch.sh — Full experiment matrix + per-run
#   wall-clock time, peak memory (RSS), and CPU% instrumentation.
#
#   3 protocols x 2 mobility models x 5 scales x 10 seeds = 300 runs
#
# VERIFIED against the actual fanet-compare.cc CLI (2026-07-16):
#   --protocol=AODV|OLSR|DSDV   (case-sensitive, must be UPPERCASE)
#   --mobility=Realistic|RWP    (case-sensitive)
#   --nNodes=N
#   --RngRun=S
#   --waypointDir=waypoints_independent   (default, no need to pass)
#   There is NO --flowmonOut flag. The program itself appends one line
#   per run to results.csv (relative to $NS3_DIR), WITHOUT a seed
#   column. This script tags each appended line with protocol/mobility/
#   nodes/seed itself, immediately after each run, so runs stay
#   traceable despite the program not recording RngRun.
#
# OUTPUT:
#   $OUTDIR/results_tagged.csv   one row per run: protocol,mobility,nodes,
#                                 seed,pdr_pct,delay_ms,tx,rx,breaks,hops,
#                                 degree,lifetime
#   $OUTDIR/stage_timing.csv     one row per run: stage,protocol,mobility,
#                                 nodes,seed,wall_s,max_rss_kb,cpu_pct,exit_status
#
# REQUIREMENTS: /usr/bin/time (GNU time). Already confirmed present.
#
# USAGE:
#   chmod +x instrumented_run_batch.sh
#   NS3_DIR=~/ns-3-dev ./instrumented_run_batch.sh
# =====================================================================
set -u

NS3_DIR="${NS3_DIR:-$HOME/ns-3-dev}"
SCENARIO="${SCENARIO:-fanet-compare}"
OUTDIR="${OUTDIR:-$PWD/results}"
RESULTS_CSV_IN_NS3="$NS3_DIR/results.csv"     # where the C++ program appends
TAGGED_CSV="$OUTDIR/results_tagged.csv"
TIMING_CSV="$OUTDIR/stage_timing.csv"

PROTOCOLS=(AODV OLSR DSDV)
MOBILITY=(Realistic RWP)
NODES=(5 10 20 50 100)
SEEDS=$(seq 1 10)

mkdir -p "$OUTDIR"

if ! command -v /usr/bin/time >/dev/null 2>&1; then
  echo "ERROR: /usr/bin/time not found. Install with: sudo apt install time"
  exit 1
fi

if [[ ! -s "$TIMING_CSV" ]]; then
  echo "stage,protocol,mobility,nodes,seed,wall_s,max_rss_kb,cpu_pct,exit_status" > "$TIMING_CSV"
fi
if [[ ! -s "$TAGGED_CSV" ]]; then
  echo "protocol,mobility,nodes,seed,pdr_pct,delay_ms,tx,rx,breaks,hops,degree,lifetime" > "$TAGGED_CSV"
fi

cd "$NS3_DIR" || { echo "ns-3 dir not found: $NS3_DIR"; exit 1; }

n_seeds=$(echo "$SEEDS" | wc -w)
total=$(( ${#PROTOCOLS[@]} * ${#MOBILITY[@]} * ${#NODES[@]} * n_seeds ))
echo "Experiment matrix: $total runs"
echo "Tagged results   -> $TAGGED_CSV"
echo "Timing data      -> $TIMING_CSV"
echo "----------------------------------------"

done_n=0; fail_n=0
for p in "${PROTOCOLS[@]}"; do
  for m in "${MOBILITY[@]}"; do
    for n in "${NODES[@]}"; do
      for s in $SEEDS; do
        tag="${p}_${m}_n${n}_s${s}"
        log="$OUTDIR/log_${tag}.txt"
        timelog=$(mktemp)

        # Line count of results.csv BEFORE this run, so we know which
        # new line(s) this run produced.
        lines_before=0
        [[ -f "$RESULTS_CSV_IN_NS3" ]] && lines_before=$(wc -l < "$RESULTS_CSV_IN_NS3")

        echo "[run ] $tag"
        /usr/bin/time -v -o "$timelog" \
          ./ns3 run "$SCENARIO --protocol=$p --mobility=$m --nNodes=$n --RngRun=$s" \
          >"$log" 2>&1
        exit_status=$?

        # ---- extract wall time / peak RSS / CPU% ----
        wall_raw=$(grep "Elapsed (wall clock) time" "$timelog" | awk -F': ' '{print $2}')
        rss_kb=$(grep "Maximum resident set size" "$timelog" | awk -F': ' '{print $2}')
        cpu_pct=$(grep "Percent of CPU" "$timelog" | awk -F': ' '{print $2}' | tr -d '%')
        wall_s=$(awk -F: -v t="$wall_raw" 'BEGIN{
          n=split(t, a, ":");
          if (n==3) print a[1]*3600+a[2]*60+a[3];
          else if (n==2) print a[1]*60+a[2];
          else print t;
        }')
        echo "${p},${m},${n},${s},${wall_s:-NA},${rss_kb:-NA},${cpu_pct:-NA},${exit_status}" \
          | sed "s/^/simulate,/" >> "$TIMING_CSV"

        # ---- pull the newly appended line(s) from results.csv and tag them ----
        if [[ -f "$RESULTS_CSV_IN_NS3" ]]; then
          lines_after=$(wc -l < "$RESULTS_CSV_IN_NS3")
          if (( lines_after > lines_before )); then
            new_line=$(tail -n $((lines_after - lines_before)) "$RESULTS_CSV_IN_NS3" | tail -n1)
            # new_line format from the C++ code:
            # protocol,mobility,nNodes,pdr,avgDelay,tx,rx,breaks,hops,degree,lifetime
            rest=$(echo "$new_line" | cut -d, -f4-)
            echo "${p},${m},${n},${s},${rest}" >> "$TAGGED_CSV"
            done_n=$((done_n+1))
            echo "  wall=${wall_s}s  peak_rss=${rss_kb}kB  cpu=${cpu_pct}%"
          else
            fail_n=$((fail_n+1)); echo "  FAILED (no new results.csv line) — see $log"
          fi
        else
          fail_n=$((fail_n+1)); echo "  FAILED (results.csv missing) — see $log"
        fi
        rm -f "$timelog"
      done
    done
  done
done

echo "----------------------------------------"
echo "Done: $done_n / $total   Failed: $fail_n"
echo "Tagged results: $TAGGED_CSV"
echo "Timing data:    $TIMING_CSV"
