# Mobility, Routing and Computational Cost in UAV Network Co-Simulation (ns-3)

Reproducibility package for two papers by the same authors. Both use the same ns-3 scenario program, the same routing protocols (AODV, OLSR, DSDV) and the same two mobility sources (Random Waypoint, and trajectories recorded from a ROS 2 / Gazebo UAV simulation).

1. **LARS 2026** - Coupling UAV mobility patterns with routing protocol selection (5, 10 and 20 nodes).
2. **Computational cost study (2026 journal manuscript, in preparation)** - "Computational Cost of UAV Network Co-Simulation: Scalability, Topology Churn, and Routing Protocol Effects" (5 to 100 nodes, 300 runs).

## Repository layout

- `ns3-scratch/fanet-compare-jpdc.cc` - scenario used for the computational cost study (use this one for that paper)
- `ns3-scratch/fanet-compare.cc` - scenario used for the LARS 2026 paper (includes the preliminary GridCoverage branch)
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
cp /path/to/this/repo/ns3-scratch/fanet-compare-jpdc.cc scratch/fanet-compare.cc
cp -r /path/to/this/repo/waypoints/waypoints_independent .
CXX=/usr/bin/g++-11 ./ns3 configure --build-profile=default
./ns3 build
```

Note: for the cost study, `fanet-compare-jpdc.cc` is installed under the name `scratch/fanet-compare.cc`. It is byte-identical to the program that was run for the manuscript.

## Running one configuration

```
./ns3 run "fanet-compare --protocol=AODV --mobility=Realistic --nNodes=20 --RngRun=1"
```

`--protocol` is AODV, OLSR or DSDV (upper case). `--mobility` is `RWP` or `Realistic`. The program appends one line per run to `results.csv` (no header, no seed column). `scripts/instrumented_run_batch.sh` is the wrapper that tags each line with protocol, mobility, nodes and seed and measures wall-clock time, peak RSS and CPU with GNU `time`; see its header for usage.

## Scenario parameters

IEEE 802.11a, OfdmRate6Mbps; LogDistance propagation (exponent 3.0) plus a 17.5 m range limit; 32 s simulated time; 10 seeds per configuration; 3 protocols x 2 mobility models x 5 node counts (5, 10, 20, 50, 100) = 300 runs.

## Result files

- `results/jpdc2026_results_300runs.csv` - the 300 runs of the cost study. No header. Columns: protocol, mobility, nNodes, PDR (%), average delay (ms), tx packets, rx packets, link breaks, average hop count, average node degree, average link lifetime (s).
- `results/jpdc2026_timing_300runs.csv` - per-run cost measurements of the cost study. Header: protocol, mobility, nNodes, seed, wallClockSec, peakRssKB, linkBreaks, avgNodeDegree.
- `results/parallel_benchmark_full/` - run-level parallelism benchmark over the same 300 runs with P = 1 and P = 6 concurrent processes (`per_run_all.csv`: PID, start, end, duration, exit status, peak RSS per run; `batch_summary.csv`; `speedup_summary.csv`). `results/parallel_benchmark_pilot/` is a smaller pilot (60 runs, P = 1, 2, 4, 6).
- `results/results_n10.csv`, `results/scalability_summary.csv`, `results/lars-revision-2026/` - LARS 2026 data.

## Provenance of the timing numbers (please read)

Table 1 of the cost study (mean wall-clock time per configuration) is built from two sweeps of the same 300 configurations:

- all cells except Realistic mobility with 5 and 10 nodes come from `results/jpdc2026_timing_300runs.csv`;
- Realistic mobility with 5 and 10 nodes comes from an earlier instrumented sweep. In `jpdc2026_timing_300runs.csv` these 60 `wallClockSec` values come from a re-run that was affected by other load on the machine and do not match Table 1. `peakRssKB`, `linkBreaks` and `avgNodeDegree` are not affected.

The raw output of that earlier sweep is not distributed: its link-break counts for RWP differ from the final scenario, so it belongs to an earlier version of the program. As an independent check, the benchmark in `results/parallel_benchmark_full/` re-ran all 300 configurations sequentially (P = 1, 3938 s in total). Its per-configuration means agree with Table 1 within about 3% for 20 nodes and above, within about 7% at 10 nodes, and are 12-20% higher at 5 nodes, where runs last well under a second and process start-up dominates. The AODV/OLSR cost ratio at 100 nodes is 4.2 in both.

Parallel speed-up (six physical cores, each ns-3 process single-threaded): 3940 s at P = 1 to 726 s at P = 6, i.e. 5.43x speed-up and 90.4% parallel efficiency.

## Reproducing the figures

```
python3 scripts/make_figures.py --timing results/jpdc2026_timing_300runs.csv \
  --perrun results/parallel_benchmark_full/per_run_all.csv --out figs
```

This regenerates Figures 3 (cost vs. nodes, from the Table 1 values embedded in the script), 4 (peak memory) and 5 (cost vs. link breaks). Figure 1 comes from `scripts/figures/make_fig1.py`.

## Citation

See `CITATION.cff`. LARS 2026: M. S. Joshan, D. Bonilla Licea, and K. C. T. Vivaldini, "Coupling UAV Mobility Patterns with Routing Protocol Selection in FANETs: A Co-Simulation Study," in Proc. LARS 2026.

## License

MIT License (see LICENSE).

## LARS 2026 Revision -- GridCoverage Mobility Model (Preliminary)

Added 2026-09-24 in response to Daniel Bonilla Licea proposal to restructure the LARS revision as a mobility x network/communication-metrics matrix, with each mobility model tied to a concrete, named practical scenario rather than a realistic/non-realistic label.

Scope note: everything in this section is for the LARS 2026 revision only. It is NOT part of the cost-study dataset or claims -- the existing RWP and Realistic branches in ns3-scratch/fanet-compare.cc, and the results already in results/results_n10.csv and results/scalability_summary.csv, are unmodified.

Model: a coordinated multi-UAV extension of the single-UAV Grid Coverage algorithm from Duarte de Souza, Pereira, Pazelli and Vivaldini, "Evaluating Coverage Path Planning Strategies for UAVs with Real-Time Obstacle Avoidance in Forested Environments," IEEE ICAR 2025, DOI 10.1109/ICAR65334.2025.11338737. Represents N UAVs performing a coordinated forest/agricultural biomass-mapping survey, each covering one horizontal strip of the same target area with a boustrophedon (lawnmower) sweep, at their reported Grid Coverage cruise speed (1.33 m/s). This multi-UAV extension is our own construction and has not been validated against the authors raw trajectory logs -- treat as preliminary.

Files:
- ns3-scratch/fanet-compare.cc -- new mobility="GridCoverage" branch (RWP and Realistic branches unchanged)
- scripts/generate_gridcoverage_traces.py -- generates the per-node waypoint trace files
- results/lars-revision-2026/gridcoverage_results.csv -- raw ns-3 output, 3 protocols x 3 node counts x 10 seeds
- results/lars-revision-2026/mobility_matrix_summary.csv -- mean/std summary across all three mobility models (RWP, Realistic, GridCoverage) side by side

Headline finding (preliminary): at matched node density, GridCoverage mobility produces substantially lower average node degree than RWP or Realistic (e.g. at 20 nodes: 5.56 vs 11.57 vs 12.96), and this changes which routing protocol performs best -- OLSR wins under RWP, AODV takes over under Realistic and GridCoverage, and DSDV degrades most sharply under GridCoverage (PDR dropping to roughly 21-27%). Statistical significance and effect sizes for these differences are large across nearly all protocol/scale combinations (Welch t-test, Mann-Whitney U, Cohen d).
