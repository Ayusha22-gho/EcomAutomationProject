"""Least-cost route generation and multi-criteria route comparison."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from shapely.geometry import LineString
from skimage.graph import MCP_Geometric

from . import GO, NO_GO, RECCE, SLOW_GO
from .grid import Grid


def speed_surface(going, R, slope, profile):
    """Illustrative cross-country speed (km/h) per cell; 0 = impassable."""
    sp = profile["speeds_kmh"]
    v = np.zeros(going.shape, "float32")
    v[going == GO] = sp["GO"]
    v[going == SLOW_GO] = sp["SLOW_GO"]
    v[going == RECCE] = sp["RECCE"]
    slope_factor = np.clip(1.0 - slope / (profile["slope_no_go_deg"] * 1.4), 0.3, 1.0)
    v *= slope_factor
    v[(going == GO) & R["track"]] = sp["track"]
    v[(going == GO) & R["road"]] = sp["road"]
    v[going == NO_GO] = 0
    return v


ROUTE_DEFS = {
    "A-DIRECT": "Shortest passable distance (avoids NO-GO only)",
    "B-FASTEST": "Minimum estimated transit time (RECCE cells allowed at reduced speed)",
    "C-ASSURED": "Minimum time avoiding all REQUIRES-RECCE cells (no unverified crossings)",
    "D-CONCEALED": "Minimum time weighted by exposure to OP SIERRA line of sight",
}


def cost_surfaces(going, speed, visible):
    sec_per_m = np.where(speed > 0, 3.6 / np.maximum(speed, 1e-3), np.inf)
    passable = going != NO_GO
    direct = np.where(passable, 1.0, np.inf)
    fastest = np.where(going == RECCE, sec_per_m * 1.5, sec_per_m)
    assured = np.where(going == RECCE, np.inf, np.where(going == SLOW_GO, sec_per_m * 1.5, sec_per_m))
    concealed = fastest * (1.0 + 6.0 * visible)
    return {"A-DIRECT": direct, "B-FASTEST": fastest, "C-ASSURED": assured, "D-CONCEALED": concealed}


def least_cost_path(cost, start_rc, end_rc, res):
    m = MCP_Geometric(cost.astype("float64"), fully_connected=True, sampling=(res, res))
    cum, _ = m.find_costs([start_rc], [end_rc])
    if not np.isfinite(cum[end_rc]):
        return None
    return np.array(m.traceback(end_rc))


def route_metrics(path, going, speed, slope, visible, R, res):
    rr, cc = path[:, 0], path[:, 1]
    step = np.hypot(np.diff(rr), np.diff(cc)) * res
    step = np.append(step, 0.0)
    v = np.maximum(speed[rr, cc], 1e-3)
    time_s = float(np.sum(step * 3.6 / v))
    g = going[rr, cc]
    length = float(step.sum())
    share = {k: float(step[g == code].sum() / length) for k, code in
             (("GO", GO), ("SLOW-GO", SLOW_GO), ("RECCE", RECCE), ("NO-GO", NO_GO))}
    lbl, n_recce = ndi.label(g == RECCE)
    crossings = ndi.label(R["crossing"][rr, cc])[1]
    exposure = float(step[visible[rr, cc] > 0.5].sum() / length)
    on_road = float(step[(R["road"] | R["track"])[rr, cc]].sum() / length)
    return {
        "length_m": round(length, 0), "est_time_min": round(time_s / 60.0, 1),
        "avg_speed_kmh": round(length / time_s * 3.6, 1),
        "pct_GO": round(100 * share["GO"], 1), "pct_SLOW_GO": round(100 * share["SLOW-GO"], 1),
        "pct_RECCE": round(100 * share["RECCE"], 1), "pct_NO_GO": round(100 * share["NO-GO"], 1),
        "pct_on_road_track": round(100 * on_road, 1),
        "max_slope_deg": round(float(slope[rr, cc].max()), 1),
        "recce_sections": int(n_recce), "water_crossings": int(crossings),
        "pct_exposed_to_OP": round(100 * exposure, 1),
    }


def score_routes(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Normalised weighted score (0 = best). Illustrative decision support only."""
    def norm(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else s * 0.0
    risk = df["pct_RECCE"] + 0.5 * df["pct_SLOW_GO"] + 10 * df["recce_sections"]
    score = (weights["time"] * norm(df["est_time_min"]) + weights["risk"] * norm(risk)
             + weights["exposure"] * norm(df["pct_exposed_to_OP"])
             + weights["crossings"] * norm(df["water_crossings"].astype(float)))
    df = df.copy()
    df["risk_index"] = risk.round(1)
    df["weighted_score"] = score.round(3)
    df["rank"] = df["weighted_score"].rank(method="min").astype(int)
    return df


def generate_routes(going, R, slope, visible, profile, grid: Grid, sp_rc, obj_rc, weights):
    speed = speed_surface(going, R, slope, profile)
    costs = cost_surfaces(going, speed, visible)
    rows, geoms = [], []
    for name, cost in costs.items():
        path = least_cost_path(cost, sp_rc, obj_rc, grid.res)
        if path is None:
            continue
        x, y = grid.rc_to_xy(path[:, 0], path[:, 1])
        geom = LineString(np.column_stack([x, y])).simplify(1.5)
        m = route_metrics(path, going, speed, slope, visible, R, grid.res)
        rows.append({"route": name, "definition": ROUTE_DEFS[name], **m})
        geoms.append(geom)
    df = score_routes(pd.DataFrame(rows), weights)
    gdf = gpd.GeoDataFrame(df, geometry=geoms, crs=grid.crs)
    return gdf, speed


def viewshed(dsm, dtm, grid: Grid, obs_rc, observer_h, target_h, max_range, cell=4.0, samples=220):
    """Binary line-of-sight from one observer (computed on a coarsened surface for speed)."""
    f = int(round(cell / grid.res))
    Hc, Wc = grid.height // f, grid.width // f
    surf = dsm[:Hc * f, :Wc * f].reshape(Hc, f, Wc, f).mean(axis=(1, 3))
    ground = dtm[:Hc * f, :Wc * f].reshape(Hc, f, Wc, f).mean(axis=(1, 3))
    orow, ocol = obs_rc[0] / f, obs_rc[1] / f
    oz = ground[int(orow), int(ocol)] + observer_h
    tr, tc = np.mgrid[0:Hc, 0:Wc]
    tr = tr.ravel().astype(float); tc = tc.ravel().astype(float)
    tz = ground.ravel() + target_h
    dist = np.hypot(tr - orow, tc - ocol) * cell
    vis = np.zeros(tr.size, bool)
    t = np.linspace(0.02, 0.97, samples)[None, :]
    for s in range(0, tr.size, 4000):
        e = slice(s, s + 4000)
        sr = orow + (tr[e, None] - orow) * t
        sc = ocol + (tc[e, None] - ocol) * t
        sz = surf[np.clip(sr.astype(int), 0, Hc - 1), np.clip(sc.astype(int), 0, Wc - 1)]
        d = dist[e, None] * t
        sz = np.where(d < 12.0, -np.inf, sz)      # observer on a cleared site / mast
        ang_s = np.max((sz - oz) / np.maximum(d, 1e-3), axis=1)
        ang_t = (tz[e] - oz) / np.maximum(dist[e], 1e-3)
        vis[e] = ang_t >= ang_s
    vis &= dist <= max_range
    vis = ndi.median_filter(vis.reshape(Hc, Wc).astype("float32"), size=5)
    return np.kron(vis, np.ones((f, f)))[:grid.height, :grid.width].astype("float32")
