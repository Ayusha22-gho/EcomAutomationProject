#!/usr/bin/env python3
"""End-to-end reference pipeline for Exercise TERRA SWIFT (AOI KESTREL).

    python run_pipeline.py                 # full run, all products into ./outputs
    python run_pipeline.py --season dry    # override the primary season
    python run_pipeline.py --profile tracked

Every product is regenerated deterministically from config/ (fixed random seed),
which is the repeatability demonstration required by the course.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio import features as rfeatures
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from going import CLASS_COLOURS, CLASS_NAMES, GO, NO_GO, RECCE, SLOW_GO  # noqa: E402
from going import io as gio  # noqa: E402
from going import maps  # noqa: E402
from going.classify import REASONS, classify_going, classify_truth, rasterise_features, soil_wetness  # noqa: E402
from going.grid import Grid  # noqa: E402
from going.routes import generate_routes, viewshed  # noqa: E402
from going.survey import Camera, SurveyParams, design, plan_mission  # noqa: E402
from going.synth import build_world  # noqa: E402
from going.terrain import hydrology, slope_degrees, vari, vegetation_structure  # noqa: E402
from going.uas import canopy_cover, simulate_uas  # noqa: E402
from going.validate import (accuracy_assessment, dem_checkpoints, simulate_ground_observations,  # noqa: E402
                            stratified_sample)

LOG: list[dict] = []


def step(name):
    def deco(fn):
        def wrapper(*a, **k):
            t = time.time()
            print(f"[{len(LOG) + 1:02d}] {name} ...", flush=True)
            out = fn(*a, **k)
            LOG.append({"step": len(LOG) + 1, "name": name, "seconds": round(time.time() - t, 2)})
            return out
        return wrapper
    return deco


def hex_to_rgba(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


@step("Load configuration")
def load_config(args):
    cfg = json.loads((ROOT / "config/project.json").read_text())
    crit = json.loads((ROOT / "config/going_criteria.json").read_text())
    if args.season:
        cfg["primary_season"] = args.season
    if args.profile:
        cfg["vehicle_profile"] = args.profile
    return cfg, crit


@step("Survey planning (GSD, overlap, flight lines, GCPs, QGC .plan)")
def survey_planning(grid, world, out):
    d = design(Camera(), SurveyParams(), grid.width * grid.res, grid.height * grid.res)
    plan = plan_mission(d, grid, world["dtm"], out / "mission")
    return d, plan


@step("Generate synthetic ground truth world")
def make_world(grid, cfg):
    return build_world(grid, cfg["random_seed"])


@step("Simulate UAS photogrammetry products (ortho, DSM, DTM, confidence)")
def make_uas(world, grid, cfg):
    return simulate_uas(world, grid, cfg["random_seed"])


@step("Terrain derivatives (slope, hydrology/TWI, vegetation structure, VARI)")
def derive_layers(uas, grid, crit, profile):
    slope = slope_degrees(uas["dtm"], grid.res, crit["slope_baseline_smoothing_sigma_m"])
    hyd = hydrology(uas["dtm"], grid)
    veg, cover = vegetation_structure(uas["chm"], profile)
    return {"slope": slope, "twi": hyd["twi"], "flow_acc": hyd["flow_acc_m2"], "drainage": hyd["drainage"],
            "veg": veg, "cover": cover, "vari": vari(uas["ortho"]), "confidence": uas["confidence"]}


@step("GOING classification (primary + season/profile variants)")
def classify_all(layers, R, crit, cfg, grid, uas):
    mmu = int(crit["generalisation"]["min_mapping_unit_m2"] / grid.res ** 2)
    out = {}
    for prof in ("wheeled_4x4", "tracked"):
        P = crit["profiles"][prof]
        veg, cover = vegetation_structure(uas["chm"], P)
        L = dict(layers, veg=veg, cover=cover, raster_features=R)
        for season in ("dry", "wet"):
            out[(prof, season)] = classify_going(L, P, crit["seasons"][season], crit, mmu)
    return out


@step("Truth model and simulated ground observations")
def truth_and_validation(world, grid, crit, cfg, going, uas, rng):
    prof = crit["profiles"][cfg["vehicle_profile"]]
    t_slope = slope_degrees(world["dtm"], grid.res, crit["slope_baseline_smoothing_sigma_m"])
    t_hyd = hydrology(world["dtm"], grid)
    feats = world["features"]
    R_true = rasterise_features(feats, grid)
    cr = np.zeros(grid.shape, "uint8")
    for _, c in feats["crossings"].iterrows():
        ok = (c["true_mlc"] >= 16) if c["type"] == "bridge" else (c["true_depth_m"] <= prof["max_ford_depth_m"])
        m = grid.rasterize([c.geometry.buffer(9.0)]) == 1
        cr[m & (R_true["water"] | R_true["road"] | R_true["track"])] = 1 if ok else 2
    tl = {"slope": t_slope, "cover": canopy_cover(world["chm"], prof["canopy_height_tree_m"], 7),
          "raster_features": R_true, "soil_wetness": soil_wetness(world, t_hyd["twi"]), "crossing_truth": cr}
    truth = classify_truth(world, tl, prof, cfg["primary_season"])

    v = cfg["validation"]
    samples = stratified_sample(going, v["samples_per_class"], v["min_spacing_m"] / grid.res, rng)
    obs = simulate_ground_observations(samples, truth, grid, v["observer_error_rate"], rng)
    acc = accuracy_assessment(obs, going)
    dem_cp, dem_sum = dem_checkpoints(world, uas, grid, v["dem_checkpoints"], v["gnss_checkpoint_sigma_m"], rng)
    agree_full = float((truth == np.where(going == RECCE, truth, going)).mean())
    return truth, obs, acc, dem_cp, dem_sum, agree_full, tl


@step("Sensitivity analysis of illustrative thresholds")
def sensitivity(layers, R, crit, cfg, grid):
    base = crit["profiles"][cfg["vehicle_profile"]]
    season = crit["seasons"][cfg["primary_season"]]
    L = dict(layers, raster_features=R)
    rows = []
    variants = [("baseline", {}, {}),
                ("slope limits -5 deg", {"slope_slow_go_deg": base["slope_slow_go_deg"] - 5,
                                         "slope_no_go_deg": base["slope_no_go_deg"] - 5}, {}),
                ("slope limits +5 deg", {"slope_slow_go_deg": base["slope_slow_go_deg"] + 5,
                                         "slope_no_go_deg": base["slope_no_go_deg"] + 5}, {}),
                ("TWI thresholds -1", {}, {"twi_slow_go": season["twi_slow_go"] - 1, "twi_recce": season["twi_recce"] - 1}),
                ("TWI thresholds +1", {}, {"twi_slow_go": season["twi_slow_go"] + 1, "twi_recce": season["twi_recce"] + 1})]
    for name, pmod, smod in variants:
        g, _ = classify_going(L, dict(base, **pmod), dict(season, **smod), crit,
                              int(crit["generalisation"]["min_mapping_unit_m2"]))
        rows.append({"variant": name, **{CLASS_NAMES[c]: round(100 * (g == c).mean(), 1)
                                         for c in (GO, SLOW_GO, NO_GO, RECCE)}})
    return pd.DataFrame(rows)


def polygonise(arr, grid, names, field="class"):
    recs = []
    for geom, val in rfeatures.shapes(arr.astype("int32"), transform=grid.transform):
        if val == 0:
            continue
        s = shape(geom)
        recs.append({field + "_code": int(val), field: names.get(int(val), str(val)), "area_m2": round(s.area, 1),
                     "geometry": s})
    return gpd.GeoDataFrame(recs, geometry="geometry", crs=grid.crs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--season", choices=["dry", "wet"])
    ap.add_argument("--profile", choices=["wheeled_4x4", "tracked"])
    ap.add_argument("--out", default=str(ROOT / "outputs"))
    args = ap.parse_args()

    t0 = time.time()
    cfg, crit = load_config(args)
    out = Path(args.out)
    for sub in ("rasters", "vector", "maps", "reports", "metadata", "mission"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    grid = Grid.from_config(cfg)
    rng = np.random.default_rng(cfg["random_seed"] + 7)
    profile_name, season_name = cfg["vehicle_profile"], cfg["primary_season"]
    profile, season = crit["profiles"][profile_name], crit["seasons"][season_name]

    world = make_world(grid, cfg)
    survey_d, plan = survey_planning(grid, world, out)
    uas = make_uas(world, grid, cfg)
    layers = derive_layers(uas, grid, crit, profile)
    R = rasterise_features(uas["digitised"], grid, crit["data_confidence"]["stream_bank_buffer_m"])
    variants = classify_all(layers, R, crit, cfg, grid, uas)
    going, reason = variants[(profile_name, season_name)]

    truth, obs, acc, dem_cp, dem_sum, agree_full, tl = truth_and_validation(world, grid, crit, cfg, going, uas, rng)

    op = cfg["observation_point"]
    visible = step("Line-of-sight from OP SIERRA")(viewshed)(
        uas["dsm"], uas["dtm"], grid, (op["row"], op["col"]), op["observer_height_m"], op["target_height_m"],
        op["max_range_m"])

    sp = cfg["nominated_points"]["SP_ALPHA"]; ob = cfg["nominated_points"]["OBJ_BRAVO"]
    routes, speed = step("Route generation and comparison")(generate_routes)(
        going, R, layers["slope"], visible, profile, grid, (sp["row"], sp["col"]), (ob["row"], ob["col"]),
        crit["route_weights"])
    sens = sensitivity(layers, R, crit, cfg, grid)

    # ------------------------------------------------------------------ exports
    @step("Export rasters, GeoPackage terrain database and metadata")
    def export():
        rd = out / "rasters"
        cmap = {0: (0, 0, 0, 0), **{c: hex_to_rgba(CLASS_COLOURS[c]) for c in (GO, SLOW_GO, NO_GO, RECCE)}}
        products = [
            ("orthomosaic_rgb.tif", uas["ortho"], None, "UAS RGB orthomosaic (simulated, 1 m)", ["Red", "Green", "Blue"], None),
            ("dsm.tif", uas["dsm"], -9999.0, "Digital Surface Model (m)", None, None),
            ("dtm.tif", uas["dtm"], -9999.0, "Digital Terrain Model - bare earth (m)", None, None),
            ("chm.tif", uas["chm"], -9999.0, "Canopy/feature height model DSM-DTM (m)", None, None),
            ("hillshade.tif", (maps.hillshade(uas["dtm"]) * 255).astype("uint8"), None, "Hillshade 315/45", None, None),
            ("slope_deg.tif", layers["slope"], -9999.0, "Slope (degrees, 2 m baseline)", None, None),
            ("twi.tif", layers["twi"], -9999.0, "Topographic Wetness Index", None, None),
            ("flow_accumulation_m2.tif", layers["flow_acc"], -9999.0, "D8 flow accumulation (m2)", None, None),
            ("vari.tif", layers["vari"], -9999.0, "Visible Atmospherically Resistant Index", None, None),
            ("canopy_cover.tif", layers["cover"], -9999.0, "Canopy cover fraction (15 m window)", None, None),
            ("vegetation_class.tif", layers["veg"], 255, "0 open,1 scrub,2 light wood,3 dense wood", None, None),
            ("data_confidence.tif", uas["confidence"], -9999.0, "Ground-visibility confidence 0-1", None, None),
            ("going_class.tif", going, 0, f"GOING class {profile_name}/{season_name}: 1 GO 2 SLOW-GO 3 NO-GO 4 RECCE", None, cmap),
            ("going_reason.tif", reason, None, "Rule that determined the GOING class (see reports/reason_codes.csv)", None, None),
            ("going_wheeled_dry.tif", variants[("wheeled_4x4", "dry")][0], 0, "GOING wheeled dry", None, cmap),
            ("going_wheeled_wet.tif", variants[("wheeled_4x4", "wet")][0], 0, "GOING wheeled wet", None, cmap),
            ("going_tracked_wet.tif", variants[("tracked", "wet")][0], 0, "GOING tracked wet", None, cmap),
            ("speed_kmh.tif", speed, -9999.0, "Illustrative cross-country speed (km/h)", None, None),
            ("viewshed_op_sierra.tif", visible.astype("uint8"), 255, "1 = visible from OP SIERRA", None, None),
        ]
        records = []
        for fn, arr, nd, desc, bands, cm in products:
            p = gio.write_raster(rd / fn, arr, grid, nodata=nd, description=desc, band_names=bands, colormap=cm)
            records.append(gio.metadata_record(
                p, desc, desc + ". Part of the AOI KESTREL rapid terrain package.",
                ["Synthetic world generated (going.synth)", "UAS survey + SfM photogrammetry simulated (going.uas)",
                 "Derived/classified by going pipeline using config/going_criteria.json"], grid, cfg,
                accuracy=f"DTM RMSEz non-veg {dem_sum['non-vegetated']['rmse_z_m']} m; veg "
                         f"{dem_sum['vegetated']['rmse_z_m']} m; RMSEr {dem_sum['horizontal']['rmse_r_m']} m",
                keywords=["terrain", "GOING", "UAS", "trafficability"], criteria_version=crit.get("version")))

        going_poly = polygonise(going, grid, CLASS_NAMES, "going")
        aoi = gpd.GeoDataFrame([{"name": cfg["project"]["aoi_name"], "area_km2": grid.bounds_polygon.area / 1e6}],
                               geometry=[grid.bounds_polygon], crs=grid.crs)
        pts = gpd.GeoDataFrame([{"name": k, "description": v["description"]} for k, v in cfg["nominated_points"].items()]
                               + [{"name": op["name"], "description": op["note"]}],
                               geometry=[Point(*grid.rc_to_xy(v["row"], v["col"])) for v in cfg["nominated_points"].values()]
                               + [Point(*grid.rc_to_xy(op["row"], op["col"]))], crs=grid.crs)
        D = uas["digitised"]
        layers_out = {
            "aoi": aoi, "nominated_points": pts,
            "roads": D["roads"], "streams": D["streams"], "drainage_derived": layers["drainage"],
            "water_bodies": D["water_bodies"], "marsh": D["marsh"], "fields": D["fields"],
            "buildings": D["buildings"], "built_up": D["built_up"], "quarry": D["quarry"],
            "linear_obstacles": D["linear_obstacles"], "crossings": D["crossings"].drop(
                columns=["true_mlc", "true_depth_m"], errors="ignore"),
            "vertical_obstructions": D["pylons"], "powerline": D["powerline"],
            "going_polygons": going_poly, "routes": routes,
            "viewshed_op_sierra": polygonise(visible.astype("uint8"), grid, {1: "visible"}, "los"),
            "validation_points": obs.drop(columns=["map_code", "obs_code"]),
            "dem_checkpoints": dem_cp, "gcps": plan["gcps"], "flight_lines": plan["flight_lines"],
            "photo_centres": plan["photo_centres"],
        }
        gp = gio.write_gpkg(out / "vector/terrain_db.gpkg", layers_out)
        records.append(gio.metadata_record(gp, "AOI KESTREL terrain database",
                                           "Unified GeoPackage: " + ", ".join(layers_out), ["Digitised from simulated "
                                           "orthomosaic; derived layers from going pipeline"], grid, cfg,
                                           product_type="vector", keywords=["terrain database", "GeoPackage"],
                                           criteria_version=crit.get("version")))
        gio.write_metadata(out / "metadata", records)
        return going_poly

    export()

    # ------------------------------------------------------------------ reports
    @step("Write reports (route comparison, validation, statistics)")
    def reports():
        rp = out / "reports"
        r = routes.drop(columns="geometry")
        r.to_csv(rp / "route_comparison.csv", index=False)
        acc["confusion_matrix"].to_csv(rp / "confusion_matrix.csv")
        acc["per_class"].to_csv(rp / "per_class_accuracy.csv", index=False)
        dem_cp.drop(columns="geometry").to_csv(rp / "dem_checkpoints.csv", index=False)
        sens.to_csv(rp / "sensitivity_analysis.csv", index=False)
        pd.DataFrame([{"code": k, "reason": v} for k, v in REASONS.items()]).to_csv(rp / "reason_codes.csv", index=False)
        area = []
        for (p, s), (g, _) in variants.items():
            area.append({"profile": p, "season": s, **{CLASS_NAMES[c] + " %": round(100 * (g == c).mean(), 1)
                                                       for c in (GO, SLOW_GO, NO_GO, RECCE)}})
        pd.DataFrame(area).to_csv(rp / "class_area_statistics.csv", index=False)
        rc = pd.Series(reason.ravel()).value_counts()
        reasons_tbl = pd.DataFrame({"reason": [REASONS.get(int(k), str(k)) for k in rc.index],
                                    "area_pct": (100 * rc.values / reason.size).round(2)})
        summary = {
            "aoi": cfg["project"]["aoi_name"], "profile": profile_name, "season": season_name,
            "survey": {k: survey_d[k] for k in ("gsd_cm", "line_spacing_m", "trigger_distance_m", "n_lines",
                                                 "total_images", "flight_time_min", "sorties")},
            "dem_accuracy": dem_sum,
            "classification": {"overall_accuracy": acc["overall_accuracy"], "oa_95ci": acc["oa_95ci"],
                               "kappa": acc["kappa"], "area_weighted_oa": acc["area_weighted_oa"],
                               "recce_resolution": acc["recce_resolution"],
                               "recce_flag_efficiency": acc["recce_flag_efficiency"],
                               "unsafe_commission_points": acc["unsafe_commission"],
                               "wall_to_wall_agreement_excl_recce": round(agree_full, 3)},
            "routes": r[["route", "length_m", "est_time_min", "pct_RECCE", "pct_exposed_to_OP", "weighted_score",
                         "rank"]].to_dict("records"),
            "processing_log": LOG, "runtime_s": round(time.time() - t0, 1),
        }
        (rp / "run_summary.json").write_text(json.dumps(summary, indent=2, default=str))
        _validation_markdown(rp / "VALIDATION_REPORT.md", acc, dem_sum, dem_cp, sens, agree_full, cfg, crit,
                             profile_name, season_name, obs, reasons_tbl, world, uas)
        _route_markdown(rp / "ROUTE_ASSESSMENT.md", r, profile_name, season_name, crit)
        return summary

    summary = reports()

    # ------------------------------------------------------------------ maps
    @step("Produce map products (PNG)")
    def make_maps():
        md = out / "maps"
        ctx = {"grid": grid, "uas": uas, "layers": layers, "features": world["features"], "digitised": uas["digitised"],
               "profile": profile, "profile_name": profile_name, "season": season, "season_name": season_name,
               "criteria": crit, "going": going, "visible": visible, "survey": survey_d, "plan": plan,
               "ref_dem": world["dtm"], "op_xy": tuple(float(v) for v in grid.rc_to_xy(op["row"], op["col"])),
               "points_xy": {k.replace("_", " "): tuple(float(v) for v in grid.rc_to_xy(p["row"], p["col"]))
                             for k, p in cfg["nominated_points"].items()}}
        maps.survey_plan_map(ctx, md / "01_survey_plan.png")
        maps.ortho_map(ctx, md / "02_orthomosaic.png")
        maps.dem_map(ctx, md / "03_dtm_hillshade_contours.png")
        maps.slope_map(ctx, md / "04_slope_classes.png")
        maps.drainage_map(ctx, md / "05_drainage_wetness.png")
        maps.vegetation_map(ctx, md / "06_vegetation_structure.png")
        maps.obstacle_map(ctx, md / "07_obstacle_overlay.png")
        maps.confidence_map(ctx, md / "08_data_confidence.png")
        maps.going_map(ctx, going, md / "09_going_classification.png",
                       "TERRAIN TRAFFICABILITY (GOING) MAP - AOI KESTREL",
                       f"Vehicle profile: {profile_name}  |  Season: {season_name}  |  MMU "
                       f"{crit['generalisation']['min_mapping_unit_m2']} m2", "PRD-09G",
                       [f"Validation OA {acc['overall_accuracy']:.0%}", f"kappa {acc['kappa']:.2f} (simulated)", ""])
        maps.going_comparison(ctx, {"Wheeled - DRY": variants[("wheeled_4x4", "dry")][0],
                                    "Wheeled - WET": variants[("wheeled_4x4", "wet")][0],
                                    "Tracked - WET": variants[("tracked", "wet")][0]},
                              md / "10_going_season_profile_comparison.png")
        maps.viewshed_map(ctx, md / "11_line_of_sight_op_sierra.png")
        maps.route_map(ctx, routes, md / "12_route_comparison.png")
        maps.route_chart(routes, md / "13_route_metrics.png")
        maps.validation_map(ctx, obs, md / "14_validation_points.png")
        maps.confusion_figure(acc, dem_sum, dem_cp, md / "15_accuracy_assessment.png")

    make_maps()
    summary["processing_log"] = LOG
    summary["runtime_s"] = round(time.time() - t0, 1)
    (out / "reports/run_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (out / "reports/processing_log.json").write_text(json.dumps(LOG, indent=2))
    print(f"\nDone in {time.time() - t0:.1f} s. Outputs in {out}")
    print(json.dumps(summary["classification"], indent=2, default=str))
    print(routes.drop(columns=["geometry", "definition"]).to_string(index=False))


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def _validation_markdown(path, acc, dem_sum, dem_cp, sens, agree_full, cfg, crit, prof, season, obs, reasons_tbl,
                         world, uas):
    cm = acc["confusion_matrix"].copy()
    cm.insert(0, "Mapped \\ Observed", cm.index)
    dem_tbl = pd.DataFrame([{"Stratum": k, **v} for k, v in dem_sum.items() if k != "horizontal"])
    missed = sorted(set(world["features"]["linear_obstacles"].obs_id) - set(uas["digitised"]["linear_obstacles"].obs_id))
    rr = acc["recce_resolution"]
    text = f"""# Validation and Accuracy Assessment Report - AOI KESTREL

**{cfg['project']['marking']}**

> **Status of these results: SIMULATED.** The reference observations below were generated from a hidden
> "ground truth" model (true terrain, soil wetness, understorey density and crossing capacities that the
> UAS could not see). The *method* is real and transferable; the *numbers* only show how the method behaves.
> They are not evidence of how accurate the approach would be on real ground.

Product assessed: `rasters/going_class.tif` (profile `{prof}`, season `{season}`). Generated automatically by
`run_pipeline.py`. Re-running with the same configuration reproduces these figures exactly (fixed seed).

## 1. Elevation model accuracy (independent check points)

{len(dem_cp)} independent check points (ICPs, *not* used as GCPs) were "surveyed" by simulated GNSS RTK
(sigma {cfg['validation']['gnss_checkpoint_sigma_m']} m) and split into non-vegetated and vegetated strata,
following the ASPRS Positional Accuracy Standards (2023) reporting convention.

{_md_table(dem_tbl)}

Horizontal (orthomosaic) accuracy: RMSEr = {dem_sum['horizontal']['rmse_r_m']} m, CE95 = {dem_sum['horizontal']['ce95_m']} m.

**Interpretation.** The non-vegetated vertical accuracy is consistent with a GCP-controlled RGB survey at
~2.7 cm GSD. Under canopy the photogrammetric DTM is interpolated rather than observed. Its error is an order of
magnitude larger and positively biased (ground modelled too high), so slopes inside woodland are unreliable.
This is why canopy areas carry low data-confidence values.

## 2. GOING classification accuracy

* Design: stratified random sampling by **map class**, {cfg['validation']['samples_per_class']} points per class,
  minimum spacing {cfg['validation']['min_spacing_m']} m (total {len(obs)} points).
* Reference: simulated patrol observation (handheld GNSS error ~3 m; observer error rate
  {cfg['validation']['observer_error_rate']:.0%} between adjacent classes).
* REQUIRES RECCE is an *information* state, not a terrain state. Its points are reported separately to show
  what the ground actually was. They are excluded from overall accuracy.

### Confusion matrix (counts)

{_md_table(cm)}

| Metric | Value |
|---|---|
| Overall accuracy (determinate classes) | **{acc['overall_accuracy']:.1%}** (95% CI {acc['oa_95ci']}) |
| Cohen's kappa | {acc['kappa']:.3f} |
| Area-weighted overall accuracy (Olofsson et al. 2014) | {acc['area_weighted_oa']:.1%} |
| Wall-to-wall agreement with truth model (excl. RECCE cells) | {agree_full:.1%} |
| Safety-critical errors (mapped GO/SLOW-GO, actually NO-GO) | {acc['unsafe_commission']} points |
| RECCE points that were in fact SLOW-GO or NO-GO ("flag efficiency") | {acc['recce_flag_efficiency']:.0%} |

### Per-class accuracy

{_md_table(acc['per_class'])}

### What the RECCE points turned out to be

GO: {rr.get('GO', 0)}, SLOW-GO: {rr.get('SLOW-GO', 0)}, NO-GO: {rr.get('NO-GO', 0)}.
Flagging is working when a high share of RECCE points proves to be problematic ground. A low share means
the flag is too cautious and is spending reconnaissance effort on ground that would have been GO.

## 3. Sensitivity of the class areas to the illustrative thresholds (% of AOI)

{_md_table(sens)}

The class areas move noticeably when thresholds shift by plus or minus 5 degrees, or when the wetness
threshold shifts by plus or minus 1 TWI unit. Thresholds must therefore be set from vehicle-specific data and
doctrine, and recorded in the product metadata.

## 4. Contribution of each rule to the map (% of AOI)

{_md_table(reasons_tbl)}

## 5. Known error sources and accuracy limitations

1. **Canopy occlusion.** RGB photogrammetry cannot see the ground under closed canopy, stem spacing or
   undergrowth. Dense understorey in "light" woodland is the largest source of GO/SLOW-GO versus NO-GO
   confusion. Linear obstacles under canopy were missed: {', '.join(missed) if missed else 'none'}.
2. **Soil strength is not observable from imagery.** TWI is a topographic proxy for wetness and does not
   measure bearing capacity, so soft ground away from drainage lines is under-predicted.
3. **Water.** Photogrammetry produces voids over water. Stream depth, bed material, bank height under
   vegetation and bridge classification (MLC) cannot be derived and are always flagged for reconnaissance.
4. **Temporal validity.** The product describes the conditions at capture date only (see
   docs/06_TERRAIN_SEASONALITY.md).
5. **Generalisation.** A minimum mapping unit of {crit['generalisation']['min_mapping_unit_m2']} m2 removes
   small patches. Narrow linear obstacles are burned back in after generalisation, but gaps narrower than
   about 2 m may still be closed.
6. **Reference data quality.** Ground observations have their own positional and judgement errors, and
   handheld GNSS error near class boundaries produces apparent disagreement.
7. **Sample size.** With {cfg['validation']['samples_per_class']} points per class, the 95% confidence
   intervals on per-class accuracy are roughly plus or minus 10-14 percentage points.

## 6. Recommendation

Release the product as **"UAS-derived, partially validated"**. All REQUIRES RECCE areas on selected routes,
and all woodland, must be checked on the ground before being relied upon for movement.
"""
    path.write_text(text)


def _route_markdown(path, r, prof, season, crit):
    best = r.sort_values("rank").iloc[0]
    w = crit["route_weights"]
    cols = ["route", "length_m", "est_time_min", "avg_speed_kmh", "pct_GO", "pct_SLOW_GO", "pct_RECCE",
            "pct_on_road_track", "max_slope_deg", "recce_sections", "water_crossings", "pct_exposed_to_OP",
            "risk_index", "weighted_score", "rank"]
    text = f"""# Illustrative Mobility Assessment - Route Comparison (SP ALPHA to OBJ BRAVO)

**UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA**

Profile `{prof}`, season `{season}`. Routes are least-cost paths across `going_class.tif` and
`speed_kmh.tif`, with 8-connected moves, computed with the cost definitions below.

| Route | Definition |
|---|---|
""" + "\n".join(f"| {a} | {b} |" for a, b in zip(r.route, r.definition)) + f"""

## Metrics

{_md_table(r[cols])}

Weighted score (0 = best) = {w['time']} x time + {w['risk']} x risk + {w['exposure']} x exposure +
{w['crossings']} x crossings. Each term is min-max normalised across the candidate routes, and the risk index is
%RECCE + 0.5 x %SLOW-GO + 10 x number of RECCE sections.

## Assessment

* Highest-ranked route under these illustrative weights: **{best.route}**
  ({best.length_m:.0f} m, about {best.est_time_min} min, {best.pct_RECCE}% on unverified ground,
  {best.pct_exposed_to_OP}% exposed to OP SIERRA).
* Any route with RECCE sections, especially crossings at FORD F1 or BRIDGE B1, should not be committed to
  until engineer or patrol reconnaissance confirms ford depth, bed and banks, or bridge classification.
* The weights express the commander's priorities. Changing them changes the ranking. The tool supports the
  decision but does not make it.
* Transit times use an illustrative speed table and exclude halts, obstacle breaching, navigation errors and
  the effects of enemy action.
"""
    path.write_text(text)


if __name__ == "__main__":
    main()
