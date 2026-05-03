#!/usr/bin/env python3
"""
SimpleLuminet V2.1 — Dot Matrix Printer Emulation
Jean-Pierre Luminet's 1979 black hole (A&A 75, 228-235).

Key features:
  - Enhanced gravitational lensing: far-side light bent upward around photon sphere
  - Bayer 8x8 ordered dithering for authentic halftone
  - Moderate Doppler asymmetry (top ~3-5x more dots than bottom)
  - Printer artifacts: pass-banding, vertical misalignment, pin jitter
  - Off-white paper, near-black ink, fixed dot size
"""
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as patches
from scipy.ndimage import gaussian_filter
from datetime import datetime

# ============================================================
# PHYSICS
# ============================================================
BH = 0.8; NUM = 300000; TILT = np.radians(75)
CT, ST = np.cos(TILT), np.sin(TILT); RI, RO = BH*1.05, BH*6.0

power = -2.5
rr = (np.random.uniform(RI**power, RO**power, NUM))**(1/power)
tr = np.random.uniform(0, 2*np.pi, NUM)
r = rr + np.random.normal(0, rr*0.03, NUM)
t = tr + np.random.normal(0, 0.15, NUM); r = np.clip(r, RI, RO)

xd = r*np.cos(t); yd = r*np.sin(t); zd = np.random.normal(0, BH*0.1, NUM)
xv = xd; yv = yd*CT - zd*ST; zv = yd*ST + zd*CT

v = 1/np.sqrt(r)
br = (1 + 8.0*v*np.sin(t)/9.0)
br = np.clip(br + np.random.normal(0, 0.12, NUM), 0.03, 1.0)

# ============================================================
# GRAVITATIONAL LENSING
# ============================================================
d3 = np.sqrt(xv**2 + yv**2 + zv**2); ib = zv < 0
impact = np.sqrt(xv**2 + yv**2)

# Deflection strongest near photon sphere (r ~ 1.5*BH)
# Compute only for behind-BH particles
photon_sphere = 1.5*BH
deflection_behind = 1.8*BH**1.5 / (np.abs(impact[ib] - photon_sphere) + 0.2*BH)
deflection_behind = np.clip(deflection_behind, 0, BH*2.0)

# Upward deflection (positive y) for behind-BH particles → halo arc
angle_behind = np.arctan2(yv[ib], np.abs(xv[ib]) + 0.01)
yv[ib] += deflection_behind * np.cos(angle_behind)

# Slight radial push for edge warp
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

# Moderate spatial Doppler boost
yn = yv[vis]/(RO*ST*1.1)
boost = 1.0 + 10*np.clip(yn, 0, 1)  # Reduced from 30x to 10x
bc = np.clip(br[vis]*boost, 0, 1.0)

# ============================================================
# GRID + BLUR + GAMMA (unified normalization)
# ============================================================
DPI, GC, GR = 80, 1200, 900
vxm, vxM = -RO*0.9, RO*0.9; vym, vyM = -RO*ST*1.1, RO*ST*1.1
ci = ((xv[vis]-vxm)/(vxM-vxm)*(GC-1)).astype(int)
ri = ((yv[vis]-vym)/(vyM-vym)*(GR-1)).astype(int)
ok = (ci>=0)&(ci<GC)&(ri>=0)&(ri<GR)

dg = np.zeros((GR, GC))
np.add.at(dg, (ri[ok], ci[ok]), bc[ok])
dg = gaussian_filter(dg, sigma=1.5)
dg = np.clip(dg / dg.max(), 0, 1)
dg = dg ** 0.55

# Check natural asymmetry
mid = GR//2
print(f"Density: top(450-899) sum={dg[mid:].sum():.0f} bot(0-449) sum={dg[:mid].sum():.0f} ratio={dg[mid:].sum()/max(dg[:mid].sum(),1):.2f}")

# ============================================================
# BAYER DITHERING (single bias)
# ============================================================
def bayer(n):
    if n==1: return np.array([[0]], dtype=float)
    m = bayer(n//2); return np.block([[4*m,4*m+2],[4*m+3,4*m+1]])/(n*n)

bt = np.tile(bayer(8), (GR//8+1, GC//8+1))[:GR, :GC]
BIAS = -0.008  # Slight negative for more dots (~80-100K target)
dithered = (dg > (bt + BIAS)).astype(float)
dr, dc = np.where(dithered > 0.5)

dx = vxm + (dc/(GC-1))*(vxM-vxm)
dy = vym + (dr/(GR-1))*(vyM-vym)
total = len(dx)

td = (dy > 0.3).sum(); bd = (dy < -0.3).sum()
print(f"Dots: {total}  Top(y>0.3): {td}  Bot(y<-0.3): {bd}  ratio: {td/max(bd,1):.2f}")

# ============================================================
# PRINTER ARTIFACTS
# ============================================================
PAPER, INK = '#F5F0E0', '#1A1A1A'; JR, DR = 0.03, 1.2

if total > 0:
    dx += np.random.normal(0, JR*(vxM-vxm)/GC, total)
    dy += np.random.normal(0, JR*(vyM-vym)/GR, total)
    bp = (dr%6).astype(float)/6; ed = (bp<0.15)|(bp>0.85)
    al = np.ones(total); al[ed] = 0.82
    bi = dr//6
    sh = {int(b): np.random.normal(0, 0.08) for b in np.unique(bi)}
    dx += np.array([sh[int(b)] for b in bi])

# ============================================================
# RENDER
# ============================================================
fig = plt.figure(figsize=(GC/DPI, GR/DPI), dpi=DPI,
                facecolor=PAPER, edgecolor=PAPER)
ax = fig.add_axes([0,0,1,1]); ax.set_facecolor(PAPER)
ax.scatter(dx, dy, s=DR**2, c=INK, marker='o', alpha=al,
           edgecolors='none', rasterized=True, linewidth=0)
ax.add_patch(patches.Circle((0,0), BH, fill=True,
           facecolor=PAPER, edgecolor=INK, linewidth=0.4, zorder=10))
ax.set_aspect('equal')
ax.set_xlim(vxm, vxM); ax.set_ylim(vym, vyM); ax.axis('off')

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
out = f"luminet_v2_1_{ts}.png"
fig.savefig(out, dpi=DPI, facecolor=PAPER, edgecolor=PAPER,
            bbox_inches=None, pad_inches=0)
# Also save a stable copy for README
fig.savefig("luminet_v2_1_final.png", dpi=DPI, facecolor=PAPER, edgecolor=PAPER,
            bbox_inches=None, pad_inches=0)
plt.close(fig)
print(f"Saved: {out}")
print(f"Also saved: luminet_v2_1_final.png")
print(f"Features: Bayer dithering, lensing, Doppler, printer banding")
