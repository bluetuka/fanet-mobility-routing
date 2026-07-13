#!/usr/bin/env bash
# =====================================================================
# run_batch.sh — Full experiment matrix for the FANET mobility paper
#   3 protocols x 2 mobility models x 4 scales x N seeds
#
# ADAPT THE ONE LINE MARKED >>> to your ns-3 script's CLI.
# Assumes your ns-3 scenario accepts:
#   --protocol={aodv|olsr|dsdv} --mobility={rwp|real} --nodes=N
#   --seed=S --flowmonOut=PATH [--traceFile=CSV for real mobility]
# If your flags differ, change only the ns3 line below.
# =====================================================================
set -u

NS3_DIR="${NS3_DIR:-$HOME/ns-3-dev}"          # path to your ns-3 tree
SCENARIO="${SCENARIO:-fanet-eval}"            # your scenario program name
OUTDIR="${OUTDIR:-$PWD/results}"
TRACE_DIR="${TRACE_DIR:-$PWD/trajectories}"   # CSVs extracted from rosbag

PROTOCOLS=(aodv olsr dsdv)
MOBILITY=(rwp real)
NODES=(5 20 50 100)
SEEDS=$(seq 1 10)                             # >=10 seeds per config

mkdir -p "$OUTDIR"
cd "$NS3_DIR" || { echo "ns-3 dir not found: $NS3_DIR"; exit 1; }

total=0; done_n=0; fail_n=0
for p in "${PROTOCOLS[@]}"; do
  for m in "${MOBILITY[@]}"; do
    for n in "${NODES[@]}"; do
      for s in $SEEDS; do total=$((total+1)); done
    done
  done
done
echo "Experiment matrix: $total runs"
echo "----------------------------------------"

for p in "${PROTOCOLS[@]}"; do
  for m in "${MOBILITY[@]}"; do
    for n in "${NODES[@]}"; do
      for s in $SEEDS; do
        tag="${p}_${m}_n${n}_s${s}"
        out="$OUTDIR/flowmon_${tag}.xml"
        log="$OUTDIR/log_${tag}.txt"

        if [[ -s "$out" ]]; then
          echo "[skip] $tag (already done)"
          done_n=$((done_n+1)); continue
        fi

        extra=""
        if [[ "$m" == "real" ]]; then
          extra="--traceFile=$TRACE_DIR/traj_n${n}.csv"
        fi

        echo "[run ] $tag"
        # >>> ADAPT THIS LINE TO YOUR SCENARIO'S CLI <<<
        ./ns3 run "$SCENARIO --protocol=$p --mobility=$m --nodes=$n \
          --seed=$s --flowmonOut=$out $extra" >"$log" 2>&1

        if [[ -s "$out" ]]; then
          done_n=$((done_n+1))
        else
          fail_n=$((fail_n+1)); echo "  FAILED — see $log"
        fi
      done
    done
  done
done

echo "----------------------------------------"
echo "Done: $done_n / $total   Failed: $fail_n"
echo "Next: python3 parse_flowmon.py $OUTDIR -o all_results.csv"
