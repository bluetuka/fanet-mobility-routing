#!/usr/bin/env bash
# =====================================================================
# run_parallel_benchmark.sh -- run-level parallelism benchmark (JPDC2026)
#
# Executes the SAME set of independent ns-3 runs (fanet-compare, existing
# arguments) with at most P concurrent processes, for each P in PS_LIST,
# and records batch makespan, per-run duration, PID, exit status, peak RSS.
#
# NON-DESTRUCTIVE: does not touch the simulation source, the seeds, the
# existing results.csv or any existing results folder. Every run executes
# in its own working directory (--cwd), so the program's append to
# "results.csv" lands in that run's private directory (no collisions).
#
# Only run-level parallelism is measured: each ns-3 process stays
# single-threaded.
#
# Environment overrides (defaults = pilot of 60 runs):
#   NS3_DIR, WAYPOINT_DIR, BENCH_DIR
#   PS_LIST="1 2 4 6"
#   NODES_LIST="100 50"   MOB_LIST="RWP Realistic"
#   PROTO_LIST="AODV DSDV OLSR"   SEED_LIST="1 2 3 4 5"
# Full experiment (300 runs):
#   NODES_LIST="100 50 20 10 5" SEED_LIST="1 2 3 4 5 6 7 8 9 10" \
#   PS_LIST="1 6" BENCH_DIR=$HOME/ns-3-dev/benchmark_parallel_full ./run_parallel_benchmark.sh
# =====================================================================
set -u

NS3_DIR="${NS3_DIR:-$HOME/ns-3-dev}"
WAYPOINT_DIR="${WAYPOINT_DIR:-$NS3_DIR/waypoints_independent}"
BENCH_DIR="${BENCH_DIR:-$NS3_DIR/benchmark_parallel}"
PS_LIST="${PS_LIST:-1 2 4 6}"
NODES_LIST="${NODES_LIST:-100 50}"      # heavy first (same fixed order for every P)
MOB_LIST="${MOB_LIST:-RWP Realistic}"
PROTO_LIST="${PROTO_LIST:-AODV DSDV OLSR}"
SEED_LIST="${SEED_LIST:-1 2 3 4 5}"

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -x "$NS3_DIR/ns3" ]] || die "ns3 launcher not found in $NS3_DIR"
[[ -d "$WAYPOINT_DIR" ]] || die "waypoint dir not found: $WAYPOINT_DIR"
TIME_BIN="${TIME_BIN:-/usr/bin/time}"
command -v "$TIME_BIN" >/dev/null 2>&1 || die "GNU time missing (sudo apt install time)"
(( BASH_VERSINFO[0] > 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 3) )) || die "bash >= 4.3 needed (wait -n)"

mkdir -p "$BENCH_DIR" || die "cannot create $BENCH_DIR"
BENCH_DIR="$(cd "$BENCH_DIR" && pwd)"
WAYPOINT_DIR="$(cd "$WAYPOINT_DIR" && pwd)"

# Build the fixed ordered configuration list (identical for every P).
CONFIGS=()
for n in $NODES_LIST; do for p in $PROTO_LIST; do for m in $MOB_LIST; do for s in $SEED_LIST; do
  CONFIGS+=("$p $m $n $s")
done; done; done; done
TOTAL=${#CONFIGS[@]}

run_one() {   # args: P protocol mobility nNodes seed
  local P=$1 p=$2 m=$3 n=$4 s=$5
  local tag="${p}_${m}_n${n}_s${s}"
  local d="$BENCH_DIR/P${P}/runs/$tag"
  mkdir -p "$d"
  local t0 t1 rc rss
  t0=$(date +%s.%N)
  "$TIME_BIN" -v -o "$d/time.txt" \
    "$NS3_DIR/ns3" run --no-build --cwd "$d" \
    "fanet-compare --protocol=$p --mobility=$m --waypointDir=$WAYPOINT_DIR --nNodes=$n --RngRun=$s" \
    >"$d/stdout.txt" 2>"$d/stderr.txt"
  rc=$?
  t1=$(date +%s.%N)
  rss=$(grep "Maximum resident set size" "$d/time.txt" 2>/dev/null | awk -F': ' '{print $2}')
  local row_ok=0; [[ -s "$d/results.csv" ]] && row_ok=1
  # one private line per run (no shared file is appended concurrently)
  echo "$P,$p,$m,$n,$s,$BASHPID,$t0,$t1,$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.3f", b-a}'),$rc,${rss:-NA},$row_ok" > "$d/meta.csv"
}

# ---- preflight: smoke run (also warms the page cache / binary) ----------
echo "== Preflight =="
echo "host: $(hostname)  cpus: $(nproc)  load: $(cut -d' ' -f1-3 /proc/loadavg)"
grep -m1 "model name" /proc/cpuinfo || true
[[ -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]] && echo "governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
echo "configurations per P: $TOTAL   P list: $PS_LIST"

ORIG_CSV="$NS3_DIR/results.csv"
before_sum="absent"; [[ -f "$ORIG_CSV" ]] && before_sum=$(md5sum "$ORIG_CSV" | cut -d' ' -f1)

SMOKE="$BENCH_DIR/smoke"; rm -rf "$SMOKE"; mkdir -p "$SMOKE"
BENCH_SAVE="$BENCH_DIR"; BENCH_DIR="$SMOKE"
run_one 0 AODV RWP 5 1
BENCH_DIR="$BENCH_SAVE"
IFS=, read -r _ _ _ _ _ _ _ _ sdur src _ srow < "$SMOKE/P0/runs/AODV_RWP_n5_s1/meta.csv"
[[ "$src" == "0" && "$srow" == "1" ]] || die "smoke run failed (exit=$src, results row=$srow). See $SMOKE/P0/runs/AODV_RWP_n5_s1/stderr.txt"
echo "smoke run OK (${sdur}s)"

BATCH_CSV="$BENCH_DIR/batch_summary.csv"
[[ -f "$BATCH_CSV" ]] || echo "P,runs,failed,start_epoch,end_epoch,makespan_s,sum_run_s,mean_run_s,loadavg_at_start" > "$BATCH_CSV"

for P in $PS_LIST; do
  [[ -d "$BENCH_DIR/P${P}" ]] && die "$BENCH_DIR/P${P} already exists; move it away (never overwritten)"
  mkdir -p "$BENCH_DIR/P${P}/runs"
  echo
  echo "== P=$P : $TOTAL runs, at most $P concurrent =="
  load=$(cut -d' ' -f1 /proc/loadavg)
  T0=$(date +%s.%N)
  for cfg in "${CONFIGS[@]}"; do
    read -r p m n s <<< "$cfg"
    while (( $(jobs -rp | wc -l) >= P )); do wait -n; done
    run_one "$P" "$p" "$m" "$n" "$s" &
  done
  wait
  T1=$(date +%s.%N)

  cat "$BENCH_DIR/P${P}"/runs/*/meta.csv > "$BENCH_DIR/P${P}/per_run.csv"
  awk -F, -v P="$P" -v t0="$T0" -v t1="$T1" -v load="$load" '
    { n++; if ($10 != 0 || $12 != 1) f++; sum += $9 }
    END { printf "%s,%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%s\n", P, n, f+0, t0, t1, t1-t0, sum, sum/n, load }' \
    "$BENCH_DIR/P${P}/per_run.csv" >> "$BATCH_CSV"
  tail -1 "$BATCH_CSV"
done

# per-run table with header, for all P
{ echo "P,protocol,mobility,nNodes,seed,pid,start_epoch,end_epoch,duration_s,exit_status,peak_rss_kb,results_row_present"
  for P in $PS_LIST; do cat "$BENCH_DIR/P${P}/per_run.csv"; done; } > "$BENCH_DIR/per_run_all.csv"

# the original results.csv must be untouched
after_sum="absent"; [[ -f "$ORIG_CSV" ]] && after_sum=$(md5sum "$ORIG_CSV" | cut -d' ' -f1)
if [[ "$before_sum" == "$after_sum" ]]; then echo "original results.csv untouched (OK)"; else echo "WARNING: $ORIG_CSV changed during the benchmark"; fi

echo
echo "Done. Now run:  python3 summarize_parallel_benchmark.py $BENCH_DIR"
