# Coupling UAV Mobility Patterns with Routing Protocol Selection in FANETs

Reproducibility package for the LARS 2026 conference paper.

## Overview

This repository contains the simulation code, trajectory data, and analysis scripts used to evaluate how realistic UAV mobility (captured via ROS2/Gazebo) versus synthetic Random Waypoint (RWP) mobility affects the performance of three FANET routing protocols (AODV, OLSR, DSDV) across 5, 10, and 20 nodes.

## Structure

- ns3-scratch: main ns-3 simulation program (fanet-compare.cc)
- waypoints: 5 realistic UAV trajectories captured from Gazebo
- scripts: batch runners, analysis scripts, and figure generation code
- results: aggregated CSV results (5, 10, 20 nodes; 10 seeds each)

## Reproducing the Simulations

1. Install ns-3 (tested with ns-3-dev; requires GCC 11 with CXX_EXTENSIONS=ON).
2. Copy ns3-scratch/fanet-compare.cc into your ns-3 scratch directory.
3. Copy waypoints/waypoints_independent into your ns-3 working directory.
4. Run scripts/run_batch.sh and scripts/run_batch_n10.sh.
5. Run scripts/parse_flowmon.py and scripts/analyze.py to regenerate the summary CSVs.

## Build Note

This ns-3 version requires GCC 11 with CXX_EXTENSIONS=ON. If your toolchain raises uint128_t typedef errors under newer GCC versions, patch build-support/macros-and-definitions.cmake to set CMAKE_CXX_EXTENSIONS to ON.

## Experimental Setup

MAC/PHY: IEEE 802.11a, OfdmRate6Mbps
Propagation: LogDistance (alpha=3.0) plus Range (17.5 m)
Simulation time: 32 s
Seeds: 10 per configuration

## Citation

M. S. Joshan, D. Bonilla Licea, and K. C. T. Vivaldini, "Coupling UAV Mobility Patterns with Routing Protocol Selection in FANETs: A Co-Simulation Study," in Proc. LARS 2026.

## License

MIT License (see LICENSE file).


## LARS 2026 Revision -- GridCoverage Mobility Model (Preliminary)

Added 2026-09-24 in response to Daniel Bonilla Licea proposal to restructure the LARS revision as a mobility x network/communication-metrics matrix, with each mobility model tied to a concrete, named practical scenario rather than a realistic/non-realistic label.

Scope note: everything in this section is for the LARS 2026 revision only. It is NOT part of the JPDC dataset or claims -- the existing RWP and Realistic branches in ns3-scratch/fanet-compare.cc, and the results already in results/results_n10.csv and results/scalability_summary.csv, are unmodified.

Model: a coordinated multi-UAV extension of the single-UAV Grid Coverage algorithm from Duarte de Souza, Pereira, Pazelli and Vivaldini, "Evaluating Coverage Path Planning Strategies for UAVs with Real-Time Obstacle Avoidance in Forested Environments," IEEE ICAR 2025, DOI 10.1109/ICAR65334.2025.11338737. Represents N UAVs performing a coordinated forest/agricultural biomass-mapping survey, each covering one horizontal strip of the same target area with a boustrophedon (lawnmower) sweep, at their reported Grid Coverage cruise speed (1.33 m/s). This multi-UAV extension is our own construction and has not been validated against the authors raw trajectory logs -- treat as preliminary.

Files:
- ns3-scratch/fanet-compare.cc -- new mobility="GridCoverage" branch (RWP and Realistic branches unchanged)
- scripts/generate_gridcoverage_traces.py -- generates the per-node waypoint trace files
- results/lars-revision-2026/gridcoverage_results.csv -- raw ns-3 output, 3 protocols x 3 node counts x 10 seeds
- results/lars-revision-2026/mobility_matrix_summary.csv -- mean/std summary across all three mobility models (RWP, Realistic, GridCoverage) side by side

Headline finding (preliminary): at matched node density, GridCoverage mobility produces substantially lower average node degree than RWP or Realistic (e.g. at 20 nodes: 5.56 vs 11.57 vs 12.96), and this changes which routing protocol performs best -- OLSR wins under RWP, AODV takes over under Realistic and GridCoverage, and DSDV degrades most sharply under GridCoverage (PDR dropping to roughly 21-27%). Statistical significance and effect sizes for these differences are large across nearly all protocol/scale combinations (Welch t-test, Mann-Whitney U, Cohen d).
