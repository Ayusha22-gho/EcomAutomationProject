"""Simulated UAS photogrammetry products (stand-in for OpenDroneMap / WebODM output).

Reproduces the characteristic behaviour of RGB structure-from-motion products:
* DSM noise of a few centimetres over textured open ground;
* data voids over water (no stable tie points) that the software fills by interpolation;
* no ground returns under closed canopy, so the DTM is interpolated and biased high;
* hedgerows partly misclassified as ground;
* an orthomosaic that shows only the top of the canopy.
The hidden layers of the synthetic world (soil wetness, understorey, ford depth) are
deliberately NOT used here.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from scipy import ndimage as ndi

from . import LC
from .grid import Grid
from .synth import fractal_noise


def _fill_nan(a, sigma):
    """Normalised-convolution gap filling (approximates TIN/IDW interpolation)."""
    valid = np.isfinite(a)
    filled = np.where(valid, a, 0.0)
    num = ndi.gaussian_filter(filled, sigma)
    den = ndi.gaussian_filter(valid.astype(float), sigma)
    out = np.where(valid, a, num / np.maximum(den, 1e-6))
    if np.isnan(out).any() or (den < 1e-3).any():
        out = np.where(den < 1e-3, _fill_nan(np.where(den < 1e-3, np.nan, out), sigma * 2), out)
    return out


def canopy_cover(chm, tree_height, radius_px=7):
    size = 2 * radius_px + 1
    return ndi.uniform_filter((chm >= tree_height).astype("float32"), size=size)


def simulate_uas(world: dict, grid: Grid, seed: int) -> dict:
    rng = np.random.default_rng(seed + 1)
    H, W = grid.shape
    lc = world["landcover"]
    dtm_t, dsm_t, chm_t = world["dtm"], world["dsm"], world["chm"]

    # ---------------------------------------------------------------- DSM
    lowfreq = fractal_noise((H, W), 4.0, rng, std=0.025)          # residual block deformation after GCP adjustment
    noise_sd = np.where(chm_t > 2.0, 0.25, 0.04)
    dsm = dsm_t + lowfreq + rng.normal(0, 1, (H, W)) * noise_sd
    dsm = np.where(chm_t > 2.0, ndi.gaussian_filter(dsm, 1.0), dsm)   # crown smoothing by dense matching
    void = world["water"].copy()
    void |= ndi.binary_dilation(world["water"], iterations=2) & (rng.random((H, W)) < 0.5)
    dsm = _fill_nan(np.where(void, np.nan, dsm), 4)

    # ---------------------------------------------------------------- DTM
    cover = canopy_cover(chm_t, 3.0, 5)
    ground_visible = (chm_t < 0.6) | ((chm_t < 3.0) & (rng.random((H, W)) < 0.3))
    ground_visible |= (cover < 0.35) & (chm_t < 3.0)
    ground_visible &= ~void & (lc != LC["BUILDING"])
    dtm_obs = np.where(ground_visible, dtm_t + lowfreq + rng.normal(0, 0.05, (H, W)), np.nan)
    hedge_leak = (lc != LC["BUILDING"]) & (chm_t > 1.5) & (chm_t < 3.0) & (rng.random((H, W)) < 0.25)
    dtm_obs = np.where(hedge_leak, dsm, dtm_obs)
    dtm = _fill_nan(dtm_obs, 6)
    under_canopy = ~ground_visible & (chm_t >= 3.0)
    dtm = np.where(under_canopy, dtm + 0.4 * cover + rng.normal(0, 0.15, (H, W)), dtm)
    dtm = ndi.median_filter(dtm, size=3)

    # ---------------------------------------------------------------- confidence
    gv = ndi.uniform_filter(ground_visible.astype("float32"), 9)
    conf = 0.15 + 0.85 * gv
    conf = np.where(void, 0.1, conf)
    texture_poor = (lc == LC["CULTIVATED"]) | (lc == LC["QUARRY"])
    conf = np.where(texture_poor, conf * 0.9, conf)
    conf = ndi.gaussian_filter(conf, 2).clip(0, 1)

    chm = np.clip(dsm - dtm, 0, None)

    ortho = _orthomosaic(world, grid, rng, dtm_t)

    digitised = _digitise(world["features"], cover, grid)

    return {
        "dsm": dsm.astype("float32"), "dtm": dtm.astype("float32"), "chm": chm.astype("float32"),
        "confidence": conf.astype("float32"), "ortho": ortho, "void": void,
        "ground_visible": ground_visible, "digitised": digitised,
    }


def hillshade(z, res=1.0, az=315.0, alt=45.0):
    gy, gx = np.gradient(z, res)
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    azr, altr = np.radians(az), np.radians(alt)
    hs = np.sin(altr) * np.sin(slope) + np.cos(altr) * np.cos(slope) * np.cos(azr - np.pi / 2 - aspect)
    return np.clip(hs, 0, 1)


def _orthomosaic(world, grid, rng, dtm):
    H, W = grid.shape
    lc, chm = world["landcover"], world["chm"]
    palette = {
        LC["GRASS"]: (118, 150, 72), LC["CULTIVATED"]: (128, 98, 68), LC["SCRUB"]: (98, 112, 58),
        LC["FOREST_LIGHT"]: (62, 96, 44), LC["FOREST_DENSE"]: (40, 72, 34), LC["BUILT_UP"]: (150, 145, 132),
        LC["BUILDING"]: (150, 80, 62), LC["ROAD"]: (92, 92, 96), LC["TRACK"]: (160, 140, 108),
        LC["WATER"]: (48, 70, 78), LC["MARSH"]: (96, 110, 70), LC["QUARRY"]: (182, 176, 166),
    }
    rgb = np.zeros((H, W, 3), "float32")
    for code, col in palette.items():
        rgb[lc == code] = col
    tex = fractal_noise((H, W), 2.0, rng, std=1.0)
    rgb *= (1.0 + 0.06 * tex)[..., None]
    trees = chm > 3.0
    crown_shade = ndi.gaussian_filter(chm, 1.2)
    rgb[trees] *= (0.75 + 0.35 * (crown_shade[trees] / (crown_shade[trees].max() + 1e-6)))[:, None]
    gap = (lc == LC["FOREST_LIGHT"]) & ~trees
    rgb[gap] = rgb[gap] * 0.5 + np.array(palette[LC["GRASS"]]) * 0.5
    r = np.arange(H)[:, None] * np.ones((1, W))
    plough = (lc == LC["CULTIVATED"])
    rgb[plough] *= (1.0 + 0.08 * np.sin(r[plough] / 1.6))[:, None]
    marsh = lc == LC["MARSH"]
    pools = marsh & (fractal_noise((H, W), 2.5, rng) > 1.0)
    rgb[pools] = palette[LC["WATER"]]
    roof = ndi.label(lc == LC["BUILDING"])[0]
    roof_cols = rng.choice([[150, 80, 62], [120, 120, 125], [95, 85, 80]], size=roof.max() + 1)
    rgb[roof > 0] = roof_cols[roof[roof > 0]]
    hs = hillshade(dtm + chm)
    rgb *= (0.55 + 0.6 * hs)[..., None]
    rgb += rng.normal(0, 3, rgb.shape)
    return np.clip(rgb, 0, 255).astype("uint8")


def _digitise(feats: dict, cover, grid: Grid) -> dict[str, gpd.GeoDataFrame]:
    """Analyst digitising from the orthomosaic: features hidden under canopy are missed."""
    out = {}
    for name, g in feats.items():
        g = g.copy()
        g["source"] = "UAS ortho digitised (simulated)"
        g["capture_date"] = "D-day 0"
        out[name] = g
    lo = out["linear_obstacles"].copy()
    keep_geoms = []
    for geom in lo.geometry:
        pts = [geom.interpolate(d) for d in np.arange(0, geom.length, 2.0)]
        rr, cc = grid.xy_to_rc([p.x for p in pts], [p.y for p in pts])
        rr = np.clip(rr, 0, grid.height - 1)
        cc = np.clip(cc, 0, grid.width - 1)
        visible = cover[rr, cc] < 0.5
        keep_geoms.append(visible.mean())
    lo["visible_fraction"] = keep_geoms
    lo["confidence"] = np.where(lo["visible_fraction"] > 0.85, "high",
                                np.where(lo["visible_fraction"] > 0.6, "medium", "low"))
    out["linear_obstacles"] = lo[lo["visible_fraction"] > 0.6].reset_index(drop=True)
    return out
