"""Terrain derivatives: slope, hydrology, wetness, vegetation structure."""
from __future__ import annotations

import heapq

import geopandas as gpd
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString
from shapely.ops import linemerge

from .grid import Grid
from .uas import canopy_cover

D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def slope_degrees(dtm, res, sigma_m=2.0):
    """Central-difference slope on a lightly smoothed DTM (vehicle-scale baseline, not micro-relief)."""
    z = ndi.gaussian_filter(dtm.astype("float64"), sigma_m / res) if sigma_m > 0 else dtm
    gy, gx = np.gradient(z, res)
    return np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")


def priority_flood_fill(z, eps=1e-4):
    """Barnes et al. (2014) priority-flood with epsilon: removes all pits so every cell drains."""
    H, W = z.shape
    filled = z.astype("float64").copy()
    closed = np.zeros((H, W), bool)
    heap = []
    for r in range(H):
        for c in (0, W - 1):
            heap.append((filled[r, c], r, c)); closed[r, c] = True
    for c in range(1, W - 1):
        for r in (0, H - 1):
            heap.append((filled[r, c], r, c)); closed[r, c] = True
    heapq.heapify(heap)
    push, pop = heapq.heappush, heapq.heappop
    while heap:
        zc, r, c = pop(heap)
        for dr, dc in D8:
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and not closed[rr, cc]:
                closed[rr, cc] = True
                if filled[rr, cc] <= zc:
                    filled[rr, cc] = zc + eps
                push(heap, (filled[rr, cc], rr, cc))
    return filled


def d8_accumulation(filled, res):
    """D8 flow direction (receiver index) and accumulation (cells)."""
    H, W = filled.shape
    pad = np.pad(filled, 1, constant_values=np.inf)
    best = np.zeros((H, W)); rec = np.full((H, W), -1, dtype=np.int64)
    idx = np.arange(H * W).reshape(H, W)
    for dr, dc in D8:
        nb = pad[1 + dr:H + 1 + dr, 1 + dc:W + 1 + dc]
        drop = (filled - nb) / (res * np.hypot(dr, dc))
        better = drop > best
        best = np.where(better, drop, best)
        tgt = np.clip(idx + dr * W + dc, 0, H * W - 1)
        rec = np.where(better, tgt, rec)
    order = np.argsort(-filled, axis=None)
    acc = np.ones(H * W)
    recf = rec.ravel()
    for i in order:
        j = recf[i]
        if j >= 0:
            acc[j] += acc[i]
    return rec, acc.reshape(H, W)


def hydrology(dtm, grid: Grid, cell=2.0, stream_threshold_m2=15000.0):
    """Hydrology on a 2 m resample for speed. Returns TWI, accumulation, drainage lines."""
    f = int(round(cell / grid.res))
    Hc, Wc = grid.height // f, grid.width // f
    zc = dtm[:Hc * f, :Wc * f].reshape(Hc, f, Wc, f).mean(axis=(1, 3))
    filled = priority_flood_fill(zc)
    rec, acc = d8_accumulation(filled, cell)
    slope = np.radians(slope_degrees(zc, cell, sigma_m=0))
    sca = acc * cell                       # specific catchment area (m2 per m contour)
    twi = np.log(sca / np.tan(np.maximum(slope, np.radians(0.5))))
    up = lambda a: np.kron(a, np.ones((f, f)))[:grid.height, :grid.width]
    twi_full = ndi.gaussian_filter(up(twi), 1.0).astype("float32")
    acc_full = up(acc * cell * cell).astype("float32")

    streams = acc * cell * cell >= stream_threshold_m2
    segs = []
    recf = rec.ravel()
    for i in np.flatnonzero(streams.ravel()):
        j = recf[i]
        if j < 0:
            continue
        r0, c0 = divmod(i, Wc); r1, c1 = divmod(j, Wc)
        x0, y0 = grid.rc_to_xy(r0 * f + (f - 1) / 2, c0 * f + (f - 1) / 2)
        x1, y1 = grid.rc_to_xy(r1 * f + (f - 1) / 2, c1 * f + (f - 1) / 2)
        segs.append(LineString([(float(x0), float(y0)), (float(x1), float(y1))]))
    merged = linemerge(segs) if segs else None
    geoms = list(merged.geoms) if merged is not None and hasattr(merged, "geoms") else ([merged] if merged else [])
    drainage = gpd.GeoDataFrame({"source": ["DTM-derived D8 (threshold %.0f m2)" % stream_threshold_m2] * len(geoms),
                                 "length_m": [g.length for g in geoms]}, geometry=geoms, crs=grid.crs)
    drainage = drainage[drainage.length_m > 20].reset_index(drop=True)
    return {"twi": twi_full, "flow_acc_m2": acc_full, "drainage": drainage}


def vari(ortho):
    """Visible Atmospherically Resistant Index from RGB (no NIR band on a standard UAS camera)."""
    rgb = ortho.astype("float32")
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    den = g + r - b
    out = np.where(np.abs(den) > 1, (g - r) / np.where(np.abs(den) > 1, den, 1), 0)
    return np.clip(out, -1, 1).astype("float32")


VEG_CLASSES = {0: "Open / low vegetation", 1: "Scrub", 2: "Light woodland", 3: "Dense woodland"}


def vegetation_structure(chm, profile):
    cover = canopy_cover(chm, profile["canopy_height_tree_m"], 7)
    veg = np.zeros(chm.shape, "uint8")
    scrub = (ndi.uniform_filter((chm >= profile["scrub_height_min_m"]).astype("float32"), 5) > 0.4)
    veg[scrub] = 1
    trees = cover >= 0.2
    veg[trees] = 2
    veg[cover >= profile["canopy_cover_no_go"]] = 3
    return veg, cover.astype("float32")
