import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- Parameters ---
IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 900
DPI = 300
BG_COLOR = 'black'
POINT_COLOR = '#FFFFF0'  # Warm white for vintage feel

# Black Hole
BH_RADIUS = 0.8
PHOTON_RING_SCALE = 1.5  # Photon ring radius multiplier

# Accretion Disk
NUM_POINTS = 50000
R_INNER = BH_RADIUS * 1.05  # Closer to event horizon
R_OUTER = BH_RADIUS * 6.0
DISK_THICKNESS = BH_RADIUS * 0.1  # Thinner disk
TILT_ANGLE = np.radians(75)

# Physics & Appearance
DOPPLER_FACTOR = 4.5      # Stronger Doppler contrast
POINT_SIZE_BASE = 0.5     # Keep original size
POINT_SIZE_VAR = 0.5      # Less size variation
NOISE_FACTOR = 0.2        # More turbulence

# Lensing Simulation
LENSING_STRENGTH = 1.2    # Stronger lensing effect
LENSING_REGION_SCALE = 2.5 # Wider lensing influence

# --- Calculations ---
COS_TILT = np.cos(TILT_ANGLE)
SIN_TILT = np.sin(TILT_ANGLE)

# Generate points with steeper density gradient
power = -2.5  # More particles near center
radius_raw = (np.random.uniform(R_INNER**power, R_OUTER**power, NUM_POINTS))**(1/power)

theta_raw = np.random.uniform(0, 2 * np.pi, NUM_POINTS)

# Enhanced spiral structure
radius = radius_raw + np.random.normal(0, radius_raw * NOISE_FACTOR * 0.15, NUM_POINTS) \
                  + np.sin(theta_raw * 3 + radius_raw / R_OUTER * 2*np.pi) * radius_raw * 0.1
theta = theta_raw + np.random.normal(0, NOISE_FACTOR * 0.75 / (radius/R_OUTER), NUM_POINTS)

radius = np.clip(radius, R_INNER, R_OUTER)

# 3D coordinates with vertical stratification
x_disk = radius * np.cos(theta)
y_disk = radius * np.sin(theta)
z_disk = np.random.normal(0, DISK_THICKNESS * (radius/R_OUTER)**0.3, NUM_POINTS)

# View transformation
x_view = x_disk
y_view = y_disk * COS_TILT - z_disk * SIN_TILT
z_view = y_disk * SIN_TILT + z_disk * COS_TILT

# Doppler boosting with velocity profile
v_phi = 1/np.sqrt(radius)  # Keplerian velocity
brightness = (1 + DOPPLER_FACTOR * v_phi * np.sin(theta) / (1 + DOPPLER_FACTOR))
brightness = np.clip(brightness + np.random.normal(0, 0.15, NUM_POINTS), 0.1, 1.0)

point_sizes = POINT_SIZE_BASE + brightness * POINT_SIZE_VAR  # Keep sizes small

# Enhanced lensing simulation
dist_from_center = np.sqrt(x_view**2 + y_view**2 + z_view**2)
is_behind = z_view < 0
lensing_factor = LENSING_STRENGTH * BH_RADIUS**2 / (dist_from_center**2 + 1e-6)

# Apply angular deflection
phi = np.arctan2(y_view, x_view)
deflection = lensing_factor * (1 - np.exp(-dist_from_center/(BH_RADIUS*1.5)))
x_view += deflection * np.cos(phi)
y_view += deflection * np.sin(phi)

# Photon ring simulation
photon_ring_mask = (dist_from_center < BH_RADIUS*PHOTON_RING_SCALE) & is_behind
x_view[photon_ring_mask] = BH_RADIUS * PHOTON_RING_SCALE * np.cos(phi[photon_ring_mask])
y_view[photon_ring_mask] = BH_RADIUS * PHOTON_RING_SCALE * np.sin(phi[photon_ring_mask])

# Visibility filtering
dist_proj = np.sqrt(x_view**2 + y_view**2)
is_hidden = (dist_proj < BH_RADIUS*0.95) & is_behind
visible_mask = ~is_hidden

# --- Plotting ---
fig, ax = plt.subplots(figsize=(IMAGE_WIDTH/DPI, IMAGE_HEIGHT/DPI), dpi=DPI)
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(BG_COLOR)

# Accretion disk with gamma correction for better contrast
gamma = 0.6
point_alpha = np.clip(brightness[visible_mask]**gamma, 0.05, 0.95)

ax.scatter(x_view[visible_mask], y_view[visible_mask], 
           s=point_sizes[visible_mask], 
           c=POINT_COLOR, 
           marker='.', 
           alpha=point_alpha, 
           edgecolors='none',
           rasterized=True)

# Black hole silhouette with sharp edge
bh_circle = patches.Circle((0, 0), BH_RADIUS, fill=True, color=BG_COLOR, zorder=10)
ax.add_patch(bh_circle)

# Add subtle photon ring glow
for i in range(3):
    ax.add_patch(patches.Circle((0,0), BH_RADIUS*(1 + i*0.07), 
                fill=True, 
                color=BG_COLOR, 
                alpha=0.7*(1-i/3), 
                zorder=9+i))

ax.set_aspect('equal')
ax.set_xlim(-R_OUTER*0.9, R_OUTER*0.9)
ax.set_ylim(-R_OUTER*SIN_TILT*1.1, R_OUTER*SIN_TILT*1.1)
ax.axis('off')

plt.tight_layout(pad=0)
plt.savefig("luminet_style_blackhole.png", dpi=DPI, bbox_inches='tight', pad_inches=0)
plt.show()