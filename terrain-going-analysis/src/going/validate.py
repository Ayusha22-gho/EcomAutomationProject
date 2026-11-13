"""Validation: DEM checkpoint accuracy and GOING classification accuracy assessment."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from . import CLASS_NAMES, GO, LC, NO_GO, RECCE, SLOW_GO
from .grid import Grid

DETERMINATE = [GO, SLOW_GO, NO_GO]


def dem_checkpoints(world, uas, grid: Grid, n, gnss_sigma, rng):
    """Independent check points (ICPs) surveyed by simulated GNSS RTK; split open vs vegetated."""
    lc = world["landcover"]
    open_mask = np.isin(lc, [LC["GRASS"], LC["CULTIVATED"], LC["ROAD"], LC["TRACK"], LC["BUILT_UP"], LC["QUARRY"]])
    veg_mask = np.isin(lc, [LC["FOREST_LIGHT"], LC["FOREST_DENSE"], LC["SCRUB"]])
    rows = []
    for label, mask, k in (("non-vegetated", open_mask, int(n * 0.6)), ("vegetated", veg_mask, n - int(n * 0.6))):
        idx = rng.choice(np.flatnonzero(mask.ravel()), size=k, replace=False)
        for i in idx:
            r, c = divmod(int(i), grid.width)
            z_ref = float(world["dtm"][r, c] + rng.normal(0, gnss_sigma))
            z_dem = float(uas["dtm"][r, c])
            x, y = grid.rc_to_xy(r, c)
            dx, dy = rng.normal(0, 0.035, 2)
            rows.append({"cp_id": f"ICP{len(rows) + 1:02d}", "land_class": label, "z_ref_m": round(z_ref, 3),
                         "z_dem_m": round(z_dem, 3), "dz_m": round(z_dem - z_ref, 3),
                         "dx_m": round(float(dx), 3), "dy_m": round(float(dy), 3),
                         "geometry": Point(float(x), float(y))})
    df = gpd.GeoDataFrame(rows, geometry="geometry", crs=grid.crs)
    summary = {}
    for label, sub in df.groupby("land_class"):
        dz = sub["dz_m"].to_numpy()
        summary[label] = {"n": int(len(dz)), "mean_error_m": round(float(dz.mean()), 3),
                          "std_m": round(float(dz.std(ddof=1)), 3),
                          "rmse_z_m": round(float(np.sqrt(np.mean(dz ** 2))), 3),
                          "nva_95_m": round(float(1.96 * np.sqrt(np.mean(dz ** 2))), 3),
                          "p95_abs_m": round(float(np.percentile(np.abs(dz), 95)), 3)}
    rmse_r = float(np.sqrt(np.mean(df["dx_m"] ** 2 + df["dy_m"] ** 2)))
    summary["horizontal"] = {"rmse_r_m": round(rmse_r, 3), "ce95_m": round(2.4477 * rmse_r / np.sqrt(2), 3)}
    return df, summary


def stratified_sample(going, n_per_class, min_spacing_px, rng):
    pts = []
    for code in (GO, SLOW_GO, NO_GO, RECCE):
        cand = np.flatnonzero(going.ravel() == code)
        rng.shuffle(cand)
        chosen = []
        for i in cand:
            r, c = divmod(int(i), going.shape[1])
            if all((r - a) ** 2 + (c - b) ** 2 >= min_spacing_px ** 2 for a, b, _ in pts + chosen):
                chosen.append((r, c, code))
            if len(chosen) >= n_per_class:
                break
        pts.extend(chosen)
    return pts


def simulate_ground_observations(samples, truth, grid: Grid, err_rate, rng, gnss_err_m=3.0):
    """A patrol visits each point: handheld GNSS error displaces the observation; observer errs at err_rate."""
    rows = []
    H, W = truth.shape
    for k, (r, c, mapped) in enumerate(samples):
        dr, dc = rng.normal(0, gnss_err_m / grid.res / np.sqrt(2), 2)
        ro = int(np.clip(round(r + dr), 0, H - 1)); co = int(np.clip(round(c + dc), 0, W - 1))
        obs = int(truth[ro, co])
        if rng.random() < err_rate:
            obs = int(rng.choice([x for x in DETERMINATE if abs(x - obs) == 1]))
        x, y = grid.rc_to_xy(r, c)
        rows.append({"obs_id": f"GO{k + 1:03d}", "map_class": CLASS_NAMES[mapped], "obs_class": CLASS_NAMES[obs],
                     "map_code": mapped, "obs_code": obs, "observer": "Simulated patrol",
                     "method": "Simulated ground observation", "geometry": Point(float(x), float(y))})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=grid.crs)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return (centre - half, centre + half)


def accuracy_assessment(obs: gpd.GeoDataFrame, going: np.ndarray) -> dict:
    labels_map = [GO, SLOW_GO, NO_GO, RECCE]
    cm = pd.DataFrame(0, index=[CLASS_NAMES[c] for c in labels_map],
                      columns=[CLASS_NAMES[c] for c in DETERMINATE])
    for m, o in zip(obs.map_code, obs.obs_code):
        cm.loc[CLASS_NAMES[m], CLASS_NAMES[o]] += 1

    det = cm.loc[[CLASS_NAMES[c] for c in DETERMINATE]]
    n = det.values.sum()
    diag = np.trace(det.values)
    oa = diag / n
    pe = (det.sum(1).values * det.sum(0).values).sum() / n ** 2
    kappa = (oa - pe) / (1 - pe)

    per_class = []
    for c in DETERMINATE:
        name = CLASS_NAMES[c]
        ua_n, ua_k = det.loc[name].sum(), det.loc[name, name]
        pa_n, pa_k = det[name].sum(), det.loc[name, name]
        ua_ci, pa_ci = wilson(ua_k, ua_n), wilson(pa_k, pa_n)
        per_class.append({"class": name, "users_accuracy": round(ua_k / ua_n, 3) if ua_n else None,
                          "ua_95ci": f"{ua_ci[0]:.2f}-{ua_ci[1]:.2f}",
                          "producers_accuracy": round(pa_k / pa_n, 3) if pa_n else None,
                          "pa_95ci": f"{pa_ci[0]:.2f}-{pa_ci[1]:.2f}", "n_mapped": int(ua_n)})

    # Olofsson et al. (2014) area-weighted estimator over the determinate strata
    areas = {CLASS_NAMES[c]: float((going == c).sum()) for c in DETERMINATE}
    tot = sum(areas.values())
    p = np.zeros((3, 3))
    for i, ci in enumerate(DETERMINATE):
        row = det.loc[CLASS_NAMES[ci]].values.astype(float)
        if row.sum():
            p[i] = areas[CLASS_NAMES[ci]] / tot * row / row.sum()
    oa_area = float(np.trace(p))

    recce_row = cm.loc[CLASS_NAMES[RECCE]]
    flagged_problem = int(recce_row[[CLASS_NAMES[SLOW_GO], CLASS_NAMES[NO_GO]]].sum())

    # Safety-critical error: mapped GO/SLOW-GO but actually NO-GO (vehicle could become stuck)
    unsafe = int(det.loc[CLASS_NAMES[GO], CLASS_NAMES[NO_GO]] + det.loc[CLASS_NAMES[SLOW_GO], CLASS_NAMES[NO_GO]])
    return {
        "confusion_matrix": cm, "overall_accuracy": round(oa, 3), "oa_95ci": "%.2f-%.2f" % wilson(diag, n),
        "kappa": round(kappa, 3), "area_weighted_oa": round(oa_area, 3), "per_class": pd.DataFrame(per_class),
        "n_determinate": int(n), "recce_resolution": recce_row.to_dict(),
        "recce_flag_efficiency": round(flagged_problem / max(recce_row.sum(), 1), 3),
        "unsafe_commission": unsafe,
    }
