# Run-level parallelism benchmark (JPDC 2026)

Measures wall-clock makespan of the same independent ns-3 runs executed with at most
P = 1, 2, 4, 6 concurrent processes. Does not modify the simulation, the seeds or any
existing result. Each ns-3 process stays single-threaded (run-level parallelism only).

Pilot: 2 node counts (50, 100) x 2 mobility (RWP, Realistic) x 3 protocols x 5 seeds = 60 runs.

    cd ~/ns-3-dev
    ./ns3 build                       # build once, runs use --no-build
    ./run_parallel_benchmark.sh       # about 1 h for P=1,2,4,6
    python3 summarize_parallel_benchmark.py benchmark_parallel

Outputs (all under benchmark_parallel/): batch_summary.csv (makespan per P),
per_run_all.csv (PID, start, end, duration, exit status, peak RSS per run),
speedup_summary.csv (S_p = T_1/T_p, E_p = S_p/p), and per-run stdout/stderr/results.csv
in P<k>/runs/<tag>/. Each run has its own working directory, so the program's append to
results.csv cannot collide. The summary script also checks that every configuration
produces the identical results row for every P.

Notes: the 6 cores are physical (no SMT). Close other heavy programs while measuring.
