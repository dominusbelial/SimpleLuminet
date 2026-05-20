#!/usr/bin/env python3
"""
SimpleLuminet V3.5 — Dot Matrix (V3.1 core + horizontal + small dots)
Core approach from V3.1 (best dot asymmetry at 1.62:1) with:
  - 90° rotation for Luminet left/right orientation
  - DR 0.8 (smaller dots, was 1.2)
  - NUM 500K (was 300K)
  - sigma 1.2, gamma 0.55, half-norm with 0.55 dim
"""
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as patches
from scipy.ndimage import gaussian_filter
from datetime import datetime
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

BH = 0.8; NUM = 500000; TILT = np.radians(75)
CT, ST = np.cos(TILT), np.sin(TILT); RI, RO = BH*1.05, BH*6.0

power = -2.5
rr = (np.random.uniform(RI**power, RO**power, NUM))**(1/power)
tr = np.random.uniform(0, 2*np.pi, NUM)
r = rr + np.random.normal(0, rr*0.03, NUM)
t = tr + np.random.normal(0, 0.15, NUM); r = np.clip(r, RI, RO)

xd = r*np.cos(t); yd = r*np.sin(t); zd = np.random.normal(0, BH*0.1, NUM)
v = 1/np.sqrt(r)
br = (1 + 8.0*v*np.sin(t)/9.0)
br = np.clip(br + np.random.normal(0, 0.12, NUM), 0.03, 1.0)

# View transformation + 90° rotation
xv1 = xd; yv1 = yd*CT - zd*ST; zv1 = yd*ST + zd*CT
xv = -yv1; yv = xv1; zv = zv1  # 90°: bright side on LEFT

# Lensing (same as V3.1)
d3 = np.sqrt(xv**2 + yv**2 + zv**2); ib = zv < 0
impact = np.sqrt(xv**2 + yv**2)

photon_sphere = 1.5*BH
deflection_behind = 1.8*BH**1.5 / (np.abs(impact[ib] - photon_sphere) + 0.2*BH)
deflection_behind = np.clip(deflection_behind, 0, BH*2.0)

angle_behind = np.arctan2(yv[ib], np.abs(xv[ib]) + 0.01)
yv[ib] += deflection_behind * np.cos(angle_behind)

rp_behind = np.sqrt(xv[ib]**2 + yv[ib]**2) + 0.01
xv[ib] += deflection_behind*0.3 * (xv[ib]/rp_behind)
yv[ib] += deflection_behind*0.3 * (yv[ib]/rp_behind)

# Photon ring
ring = (impact < BH*1.5) & ib
pa = np.arctan2(yv, xv)
xv[ring] = BH*1.5*np.cos(pa[ring])
yv[ring] = BH*1.5*np.sin(pa[ring])

# Visibility
d3 = np.sqrt(xv**2 + yv**2 + zv**2)
dp = np.sqrt(xv**2 + yv**2); ib = zv < 0
vis = ~((dp < BH*0.95) & ib)

# Spatial Doppler boost (V3.1 approach: xv < 0 = left = approaching = brighter)
xn = xv[vis]/(RO*0.9)
boost = 1.0 + 10*np.clip(-xn, 0, 1)  # -xn > 0 when xv < 0 (left)
bc = np.clip(br[vis]*boost, 0, 1.0)

# Grid
DPI, GC, GR = 80, 1400, 700
vxm, vxM = -RO*0.85, RO*0.85
vym, vyM = -RO*ST*0.95, RO*ST*1.05

ci = ((xv[vis]-vxm)/(vxM-vxm)*(GC-1)).astype(int)
ri = ((yv[vis]-vym)/(vyM-vym)*(GR-1)).astype(int)
ok = (ci>=0)&(ci<GC)&(ri>=0)&(ri<GR)

dg = np.zeros((GR, GC))
np.add.at(dg, (ri[ok], ci[ok]), bc[ok])
dg = gaussian_filter(dg, sigma=1.2)

# Half-normalize: left (approaching) vs right (receding)
midc = GC//2
left = dg[:, :midc]; right = dg[:, midc:]
if left.max() > 0: left = np.clip(left / left.max(), 0, 1)
if right.max() > 0: right = np.clip(right / right.max(), 0, 1)
dg_half = np.zeros_like(dg)
dg_half[:, :midc] = left
dg_half[:, midc:] = right

# Dim receding (right) side
dg_half[:, midc:] *= 0.55

# Gamma
dg_half = dg_half ** 0.55

left_sum = dg_half[:, :midc].sum()
right_sum = dg_half[:, midc:].sum()
print(f"Density: left={left_sum:.0f} right={right_sum:.0f} ratio={left_sum/max(right_sum,1):.2f}")

# Bayer dithering
def bayer(n):
    if n==1: return np.array([[0]], dtype=float)
    m = bayer(n//2); return np.block([[4*m,4*m+2],[4*m+3,4*m+1]])/(n*n)

bt = np.tile(bayer(8), (GR//8+1, GC//8+1))[:GR, :GC]
BIAS = -0.020
dithered = (dg_half > (bt + BIAS)).astype(float)
dr, dc = np.where(dithered > 0.5)
dx = vxm + (dc/(GC-1))*(vxM-vxm)
dy = vym + (dr/(GR-1))*(vyM-vym)
total = len(dx)

ld = (dx < -0.2).sum(); rd = (dx > 0.2).sum()
print(f"Dots: {total}  Left: {ld}  Right: {rd}  ratio: {ld/max(rd,1):.2f}")

# Printer artifacts
PAPER = '#F5F0E0'; INK = '#1A1A1A'; BH_SHADOW = '#0D0D0D'
JR = 0.03; DOT_R = 0.8  # Smaller dots

if total > 0:
    dx += np.random.normal(0, JR*(vxM-vxm)/GC, total)
    dy += np.random.normal(0, JR*(vyM-vym)/GR, total)
    bp = (dr%6).astype(float)/6; ed = (bp<0.15)|(bp>0.85)
    al = np.ones(total); al[ed] = 0.82

# Render
fig = plt.figure(figsize=(GC/DPI, GR/DPI), dpi=DPI,
                facecolor=PAPER, edgecolor=PAPER)
ax = fig.add_axes([0,0,1,1]); ax.set_facecolor(PAPER)
ax.scatter(dx, dy, s=DOT_R**2, c=INK, marker='o', alpha=al,
           edgecolors='none', rasterized=True, linewidth=0)
ax.add_patch(patches.Circle((0,0), BH, fill=True,
           facecolor=BH_SHADOW, edgecolor=INK, linewidth=0.5, zorder=10))
ax.set_aspect('equal')
ax.set_xlim(vxm, vxM); ax.set_ylim(vym, vyM); ax.axis('off')

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
out = f"luminet_v3_5_{ts}.png"
fig.savefig(out, dpi=DPI, facecolor=PAPER, edgecolor=PAPER,
            bbox_inches=None, pad_inches=0)
fig.savefig("luminet_v3_5_final.png", dpi=DPI, facecolor=PAPER, edgecolor=PAPER,
            bbox_inches=None, pad_inches=0)
plt.close(fig)
print(f"Saved: {out} | luminet_v3_5_final.png")
