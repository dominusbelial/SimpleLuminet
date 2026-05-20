#!/usr/bin/env python3
"""
SimpleLuminet V3 — Dot Matrix Printer Emulation (Vision-Model Readable)
Jean-Pierre Luminet's 1979 black hole (A&A 75, 228-235).

Key fixes over V2.1:
  - DARK black hole shadow (ink-colored, not paper-colored) — the #1 fix
  - Wider 2:1 aspect ratio matching the original 700×346
  - Tighter crop around the black hole
  - Higher dot density in photon ring via lower blur + sharper dithering
  - More dramatic Doppler asymmetry
  - Clearer lensing halo
  - Keeps Bayer 8×8 dithering and printer artifacts
"""
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as patches
from scipy.ndimage import gaussian_filter
from datetime import datetime

# ============================================================
# PHYSICS (same core model as V2.1)
# ============================================================
BH = 0.8; NUM = 400000; TILT = np.radians(75)
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
# GRAVITATIONAL LENSING (V2.1 model — kept as-is, it's good)
# ============================================================
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

# Enhanced spatial Doppler boost (more dramatic asymmetry)
yn = yv[vis]/(RO*ST*1.1)
boost = 1.0 + 15*np.clip(yn, 0, 1)  # Bumped from 10x to 15x for clearer asymmetry
bc = np.clip(br[vis]*boost, 0, 1.0)

# ============================================================
# GRID — wider aspect ratio (2:1 like original 700×346)
# ============================================================
DPI, GC, GR = 80, 1400, 700  # 2:1 ratio, matching original proportions
vxm, vxM = -RO*0.85, RO*0.85
vym, vyM = -RO*ST*0.95, RO*ST*1.05  # Tighter vertical crop

ci = ((xv[vis]-vxm)/(vxM-vxm)*(GC-1)).astype(int)
ri = ((yv[vis]-vym)/(vyM-vym)*(GR-1)).astype(int)
ok = (ci>=0)&(ci<GC)&(ri>=0)&(ri<GR)

dg = np.zeros((GR, GC))
np.add.at(dg, (ri[ok], ci[ok]), bc[ok])

# Sharper blur for clearer photon ring + less washout
dg = gaussian_filter(dg, sigma=1.2)  # Reduced from 1.5
dg = np.clip(dg / dg.max(), 0, 1)

# Half-normalize: keep bottom dim, top bright — V2.1 does unified norm
# but we want asymmetry to survive
mid = GR//2
top = dg[mid:, :]
bot = dg[:mid, :]
if top.max() > 0:
    top = np.clip(top / top.max(), 0, 1)
if bot.max() > 0:
    bot = np.clip(bot / bot.max(), 0, 1)

# Recombine after half-normalization
dg_half = np.zeros_like(dg)
dg_half[mid:, :] = top
dg_half[:mid, :] = bot

# Dim the bottom half to create clear Doppler asymmetry
# (top = approaching = brighter, bottom = receding = dimmer)
dg_half[:mid, :] *= 0.55  # Bottom half 55% as bright

# Gamma BEFORE half-dim (skill pitfall #10)
dg_half = dg_half ** 0.55

print(f"Density: top sum={dg_half[mid:].sum():.0f} bot sum={dg_half[:mid].sum():.0f} ratio={dg_half[mid:].sum()/max(dg_half[:mid].sum(),1):.2f}")

# ============================================================
# BAYER DITHERING
# ============================================================
def bayer(n):
    if n==1: return np.array([[0]], dtype=float)
    m = bayer(n//2); return np.block([[4*m,4*m+2],[4*m+3,4*m+1]])/(n*n)

bt = np.tile(bayer(8), (GR//8+1, GC//8+1))[:GR, :GC]
BIAS = -0.015  # More negative = more dots for clearer structure
dithered = (dg_half > (bt + BIAS)).astype(float)
dr, dc = np.where(dithered > 0.5)

dx = vxm + (dc/(GC-1))*(vxM-vxm)
dy = vym + (dr/(GR-1))*(vyM-vym)
total = len(dx)

td = (dy > 0.3).sum(); bd = (dy < -0.3).sum()
print(f"Dots: {total}  Top(y>0.3): {td}  Bot(y<-0.3): {bd}  ratio: {td/max(bd,1):.2f}")

# ============================================================
# PRINTER ARTIFACTS (kept from V2.1)
# ============================================================
PAPER = '#F5F0E0'
INK = '#1A1A1A'
BH_SHADOW = '#0D0D0D'  # DARK — THIS IS THE KEY FIX
JR, DR = 0.03, 1.2

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

# THE FIX: Dark black hole shadow instead of paper-colored
ax.add_patch(patches.Circle((0,0), BH, fill=True,
           facecolor=BH_SHADOW, edgecolor=INK, linewidth=0.5, zorder=10))
ax.set_aspect('equal')
ax.set_xlim(vxm, vxM); ax.set_ylim(vym, vyM); ax.axis('off')

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
out = f"luminet_v3_{ts}.png"
fig.savefig(out, dpi=DPI, facecolor=PAPER, edgecolor=PAPER,
            bbox_inches=None, pad_inches=0)
fig.savefig("luminet_v3_final.png", dpi=DPI, facecolor=PAPER, edgecolor=PAPER,
            bbox_inches=None, pad_inches=0)
plt.close(fig)
print(f"Saved: {out}")
print(f"Also saved: luminet_v3_final.png")
print(f"Features: DARK shadow, 2:1 ratio, half-norm Doppler, sharper blur, Bayer dither")
