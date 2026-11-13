#!/usr/bin/env python3
"""Run the QGIS processing models on the pipeline products and cross-check the result.

    python3 qgis/run_models.py [--season wet|dry] [--profile wheeled_4x4|tracked]

Outputs go to outputs/qgis_model/. The GOING raster produced by the QGIS model is compared
cell-by-cell with the reference Python implementation (outputs/rasters/going_class.tif).
This is the repeatability / independent-implementation check in the validation plan.
"""
import argparse
import json

import numpy as np
from osgeo import gdal

import qgis_env

qgis_env.start()

import processing  # noqa: E402
from qgis.core import QgsProcessingFeedback, QgsProcessingModelAlgorithm  # noqa: E402

ROOT = qgis_env.PROJECT_ROOT
OUT = ROOT / "outputs"
QOUT = OUT / "qgis_model"


def load_model(name):
    m = QgsProcessingModelAlgorithm()
    if not m.fromFile(str(ROOT / "qgis/models" / name)):
        raise SystemExit("Cannot load model " + name)
    return m


class Quiet(QgsProcessingFeedback):
    def pushInfo(self, info):
        if "Class shares" in info:
            print("   ", info)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="wet", choices=["dry", "wet"])
    ap.add_argument("--profile", default="wheeled_4x4", choices=["wheeled_4x4", "tracked"])
    a = ap.parse_args()
    QOUT.mkdir(parents=True, exist_ok=True)
    R = OUT / "rasters"
    fb = Quiet()

    print("Running model: GOING terrain analysis ...")
    res = processing.run(load_model("going_terrain_analysis.model3"), {
        "DTM": str(R / "dtm.tif"), "CHM": str(R / "chm.tif"), "CONFIDENCE": str(R / "data_confidence.tif"),
        "TERRAIN_DB": str(OUT / "vector/terrain_db.gpkg"), "CRITERIA": str(ROOT / "config/going_criteria.json"),
        "PROFILE": ["wheeled_4x4", "tracked"].index(a.profile), "SEASON": ["dry", "wet"].index(a.season),
        "slope_degrees": str(QOUT / "slope_qgis.tif"),
        "topographic_wetness_index": str(QOUT / "twi_qgis.tif"),
        "going_classification_raster": str(QOUT / "going_qgis.tif"),
        "going_rule_codes": str(QOUT / "going_reason_qgis.tif"),
        "going_polygons": str(QOUT / "going_polygons_qgis.gpkg"),
        "class_area_report_html": str(QOUT / "class_report.html"),
    }, feedback=fb)
    print("   outputs:", ", ".join(sorted(res)))

    pts = json.loads((ROOT / "config/project.json").read_text())
    ds = gdal.Open(str(R / "dtm.tif"))
    gt = ds.GetGeoTransform()

    def xy(p):
        return f"{gt[0] + (p['col'] + 0.5) * gt[1]},{gt[3] + (p['row'] + 0.5) * gt[5]} [EPSG:32630]"

    print("Running model: GOING route analysis ...")
    rr = processing.run(load_model("going_route_analysis.model3"), {
        "GOING": str(QOUT / "going_qgis.tif"),
        "START": xy(pts["nominated_points"]["SP_ALPHA"]), "END": xy(pts["nominated_points"]["OBJ_BRAVO"]),
        "SPEED_GO": 18, "SPEED_SLOW_GO": 7, "SPEED_RECCE": 5,
        "route_fastest": str(QOUT / "route_fastest_qgis.gpkg"), "route_assured": str(QOUT / "route_assured_qgis.gpkg"),
    }, feedback=fb)
    print("   outputs:", ", ".join(sorted(rr)))

    q = gdal.Open(str(QOUT / "going_qgis.tif")).ReadAsArray()
    p = gdal.Open(str(R / "going_class.tif")).ReadAsArray()
    agree = float((q == p).mean())
    per = {}
    for c, n in ((1, "GO"), (2, "SLOW-GO"), (3, "NO-GO"), (4, "RECCE")):
        per[n] = {"python_pct": round(100 * float((p == c).mean()), 1), "qgis_pct": round(100 * float((q == c).mean()), 1)}
    summary = {"cell_agreement": round(agree, 4), "class_shares": per,
               "note": "Differences come from slope smoothing (5x5 mean vs Gaussian) and the TWI algorithm "
                       "(GRASS r.watershed vs the pipeline's priority-flood D8)."}
    (QOUT / "crosscheck.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
