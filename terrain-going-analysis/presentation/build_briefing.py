#!/usr/bin/env python3
"""Build the operator briefing deck (PPTX) and the workflow/architecture diagrams.

    python presentation/build_briefing.py      (run after run_pipeline.py and qgis/run_models.py)

Every number on the slides is read from outputs/reports/, so the deck always matches the
latest pipeline run.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402
from pptx.util import Emu, Inches, Pt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MAPS = OUT / "maps"
ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(exist_ok=True)
MARKING = "UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA"
NAVY = RGBColor(0x1B, 0x2A, 0x41)
RED = RGBColor(0xB3, 0x00, 0x00)
GREY = RGBColor(0x55, 0x55, 0x55)


# ----------------------------------------------------------------------------- diagrams
def _box(ax, x, y, w, h, text, fc, fs=9, ec="#1b2a41", bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, wrap=True,
            weight="bold" if bold else "normal")


def _arrow(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#1b2a41"))


def workflow_diagram(path):
    fig, ax = plt.subplots(figsize=(16, 7.6))
    ax.set_xlim(0, 16); ax.set_ylim(0, 7.6); ax.axis("off")
    phases = [
        ("1 PLAN", "#dbe9f6", ["Task & AOI\n(1 km2)", "Airspace / C-UAS\ndeconfliction", "Flight design\nGSD 2.7 cm, 80/70%",
                               "GCP / ICP layout"]),
        ("2 COLLECT", "#e3f1dc", ["Pre-flight checks", "Fly 3 sorties\n~1,500 images", "GNSS RTK GCPs\n& check points",
                                  "Field QA:\ncoverage, blur"]),
        ("3 PROCESS", "#fff2cc", ["SfM photogrammetry\n(WebODM / ODM)", "Orthomosaic", "DSM / DTM\n(ground filter)",
                                  "Accuracy report\n(RMSE at ICPs)"]),
        ("4 ANALYSE", "#fde0d2", ["Terrain DB\n(GeoPackage)", "Slope, TWI,\nvegetation, obstacles",
                                  "GOING rules\n(QGIS model)", "Routes &\nline of sight"]),
        ("5 VALIDATE", "#eadcf5", ["Stratified sample", "Ground obs\n(sim./patrol)", "Confusion matrix\nOA, kappa",
                                   "Limitations\nlog"]),
        ("6 DISSEMINATE", "#e0e0e0", ["Map layouts\n(A3 PDF)", "Metadata +\nmarking", "Operator brief",
                                      "Update cycle\n(change triggers)"]),
    ]
    w, h = 2.35, 0.95
    for i, (title, col, steps) in enumerate(phases):
        x = 0.25 + i * 2.62
        _box(ax, x, 6.45, w, 0.75, title, col, 12, bold=True)
        for j, s in enumerate(steps):
            y = 5.2 - j * 1.25
            _box(ax, x, y, w, h, s, "white" if j % 2 else col, 9)
            if j:
                _arrow(ax, x + w / 2, y + h + 0.3, x + w / 2, y + h)
        if i < len(phases) - 1:
            _arrow(ax, x + w, 6.82, x + 2.62, 6.82)
    ax.text(8, 0.18, "Feedback loop: validation findings and change triggers -> re-task survey / update criteria "
                     "(see docs/07_MAP_UPDATE_PROCEDURE.md)", ha="center", fontsize=10, style="italic")
    ax.set_title("RAPID TERRAIN MAPPING & GOING ANALYSIS - END-TO-END WORKFLOW", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def architecture_diagram(path, n_layers):
    fig, ax = plt.subplots(figsize=(16, 7.6))
    ax.set_xlim(0, 16); ax.set_ylim(0, 7.6); ax.axis("off")
    layers = [
        (6.3, "DATA ACQUISITION\nLAYER", "#dbe9f6",
         ["QGroundControl / DJI Pilot 2\n(mission .plan / KML)", "UAS + RGB camera\n(simulated in demo)",
          "GNSS RTK GCP/ICP", "Public reference data\nGLO-30 DEM, OSM, WorldCover"]),
        (4.75, "PROCESSING LAYER", "#fff2cc",
         ["WebODM / ODM\n(or Metashape / Pix4D)", "going pipeline (Python)\nsynthetic stand-in",
          "GDAL / rasterio", "GRASS (r.watershed,\nr.cost, r.drain)"]),
        (3.2, "GIS INTEGRATION\n& ANALYSIS LAYER", "#fde0d2",
         ["QGIS 3.34 LTR", f"GeoPackage terrain DB\n({n_layers} layers)", "Processing models\n(.model3) + script",
          "Criteria JSON\n(profile x season)"]),
        (1.65, "PRODUCT &\nDISSEMINATION LAYER", "#e3f1dc",
         ["GeoTIFF (COG-style)\northo, DSM, DTM, GOING", "A3 PDF layouts\nGOING, routes", "Reports: validation,\nroute assessment",
          "ISO 19115 metadata\n+ checksums"]),
    ]
    for y, title, col, items in layers:
        _box(ax, 0.2, y, 3.0, 1.2, title, col, 10, bold=True)
        for i, it in enumerate(items):
            _box(ax, 3.5 + i * 3.1, y + 0.1, 2.9, 1.0, it, "white", 9)
    for y in (6.3, 4.75, 3.2):
        _arrow(ax, 1.7, y, 1.7, y - 0.33)
    _box(ax, 0.2, 0.2, 15.6, 1.0, "CROSS-CUTTING: security marking & classification handling | version control (git) | "
         "fixed random seed for repeatability | data-quality checklist | metadata standard | map update procedure",
         "#eeeeee", 10)
    ax.set_title("PROJECT ARCHITECTURE - SOFTWARE & DATA LAYERS", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------- deck helpers
class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        self.blank = self.prs.slide_layouts[6]
        self.n = 0

    def _frame(self, title, subtitle=None):
        s = self.prs.slides.add_slide(self.blank)
        self.n += 1
        for top in (Inches(0.02), Inches(7.18)):
            tb = s.shapes.add_textbox(0, top, self.prs.slide_width, Inches(0.3))
            p = tb.text_frame.paragraphs[0]
            p.text = MARKING
            p.alignment = PP_ALIGN.CENTER
            p.runs[0].font.size = Pt(11); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = RED
        bar = s.shapes.add_shape(1, 0, Inches(0.32), self.prs.slide_width, Inches(0.85))
        bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
        tf = bar.text_frame
        tf.margin_left = Inches(0.4)
        p = tf.paragraphs[0]
        p.text = title
        p.runs[0].font.size = Pt(26); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        if subtitle:
            tb = s.shapes.add_textbox(Inches(0.4), Inches(1.2), Inches(12.5), Inches(0.4))
            r = tb.text_frame.paragraphs[0]
            r.text = subtitle
            r.runs[0].font.size = Pt(14); r.runs[0].font.italic = True; r.runs[0].font.color.rgb = GREY
        ft = s.shapes.add_textbox(Inches(12.3), Inches(6.85), Inches(1), Inches(0.3))
        ft.text_frame.paragraphs[0].text = str(self.n)
        ft.text_frame.paragraphs[0].runs[0].font.size = Pt(10)
        return s

    def bullets(self, s, items, left=0.5, top=1.7, width=12.3, height=5.0, size=18):
        tb = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, it in enumerate(items):
            lvl = 1 if it.startswith("  ") else 0
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = ("- " if lvl else "") + it.strip()
            p.level = lvl
            p.space_after = Pt(6)
            for r in p.runs:
                r.font.size = Pt(size - 3 * lvl)
                if not lvl and it.strip().endswith(":"):
                    r.font.bold = True
        return tb

    def image(self, s, path, left, top, width=None, height=None):
        kw = {}
        if width:
            kw["width"] = Inches(width)
        if height:
            kw["height"] = Inches(height)
        return s.shapes.add_picture(str(path), Inches(left), Inches(top), **kw)

    def table(self, s, df, left, top, width, height, size=12, col_widths=None):
        rows, cols = df.shape[0] + 1, df.shape[1]
        t = s.shapes.add_table(rows, cols, Inches(left), Inches(top), Inches(width), Inches(height)).table
        for j, c in enumerate(df.columns):
            t.cell(0, j).text = str(c)
        for i in range(df.shape[0]):
            for j in range(cols):
                t.cell(i + 1, j).text = str(df.iat[i, j])
        for i in range(rows):
            for j in range(cols):
                for p in t.cell(i, j).text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(size)
        if col_widths:
            for j, w in enumerate(col_widths):
                t.columns[j].width = Inches(w)
        return t

    def notes(self, s, text):
        s.notes_slide.notes_text_frame.text = text

    def slide(self, title, subtitle=None):
        return self._frame(title, subtitle)


def main():
    workflow_diagram(ASSETS / "workflow_diagram.png")
    summary = json.loads((OUT / "reports/run_summary.json").read_text())
    routes = pd.read_csv(OUT / "reports/route_comparison.csv")
    per_class = pd.read_csv(OUT / "reports/per_class_accuracy.csv")
    areas = pd.read_csv(OUT / "reports/class_area_statistics.csv")
    cross = OUT / "qgis_model/crosscheck.json"
    cross = json.loads(cross.read_text()) if cross.exists() else None
    crit = json.loads((ROOT / "config/going_criteria.json").read_text())
    c = summary["classification"]
    dem = summary["dem_accuracy"]
    sv = summary["survey"]
    import pyogrio
    n_rasters = len(list((OUT / "rasters").glob("*.tif")))
    n_layers = len(pyogrio.list_layers(OUT / "vector/terrain_db.gpkg"))
    n_maps = len(list(MAPS.glob("*.png")))
    architecture_diagram(ASSETS / "architecture_diagram.png", n_layers)

    d = Deck()

    # 1 title
    s = d.slide("EXERCISE TERRA SWIFT", "Rapid Terrain Mapping & Terrain Trafficability (GOING) Analysis using UAS and GIS")
    d.bullets(s, ["Operator briefing - AOI KESTREL (notional, 1 km2)",
                  "Geospatial Cell, Course Syndicate GEO-1",
                  "Software-only demonstration: simulated UAS survey -> photogrammetry products -> QGIS terrain "
                  "database -> GOING classification -> route assessment -> validation",
                  "All data synthetic. Criteria illustrative, not doctrine."], top=2.0, size=20)
    d.image(s, MAPS / "09_going_classification.png", 7.6, 3.9, width=4.6)
    d.notes(s, "Introduce the syndicate and the purpose: to show that a small team with commonly available software "
               "can turn UAS imagery into a validated mobility product quickly and repeatably. Stress the marking: "
               "everything shown is synthetic.")

    # 2 BLUF
    s = d.slide("BOTTOM LINE UP FRONT")
    best = routes.sort_values("rank").iloc[0]
    d.bullets(s, [
        "Capability demonstrated:",
        f"  1 km2 terrain package (ortho, DSM/DTM, {n_rasters} rasters, {n_layers}-layer GeoPackage, {n_maps} map "
        f"products) generated end-to-end in about {summary['runtime_s']:.0f} s",
        "  Automated GOING classification (GO / SLOW-GO / NO-GO / REQUIRES RECCE) by vehicle profile and season",
        f"  Independent QGIS model reproduces the result ({cross['cell_agreement']:.0%} cell agreement)" if cross else
        "  QGIS processing model provided for repeatable production",
        "Key results (SIMULATED):",
        f"  Classification overall accuracy {c['overall_accuracy']:.0%} (95% CI {c['oa_95ci']}), kappa {c['kappa']:.2f}",
        f"  DTM accuracy: {dem['non-vegetated']['rmse_z_m']} m RMSEz in the open, {dem['vegetated']['rmse_z_m']} m under canopy",
        f"  Recommended route under the illustrative weights: {best.route} ({best.length_m / 1000:.1f} km, about {best.est_time_min:.0f} min, no unverified crossings)",
        "Main limitation: the UAS sees the top of the canopy and the surface of the ground, not soil strength, "
        "so REQUIRES RECCE areas must be checked on the ground.",
    ], size=17)
    d.notes(s, "Give the commander the answer first. Make the distinction between the capability demonstrated (real, "
               "repeatable workflow) and the numbers (simulated, illustrating the method).")

    # 3 demonstrated vs simulated
    s = d.slide("WHAT IS DEMONSTRATED vs SIMULATED")
    df = pd.DataFrame([
        ["Survey design (GSD, overlap, lines, GCPs)", "Demonstrated - real calculations, QGC .plan files", "Not flown"],
        ["Photogrammetry (SfM)", "Procedure documented for WebODM/ODM", "Products simulated with realistic error"],
        ["GIS terrain database & derivatives", "Demonstrated on the products", "Input data synthetic"],
        ["GOING classification", "Demonstrated: Python + QGIS model", "Criteria illustrative"],
        ["Route comparison & line of sight", "Demonstrated (least-cost, viewshed)", "Speeds illustrative"],
        ["Validation", "Method demonstrated (stratified, CM, kappa)", "Ground observations simulated"],
        ["Automation & map production", "Demonstrated: one-command rebuild, A3 PDFs", "-"],
    ], columns=["Component", "Status", "Simulated element"])
    d.table(s, df, 0.5, 1.6, 12.3, 4.6, 14, [4.2, 4.5, 3.6])
    d.notes(s, "This slide protects the integrity of the project. Every result elsewhere in the brief should be read "
               "against this table.")

    # 4 architecture
    s = d.slide("PROJECT ARCHITECTURE & SOFTWARE")
    d.image(s, ASSETS / "architecture_diagram.png", 0.4, 1.4, width=12.5)
    d.notes(s, "All software is free and open source and runs on a standard laptop: QGIS 3.34 LTR with GRASS, "
               "WebODM/ODM, QGroundControl and Python 3 with GDAL. Commercial alternatives "
               "(Metashape, Pix4D, ArcGIS Pro) can replace any component without changing the method.")

    # 5 workflow
    s = d.slide("END-TO-END WORKFLOW")
    d.image(s, ASSETS / "workflow_diagram.png", 0.4, 1.4, width=12.5)
    d.notes(s, "Six phases. Planning-to-dissemination time for a real 1 km2 task depends mainly on processing "
               "hardware and ground-truthing; analysis and map generation are automated.")

    # 6 survey
    s = d.slide("PHASE 1 - UAS SURVEY PLAN", "Simulated mission - parameters computed by going.survey")
    d.image(s, MAPS / "01_survey_plan.png", 0.3, 1.6, height=5.5)
    d.bullets(s, [f"GSD {sv['gsd_cm']} cm/px at 100 m AGL (terrain-follow)",
                  "Overlap 80% forward / 70% side",
                  f"{sv['n_lines']} lines, {sv['line_spacing_m']} m apart",
                  f"Trigger every {sv['trigger_distance_m']} m",
                  f"~{sv['total_images']} images, {sv['flight_time_min']} min in {sv['sorties']} sorties",
                  "9 GCPs + 25 independent check points",
                  "Hazard: 33 kV power line, 28 m pylons",
                  "Output: QGroundControl .plan per sortie"], left=7.6, top=1.8, width=5.4, size=16)
    d.notes(s, "Explain overlap choice (80/70 for mixed vegetation), terrain-following to keep GSD constant, and "
               "the vertical hazard. Mention airspace authorisation and friendly C-UAS deconfliction (SOP).")

    # 7 products
    s = d.slide("PHASE 3 - PHOTOGRAMMETRY PRODUCTS", "Orthomosaic and DTM (simulated SfM output, 1 m distribution)")
    d.image(s, MAPS / "02_orthomosaic.png", 0.2, 1.6, height=5.4)
    d.image(s, MAPS / "03_dtm_hillshade_contours.png", 6.7, 1.6, height=5.4)
    d.notes(s, "Products reproduce real SfM behaviour: voids over water, interpolated ground under canopy, "
               "few-cm noise in the open. The confidence layer records where the ground was really seen.")

    # 8 factors
    s = d.slide("PHASE 4 - TERRAIN FACTORS IN THE GIS DATABASE")
    for i, f in enumerate(["04_slope_classes.png", "05_drainage_wetness.png", "06_vegetation_structure.png",
                           "07_obstacle_overlay.png"]):
        d.image(s, MAPS / f, 0.2 + (i % 2) * 6.5, 1.35 + (i // 2) * 2.9, height=2.85)
    d.notes(s, "Four factor groups feed the model: slope (vehicle baseline), drainage and wetness (TWI), "
               "vegetation structure (canopy height and cover) and obstacles (digitised and DTM-derived). They are "
               "held together in one GeoPackage with a defined schema.")

    # 9 criteria
    s = d.slide("CLASSIFICATION CRITERIA (ILLUSTRATIVE)", "Wheeled 4x4 profile - precedence NO-GO > RECCE > SLOW-GO > GO")
    p = crit["profiles"]["wheeled_4x4"]
    w, dr = crit["seasons"]["wet"], crit["seasons"]["dry"]
    df = pd.DataFrame([
        ["GO", f"Slope < {p['slope_slow_go_deg']:.0f} deg; open/low vegetation; firm; roads & tracks", "-"],
        ["SLOW-GO", f"Slope {p['slope_slow_go_deg']:.0f}-{p['slope_no_go_deg']:.0f} deg; scrub; light woodland; built-up; "
                    f"cultivated (wet); TWI >= {w['twi_slow_go']} (wet) / {dr['twi_slow_go']} (dry); low walls",
         "Speed reduced"],
        ["NO-GO", f"Slope >= {p['slope_no_go_deg']:.0f} deg; canopy cover >= {p['canopy_cover_no_go']:.0%}; water; "
                  f"buildings; obstacles >= {p['step_height_no_go_m']} m; marsh (wet)", "Impassable"],
        ["REQUIRES RECCE", f"Crossings of unknown capacity; data confidence < {crit['data_confidence']['recce_below']}; "
                           f"TWI >= {w['twi_recce']} (wet); stream banks under canopy; marsh (dry)", "Unverified"],
    ], columns=["Class", "Criteria (any condition)", "Effect"])
    d.table(s, df, 0.4, 1.7, 12.5, 4.2, 14, [2.2, 8.5, 1.8])
    d.notes(s, "Thresholds are in config/going_criteria.json, so they can be changed without touching code. "
               "Stress that RECCE is an information state: 'we do not know', not a terrain type.")

    # 10 GOING map
    s = d.slide("GOING MAP - WHEELED, WET SEASON")
    d.image(s, MAPS / "09_going_classification.png", 0.3, 1.25, height=5.85)
    a = areas[(areas.profile == "wheeled_4x4") & (areas.season == "wet")].iloc[0]
    d.bullets(s, [f"GO {a['GO %']}%", f"SLOW-GO {a['SLOW-GO %']}%", f"NO-GO {a['NO-GO %']}%",
                  f"RECCE {a['REQUIRES RECCE %']}%", "", "Key NO-GO: Kestrel Brook, marsh, dense wood NE, escarpment, quarry",
                  "Crossings: BRIDGE B1, FORD F1 - capacity unknown"], left=8.6, top=1.6, width=4.5, size=15)
    d.notes(s, "Walk the map from SP ALPHA to OBJ BRAVO. The brook and marsh split the AOI; only two crossings "
               "exist plus the way round the source of the brook in the north.")

    # 11 sensitivity
    s = d.slide("SEASON & VEHICLE SENSITIVITY")
    d.image(s, MAPS / "10_going_season_profile_comparison.png", 0.3, 1.4, width=12.7)
    d.notes(s, "The same terrain gives different products depending on season and vehicle. Products must be labelled "
               "with both and re-issued when conditions change (see seasonality doc).")

    # 12 routes
    s = d.slide("MOBILITY ASSESSMENT - ROUTE OPTIONS")
    d.image(s, MAPS / "12_route_comparison.png", 0.2, 1.25, height=5.85)
    rt = routes[["route", "length_m", "est_time_min", "pct_RECCE", "pct_exposed_to_OP", "rank"]].copy()
    rt.columns = ["Route", "Length m", "Time min", "% RECCE", "% exposed", "Rank"]
    d.table(s, rt, 8.0, 1.6, 5.1, 2.4, 11)
    d.bullets(s, ["B fastest: track + FORD F1 (unverified)", "C assured: around brook source, no RECCE",
                  "D concealed: least exposure to OP SIERRA", "Weights = commander's priorities"],
              left=8.0, top=4.3, width=5.1, size=14)
    d.notes(s, "Each route is optimal for a different criterion. The weighted score is decision support only. "
               "Recommend tasking a patrol to confirm FORD F1, which would make Route B viable.")

    # 13 validation
    s = d.slide("VALIDATION & ACCURACY (SIMULATED GROUND OBSERVATIONS)")
    d.image(s, MAPS / "15_accuracy_assessment.png", 0.2, 1.3, width=8.6)
    pc = per_class[["class", "users_accuracy", "producers_accuracy"]].copy()
    pc.columns = ["Class", "User's acc.", "Producer's acc."]
    d.table(s, pc, 8.9, 1.5, 4.2, 1.6, 12)
    d.bullets(s, [f"OA {c['overall_accuracy']:.0%} ({c['oa_95ci']}), kappa {c['kappa']:.2f}",
                  f"Area-weighted OA {c['area_weighted_oa']:.0%}",
                  f"Unsafe errors (mapped passable, actually NO-GO): {c['unsafe_commission_points']}",
                  f"RECCE points that proved SLOW-GO or NO-GO: {c['recce_flag_efficiency']:.0%}",
                  "Main confusion: GO vs SLOW-GO (soil, undergrowth)"], left=8.9, top=3.3, width=4.3, size=13)
    d.notes(s, "Explain stratified sampling, why RECCE points are reported separately, and why the 'unsafe' error "
               "count matters more to a commander than overall accuracy.")

    # 14 limitations
    s = d.slide("LIMITATIONS & SEASONALITY")
    d.bullets(s, [
        "Sensor & method:",
        "  RGB photogrammetry cannot see under canopy: stem spacing, undergrowth and hidden walls are missed (W2, W3)",
        "  No soil strength or bearing capacity - wetness index is a proxy only",
        "  Water depth, bed material and bridge class cannot be derived",
        "Temporal:",
        "  Product valid for capture conditions only; rain, flood, harvest, snow or frost change GOING within hours",
        "Model:",
        "  Illustrative thresholds; class areas change by several percentage points for +/-5 deg slope limits",
        "  1 m analysis grid, 100 m2 MMU - not suitable for micro-terrain (< 2 m gaps)",
        "Operational:",
        "  Weather, airspace, EW / GNSS denial and adversary C-UAS may prevent collection",
    ], size=16)
    d.notes(s, "Be candid. These limitations define when the product must not be trusted without ground confirmation.")

    # 15 automation
    s = d.slide("AUTOMATION & REPEATABILITY")
    lines = ["One command rebuilds every product: python run_pipeline.py (fixed seed, config-driven)",
             "QGIS model 'GOING terrain analysis': r.neighbors -> slope -> r.watershed TWI -> GOING script -> "
             "polygonise -> label -> class report",
             "QGIS model 'GOING route analysis': reclassify -> r.cost -> r.drain (fastest & assured)",
             "build_project.py writes the styled .qgz and exports A3 PDF layouts"]
    if cross:
        lines.append(f"Independent implementation check: QGIS model vs Python agree on {cross['cell_agreement']:.1%} of cells")
    lines.append("Metadata (ISO 19115 subset) + SHA-256 checksums written for every product")
    d.bullets(s, lines, size=16, width=6.3)
    qimg = OUT / "qgis_layouts/GOING_MAP_A3.png"
    if qimg.exists():
        d.image(s, qimg, 6.9, 1.6, width=6.2)
    d.notes(s, "Demonstrate live if time allows: change the season in the model dialog and re-run - the map updates "
               "in seconds.")

    # 16 SOP & update
    s = d.slide("SOP, QUALITY & MAP UPDATE CYCLE")
    d.bullets(s, [
        "Mission-planning SOP: task -> authorise -> plan -> pre-flight -> fly -> post-flight QA (docs/04)",
        "Data-quality checklist: go/no-go checks for collection, processing, analysis and dissemination (docs/08)",
        "Metadata standard: mandatory ISO 19115 fields, marking, lineage, currency, criteria version (docs/05)",
        "Seasonality: season matrix and product validity periods (docs/06)",
        "Update procedure: scheduled + event-triggered (rain > 25 mm/24 h, flooding, works, combat damage) (docs/07)",
        "Version every product: AOI_KESTREL_GOING_<profile>_<season>_v<NN>_<DTG>",
    ], size=17)
    d.notes(s, "These documents turn a demonstration into a repeatable capability.")

    # 17 recommendations
    s = d.slide("RECOMMENDATIONS & QUESTIONS")
    d.bullets(s, [
        "Adopt the workflow for course and exercise terrain support; run a real authorised 1 km2 survey next",
        "Calibrate criteria with vehicle trials and engineer advice before any operational use",
        "Add LiDAR or multispectral payloads to reduce under-canopy and soil-moisture limitations",
        "Integrate the output with the formation's geospatial information management (GIM) catalogue",
        "Task ground reconnaissance of FORD F1, BRIDGE B1 and woodland edges on the selected route",
        "", "QUESTIONS?",
    ], size=18)
    d.notes(s, "Close with clear, actionable recommendations.")

    path = Path(__file__).resolve().parent / "Operator_Briefing_AOI_KESTREL.pptx"
    d.prs.save(path)
    print("Wrote", path, f"({d.n} slides)")


if __name__ == "__main__":
    main()
