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
