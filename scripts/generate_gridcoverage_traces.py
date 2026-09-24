import math, itertools, os

# ---------------------------------------------------------------------------
# "Grid-Coverage Mission Mobility" candidate model for the LARS/JPDC
# mobility x network-metrics matrix requested by Daniel (email 2026-09-24).
#
# Grounding: Duarte de Souza, Pereira, Pazelli, Vivaldini, "Evaluating
# Coverage Path Planning Strategies for UAVs with Real-Time Obstacle
# Avoidance in Forested Environments", IEEE ICAR 2025, DOI
# 10.1109/ICAR65334.2025.11338737.
#   - Grid Coverage (their best-performing strategy): 162.68 m traveled,
#     122 s execution, avg speed 1.33 m/s (Table II, grouped-waypoint case).
#   - Single UAV in their study; here we extend to N UAVs, one per
#     horizontal strip of a partitioned area, each independently running
#     the same Grid-Coverage sweep logic. This is OUR extension, not
#     something already in their paper -- flagged explicitly as such.
#
# Practical scenario this model represents (per Daniel's request to name
# what each mobility model means, not just label it "realistic"):
#   "N UAVs performing a coordinated forest/agricultural biomass-mapping
#    survey, each covering an assigned strip of the same target area
#    with a boustrophedon (lawnmower) Grid-Coverage path, at the
#    empirically reported Grid-Coverage cruise speed."
#
# Same area/density convention as the existing RWP and Realistic branches
# (area_side formula targeting avg degree ~ 3*ln(n)) so the new column is
# directly comparable -- this addresses the reviewers' "same node density"
# complaint.
# ---------------------------------------------------------------------------

GRID_COVERAGE_SPEED = 1.33   # m/s, Caroline et al. Table II (grouped waypoints)
ASSUMED_ALTITUDE = 15.0      # m, NOT reported in the paper -- our assumption, flag in writeup
RANGE_THRESHOLD = 17.5       # m, placeholder comm range consistent with prior RWP/Realistic proxy calibration
T_MAX = 200.0                # s, long enough for several full sweep periods at this speed/scale
DT = 2.0                     # s, sampling step for the degree time-series
TRACE_DT = 1.0                # s, sampling step for exported ns-3-ready trace files

def area_side(n):
    return math.sqrt(n * 962.11 / (3.0 * math.log(n)))

def gen_grid_coverage_positions(n, L, speed=GRID_COVERAGE_SPEED, alt=ASSUMED_ALTITUDE):
    """N UAVs, each assigned one horizontal strip of the LxL area,
    each independently executing a Grid-Coverage boustrophedon sweep
    at the real reported cruise speed."""
    strip_h = L / n
    funcs = {}
    period = 2.0 * L / speed
    for i in range(n):
        y = (i + 0.5) * strip_h
        phase = (i % 3) * (period / 3.0)
        def make_func(y=y, phase=phase):
            def f(t):
                tt = (t + phase) % period
                if tt <= L / speed:
                    x = speed * tt
                else:
                    x = L - speed * (tt - L / speed)
                return (x, y, alt)
            return f
        funcs[i] = make_func()
    return funcs

def compute_topology_stats(funcs, n, range_threshold=RANGE_THRESHOLD, t_max=T_MAX, dt=DT):
    degrees = []
    t = dt
    while t <= t_max:
        positions = [funcs[i](t) for i in range(n)]
        active_links = 0
        for i, j in itertools.combinations(range(n), 2):
            p1, p2 = positions[i], positions[j]
            d = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
            if d <= range_threshold:
                active_links += 1
        deg = (2.0 * active_links) / n if n > 0 else 0.0
        degrees.append(deg)
        t += dt
    avg_degree = sum(degrees) / len(degrees)
    return avg_degree, degrees

def export_ns3_trace(funcs, n, t_max, dt, outdir):
    """Write one 'time x y z' waypoint file per node, matching the format
    already consumed by fanet-compare.cc's Realistic-mobility branch, so
    this can be dropped in as a third mobility option for a real ns-3 run."""
    os.makedirs(outdir, exist_ok=True)
    for i in range(n):
        path = os.path.join(outdir, f"node_{i}.trace")
        with open(path, "w") as f:
            t = 0.0
            while t <= t_max:
                x, y, z = funcs[i](t)
                f.write(f"{t:.2f} {x:.3f} {y:.3f} {z:.3f}\n")
                t += dt

known_rwp = {5: 3.4625, 10: 7.05, 20: 11.56502}
known_real = {5: 3.175, 10: 7.1875, 20: 12.9625}

print(f"{'n':>4} {'L (m)':>8} {'GridCovDeg':>12} {'RWP_deg':>10} {'Realistic_deg':>14}")
for n in [5, 10, 20]:
    L = area_side(n)
    funcs = gen_grid_coverage_positions(n, L)
    avg_deg, series = compute_topology_stats(funcs, n)
    print(f"{n:>4} {L:>8.2f} {avg_deg:>12.4f} {known_rwp[n]:>10.4f} {known_real[n]:>14.4f}")
    export_ns3_trace(funcs, n, T_MAX, TRACE_DT, f"gridcoverage_traces/n{n}")
