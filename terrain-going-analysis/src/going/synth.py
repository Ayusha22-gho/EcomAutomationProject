"""Synthetic 'ground truth' world for AOI KESTREL.

The generator produces the true terrain, land cover and hidden ground
conditions (soil wetness, understorey density, true ford depth). The UAS
simulator only sees what a camera could see; the hidden layers are used
exclusively to simulate ground-truth observations for validation.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint

from . import LC
from .grid import Grid


def fractal_noise(shape, beta, rng, std=1.0):
    """Isotropic 1/f^beta noise via spectral synthesis, scaled to the given std."""
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    spectrum = (rng.normal(size=f.shape) + 1j * rng.normal(size=f.shape)) / f ** (beta / 2.0)
    spectrum[0, 0] = 0.0
    field = np.fft.irfft2(spectrum, s=shape)
    return (field - field.mean()) / field.std() * std


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def stream_col(r):
    """Stream centreline: column as a function of row (flows north to south)."""
    return 330.0 + 0.22 * r + 35.0 * np.sin(r / 85.0)


STREAM_SOURCE_ROW = 140


def road_row(c):
    """Main supply route (paved) centreline row as a function of column."""
    pts_c = np.array([0, 150, 260, 420, 650, 820, 1000], float)
    pts_r = np.array([830, 815, 800, 790, 800, 840, 870], float)
    return np.interp(c, pts_c, pts_r)


def build_world(grid: Grid, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    H, W = grid.shape
    r, c = np.mgrid[0:H, 0:W].astype(float)

    # ------------------------------------------------------------------ relief
    z = 150.0 + 0.025 * (H - r) + 0.008 * c
    z += 55.0 * np.exp(-(((r - 200) / 190.0) ** 2 + ((c - 830) / 210.0) ** 2))   # NE ridge
    z += 30.0 * np.exp(-((r - 560) ** 2 + (c - 150) ** 2) / (2 * 50.0 ** 2))       # SW knoll
    # escarpment: step along the line (620,450)->(980,700), high side to the NE
    ex0, ey0, ex1, ey1 = 620.0, 450.0, 980.0, 700.0
    nx, ny = (ey1 - ey0), -(ex1 - ex0)
    nlen = np.hypot(nx, ny)
    signed = ((c - ex0) * nx + (r - ey0) * ny) / nlen
    along = ((c - ex0) * (ex1 - ex0) + (r - ey0) * (ey1 - ey0)) / np.hypot(ex1 - ex0, ey1 - ey0) ** 2
    esc_mask = _sigmoid((along - 0.1) * 7) * _sigmoid((1.1 - along) * 7)
    z += 16.0 * _sigmoid(-signed / 5.0) * esc_mask * np.exp(-np.clip(-signed - 60, 0, None) / 250.0)
    z += fractal_noise((H, W), 3.6, rng, std=1.6)
    z += rng.normal(0, 0.03, (H, W))

    # stream valley and channel
    scol = stream_col(r)
    d_stream = np.abs(c - scol) * np.cos(np.arctan(0.22))
    ramp = np.clip((r - STREAM_SOURCE_ROW) / 160.0, 0, 1)
    z -= 7.0 * np.exp(-(d_stream / 110.0) ** 2) * ramp
    channel = (d_stream < 4.0) & (r >= STREAM_SOURCE_ROW)
    bank = np.clip((5.5 - d_stream) / 1.5, 0, 1) * (r >= STREAM_SOURCE_ROW)
    z -= 1.6 * bank

    # marsh: broad flat valley floor
    marsh_core = (np.hypot((r - 545) / 85.0, (d_stream) / 38.0) < 1.0)
    z = np.where(marsh_core, ndi.gaussian_filter(z, 12) * 0.6 + z * 0.4, z)

    # quarry pit (NW), steep walls
    qd = np.maximum(np.abs(c - 170) / 55.0, np.abs(r - 335) / 38.0)
    z -= 10.0 * _sigmoid((1.0 - qd) * 22.0)

    # pond (near village)
    pond_d = np.hypot((r - 700) / 28.0, (c - 140) / 40.0)
    pond = pond_d < 1.0
    pond_level = np.percentile(z[pond], 20)
    z = np.where(pond_d < 1.25, np.minimum(z, pond_level + 0.4 * np.clip(pond_d - 1.0, 0, None) * 8), z)
    z[pond] = pond_level

    dtm = z.astype("float32")

    # --------------------------------------------------------------- vectors
    feats = _vector_features(grid, rng, dtm)

    # ------------------------------------------------------------- land cover
    lc = np.full((H, W), LC["GRASS"], dtype="uint8")
    lc[grid.rasterize(feats["fields"].geometry) == 1] = LC["CULTIVATED"]

    road_buf = grid.rasterize(feats["roads"].geometry.buffer(12)) == 1
    excluded = (grid.rasterize(feats["fields"].geometry) == 1) | road_buf | pond
    excluded |= grid.rasterize([feats["built_up"].geometry.iloc[0].buffer(20)]) == 1
    excluded |= qd < 1.15

    fnoise = fractal_noise((H, W), 3.0, rng)
    bias = 1.6 * np.exp(-(((r - 230) / 270.0) ** 2 + ((c - 760) / 240.0) ** 2))
    bias += 1.2 * np.exp(-(((r - 420) / 90.0) ** 2 + ((c - 150) / 110.0) ** 2))
    forest = ((fnoise * 0.6 + bias) > 1.05) & ~excluded
    riparian = (d_stream < 16) & (r > STREAM_SOURCE_ROW - 20) & (r < 470) & ~excluded
    forest |= riparian
    forest = ndi.binary_opening(forest, iterations=2)
    dnoise = fractal_noise((H, W), 3.0, rng)
    dense = forest & ((dnoise + 1.8 * np.exp(-(((r - 170) / 170.0) ** 2 + ((c - 820) / 160.0) ** 2))) > 1.0)
    dense = ndi.binary_opening(dense, iterations=3) & ~riparian

    ring = ndi.binary_dilation(forest, iterations=14) & ~forest
    snoise = fractal_noise((H, W), 2.6, rng)
    scrub = (ring & (snoise > -0.3)) | ((snoise > 1.6) & ~forest)
    slope_true = np.degrees(np.arctan(np.hypot(*np.gradient(ndi.gaussian_filter(dtm, 2.0)))))
    scrub |= (slope_true > 22) & (esc_mask > 0.5) & (snoise > -0.8) & ~forest
    scrub &= ~excluded

    lc[scrub] = LC["SCRUB"]
    lc[forest] = LC["FOREST_LIGHT"]
    lc[dense] = LC["FOREST_DENSE"]
    lc[qd < 1.05] = LC["QUARRY"]
    lc[grid.rasterize(feats["marsh"].geometry) == 1] = LC["MARSH"]
    lc[grid.rasterize(feats["built_up"].geometry) == 1] = LC["BUILT_UP"]
    lc[grid.rasterize(feats["roads"][feats["roads"].surface == "unpaved"].geometry.buffer(2.0)) == 1] = LC["TRACK"]
    lc[grid.rasterize(feats["roads"][feats["roads"].surface == "paved"].geometry.buffer(3.5)) == 1] = LC["ROAD"]
    water = pond | (channel & (lc != LC["ROAD"]))
    lc[water] = LC["WATER"]
    lc[grid.rasterize(feats["buildings"].geometry, all_touched=False) == 1] = LC["BUILDING"]

    # ------------------------------------------------------- canopy / heights
    crown = fractal_noise((H, W), 1.6, rng)
    chm = np.zeros((H, W), "float32")
    tree_h = 11 + 4 * fractal_noise((H, W), 3.0, rng) + 3 * crown
    light_crowns = crown > np.quantile(crown, 0.48)
    dense_crowns = crown > np.quantile(crown, 0.10)
    chm = np.where((lc == LC["FOREST_LIGHT"]) & light_crowns, np.clip(tree_h, 5, 22), chm)
    chm = np.where((lc == LC["FOREST_DENSE"]) & dense_crowns, np.clip(tree_h + 5, 8, 26), chm)
    scrub_h = np.clip(1.6 + 0.8 * crown, 0.3, 3.0)
    chm = np.where((lc == LC["SCRUB"]) & (crown > -0.6), scrub_h, chm)
    chm = np.where(lc == LC["CULTIVATED"], 0.15, chm)
    bh = grid.rasterize([(g, int(h * 10)) for g, h in zip(feats["buildings"].geometry,
                                                          feats["buildings"].height_m)],
                        dtype="int16", all_touched=False) / 10.0
    chm = np.where(lc == LC["BUILDING"], bh, chm)
    hedge = grid.rasterize(feats["linear_obstacles"][feats["linear_obstacles"]["type"] == "hedgerow"]
                           .geometry.buffer(1.0)) == 1
    chm = np.where(hedge & (chm < 2.0), 2.2, chm)
    chm = chm.astype("float32")
    dsm = (dtm + chm).astype("float32")

    # ------------------------------------------------------- hidden ground state
    wet_noise = fractal_noise((H, W), 3.2, rng)
    understorey = (fractal_noise((H, W), 3.0, rng) > 0.9) & (lc == LC["FOREST_LIGHT"])

    return {
        "dtm": dtm, "dsm": dsm, "chm": chm, "landcover": lc, "water": water,
        "channel": channel, "pond": pond, "wet_noise": wet_noise.astype("float32"),
        "understorey": understorey, "features": feats, "stream_dist": d_stream,
    }


def _vector_features(grid: Grid, rng, dtm) -> dict[str, gpd.GeoDataFrame]:
    crs = grid.crs
    H = grid.height

    def gdf(rows, geom_key="geometry"):
        return gpd.GeoDataFrame(rows, geometry=geom_key, crs=crs)

    # roads ------------------------------------------------------------------
    msr_c = np.linspace(0, 1000, 60)
    msr = grid.px_line(list(zip(msr_c, road_row(msr_c))))
    track_pts = [(300, 803), (292, 650), (300, 520), (355, 430), (384, 405), (470, 360),
                 (560, 300), (700, 228), (850, 120), (905, 72)]
    t1 = grid.px_line(track_pts)
    t2 = grid.px_line([(650, 800), (700, 900), (760, 1000)])
    roads = gdf([
        {"name": "MSR GRANITE", "surface": "paved", "width_m": 7.0, "geometry": msr},
        {"name": "TRACK T1", "surface": "unpaved", "width_m": 4.0, "geometry": t1},
        {"name": "TRACK T2", "surface": "unpaved", "width_m": 4.0, "geometry": t2},
    ])

    # stream -----------------------------------------------------------------
    sr = np.linspace(STREAM_SOURCE_ROW, H, 200)
    stream = gdf([{"name": "KESTREL BROOK", "width_m": 8.0, "perennial": True,
                   "geometry": grid.px_line(list(zip(stream_col(sr), sr)))}])

    # crossings: bridge on MSR, ford on T1
    bridge_r = 789.0
    bridge_c = float(stream_col(bridge_r))
    bridge_r = float(road_row(bridge_c))
    ford = (384.0, 405.0)
    crossings = gdf([
        {"name": "BRIDGE B1", "type": "bridge", "mlc_known": False, "true_mlc": 30,
         "geometry": grid.px_point(bridge_c, bridge_r)},
        {"name": "FORD F1", "type": "ford", "depth_known": False, "true_depth_m": 0.55,
         "geometry": grid.px_point(*ford)},
    ])

    # water bodies / marsh / quarry -------------------------------------------
    t = np.linspace(0, 2 * np.pi, 80)
    pond = grid.px_poly(list(zip(140 + 40 * np.cos(t), 700 + 28 * np.sin(t))))
    water_bodies = gdf([{"name": "POND P1", "type": "pond", "geometry": pond}])

    mr = np.linspace(470, 620, 40)
    marsh_line = grid.px_line(list(zip(stream_col(mr), mr)))
    marsh = gdf([{"name": "MARSH M1", "type": "marsh", "geometry": marsh_line.buffer(32 * grid.res)}])
    quarry = gdf([{"name": "QUARRY Q1", "type": "quarry", "depth_m": 10.0,
                   "geometry": grid.px_poly([(115, 297), (225, 297), (225, 373), (115, 373)])}])

    # fields -------------------------------------------------------------------
    fields = gdf([
        {"name": "F1", "crop": "arable", "geometry": grid.px_poly([(20, 870), (200, 870), (200, 990), (20, 990)])},
        {"name": "F2", "crop": "arable", "geometry": grid.px_poly([(300, 840), (470, 840), (470, 990), (300, 990)])},
        {"name": "F3", "crop": "arable", "geometry": grid.px_poly([(560, 880), (760, 880), (760, 990), (560, 990)])},
        {"name": "F4", "crop": "arable", "geometry": grid.px_poly([(20, 420), (100, 420), (100, 560), (20, 560)])},
    ])

    # buildings ---------------------------------------------------------------
    bld, tries = [], 0
    while len(bld) < 30 and tries < 3000:
        tries += 1
        cc = rng.uniform(170, 360)
        rr = rng.uniform(735, 860)
        if abs(rr - road_row(cc)) < 12 or np.hypot((cc - 140) / 50, (rr - 700) / 38) < 1:
            continue
        w, h = rng.uniform(8, 16), rng.uniform(6, 12)
        fp = grid.px_poly([(cc - w / 2, rr - h / 2), (cc + w / 2, rr - h / 2),
                           (cc + w / 2, rr + h / 2), (cc - w / 2, rr + h / 2)])
        if any(fp.buffer(4).intersects(b["geometry"]) for b in bld):
            continue
        bld.append({"bld_id": f"B{len(bld) + 1:02d}", "height_m": round(float(rng.uniform(5, 9)), 1),
                    "use": rng.choice(["dwelling", "farm", "store"]), "geometry": fp})
    buildings = gdf(bld)
    built_up = gdf([{"name": "VILLAGE HOLM", "geometry":
                     MultiPoint([p for g in buildings.geometry for p in g.exterior.coords]).convex_hull.buffer(12)}])

    # linear obstacles ------------------------------------------------------------
    lin = [
        ("hedgerow", "H1a", [(20, 865), (95, 865)], 2.2, 2.0),
        ("hedgerow", "H1b", [(108, 865), (200, 865)], 2.2, 2.0),
        ("hedgerow", "H2", [(205, 872), (205, 995)], 2.2, 2.0),
        ("hedgerow", "H3a", [(295, 835), (380, 835)], 2.0, 2.0),
        ("hedgerow", "H3b", [(392, 835), (480, 835)], 2.0, 2.0),
        ("hedgerow", "H4a", [(555, 875), (640, 875)], 2.0, 2.0),
        ("hedgerow", "H4b", [(652, 875), (765, 875)], 2.0, 2.0),
        ("stone_wall", "W1", [(560, 120), (600, 180), (640, 235), (690, 290)], 1.2, 1.0),
        ("stone_wall", "W2", [(105, 420), (105, 560)], 0.5, 0.8),
        ("stone_wall", "W3", [(780, 120), (820, 160), (860, 200)], 1.0, 0.8),
        ("ditch", "D1", [(0, 840), (60, 836), (140, 826)], 1.4, 2.5),
        ("ditch", "D2", [(470, 838), (470, 990)], 1.0, 2.0),
    ]
    linear_obstacles = gdf([{"type": t_, "obs_id": i, "height_or_depth_m": hgt, "width_m": wd,
                             "geometry": grid.px_line(p)} for t_, i, p, hgt, wd in lin])

    # vertical obstructions (UAS flight safety) -----------------------------------
    pl = grid.px_line([(0, 250), (1000, 420)])
    pylons = gdf([{"obs_id": f"PY{i + 1}", "height_m": 28.0, "geometry": pl.interpolate(f, normalized=True)}
                  for i, f in enumerate([0.08, 0.36, 0.64, 0.92])])
    powerline = gdf([{"name": "OHL 33kV", "height_m": 22.0, "geometry": pl}])

    return {
        "roads": roads, "streams": stream, "crossings": crossings, "water_bodies": water_bodies,
        "marsh": marsh, "quarry": quarry, "fields": fields, "buildings": buildings,
        "built_up": built_up, "linear_obstacles": linear_obstacles, "pylons": pylons,
        "powerline": powerline,
    }
