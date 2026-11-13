#!/usr/bin/env python3
"""Build the QGIS Processing models (.model3) for the GOING workflow.

    python3 qgis/build_models.py

Creates:
  qgis/models/going_terrain_analysis.model3  - DTM/CHM/TWI -> GOING raster, polygons, class report
  qgis/models/going_route_analysis.model3    - GOING raster -> fastest and assured routes (GRASS r.cost/r.drain)

Both open in the Model Designer (Processing > Graphical Modeler > Open Model) and can be
run from the toolbox, in batch mode, or headless with qgis_process.
"""
from qgis.PyQt.QtCore import QPointF

import qgis_env

qgis_env.start()

from qgis.core import (QgsProcessingModelAlgorithm, QgsProcessingModelChildAlgorithm,  # noqa: E402
                       QgsProcessingModelChildParameterSource as Src, QgsProcessingModelOutput,
                       QgsProcessingModelParameter, QgsProcessingParameterEnum, QgsProcessingParameterFile,
                       QgsProcessingParameterNumber, QgsProcessingParameterPoint,
                       QgsProcessingParameterRasterLayer)

MODELS = qgis_env.HERE / "models"
MODELS.mkdir(exist_ok=True)


def add_input(model, param, x, y):
    mp = QgsProcessingModelParameter(param.name())
    mp.setPosition(QPointF(x, y))
    model.addModelParameter(param, mp)


def child(model, alg_id, cid, desc, x, y, params: dict, outputs: dict | None = None, deps=None):
    c = QgsProcessingModelChildAlgorithm(alg_id)
    c.setChildId(cid)
    c.setDescription(desc)
    c.setPosition(QPointF(x, y))
    for k, v in params.items():
        c.addParameterSources(k, v if isinstance(v, list) else [v])
    if outputs:
        outs = {}
        for child_out, (name, desc_o) in outputs.items():
            o = QgsProcessingModelOutput(name, desc_o)
            o.setChildId(cid)
            o.setChildOutputName(child_out)
            o.setPosition(QPointF(x + 160, y + 60))
            outs[name] = o
        c.setModelOutputs(outs)
    model.addChildAlgorithm(c)
    return c


def M(name):
    return Src.fromModelParameter(name)


def S(v):
    return Src.fromStaticValue(v)


def C(cid, out):
    return Src.fromChildOutput(cid, out)


def terrain_model():
    m = QgsProcessingModelAlgorithm("GOING terrain analysis", "Terrain analysis (GOING)", "goingterrainanalysis")
    m.setHelpContent({"ALG_DESC": "Automated rapid terrain analysis: smooths the UAS DTM to a vehicle-scale "
                      "baseline, derives slope and a topographic wetness index, runs the rule-based GOING "
                      "classification against the terrain GeoPackage, then vectorises and labels the result "
                      "and reports class areas. UNCLASSIFIED // EXERCISE ONLY.",
                      "ALG_CREATOR": "Course Syndicate GEO-1", "ALG_VERSION": "1.0"})
    add_input(m, QgsProcessingParameterRasterLayer("DTM", "UAS DTM (bare earth)"), 80, 60)
    add_input(m, QgsProcessingParameterRasterLayer("CHM", "Canopy height model"), 80, 160)
    add_input(m, QgsProcessingParameterRasterLayer("CONFIDENCE", "UAS data confidence", optional=True), 80, 260)
    add_input(m, QgsProcessingParameterFile("TERRAIN_DB", "Terrain database (GeoPackage)", extension="gpkg"),
              80, 360)
    add_input(m, QgsProcessingParameterFile("CRITERIA", "Criteria JSON", extension="json", optional=True),
              80, 460)
    add_input(m, QgsProcessingParameterEnum("PROFILE", "Vehicle profile", ["wheeled_4x4", "tracked"],
                                            defaultValue=0), 80, 560)
    add_input(m, QgsProcessingParameterEnum("SEASON", "Season", ["dry", "wet"], defaultValue=1), 80, 660)

    child(m, qgis_env.grass_id("r.neighbors"), "smooth_dtm", "1 Smooth DTM (5x5 mean, vehicle baseline)", 400, 60,
          {"input": M("DTM"), "method": S(0), "size": S(5), "output": S("TEMPORARY_OUTPUT")})
    child(m, "native:slope", "slope", "2 Slope (degrees)", 400, 160,
          {"INPUT": C("smooth_dtm", "output"), "Z_FACTOR": S(1.0), "OUTPUT": S("TEMPORARY_OUTPUT")},
          {"OUTPUT": ("SLOPE", "Slope (degrees)")})
    child(m, qgis_env.grass_id("r.watershed"), "hydro", "3 Flow accumulation + wetness index (r.watershed)",
          400, 280, {"elevation": M("DTM"), "threshold": S(3000), "-s": S(True),
                     "accumulation": S("TEMPORARY_OUTPUT"), "tci": S("TEMPORARY_OUTPUT"),
                     "GRASS_REGION_CELLSIZE_PARAMETER": S(2.0)},
          {"tci": ("TWI", "Topographic wetness index")})
    child(m, "script:goingclassify", "classify", "4 GOING classification (rule-based)", 700, 220,
          {"DTM": M("DTM"), "SLOPE": C("slope", "OUTPUT"), "CHM": M("CHM"), "TWI": C("hydro", "tci"),
           "CONFIDENCE": M("CONFIDENCE"), "TERRAIN_DB": M("TERRAIN_DB"), "CRITERIA": M("CRITERIA"),
           "PROFILE": M("PROFILE"), "SEASON": M("SEASON"), "MMU": S(0),
           "OUTPUT_GOING": S("TEMPORARY_OUTPUT"), "OUTPUT_REASON": S("TEMPORARY_OUTPUT")},
          {"OUTPUT_GOING": ("GOING", "GOING classification raster"),
           "OUTPUT_REASON": ("GOING_REASON", "GOING rule codes")})
    child(m, "gdal:polygonize", "polygonize", "5 Vectorise GOING classes", 1000, 160,
          {"INPUT": C("classify", "OUTPUT_GOING"), "BAND": S(1), "FIELD": S("going_code"),
           "EIGHT_CONNECTEDNESS": S(False), "OUTPUT": S("TEMPORARY_OUTPUT")})
    child(m, "native:fieldcalculator", "label", "6 Add class labels", 1000, 260,
          {"INPUT": C("polygonize", "OUTPUT"), "FIELD_NAME": S("going"), "FIELD_TYPE": S(2), "FIELD_LENGTH": S(24),
           "FIELD_PRECISION": S(0),
           "FORMULA": S("CASE WHEN \"going_code\"=1 THEN 'GO' WHEN \"going_code\"=2 THEN 'SLOW-GO' "
                        "WHEN \"going_code\"=3 THEN 'NO-GO' WHEN \"going_code\"=4 THEN 'REQUIRES RECCE' END"),
           "OUTPUT": S("TEMPORARY_OUTPUT")})
    child(m, "native:fieldcalculator", "area", "7 Polygon area (m2)", 1000, 360,
          {"INPUT": C("label", "OUTPUT"), "FIELD_NAME": S("area_m2"), "FIELD_TYPE": S(0), "FIELD_LENGTH": S(12),
           "FIELD_PRECISION": S(1), "FORMULA": S("round($area, 1)"), "OUTPUT": S("TEMPORARY_OUTPUT")},
          {"OUTPUT": ("GOING_POLYGONS", "GOING polygons")})
    child(m, "native:rasterlayeruniquevaluesreport", "report", "8 Class area report", 700, 420,
          {"INPUT": C("classify", "OUTPUT_GOING"), "BAND": S(1), "OUTPUT_HTML_FILE": S("TEMPORARY_OUTPUT")},
          {"OUTPUT_HTML_FILE": ("CLASS_REPORT", "Class area report (HTML)")})
    return m


def route_model():
    m = QgsProcessingModelAlgorithm("GOING route analysis", "Terrain analysis (GOING)", "goingrouteanalysis")
    m.setHelpContent({"ALG_DESC": "Generates a FASTEST route (REQUIRES-RECCE ground allowed at reduced speed) and "
                      "an ASSURED route (REQUIRES-RECCE ground excluded) between two nominated points across a "
                      "GOING raster, using illustrative speeds and GRASS r.cost / r.drain. NO-GO is impassable.",
                      "ALG_CREATOR": "Course Syndicate GEO-1", "ALG_VERSION": "1.0"})
    add_input(m, QgsProcessingParameterRasterLayer("GOING", "GOING classification raster"), 80, 60)
    add_input(m, QgsProcessingParameterPoint("START", "Start point (SP)"), 80, 160)
    add_input(m, QgsProcessingParameterPoint("END", "Objective / end point"), 80, 260)
    for name, val, y in (("SPEED_GO", 18, 360), ("SPEED_SLOW_GO", 7, 440), ("SPEED_RECCE", 5, 520)):
        add_input(m, QgsProcessingParameterNumber(name, f"{name.replace('SPEED_', '')} speed (km/h)",
                                                  type=QgsProcessingParameterNumber.Double, defaultValue=val,
                                                  minValue=0.1), 80, y)

    def cost_table(include_recce):
        expr = ("array(1,1,3.6/@SPEED_GO, 2,2,3.6/@SPEED_SLOW_GO" +
                (", 4,4,3.6/@SPEED_RECCE*1.5)" if include_recce else ")"))
        return Src.fromExpression(expr)

    for i, (tag, rec) in enumerate((("fastest", True), ("assured", False))):
        y = 80 + i * 300
        label = tag.upper()
        child(m, "native:reclassifybytable", f"cost_{tag}", f"{label}: cost surface (s/m), NO-GO = NoData",
              420, y, {"INPUT_RASTER": M("GOING"), "RASTER_BAND": S(1), "TABLE": cost_table(rec),
                       "NO_DATA": S(-9999), "RANGE_BOUNDARIES": S(2), "NODATA_FOR_MISSING": S(True),
                       "DATA_TYPE": S(5), "OUTPUT": S("TEMPORARY_OUTPUT")})
        child(m, qgis_env.grass_id("r.cost"), f"rcost_{tag}", f"{label}: accumulated cost (r.cost)", 720, y,
              {"input": C(f"cost_{tag}", "OUTPUT"), "start_coordinates": M("START"),
               "stop_coordinates": M("END"), "-k": S(True), "output": S("TEMPORARY_OUTPUT"),
               "outdir": S("TEMPORARY_OUTPUT")})
        child(m, qgis_env.grass_id("r.drain"), f"drain_{tag}", f"{label}: least-cost path (r.drain)", 1020, y,
              {"input": C(f"rcost_{tag}", "output"), "direction": C(f"rcost_{tag}", "outdir"),
               "start_coordinates": M("END"), "-d": S(True), "output": S("TEMPORARY_OUTPUT"),
               "drain": S("TEMPORARY_OUTPUT")})
        child(m, "native:fieldcalculator", f"len_{tag}", f"{label}: route length", 1020, y + 120,
              {"INPUT": C(f"drain_{tag}", "drain"), "FIELD_NAME": S("route"), "FIELD_TYPE": S(2),
               "FIELD_LENGTH": S(20), "FIELD_PRECISION": S(0), "FORMULA": S(f"'{label} ' || round($length) || ' m'"),
               "OUTPUT": S("TEMPORARY_OUTPUT")},
              {"OUTPUT": (f"ROUTE_{label}", f"Route {label}")})
    return m


if __name__ == "__main__":
    for model, fn in ((terrain_model(), "going_terrain_analysis.model3"),
                      (route_model(), "going_route_analysis.model3")):
        ok, errors = model.validate()
        if not ok:
            print("Validation issues for", fn, errors)
        path = MODELS / fn
        model.toFile(str(path))
        print("Wrote", path)
    qgis_env.install_scripts()
