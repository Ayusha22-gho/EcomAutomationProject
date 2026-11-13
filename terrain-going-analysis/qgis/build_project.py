#!/usr/bin/env python3
"""Assemble the styled QGIS project and export the print layouts.

    python3 qgis/build_project.py

Creates outputs/AOI_KESTREL_GOING.qgz (relative paths, opens on any machine that has the
outputs folder), saves reusable QML styles to qgis/styles/, and exports two A3 layouts
(GOING map, route comparison) to outputs/qgis_layouts/ as PDF and PNG.
"""
import json

import qgis_env

qgis_env.start()

from qgis.PyQt.QtCore import QPointF  # noqa: E402
from qgis.PyQt.QtGui import QColor, QFont  # noqa: E402
from qgis.core import (QgsCategorizedSymbolRenderer, QgsColorRampShader, QgsCoordinateReferenceSystem,  # noqa: E402
                       QgsFillSymbol, QgsLayerTreeGroup, QgsLayoutExporter, QgsLayoutItemLabel,
                       QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemMapGrid, QgsLayoutItemPicture,
                       QgsLayoutItemScaleBar, QgsLayoutPoint, QgsLayoutSize, QgsLineSymbol, QgsMarkerSymbol,
                       QgsPalLayerSettings, QgsPalettedRasterRenderer, QgsPrintLayout, QgsProject,
                       QgsRasterLayer, QgsRasterShader, QgsRendererCategory, QgsSingleBandPseudoColorRenderer,
                       QgsSingleSymbolRenderer, QgsTextFormat, QgsUnitTypes, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling, QgsLayoutItemAttributeTable, QgsLayoutFrame,
                       QgsApplication, QgsLinePatternFillSymbolLayer)

ROOT = qgis_env.PROJECT_ROOT
OUT = ROOT / "outputs"
STYLES = qgis_env.HERE / "styles"
LAYOUTS = OUT / "qgis_layouts"
STYLES.mkdir(exist_ok=True)
LAYOUTS.mkdir(exist_ok=True)
CRIT = json.loads((ROOT / "config/going_criteria.json").read_text())
MARKING = "UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:32630"))
project.setTitle("AOI KESTREL - Rapid Terrain Mapping & GOING Analysis (Exercise TERRA SWIFT)")
project.writeEntryBool("Paths", "/Absolute", False)
root = project.layerTreeRoot()


def group(name) -> QgsLayerTreeGroup:
    return root.addGroup(name)


def raster(grp, fname, name, visible=False):
    lyr = QgsRasterLayer(str(OUT / "rasters" / fname), name)
    assert lyr.isValid(), fname
    project.addMapLayer(lyr, False)
    node = grp.addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    return lyr


def vector(grp, layer, name, visible=True):
    lyr = QgsVectorLayer(f"{OUT / 'vector/terrain_db.gpkg'}|layername={layer}", name, "ogr")
    assert lyr.isValid(), layer
    project.addMapLayer(lyr, False)
    node = grp.addLayer(lyr)
    node.setItemVisibilityChecked(visible)
    return lyr


def pseudo(lyr, stops, discrete=False):
    shader = QgsColorRampShader()
    shader.setColorRampType(QgsColorRampShader.Discrete if discrete else QgsColorRampShader.Interpolated)
    shader.setColorRampItemList([QgsColorRampShader.ColorRampItem(v, QColor(c), lab) for v, c, lab in stops])
    rs = QgsRasterShader()
    rs.setRasterShaderFunction(shader)
    lyr.setRenderer(QgsSingleBandPseudoColorRenderer(lyr.dataProvider(), 1, rs))


def categorized(lyr, field, cats, geom="line", label_field=None, size=0.6):
    out = []
    for value, colour, label in cats:
        if geom == "line":
            sym = QgsLineSymbol.createSimple({"color": colour, "width": str(size)})
        elif geom == "point":
            sym = QgsMarkerSymbol.createSimple({"color": colour, "size": str(size), "outline_color": "black"})
        else:
            sym = QgsFillSymbol.createSimple({"color": colour, "outline_color": "#333333"})
        out.append(QgsRendererCategory(value, sym, label))
    lyr.setRenderer(QgsCategorizedSymbolRenderer(field, out))
    if label_field:
        label(lyr, label_field)


def single(lyr, sym):
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))


def label(lyr, field, size=8, colour="black"):
    s = QgsPalLayerSettings()
    s.fieldName = field
    fmt = QgsTextFormat()
    fmt.setFont(QFont("Sans", size, QFont.Bold))
    fmt.setSize(size)
    fmt.setColor(QColor(colour))
    buf = fmt.buffer()
    buf.setEnabled(True)
    buf.setSize(0.8)
    buf.setColor(QColor("white"))
    s.setFormat(fmt)
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))
    lyr.setLabelsEnabled(True)


def save_style(lyr, name):
    lyr.saveNamedStyle(str(STYLES / f"{name}.qml"))


# ----------------------------------------------------------------------------- layers
g_val = group("07 Validation")
g_mob = group("06 Mobility assessment")
g_going = group("05 GOING analysis")
g_db = group("04 Terrain database (GeoPackage)")
g_der = group("03 Terrain derivatives")
g_uas = group("02 UAS products")
g_plan = group("01 Survey planning")

obs = vector(g_val, "validation_points", "Ground observations (simulated)")
categorized(obs, "map_class", [(n, c, n) for n, c in (("GO", "#2e9e44"), ("SLOW-GO", "#f2c230"),
                                                    ("NO-GO", "#d7301f"), ("REQUIRES RECCE", "#7b4fd6"))],
            "point", size=2.4)
save_style(obs, "validation_points")
icp = vector(g_val, "dem_checkpoints", "DEM check points (ICP)", False)
single(icp, QgsMarkerSymbol.createSimple({"name": "triangle", "color": "white", "size": "3", "outline_color": "black"}))

routes = vector(g_mob, "routes", "Route options")
categorized(routes, "route", [("A-DIRECT", "#000000", "A Direct"), ("B-FASTEST", "#e41a1c", "B Fastest"),
                              ("C-ASSURED", "#1f78ff", "C Assured"), ("D-CONCEALED", "#ff7f00", "D Concealed")],
            "line", size=1.2)
save_style(routes, "routes")
pts = vector(g_mob, "nominated_points", "SP / OBJ / OP")
single(pts, QgsMarkerSymbol.createSimple({"name": "square", "color": "white", "size": "4", "outline_color": "black",
                                          "outline_width": "0.6"}))
label(pts, "name", 9)
view = vector(g_mob, "viewshed_op_sierra", "Visible from OP SIERRA")
vsym = QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#c000c0", "outline_width": "0.35"})
hatch = QgsLinePatternFillSymbolLayer()
hatch.setLineAngle(45)
hatch.setDistance(2.0)
hatch.setColor(QColor("#c000c0"))
vsym.appendSymbolLayer(hatch)
single(view, vsym)
save_style(view, "viewshed")
speed = raster(g_mob, "speed_kmh.tif", "Illustrative speed (km/h)")
pseudo(speed, [(0, "#d7301f", "0"), (7, "#f2c230", "7"), (18, "#2e9e44", "18"), (40, "#1a5e2a", "40")])

poly = vector(g_going, "going_polygons", "GOING polygons", False)
categorized(poly, "going", [(n, c, n) for n, c in (("GO", "#2e9e44"), ("SLOW-GO", "#f2c230"),
                                                 ("NO-GO", "#d7301f"), ("REQUIRES RECCE", "#7b4fd6"))], "fill")
save_style(poly, "going_polygons")
labels = CRIT["class_labels"]
for fname, name, vis in (("going_class.tif", "GOING - wheeled, wet (PRIMARY)", True),
                         ("going_wheeled_dry.tif", "GOING - wheeled, dry", False),
                         ("going_tracked_wet.tif", "GOING - tracked, wet", False)):
    gl = raster(g_going, fname, name, vis)
    classes = [QgsPalettedRasterRenderer.Class(int(k), QColor(CRIT["class_colours"][k]), v) for k, v in labels.items()]
    gl.setRenderer(QgsPalettedRasterRenderer(gl.dataProvider(), 1, classes))
    gl.setOpacity(0.85)
    if vis:
        save_style(gl, "going_class")
reason = raster(g_going, "going_reason.tif", "GOING rule codes", False)

lo = vector(g_db, "linear_obstacles", "Linear obstacles")
categorized(lo, "type", [("hedgerow", "#2d6a1f", "Hedgerow"), ("stone_wall", "#7f3b08", "Stone wall"),
                         ("ditch", "#08519c", "Ditch")], "line", size=1.0)
save_style(lo, "linear_obstacles")
cr = vector(g_db, "crossings", "Crossing sites")
single(cr, QgsMarkerSymbol.createSimple({"name": "diamond", "color": "#7b4fd6", "size": "4.5", "outline_color": "white"}))
label(cr, "name", 8, "#4b1fa6")
vo = vector(g_db, "vertical_obstructions", "Vertical obstructions (pylons)")
single(vo, QgsMarkerSymbol.createSimple({"name": "triangle", "color": "#9400d3", "size": "3.5"}))
pl = vector(g_db, "powerline", "Power line (UAS hazard)")
single(pl, QgsLineSymbol.createSimple({"color": "#9400d3", "width": "0.5", "line_style": "dash"}))
bld = vector(g_db, "buildings", "Buildings")
single(bld, QgsFillSymbol.createSimple({"color": "#333333", "outline_color": "#000000"}))
rd = vector(g_db, "roads", "Roads and tracks")
categorized(rd, "surface", [("paved", "#202020", "Paved road"), ("unpaved", "#8c5a2b", "Unpaved track")], "line", size=0.9)
save_style(rd, "roads")
st = vector(g_db, "streams", "Streams")
single(st, QgsLineSymbol.createSimple({"color": "#1f6fbf", "width": "1.0"}))
dr = vector(g_db, "drainage_derived", "Drainage (DTM-derived)", False)
single(dr, QgsLineSymbol.createSimple({"color": "#08306b", "width": "0.3"}))
wb = vector(g_db, "water_bodies", "Water bodies")
single(wb, QgsFillSymbol.createSimple({"color": "#3b7fbf", "outline_color": "#1f4e79"}))
for lyrname, nm in (("marsh", "Marsh"), ("quarry", "Quarry"), ("fields", "Cultivated fields"),
                    ("built_up", "Built-up area")):
    v = vector(g_db, lyrname, nm, False)
    single(v, QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#555555", "outline_style": "dash"}))
aoi = vector(g_db, "aoi", "AOI boundary")
single(aoi, QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "#d7301f", "outline_width": "0.8"}))

for fname, name, stops in (
        ("slope_deg.tif", "Slope (deg)", [(0, "#e8f5e0", "0"), (5, "#9fd38a", "5"), (15, "#f2c230", "15"),
                                          (30, "#d7301f", "30"), (60, "#67000d", "60")]),
        ("twi.tif", "Wetness index (TWI)", [(2, "#f7fbff", "2"), (8, "#6baed6", "8"), (12, "#08306b", "12")]),
        ("canopy_cover.tif", "Canopy cover", [(0, "#ffffe5", "0"), (0.65, "#41ab5d", "0.65"), (1, "#004529", "1")]),
        ("data_confidence.tif", "Data confidence", [(0, "#d7191c", "0"), (0.45, "#fdae61", "0.45"),
                                                    (1, "#1a9641", "1")])):
    r = raster(g_der, fname, name)
    pseudo(r, stops)
    save_style(r, fname.replace(".tif", ""))
veg = raster(g_der, "vegetation_class.tif", "Vegetation structure")
veg.setRenderer(QgsPalettedRasterRenderer(veg.dataProvider(), 1, [
    QgsPalettedRasterRenderer.Class(0, QColor("#f0f0d8"), "Open"), QgsPalettedRasterRenderer.Class(1, QColor("#c2d97a"), "Scrub"),
    QgsPalettedRasterRenderer.Class(2, QColor("#4f9a3a"), "Light woodland"),
    QgsPalettedRasterRenderer.Class(3, QColor("#0f4d1c"), "Dense woodland")]))

hs = raster(g_uas, "hillshade.tif", "Hillshade", True)
hs.setOpacity(0.35)
dtm = raster(g_uas, "dtm.tif", "DTM (bare earth)")
pseudo(dtm, [(150, "#2b83ba", "150"), (170, "#abdda4", "170"), (190, "#fdae61", "190"), (215, "#d7191c", "215")])
save_style(dtm, "dtm")
raster(g_uas, "dsm.tif", "DSM")
raster(g_uas, "chm.tif", "Canopy height model")
ortho = raster(g_uas, "orthomosaic_rgb.tif", "Orthomosaic", True)

fl = vector(g_plan, "flight_lines", "Flight lines", False)
single(fl, QgsLineSymbol.createSimple({"color": "#1f78ff", "width": "0.2"}))
pc = vector(g_plan, "photo_centres", "Photo centres", False)
single(pc, QgsMarkerSymbol.createSimple({"color": "#1f78ff", "size": "0.6"}))
gcp = vector(g_plan, "gcps", "Ground control points", False)
single(gcp, QgsMarkerSymbol.createSimple({"name": "cross2", "color": "yellow", "size": "4", "outline_color": "black"}))
label(gcp, "gcp_id", 7)
g_plan.setExpanded(False)
g_uas.setExpanded(False)
g_der.setExpanded(False)
g_db.setExpanded(False)


# ----------------------------------------------------------------------------- layouts
def text(layout, txt, x, y, w, h, size=10, bold=False, colour="black", align=None):
    it = QgsLayoutItemLabel(layout)
    it.setText(txt)
    f = QFont("Sans", size)
    f.setBold(bold)
    fmt = QgsTextFormat()
    fmt.setFont(f)
    fmt.setSize(size)
    fmt.setColor(QColor(colour))
    it.setTextFormat(fmt)
    it.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    it.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    if align is not None:
        it.setHAlign(align)
    layout.addLayoutItem(it)
    return it


def make_layout(name, title, subtitle, layers, legend_layers, table_layer=None):
    lm = project.layoutManager()
    old = lm.layoutByName(name)
    if old:
        lm.removeLayout(old)
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    page = layout.pageCollection().page(0)
    page.setPageSize("A3", page.Landscape)
    from qgis.PyQt.QtCore import Qt
    text(layout, MARKING, 0, 2, 420, 7, 11, True, "#b30000", Qt.AlignHCenter)
    text(layout, MARKING, 0, 289, 420, 7, 11, True, "#b30000", Qt.AlignHCenter)
    text(layout, title, 10, 10, 280, 10, 18, True)
    text(layout, subtitle, 10, 20, 280, 8, 10)

    mp = QgsLayoutItemMap(layout)
    mp.attemptMove(QgsLayoutPoint(22, 30, QgsUnitTypes.LayoutMillimeters))
    mp.attemptResize(QgsLayoutSize(245, 250, QgsUnitTypes.LayoutMillimeters))
    mp.setLayers(layers)
    mp.setKeepLayerSet(True)
    ext = aoi.extent()
    ext.grow(15)
    mp.zoomToExtent(ext)
    mp.setFrameEnabled(True)
    grid = QgsLayoutItemMapGrid("UTM grid", mp)
    grid.setIntervalX(200)
    grid.setIntervalY(200)
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(0)
    grid.setFrameStyle(QgsLayoutItemMapGrid.Zebra)
    grid.setGridLineColor(QColor(0, 0, 0, 90))
    for side in (QgsLayoutItemMapGrid.Right, QgsLayoutItemMapGrid.Top):
        grid.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, side)
    mp.grids().addGrid(grid)
    layout.addLayoutItem(mp)

    leg = QgsLayoutItemLegend(layout)
    leg.setTitle("LEGEND")
    leg.setLinkedMap(mp)
    leg.setAutoUpdateModel(False)
    model = leg.model().rootGroup()
    model.removeAllChildren()
    for lyr in legend_layers:
        model.addLayer(lyr)
    leg.attemptMove(QgsLayoutPoint(275, 30, QgsUnitTypes.LayoutMillimeters))
    leg.setFrameEnabled(True)
    layout.addLayoutItem(leg)

    sb = QgsLayoutItemScaleBar(layout)
    sb.setStyle("Single Box")
    sb.setLinkedMap(mp)
    sb.setUnits(QgsUnitTypes.DistanceMeters)
    sb.setUnitsPerSegment(100)
    sb.setNumberOfSegments(4)
    sb.setNumberOfSegmentsLeft(0)
    sb.setUnitLabel("m")
    sb.attemptMove(QgsLayoutPoint(275, 245, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(sb)

    na = QgsLayoutItemPicture(layout)
    na.setPicturePath(str(QgsApplication.pkgDataPath()) + "/svg/arrows/NorthArrow_02.svg")
    na.attemptMove(QgsLayoutPoint(390, 235, QgsUnitTypes.LayoutMillimeters))
    na.attemptResize(QgsLayoutSize(18, 22, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(na)

    text(layout, "Grid: EPSG:32630 (notional AOI). Source: simulated UAS survey + GIS model "
                 "(going pipeline v1.0). Criteria ILLUSTRATIVE - config/going_criteria.json. "
                 "Validate on the ground before use.", 275, 265, 135, 20, 7)
    if table_layer is not None:
        tbl = QgsLayoutItemAttributeTable.create(layout)
        tbl.setVectorLayer(table_layer)
        tbl.setDisplayedFields(["route", "length_m", "est_time_min", "pct_RECCE", "pct_exposed_to_OP", "rank"])
        layout.addMultiFrame(tbl)
        fr = QgsLayoutFrame(layout, tbl)
        fr.attemptMove(QgsLayoutPoint(275, 185, QgsUnitTypes.LayoutMillimeters))
        fr.attemptResize(QgsLayoutSize(140, 45, QgsUnitTypes.LayoutMillimeters))
        tbl.addFrame(fr)
    lm.addLayout(layout)
    exp = QgsLayoutExporter(layout)
    pdf = LAYOUTS / f"{name}.pdf"
    png = LAYOUTS / f"{name}.png"
    exp.exportToPdf(str(pdf), QgsLayoutExporter.PdfExportSettings())
    s = QgsLayoutExporter.ImageExportSettings()
    s.dpi = 110
    s.generateWorldFile = False
    s.exportMetadata = False
    exp.exportToImage(str(png), s)
    print("Exported", pdf.name, png.name)


primary = project.mapLayersByName("GOING - wheeled, wet (PRIMARY)")[0]
make_layout("GOING_MAP_A3", "TERRAIN TRAFFICABILITY (GOING) - AOI KESTREL",
            "Wheeled 4x4 profile, wet season. Produced with QGIS from the UAS terrain database.",
            [pts, cr, lo, rd, st, bld, wb, aoi, hs, primary],
            [poly, rd, st, lo, cr, pts])
make_layout("ROUTE_COMPARISON_A3", "MOBILITY ASSESSMENT - ROUTE OPTIONS SP ALPHA TO OBJ BRAVO",
            "Least-cost route options over the GOING surface; OP SIERRA line of sight shown.",
            [pts, routes, view, rd, st, aoi, hs, primary], [routes, view, poly, pts], routes)

out = OUT / "AOI_KESTREL_GOING.qgz"
project.write(str(out))
print("Wrote", out)
