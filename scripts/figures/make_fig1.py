import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

def draw_drone(ax, x, y, color, size=0.28, zorder=5):
    """Recognizable quadrotor icon: X-frame arms + rotor discs + body hub."""
    arm_len = size * 1.0
    rotor_r = size * 0.32
    body_r = size * 0.20
    for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        ex = x + dx * arm_len * 0.7071
        ey = y + dy * arm_len * 0.7071
        ax.plot([x, ex], [y, ey], color=color, linewidth=size * 5.5, zorder=zorder,
                solid_capstyle='round')
        ax.add_patch(Circle((ex, ey), rotor_r, facecolor='none',
                             edgecolor=color, linewidth=size * 4.5, zorder=zorder + 1))
    ax.add_patch(Circle((x, y), body_r, facecolor=color, edgecolor='none', zorder=zorder + 2))

def grid_jitter_positions(rows, cols, cell_w, cell_h, jitter_frac, seed, origin=(0.0, 0.0)):
    r = np.random.default_rng(seed)
    pts = []
    for i in range(rows):
        for j in range(cols):
            cx = origin[0] + j * cell_w + cell_w / 2
            cy = origin[1] + i * cell_h + cell_h / 2
            jx = r.uniform(-jitter_frac * cell_w / 2, jitter_frac * cell_w / 2)
            jy = r.uniform(-jitter_frac * cell_h / 2, jitter_frac * cell_h / 2)
            pts.append((cx + jx, cy + jy))
    return np.array(pts)

def edges_by_distance(pts, thresh):
    n = len(pts)
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if np.linalg.norm(pts[i] - pts[j]) < thresh:
                edges.append((i, j))
    return edges

N = 20
ICON_FOOTPRINT = 0.28 * 1.32

left_pts = grid_jitter_positions(rows=4, cols=5, cell_w=0.72, cell_h=0.72, jitter_frac=0.15, seed=3)
right_pts = grid_jitter_positions(rows=4, cols=5, cell_w=2.1, cell_h=1.7, jitter_frac=0.65, seed=11)
assert len(left_pts) == 20 and len(right_pts) == 20

best_thresh_left = None
for t in np.arange(0.6, 6.0, 0.05):
    e = edges_by_distance(left_pts, t)
    deg = 2 * len(e) / N
    if 12.5 <= deg <= 13.5:
        best_thresh_left = t
        break
if best_thresh_left is None:
    best_thresh_left = 1.6
left_edges = edges_by_distance(left_pts, best_thresh_left)

best_thresh_right = None
for t in np.arange(1.0, 2.4, 0.05):
    e = edges_by_distance(right_pts, t)
    deg = 2 * len(e) / N
    if 1.8 <= deg <= 2.2:
        best_thresh_right = t
        break
if best_thresh_right is None:
    best_thresh_right = 1.6
right_edges = edges_by_distance(right_pts, best_thresh_right)
right_deg_arr = np.zeros(N)
for i, j in right_edges:
    right_deg_arr[i] += 1
    right_deg_arr[j] += 1

GREEN = '#3B8C4A'
GREEN_LINE = '#4CAF63'
RED = '#D8503A'
RED_LINE = '#E17A68'
GRAY_BG = '#EDEDED'
GRAY_TXT = '#3A3A3A'

left_shift = np.array([-0.2, 1.2])
right_shift = np.array([7.2, -0.5])
Lp = left_pts + left_shift
Rp = right_pts + right_shift

ICON_PAD = ICON_FOOTPRINT + 0.15
lx_min, ly_min = Lp.min(axis=0) - ICON_PAD
lx_max, ly_max = Lp.max(axis=0) + ICON_PAD
rx_min, ry_min = Rp.min(axis=0) - ICON_PAD
rx_max, ry_max = Rp.max(axis=0) + ICON_PAD

TOP_MARGIN = 1.7
BOTTOM_MARGIN = 1.5
SIDE_MARGIN = 0.6

left_bg_x0 = lx_min - SIDE_MARGIN
left_bg_x1 = lx_max + SIDE_MARGIN
right_bg_x0 = rx_min - SIDE_MARGIN
right_bg_x1 = rx_max + SIDE_MARGIN
panel_y0 = min(ly_min, ry_min) - BOTTOM_MARGIN
panel_y1 = max(ly_max, ry_max) + TOP_MARGIN

fig_w = (right_bg_x1 - left_bg_x0) * 1.05
fig_h = (panel_y1 - panel_y0) * 0.62
fig, ax = plt.subplots(figsize=(fig_w, fig_h))
ax.set_xlim(left_bg_x0 - 0.3, right_bg_x1 + 0.3)
ax.set_ylim(panel_y0 - 0.3, panel_y1 + 0.3)
ax.axis('off')
ax.set_aspect('equal')

left_bg = FancyBboxPatch((left_bg_x0, panel_y0), left_bg_x1 - left_bg_x0, panel_y1 - panel_y0,
                          boxstyle="round,pad=0.02,rounding_size=0.35", facecolor=GRAY_BG, edgecolor='none', zorder=0)
right_bg = FancyBboxPatch((right_bg_x0, panel_y0), right_bg_x1 - right_bg_x0, panel_y1 - panel_y0,
                           boxstyle="round,pad=0.02,rounding_size=0.35", facecolor=GRAY_BG, edgecolor='none', zorder=0)
ax.add_patch(left_bg)
ax.add_patch(right_bg)
left_cx = (left_bg_x0 + left_bg_x1) / 2
right_cx = (right_bg_x0 + right_bg_x1) / 2

for i, j in left_edges:
    x1, y1 = Lp[i]; x2, y2 = Lp[j]
    ax.plot([x1, x2], [y1, y2], color=GREEN_LINE, linewidth=1.3, alpha=0.5, zorder=1)
for i, j in right_edges:
    x1, y1 = Rp[i]; x2, y2 = Rp[j]
    ax.plot([x1, x2], [y1, y2], color=RED_LINE, linewidth=1.6, alpha=0.8, zorder=1)

for (x, y) in Lp:
    draw_drone(ax, x, y, GREEN, size=0.28)
for (x, y) in Rp:
    draw_drone(ax, x, y, RED, size=0.28)

iso_idx = np.where(right_deg_arr == 0)[0]
if len(iso_idx) > 0:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    NODE_R = ICON_FOOTPRINT + 0.15

    def bbox_collides(text_obj):
        bb = text_obj.get_window_extent(renderer=renderer)
        (x0, y0), (x1, y1) = ax.transData.inverted().transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        x0 -= 0.08; x1 += 0.08; y0 -= 0.08; y1 += 0.08
        for (nx, ny) in Rp:
            cx = min(max(nx, x0), x1)
            cy = min(max(ny, y0), y1)
            if (nx - cx) ** 2 + (ny - cy) ** 2 < NODE_R ** 2:
                return True
        if x0 < right_bg_x0 + 0.15 or x1 > right_bg_x1 - 0.15:
            return True
        if y1 > panel_y1 - TOP_MARGIN + 0.1 or y0 < panel_y0 + BOTTOM_MARGIN - 0.1:
            return True
        return False

    label_txt = 'isolated \u2014 no relay path'
    placed = False
    for node_i in iso_idx:
        ix, iy = Rp[node_i]
        for ang_deg, dist in [(a, d) for d in (1.3, 1.7, 2.1, 2.6) for a in (200, 250, 160, 290, 340, 20, 110)]:
            ang = np.radians(ang_deg)
            tx = ix + dist * np.cos(ang)
            ty = iy + dist * np.sin(ang)
            t = ax.text(tx, ty, label_txt, fontsize=12, color=GRAY_TXT, ha='center', va='center', zorder=8)
            fig.canvas.draw()
            if not bbox_collides(t):
                ax.annotate('', xy=(ix, iy - 0.32), xytext=(tx, ty),
                            arrowprops=dict(arrowstyle='-', color='#8A8A8A', lw=1.1), zorder=7)
                placed = True
                break
            t.remove()
        if placed:
            break

ax.text(left_cx, panel_y1 - 0.55, 'Realistic Mobility (Gazebo)', fontsize=17, fontweight='bold', ha='center', va='top', color='#1A1A1A')
ax.text(left_cx, panel_y1 - 1.15, '20 UAVs', fontsize=13, ha='center', va='top', color='#1A1A1A')
ax.text(right_cx, panel_y1 - 0.55, 'Random Waypoint (RWP)', fontsize=17, fontweight='bold', ha='center', va='top', color='#1A1A1A')
ax.text(right_cx, panel_y1 - 1.15, '20 UAVs', fontsize=13, ha='center', va='top', color='#1A1A1A')

mid_cx = (left_bg_x1 + right_bg_x0) / 2
mid_w, mid_h = 2.7, 1.35
mid_box = FancyBboxPatch((mid_cx - mid_w / 2, -mid_h / 2), mid_w, mid_h,
                          boxstyle="round,pad=0.02,rounding_size=0.12", facecolor='#D9D9D9', edgecolor='#9A9A9A', linewidth=1.0, zorder=6)
ax.add_patch(mid_box)
ax.text(mid_cx, 0.0, 'Mobility Model\nDetermines\nNetwork Topology', fontsize=11, fontweight='bold', ha='center', va='center', color='#1A1A1A', zorder=7)

ax.text(left_cx, panel_y0 + 0.85, 'Mean Node Degree \u2248 13', fontsize=15, fontweight='bold', ha='center', va='bottom', color=GREEN)
ax.text(left_cx, panel_y0 + 0.35, 'Single-hop delivery \u2014 dense connectivity', fontsize=13, style='italic', ha='center', va='bottom', color=GREEN)
ax.text(right_cx, panel_y0 + 0.85, 'Mean Node Degree \u2248 2', fontsize=15, fontweight='bold', ha='center', va='bottom', color=RED)
ax.text(right_cx, panel_y0 + 0.35, 'Multi-hop routing \u2014 sparse connectivity', fontsize=13, style='italic', ha='center', va='bottom', color=RED)

plt.tight_layout()
plt.savefig('fanet_scenario1.pdf', bbox_inches='tight', pad_inches=0.05)
plt.savefig('fanet_scenario1.png', dpi=200, bbox_inches='tight', pad_inches=0.05)
print("Saved.")
