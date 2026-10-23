# Mobility, Routing and Computational Cost in UAV Network Co-Simulation (ns-3)

Code and data for the study "Computational Cost of UAV Network Co-Simulation: Scalability, Topology Churn, and Routing Protocol Effects" (journal manuscript in preparation; 5 to 100 nodes, 300 runs), and for the earlier study that preceded it:

1. **Computational cost study (2026)** - the main content of this repository (scenario `fanet-compare-simpat.cc`, data under `results/simpat_rerun_2026-10/` and `results/parallel_benchmark_*_simpat/`).
2. **Earlier mobility-vs-routing study (5, 10 and 20 nodes)** - prepared for LARS 2026; that submission was not accepted. Its scenario and data are kept for transparency (see the last section).

Both use the same ns-3 scenario program, the same routing protocols (AODV, OLSR, DSDV) and the same two mobility sources (Random Waypoint, and trajectories recorded from a ROS 2 / Gazebo UAV simulation).

## Version 1.1 (23 October 2026): correction of the Random Waypoint baseline

Version 1.0 of this repository contained a configuration error in the Random Waypoint (RWP) branch of the scenario program:

- In `fanet-compare-jpdc.cc` (v1.0 cost study) and `fanet-compare.cc` (earlier study), the RWP *destinations* were drawn with `"PositionAllocator", StringValue ("ns3::RandomRectanglePositionAllocator")`. Given only by type name, the allocator falls back to its default X, Y ~ U(0, 1), so every destination lay inside a 1 m x 1 m square and the nodes slowly gathered in one corner. Initial positions were correct.
- An intermediate fix (`fanet-compare-uav.cc`, not distributed) set the destinations correctly but did not set the initial positions, so all nodes started at the origin.

`ns3-scratch/fanet-compare-simpat.cc` fixes both: initial positions and destinations are drawn from the same calibrated square (side `sqrt(n * 962.11 / (3 ln n))` m, mean degree about 3 ln n). The Realistic (Gazebo-trace) branch is identical in all versions.

All 300 runs and both parallel benchmarks were repeated with the corrected program. Realistic-mobility link breaks and node degree are bit-identical to v1.0; all RWP values changed (for example, RWP link breaks at n = 100: 61 in v1.0, 1156 now). The v1.0 files are kept below for transparency and are marked as such; do not use them for the RWP condition.

## Repository layout

- `ns3-scratch/fanet-compare-simpat.cc` - scenario used for the computational cost study (v1.1, corrected RWP; use this one)
- `ns3-scratch/fanet-compare-jpdc.cc` - v1.0 scenario of the cost study (RWP destination bug, kept for transparency)
- `ns3-scratch/fanet-compare.cc` - scenario of the earlier 5/10/20-node study (includes the preliminary GridCoverage branch; same RWP destination bug)
- `figures/` - the five figure PDFs (Figures 3-5) exactly as used in the manuscript
- `ns3-local-build-patches.diff` - the three local build patches applied to ns-3 (see "Build")
- `waypoints/waypoints_independent/` - 5 UAV trajectories recorded from Gazebo
- `results/` - result tables (column descriptions below)
- `scripts/` - batch runners, analysis, benchmark and figure scripts

## Build (exact environment of the cost study)

- ns-3-dev commit `1324cdc8f33d862b9091452ecb9dffef952fde12` (17 May 2026, reports as ns-3.47-139)
- Compiler: `/usr/bin/g++-11` (the default compiler on the test machine was GCC 13.3.0 and was not used for the build)
- Build profile: `default` (assertions and logging ON, native optimizations OFF). Timings depend on this profile.
- Three local patches (`ns3-local-build-patches.diff`): `CXX_EXTENSIONS` set to ON in `build-support/macros-and-definitions.cmake` and `build-support/custom-modules/ns3-compiler-workarounds.cmake`, and the `uint128_t` / `int128_t` typedefs in `src/core/model/int64x64-128.h` rewritten with `unsigned __int128` / `__int128`.

```
git clone https://gitlab.com/nsnam/ns-3-dev.git && cd ns-3-dev
git checkout 1324cdc8f33d862b9091452ecb9dffef952fde12
git apply /path/to/this/repo/ns3-local-build-patches.diff
cp /path/to/this/repo/ns3-scratch/fanet-compare-simpat.cc scratch/
cp -r /path/to/this/repo/waypoints/waypoints_independent .
CXX=/usr/bin/g++-11 ./ns3 configure --build-profile=default
./ns3 build
```

`fanet-compare-simpat.cc` is byte-identical to the program that produced the v1.1 results. Besides the RWP fix it adds three optional arguments that are not used by the batch scripts: `--rwpSpeedMin`, `--rwpSpeedMax` (defaults 1.0 and 1.5 m/s, as before) and `--dumpPositions` (debug output).

## Running one configuration

```
./ns3 run "fanet-compare-simpat --protocol=AODV --mobility=Realistic --nNodes=20 --RngRun=1"
```

`--protocol` is AODV, OLSR or DSDV (upper case). `--mobility` is `RWP` or `Realistic`. The program appends one line per run to `results.csv` (no header, no seed column) and prints `Link Breaks:`, `Avg Node Degree:` and `PDR:` to stdout.

`scripts/rerun_simpat_fixed.sh` is the batch script used for v1.1: it runs the 300 configurations sequentially and times the compiled binary directly with GNU `time` (not through the `./ns3` launcher), so the measurement contains only the simulation process. `scripts/instrumented_run_batch.sh` is the v1.0 wrapper (it went through `./ns3 run`).

## Scenario parameters

IEEE 802.11a, OfdmRate6Mbps; LogDistance propagation (exponent 3.0) plus a 17.5 m range limit; 32 s simulated time; 10 seeds per configuration; 3 protocols x 2 mobility models x 5 node counts (5, 10, 20, 50, 100) = 300 runs.

## Result files

Cost study, v1.1 (corrected RWP; these are the data behind the manuscript):

- `results/simpat_rerun_2026-10/timing_simpat_300runs.csv` - one row per run (300). Header: protocol, mobility, nNodes, seed, wallClockSec, peakRssKB, cpuPct, exitStatus, linkBreaks, avgNodeDegree, pdr. Table 1 and Figures 3-5 are computed from this file.
- `results/parallel_benchmark_full_simpat/` - run-level parallelism benchmark over the same 300 configurations with P = 1 and P = 6 concurrent processes (`per_run_all.csv`: PID, start, end, duration, exit status, peak RSS per run; `batch_summary.csv`; `speedup_summary.csv`).
- `results/parallel_benchmark_pilot_simpat/` - 60-run subset (n = 50 and 100, seeds 1-5) with P = 1, 2, 4, 6.

Cost study, v1.0 (RWP destination bug; Realistic rows are still valid):

- `results/jpdc2026_results_300runs.csv` - no header. Columns: protocol, mobility, nNodes, PDR (%), average delay (ms), tx packets, rx packets, link breaks, average hop count, average node degree, average link lifetime (s).
- `results/jpdc2026_timing_300runs.csv` - header: protocol, mobility, nNodes, seed, wallClockSec, peakRssKB, linkBreaks, avgNodeDegree.
- `results/parallel_benchmark_full/`, `results/parallel_benchmark_pilot/` - v1.0 parallel benchmark.

Earlier study: `results/results_n10.csv`, `results/scalability_summary.csv`, `results/lars-revision-2026/` (see the last section).

## Provenance of the timing numbers

In v1.1, every cell of Table 1 (mean +- sd of wall-clock time over 10 seeds) comes from one sweep, `results/simpat_rerun_2026-10/timing_simpat_300runs.csv`, run sequentially on the same six-core workstation with the binary timed directly. All 300 runs exited with status 0.

As an independent check, the sequential (P = 1) batch of the parallel benchmark re-ran all 300 configurations through the `./ns3` launcher. Its per-configuration means agree with Table 1 within 6% for n >= 50 and within 3-7% at n = 20. At n = 10 and n = 5, where a run lasts about a second or less, they are 10-19% and 28-49% higher (0.16-0.21 s in absolute terms at n = 5), consistent with a fixed per-invocation launcher cost. The RWP/Realistic runtime ratio never exceeds 1.52x, and peak memory is unchanged.

Parallel speed-up (six physical cores, each ns-3 process single-threaded, `results/parallel_benchmark_full_simpat/`): 4059 s at P = 1 to 741 s at P = 6, i.e. 5.48x speed-up and 91.3% parallel efficiency; the mean run time grew from 13.52 s to 14.80 s. Subset (`results/parallel_benchmark_pilot_simpat/`): 1.95x, 3.71x and 5.22x at P = 2, 4 and 6 (efficiency 97.3%, 92.8%, 87.0%). Simulation results were identical across all P.

v1.0 note: the v1.0 Table 1 was assembled from two sweeps (see the v1.0 README in the Git history); those numbers are superseded.

## Reproducing the figures

```
python3 scripts/make_figures.py --timing results/simpat_rerun_2026-10/timing_simpat_300runs.csv --out figs
```

This writes one vector PDF per panel (fonts embedded, no title inside the image): `Figure_3_wallclock_{Realistic,RWP}.pdf` (cost vs. nodes, from the Table 1 values embedded in the script), `Figure_4_memory_{Realistic,RWP}.pdf` (peak memory) and `Figure_5_breaks_vs_time.pdf` (cost vs. link breaks). The plotted data are the same as in the manuscript figures (`figures/`); fonts and legend placement may differ slightly. Figure 1 comes from `scripts/figures/make_fig1.py`.

The parallel benchmark is run with `scripts/parallel_benchmark/run_all_parallel_simpat.sh` (calls `run_parallel_benchmark_simpat.sh`, then `summarize_parallel_benchmark.py`; about 2-2.5 h).

## Citation

See `CITATION.cff` and cite the archived version of this repository: version 1.1, https://doi.org/10.5281/zenodo.23603206 (version 1.0, https://doi.org/10.5281/zenodo.23517645, contains the RWP bug described above).

## License

MIT License (see LICENSE).

## Earlier study: GridCoverage Mobility Model (Preliminary, LARS 2026 revision)

Added 2026-09-24 in response to Daniel Bonilla Licea proposal to restructure the LARS revision as a mobility x network/communication-metrics matrix, with each mobility model tied to a concrete, named practical scenario rather than a realistic/non-realistic label.

**Warning (added in v1.1):** `ns3-scratch/fanet-compare.cc` has the same RWP destination bug described at the top of this README. All RWP numbers in this section and in `results/results_n10.csv`, `results/scalability_summary.csv` and `results/lars-revision-2026/` (including the RWP degree quoted below) were produced with it and are not valid as a Random Waypoint baseline. The Realistic and GridCoverage numbers are not affected.

Scope note: everything in this section belongs to the earlier 5/10/20-node study (LARS 2026 revision, not accepted) only. It is NOT part of the cost-study dataset or claims -- the existing RWP and Realistic branches in ns3-scratch/fanet-compare.cc, and the results already in results/results_n10.csv and results/scalability_summary.csv, are unmodified.

Model: a coordinated multi-UAV extension of the single-UAV Grid Coverage algorithm from Duarte de Souza, Pereira, Pazelli and Vivaldini, "Evaluating Coverage Path Planning Strategies for UAVs with Real-Time Obstacle Avoidance in Forested Environments," IEEE ICAR 2025, DOI 10.1109/ICAR65334.2025.11338737. Represents N UAVs performing a coordinated forest/agricultural biomass-mapping survey, each covering one horizontal strip of the same target area with a boustrophedon (lawnmower) sweep, at their reported Grid Coverage cruise speed (1.33 m/s). This multi-UAV extension is our own construction and has not been validated against the authors raw trajectory logs -- treat as preliminary.

Files:
- ns3-scratch/fanet-compare.cc -- new mobility="GridCoverage" branch (RWP and Realistic branches unchanged)
- scripts/generate_gridcoverage_traces.py -- generates the per-node waypoint trace files
- results/lars-revision-2026/gridcoverage_results.csv -- raw ns-3 output, 3 protocols x 3 node counts x 10 seeds
- results/lars-revision-2026/mobility_matrix_summary.csv -- mean/std summary across all three mobility models (RWP, Realistic, GridCoverage) side by side

Headline finding (preliminary): at matched node density, GridCoverage mobility produces substantially lower average node degree than RWP or Realistic (e.g. at 20 nodes: 5.56 vs 11.57 vs 12.96), and this changes which routing protocol performs best -- OLSR wins under RWP, AODV takes over under Realistic and GridCoverage, and DSDV degrades most sharply under GridCoverage (PDR dropping to roughly 21-27%). Statistical significance and effect sizes for these differences are large across nearly all protocol/scale combinations (Welch t-test, Mann-Whitney U, Cohen d).
