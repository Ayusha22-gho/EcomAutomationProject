"""
QGIS Processing algorithm: GOING terrain classification (rule-based).

Install: copy into the Processing scripts folder (Processing > Toolbox > Scripts >
"Add Script to Toolbox...") or run qgis/install_qgis_tools.py. Appears as
"Scripts > Terrain analysis (GOING) > GOING terrain classification (rule-based)"
with id script:goingclassify, so it can be used in the Model Designer.

Only QGIS core libraries are used (GDAL/OGR + numpy), so it runs on a standard
QGIS LTR install on Windows, macOS and Linux.

UNCLASSIFIED // EXERCISE ONLY. Criteria are illustrative.
"""
import json
import os

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterEnum,
                       QgsProcessingParameterFile, QgsProcessingParameterNumber,
                       QgsProcessingParameterRasterDestination, QgsProcessingParameterRasterLayer)

gdal.UseExceptions()

GO, SLOW_GO, NO_GO, RECCE = 1, 2, 3, 4
PROFILES = ["wheeled_4x4", "tracked"]
SEASONS = ["dry", "wet"]

DEFAULT_CRITERIA = {
    "profiles": {
        "wheeled_4x4": {"slope_slow_go_deg": 15.0, "slope_no_go_deg": 30.0, "step_height_no_go_m": 0.6,
                        "canopy_height_tree_m": 3.0, "canopy_cover_no_go": 0.65, "scrub_height_min_m": 0.6,
                        "built_up_is_slow_go": True},
        "tracked": {"slope_slow_go_deg": 20.0, "slope_no_go_deg": 35.0, "step_height_no_go_m": 0.9,
                    "canopy_height_tree_m": 3.0, "canopy_cover_no_go": 0.80, "scrub_height_min_m": 1.5,
                    "built_up_is_slow_go": True},
    },
    "seasons": {
        "dry": {"twi_slow_go": 9.5, "twi_recce": 11.0, "cultivated_is_slow_go": False, "marsh_class": "RECCE"},
        "wet": {"twi_slow_go": 7.8, "twi_recce": 9.0, "cultivated_is_slow_go": True, "marsh_class": "NO_GO"},
    },
    "data_confidence": {"recce_below": 0.45, "stream_bank_buffer_m": 15, "stream_bank_recce_below": 0.7},
    "generalisation": {"min_mapping_unit_m2": 100},
}

COLOURS = {GO: (46, 158, 68), SLOW_GO: (242, 194, 48), NO_GO: (215, 48, 31), RECCE: (123, 79, 214)}


def box_mean(a, size):
    """Moving-window mean with an integral image (no SciPy dependency)."""
    pad = size // 2
    p = np.pad(a.astype("float64"), pad, mode="edge")
    s = np.cumsum(np.cumsum(p, 0), 1)
    s = np.pad(s, ((1, 0), (1, 0)))
    h, w = a.shape
    tot = s[size:size + h, size:size + w] - s[0:h, size:size + w] - s[size:size + h, 0:w] + s[0:h, 0:w]
    return (tot / (size * size)).astype("float32")


class GoingClassification(QgsProcessingAlgorithm):
    DTM, SLOPE, CHM, TWI, CONF = "DTM", "SLOPE", "CHM", "TWI", "CONFIDENCE"
    DB, CRITERIA, PROFILE, SEASON, MMU = "TERRAIN_DB", "CRITERIA", "PROFILE", "SEASON", "MMU"
    OUT, OUT_REASON = "OUTPUT_GOING", "OUTPUT_REASON"

    def tr(self, s):
        return QCoreApplication.translate("GoingClassification", s)

    def createInstance(self):
        return GoingClassification()

    def name(self):
        return "goingclassify"

    def displayName(self):
        return self.tr("GOING terrain classification (rule-based)")

    def group(self):
        return self.tr("Terrain analysis (GOING)")

    def groupId(self):
        return "goingterrain"

    def shortHelpString(self):
        return self.tr(
            "Classifies terrain into GO (1), SLOW-GO (2), NO-GO (3) and REQUIRES RECONNAISSANCE (4) from UAS-derived "
            "rasters (DTM, slope, canopy height, wetness index, data confidence) and the vector layers of the "
            "terrain GeoPackage (water_bodies, streams, marsh, buildings, built_up, fields, roads, linear_obstacles, "
            "crossings, vertical_obstructions). Precedence: NO-GO > RECCE > SLOW-GO > GO; roads, crossings and "
            "linear obstacles are burned in after minimum-mapping-unit generalisation. "
            "Thresholds come from the criteria JSON (config/going_criteria.json) or built-in illustrative defaults. "
            "UNCLASSIFIED // EXERCISE ONLY - illustrative criteria, not doctrine.")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.DTM, self.tr("DTM (reference grid)")))
        self.addParameter(QgsProcessingParameterRasterLayer(self.SLOPE, self.tr("Slope (degrees)")))
        self.addParameter(QgsProcessingParameterRasterLayer(self.CHM, self.tr("Canopy height model (m)")))
        self.addParameter(QgsProcessingParameterRasterLayer(self.TWI, self.tr("Topographic wetness index")))
        self.addParameter(QgsProcessingParameterRasterLayer(self.CONF, self.tr("UAS data confidence (0-1)"),
                                                            optional=True))
        self.addParameter(QgsProcessingParameterFile(self.DB, self.tr("Terrain database (GeoPackage)"),
                                                     extension="gpkg"))
        self.addParameter(QgsProcessingParameterFile(self.CRITERIA, self.tr("Criteria JSON (optional)"),
                                                     extension="json", optional=True))
        self.addParameter(QgsProcessingParameterEnum(self.PROFILE, self.tr("Vehicle profile"), PROFILES,
                                                     defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(self.SEASON, self.tr("Season"), SEASONS, defaultValue=1))
        self.addParameter(QgsProcessingParameterNumber(self.MMU, self.tr("Minimum mapping unit (m2, 0 = criteria)"),
                                                       type=QgsProcessingParameterNumber.Double, defaultValue=0,
                                                       minValue=0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT, self.tr("GOING classification")))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT_REASON, self.tr("Rule (reason) codes"),
                                                                  optional=True, createByDefault=False))

    # ------------------------------------------------------------------ helpers
    def _ref(self, layer):
        ds = gdal.Open(layer.source())
        if ds is None:
            raise QgsProcessingException("Cannot open DTM " + layer.source())
        return ds

    def _aligned(self, layer, ref, resample="bilinear"):
        gt = ref.GetGeoTransform()
        w, h = ref.RasterXSize, ref.RasterYSize
        bounds = (gt[0], gt[3] + gt[5] * h, gt[0] + gt[1] * w, gt[3])
        ds = gdal.Warp("", layer.source(), format="MEM", outputBounds=bounds, width=w, height=h,
                       dstSRS=ref.GetProjection(), resampleAlg=resample)
        band = ds.GetRasterBand(1)
        arr = band.ReadAsArray().astype("float32")
        nd = band.GetNoDataValue()
        if nd is not None:
            arr[arr == nd] = np.nan
        return arr

    def _burn(self, db, ref, layer_name, buffer_m=0.0, attr=None, attr_scale=1.0, width_attr=None,
              where=None, all_touched=True):
        w, h = ref.RasterXSize, ref.RasterYSize
        out = np.zeros((h, w), "float32")
        src = ogr.Open(db)
        lyr = src.GetLayerByName(layer_name) if src else None
        if lyr is None:
            return out
        if where:
            lyr.SetAttributeFilter(where)
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ref.GetProjection())
        mem = ogr.GetDriverByName("Memory").CreateDataSource("m")
        ml = mem.CreateLayer("b", srs, ogr.wkbUnknown)
        ml.CreateField(ogr.FieldDefn("v", ogr.OFTReal))
        for f in lyr:
            g = f.GetGeometryRef()
            if g is None:
                continue
            b = buffer_m
            if width_attr is not None:
                b = max(float(f.GetField(width_attr) or 0) / 2.0, 0.75)
            g = g.Buffer(b) if b > 0 else g.Clone()
            nf = ogr.Feature(ml.GetLayerDefn())
            nf.SetGeometry(g)
            nf.SetField("v", float(f.GetField(attr)) * attr_scale if attr else 1.0)
            ml.CreateFeature(nf)
        tgt = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Float32)
        tgt.SetGeoTransform(ref.GetGeoTransform())
        tgt.SetProjection(ref.GetProjection())
        opts = ["ATTRIBUTE=v"] + (["ALL_TOUCHED=TRUE"] if all_touched else [])
        gdal.RasterizeLayer(tgt, [1], ml, options=opts)
        return tgt.GetRasterBand(1).ReadAsArray()

    def _write(self, path, arr, ref, dtype, nodata=None, colours=None):
        drv = gdal.GetDriverByName("GTiff")
        ds = drv.Create(path, ref.RasterXSize, ref.RasterYSize, 1, dtype, ["COMPRESS=DEFLATE", "TILED=YES"])
        ds.SetGeoTransform(ref.GetGeoTransform())
        ds.SetProjection(ref.GetProjection())
        b = ds.GetRasterBand(1)
        if colours:
            ct = gdal.ColorTable()
            for k, c in colours.items():
                ct.SetColorEntry(k, c + (255,))
            b.SetRasterColorTable(ct)
        if nodata is not None:
            b.SetNoDataValue(nodata)
        b.WriteArray(arr)
        ds.SetMetadataItem("MARKING", "UNCLASSIFIED // EXERCISE ONLY")
        ds.FlushCache()
        return ds

    # ------------------------------------------------------------------ main
    def processAlgorithm(self, parameters, context, feedback):
        dtm_l = self.parameterAsRasterLayer(parameters, self.DTM, context)
        ref = self._ref(dtm_l)
        res = abs(ref.GetGeoTransform()[1])
        crit_path = self.parameterAsFile(parameters, self.CRITERIA, context)
        crit = DEFAULT_CRITERIA
        if crit_path and os.path.exists(crit_path):
            with open(crit_path) as f:
                crit = json.load(f)
        P = crit["profiles"][PROFILES[self.parameterAsEnum(parameters, self.PROFILE, context)]]
        S = crit["seasons"][SEASONS[self.parameterAsEnum(parameters, self.SEASON, context)]]
        DC = crit["data_confidence"]
        mmu_m2 = self.parameterAsDouble(parameters, self.MMU, context) or crit["generalisation"]["min_mapping_unit_m2"]
        db = self.parameterAsFile(parameters, self.DB, context)

        feedback.pushInfo("Reading rasters on the DTM grid ...")
        slope = np.nan_to_num(self._aligned(self.parameterAsRasterLayer(parameters, self.SLOPE, context), ref))
        chm = np.nan_to_num(self._aligned(self.parameterAsRasterLayer(parameters, self.CHM, context), ref))
        twi = np.nan_to_num(self._aligned(self.parameterAsRasterLayer(parameters, self.TWI, context), ref))
        conf_l = self.parameterAsRasterLayer(parameters, self.CONF, context)
        conf = np.nan_to_num(self._aligned(conf_l, ref), nan=1.0) if conf_l else np.ones_like(slope)
        feedback.setProgress(20)

        feedback.pushInfo("Burning terrain database layers ...")
        water = (self._burn(db, ref, "water_bodies") + self._burn(db, ref, "streams", 4.0)) > 0
        marsh = self._burn(db, ref, "marsh") > 0
        building = self._burn(db, ref, "buildings", all_touched=False) > 0
        built_up = self._burn(db, ref, "built_up") > 0
        cultivated = self._burn(db, ref, "fields") > 0
        road = self._burn(db, ref, "roads", 3.5, where="surface = 'paved'") > 0
        track = self._burn(db, ref, "roads", 2.0, where="surface = 'unpaved'") > 0
        crossing = self._burn(db, ref, "crossings", 9.0) > 0
        stream_zone = self._burn(db, ref, "streams", float(DC.get("stream_bank_buffer_m", 15))) > 0
        pylon = self._burn(db, ref, "vertical_obstructions", 3.0) > 0
        lin_h = self._burn(db, ref, "linear_obstacles", attr="height_or_depth_m", width_attr="width_m")
        feedback.setProgress(50)

        cell = max(1, int(round(1.0 / res)))
        cover = box_mean(chm >= P["canopy_height_tree_m"], 15 * cell)
        scrub = box_mean(chm >= P["scrub_height_min_m"], 5 * cell) > 0.4
        veg = np.zeros(chm.shape, "uint8")
        veg[scrub] = 1
        veg[cover >= 0.2] = 2
        veg[cover >= P["canopy_cover_no_go"]] = 3

        cls = np.full(slope.shape, GO, "uint8")
        reason = np.zeros(slope.shape, "uint8")

        def put(mask, value, why):
            cls[mask] = value
            reason[mask] = why

        flat = slope < 5.0
        if S["cultivated_is_slow_go"]:
            put(cultivated, SLOW_GO, 10)
        if P["built_up_is_slow_go"]:
            put(built_up, SLOW_GO, 11)
        put(veg == 1, SLOW_GO, 12)
        put(veg == 2, SLOW_GO, 13)
        put((twi >= S["twi_slow_go"]) & flat, SLOW_GO, 14)
        put(slope >= P["slope_slow_go_deg"], SLOW_GO, 15)
        put((twi >= S["twi_recce"]) & (slope < 3.0), RECCE, 20)
        put(conf < DC["recce_below"], RECCE, 21)
        put(stream_zone & (conf < DC.get("stream_bank_recce_below", 0.7)), RECCE, 24)
        if S["marsh_class"] == "RECCE":
            put(marsh, RECCE, 22)
        put(slope >= P["slope_no_go_deg"], NO_GO, 30)
        put(veg == 3, NO_GO, 31)
        if S["marsh_class"] == "NO_GO":
            put(marsh, NO_GO, 32)
        put(water, NO_GO, 33)
        put(building, NO_GO, 34)

        mmu_px = int(round(mmu_m2 / (res * res)))
        if mmu_px > 1:
            feedback.pushInfo(f"Generalising to MMU {mmu_m2} m2 ({mmu_px} cells) ...")
            src = gdal.GetDriverByName("MEM").Create("", ref.RasterXSize, ref.RasterYSize, 1, gdal.GDT_Byte)
            src.GetRasterBand(1).WriteArray(cls)
            dst = gdal.GetDriverByName("MEM").Create("", ref.RasterXSize, ref.RasterYSize, 1, gdal.GDT_Byte)
            gdal.SieveFilter(src.GetRasterBand(1), None, dst.GetRasterBand(1), mmu_px, 8)
            sieved = dst.GetRasterBand(1).ReadAsArray()
            reason[sieved != cls] = 90
            cls = sieved.astype("uint8")

        put((lin_h > 0.3) & (lin_h < P["step_height_no_go_m"]), SLOW_GO, 16)
        put(lin_h >= P["step_height_no_go_m"], NO_GO, 35)
        put(pylon, NO_GO, 36)
        put(track & ~water, GO, 1)
        put(road & ~water, GO, 2)
        put(crossing & (water | road | track), RECCE, 23)
        feedback.setProgress(90)

        out = self.parameterAsOutputLayer(parameters, self.OUT, context)
        self._write(out, cls, ref, gdal.GDT_Byte, 0, COLOURS)
        results = {self.OUT: out}
        out_r = self.parameterAsOutputLayer(parameters, self.OUT_REASON, context)
        if out_r:
            self._write(out_r, reason, ref, gdal.GDT_Byte)
            results[self.OUT_REASON] = out_r
        tot = cls.size
        feedback.pushInfo("Class shares: " + ", ".join(
            f"{n} {100 * (cls == c).sum() / tot:.1f}%" for c, n in
            ((GO, "GO"), (SLOW_GO, "SLOW-GO"), (NO_GO, "NO-GO"), (RECCE, "RECCE"))))
        return results
