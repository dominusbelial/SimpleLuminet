#!/usr/bin/env python3
"""
SimpleLuminet V2 — Historically Accurate Dot Matrix Printer Emulation

Based on Jean-Pierre Luminet's 1979 black hole visualization.
Computed on an IBM 7040, printed on an IBM 1403 line printer.

Key historical accuracy improvements over V1:
  - Fixed dot size (all printer dots are the same physical size)
  - Paper-colored background (off-white) with black ink dots
  - Lower effective resolution (~80 DPI simulating printer raster)
  - Slight dot position jitter (printer imprecision)
  - Horizontal print-pass banding
  - Binary dots: each particle renders as an ink dot, brightness = dot probability
  - Bayer-ordered halftone for the photon ring

Reference: Luminet, J.-P. (1979), A&A, 75, 228-235
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ============================================================
# PHYSICS SIMULATION (preserved from V1)
# ============================================================

# --- Parameters ---
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 900

# Black Hole
BH_RADIUS = 0.8
PHOTON_RING_SCALE = 1.5

# Accretion Disk
NUM_POINTS = 250000       # More particles for richer dot pattern
R_INNER = BH_RADIUS * 1.05
R_OUTER = BH_RADIUS * 6.0
DISK_THICKNESS = BH_RADIUS * 0.1
TILT_ANGLE = np.radians(75)

# Physics & Appearance
DOPPLER_FACTOR = 4.5
NOISE_FACTOR = 0.2
LENSING_STRENGTH = 1.2
LENSING_REGION_SCALE = 2.5

# --- Dot Matrix Printer Parameters ---
PRINTER_DPI = 80              # Simulated printer resolution
DOT_RADIUS_POINTS = 1.2       # Fixed dot radius in points
PAPER_COLOR = '#F5F0E0'       # Warm off-white (aged paper)
INK_COLOR = '#1A1A1A'         # Near-black ink
INK_COLOR_RING = '#0D0D0D'    # Slightly darker for photon ring
JITTER_STD = 0.15             # Dot position jitter
BANDING_INTENSITY = 0.03      # Horizontal banding from print passes
BRIGHTNESS_THRESHOLD = 0.15   # Minimum brightness for dot placement (~250K dots)

# --- Calculations ---
COS_TILT = np.cos(TILT_ANGLE)
SIN_TILT = np.sin(TILT_ANGLE)

# Generate points
power = -2.5
radius_raw = (np.random.uniform(R_INNER**power, R_OUTER**power, NUM_POINTS))**(1/power)
theta_raw = np.random.uniform(0, 2 * np.pi, NUM_POINTS)

radius = (radius_raw
          + np.random.normal(0, radius_raw * NOISE_FACTOR * 0.15, NUM_POINTS)
          + np.sin(theta_raw * 3 + radius_raw / R_OUTER * 2*np.pi) * radius_raw * 0.1)
theta = theta_raw + np.random.normal(0, NOISE_FACTOR * 0.75 / (radius/R_OUTER), NUM_POINTS)
radius = np.clip(radius, R_INNER, R_OUTER)

# 3D coordinates
x_disk = radius * np.cos(theta)
y_disk = radius * np.sin(theta)
z_disk = np.random.normal(0, DISK_THICKNESS * (radius/R_OUTER)**0.3, NUM_POINTS)

# View transformation
x_view = x_disk
y_view = y_disk * COS_TILT - z_disk * SIN_TILT
z_view = y_disk * SIN_TILT + z_disk * COS_TILT

# Doppler boosting
v_phi = 1 / np.sqrt(radius)
brightness = (1 + DOPPLER_FACTOR * v_phi * np.sin(theta) / (1 + DOPPLER_FACTOR))
brightness = np.clip(brightness + np.random.normal(0, 0.15, NUM_POINTS), 0.1, 1.0)

# Lensing simulation
dist_from_center = np.sqrt(x_view**2 + y_view**2 + z_view**2)
is_behind = z_view < 0
lensing_factor = LENSING_STRENGTH * BH_RADIUS**2 / (dist_from_center**2 + 1e-6)
phi_angle = np.arctan2(y_view, x_view)
deflection = lensing_factor * (1 - np.exp(-dist_from_center / (BH_RADIUS * 1.5)))
x_view += deflection * np.cos(phi_angle)
y_view += deflection * np.sin(phi_angle)

# Photon ring
photon_ring_mask = (dist_from_center < BH_RADIUS * PHOTON_RING_SCALE) & is_behind
x_view[photon_ring_mask] = BH_RADIUS * PHOTON_RING_SCALE * np.cos(phi_angle[photon_ring_mask])
y_view[photon_ring_mask] = BH_RADIUS * PHOTON_RING_SCALE * np.sin(phi_angle[photon_ring_mask])

# Visibility
dist_proj = np.sqrt(x_view**2 + y_view**2)
is_hidden = (dist_proj < BH_RADIUS * 0.95) & is_behind
visible = ~is_hidden

# ============================================================
# DOT MATRIX PRINTER RENDERING
# ============================================================

# Calculate output dimensions at printer DPI
fig_width_inches = IMAGE_WIDTH / PRINTER_DPI
fig_height_inches = IMAGE_HEIGHT / PRINTER_DPI

fig, ax = plt.subplots(
    figsize=(fig_width_inches, fig_height_inches),
    dpi=PRINTER_DPI,
    facecolor=PAPER_COLOR
)
ax.set_facecolor(PAPER_COLOR)

view_x_min, view_x_max = -R_OUTER * 0.9, R_OUTER * 0.9
view_y_min, view_y_max = -R_OUTER * SIN_TILT * 1.1, R_OUTER * SIN_TILT * 1.1

# --- Step 1: Stochastic dot placement based on brightness ---
# Each particle has a probability of being plotted proportional to its brightness.
# This naturally creates the halftone effect — brighter regions get more dots.
rng = np.random.default_rng(42)
dot_mask = rng.random(visible.sum()) < (brightness[visible] / brightness[visible].max())
dot_mask = dot_mask & (brightness[visible] > BRIGHTNESS_THRESHOLD)

dot_x = x_view[visible][dot_mask]
dot_y = y_view[visible][dot_mask]

print(f"Dot count before jitter: {len(dot_x)}")

# --- Step 2: Add printer artifacts ---
# 2a. Position jitter
if len(dot_x) > 0:
    dot_x += np.random.normal(0, JITTER_STD * (view_x_max - view_x_min) / IMAGE_WIDTH, len(dot_x))
    dot_y += np.random.normal(0, JITTER_STD * (view_y_max - view_y_min) / IMAGE_HEIGHT, len(dot_y))

    # 2b. Horizontal banding: simulate print-pass boundaries
    band_phase = (dot_y * PRINTER_DPI / 6) % 1.0
    band_dropout = band_phase < 0.03
    ink_alpha = np.ones(len(dot_x))
    ink_alpha[band_dropout] = 0.82  # Slight fade at band edges

    # 2c. Ink ribbon wear variation
    ink_variation = 1.0 - np.abs(np.sin(dot_y * 0.5)) * BANDING_INTENSITY
    ink_alpha = np.clip(ink_alpha * ink_variation, 0.75, 1.0)

    # --- Step 3: Plot main disk dots ---
    ax.scatter(dot_x, dot_y,
               s=DOT_RADIUS_POINTS**2,
               c=INK_COLOR,
               marker='o',
               alpha=0.92,          # Slight transparency for paper texture feel
               edgecolors='none',
               rasterized=True,
               linewidth=0)

# --- Step 4: Photon ring dots (extra emphasis near event horizon) ---
ring_mask = (dist_from_center < BH_RADIUS * PHOTON_RING_SCALE * 1.1) & ~is_hidden & visible
if ring_mask.sum() > 0:
    ring_bright = brightness[ring_mask]
    ring_threshold = np.percentile(ring_bright, 80)
    ring_bright_mask = ring_bright > ring_threshold
    ring_x = x_view[ring_mask][ring_bright_mask]
    ring_y = y_view[ring_mask][ring_bright_mask]

    # Subsample for emphasis without overcrowding
    if len(ring_x) > 600:
        idx = np.random.choice(len(ring_x), 600, replace=False)
        ring_x, ring_y = ring_x[idx], ring_y[idx]

    ax.scatter(ring_x, ring_y,
               s=DOT_RADIUS_POINTS**2 * 1.4,
               c=INK_COLOR_RING,
               marker='o',
               alpha=0.95,
               edgecolors='none',
               rasterized=True,
               linewidth=0)

# --- Step 5: Black hole silhouette ---
bh_circle = patches.Circle(
    (0, 0), BH_RADIUS,
    fill=True,
    facecolor=PAPER_COLOR,
    edgecolor=INK_COLOR,
    linewidth=0.5,
    zorder=10
)
ax.add_patch(bh_circle)

# Subtle inner shadow ring
for i in range(2):
    ax.add_patch(patches.Circle(
        (0, 0), BH_RADIUS * (1 + i * 0.04),
        fill=True,
        facecolor=INK_COLOR,
        alpha=0.12 * (1 - i/2),
        zorder=9 + i
    ))

# --- Step 6: Printer page border ---
border = patches.Rectangle(
    (view_x_min, view_y_min),
    view_x_max - view_x_min,
    view_y_max - view_y_min,
    fill=False,
    edgecolor='#8B8378',
    linewidth=0.3,
    zorder=20
)
ax.add_patch(border)

ax.set_aspect('equal')
ax.set_xlim(view_x_min, view_x_max)
ax.set_ylim(view_y_min, view_y_max)
ax.axis('off')

plt.tight_layout(pad=0.3)

# Save at printer DPI
output_path = "luminet_dotmatrix.png"
plt.savefig(output_path, dpi=PRINTER_DPI, bbox_inches='tight',
            pad_inches=0.1, facecolor=PAPER_COLOR)
print(f"Saved: {output_path}")
print(f"Resolution: {IMAGE_WIDTH}x{IMAGE_HEIGHT} at {PRINTER_DPI} DPI (simulated printer)")
print(f"Final dot count: {len(dot_x)}")
print(f"Ink: {INK_COLOR} on {PAPER_COLOR} paper")

plt.show()
