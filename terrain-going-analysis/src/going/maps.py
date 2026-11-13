"""Standard map products for AOI KESTREL."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm

from . import CLASS_COLOURS, CLASS_NAMES, GO, NO_GO, RECCE, SLOW_GO
from .carto import GOING_CMAP, GOING_NORM, MapSheet, going_overlay_points, plot_vectors
from .uas import hillshade

ROUTE_COLOURS = {"A-DIRECT": "#000000", "B-FASTEST": "#e41a1c", "C-ASSURED": "#1f78ff", "D-CONCEALED": "#ff7f00"}
LINEAGE = "Lineage: simulated UAS survey ->\nphotogrammetry -> GIS model.\nSYNTHETIC - NOT GROUND TRUTH."


def survey_plan_map(ctx, path: Path):
    g, d, plan = ctx["grid"], ctx["survey"], ctx["plan"]
    m = MapSheet(g, "UAS SURVEY PLAN - AOI KESTREL", "Photogrammetric block design, GCP layout and hazards",
                 "PRD-01")
    m.imshow(hillshade(ctx["ref_dem"]), cmap="gray", alpha=0.6)
    x0, x1, y0, y1 = g.extent
    b = d["params"]["buffer_m"]
    m.ax.set_xlim(x0 - b - 60, x1 + b + 60); m.ax.set_ylim(y0 - b - 60, y1 + b + 60)
    plan["flight_lines"].plot(ax=m.ax, color="#1f78ff", lw=0.8)
    plan["photo_centres"].iloc[::3].plot(ax=m.ax, color="#1f78ff", markersize=1.5)
    m.ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="#d7301f", lw=2)
    plan["gcps"].plot(ax=m.ax, marker="X", color="yellow", edgecolor="k", markersize=110, zorder=12)
    for _, r in plan["gcps"].iterrows():
        m.ax.text(r.geometry.x + 15, r.geometry.y + 15, r.gcp_id, fontsize=7, weight="bold", zorder=13)
    ctx["features"]["powerline"].plot(ax=m.ax, color="#9400d3", lw=2, ls="--", zorder=10)
    ctx["features"]["pylons"].plot(ax=m.ax, color="#9400d3", marker="^", markersize=60, zorder=11)
    hx, hy = plan["home_xy"]
    m.ax.plot(hx, hy, marker="H", ms=14, mfc="white", mec="k", zorder=14)
    m.ax.text(hx + 20, hy - 30, "LAUNCH / RECOVERY", fontsize=8, weight="bold", zorder=14)
    m.add_legend_patch("AOI boundary (1 km2)", "none", lw=2)
    m.handles[-1].set_edgecolor("#d7301f")
    m.add_legend_line("Flight line", "#1f78ff", 1)
    m.add_legend_marker("Ground control point", "yellow", "X", 10)
    m.add_legend_marker("Launch / recovery site", "white", "H", 10)
    m.add_legend_line("Power line (VERTICAL HAZARD)", "#9400d3", 2, "--")
    m.add_legend_marker("Pylon 28 m", "#9400d3", "^", 8)
    m.notes = [
        f"Platform  : {d['camera']['name'][:28]}",
        f"Height AGL: {d['params']['altitude_agl_m']:.0f} m (terrain follow)",
        f"GSD       : {d['gsd_cm']} cm/px",
        f"Overlap   : {int(d['params']['front_overlap'] * 100)}% fwd / {int(d['params']['side_overlap'] * 100)}% side",
        f"Line space: {d['line_spacing_m']} m ({d['n_lines']} lines)",
        f"Trigger   : every {d['trigger_distance_m']} m",
        f"Images    : ~{d['total_images']}",
        f"Flight    : {d['flight_time_min']} min / {d['sorties']} sorties",
        f"Blur      : {d['motion_blur_px']} px @ {d['params']['speed_ms']:.0f} m/s",
        "", "SIMULATED MISSION - not flown.",
    ]
    m.save(path)


def ortho_map(ctx, path):
    m = MapSheet(ctx["grid"], "ORTHOMOSAIC - AOI KESTREL",
                 "Simulated UAS RGB orthomosaic (resampled to 1 m for distribution)", "PRD-02")
    m.imshow(ctx["uas"]["ortho"])
    going_overlay_points(m.ax, ctx["points_xy"])
    for _, r in ctx["features"]["crossings"].iterrows():
        m.ax.plot(r.geometry.x, r.geometry.y, "o", mfc="none", mec="cyan", ms=16, mew=2, zorder=20)
        m.ax.text(r.geometry.x + 20, r.geometry.y - 25, r["name"], color="cyan", fontsize=8, weight="bold")
    m.add_legend_marker("Crossing site", "none", "o", 10, "cyan")
    m.add_legend_marker("Start point / Objective", "white", "s", 9)
    m.notes = ["Native GSD (plan): ~2.7 cm", "Distributed: 1.0 m", "Source: simulated SfM", "", LINEAGE]
    m.save(path)


def dem_map(ctx, path):
    g = ctx["grid"]
    dtm = ctx["uas"]["dtm"]
    m = MapSheet(g, "DIGITAL TERRAIN MODEL - AOI KESTREL", "UAS-derived DTM with hillshade and 5 m contours",
                 "PRD-03")
    im = m.imshow(dtm, cmap="terrain", vmin=np.percentile(dtm, 1) - 10, vmax=np.percentile(dtm, 99.5) + 5)
    m.imshow(hillshade(dtm), cmap="gray", alpha=0.35)
    x0, x1, y0, y1 = g.extent
    X, Y = np.meshgrid(np.linspace(x0, x1, g.width), np.linspace(y1, y0, g.height))
    from scipy.ndimage import gaussian_filter
    zs = gaussian_filter(dtm, 3)
    lv = np.arange(np.floor(zs.min() / 5) * 5, zs.max() + 5, 5)
    cs = m.ax.contour(X, Y, zs, levels=lv, colors="#5a3d1e", linewidths=0.4)
    m.ax.contour(X, Y, zs, levels=lv[::5], colors="#5a3d1e", linewidths=1.0)
    m.ax.clabel(cs, levels=lv[::5], fontsize=6, fmt="%d")
    m.colorbar(im, "Elevation (m)")
    m.notes = [f"Min {dtm.min():.1f} m  Max {dtm.max():.1f} m", "Contour interval 5 m (index 25 m)",
               "Ground surface interpolated", "under canopy (see confidence)", "", LINEAGE]
    m.save(path)


def slope_map(ctx, path):
    prof = ctx["profile"]
    slope = ctx["layers"]["slope"]
    m = MapSheet(ctx["grid"], "SLOPE ANALYSIS - AOI KESTREL",
                 f"Slope classes for profile '{ctx['profile_name']}' (2 m vehicle baseline)", "PRD-04")
    bins = [0, 5, prof["slope_slow_go_deg"], prof["slope_no_go_deg"], 90]
    cols = ["#e8f5e0", "#9fd38a", "#f2c230", "#d7301f"]
    cl = np.digitize(slope, bins[1:-1])
    m.imshow(cl, cmap=ListedColormap(cols), vmin=-0.5, vmax=3.5)
    m.imshow(hillshade(ctx["uas"]["dtm"]), cmap="gray", alpha=0.25)
    labels = [f"0-5 deg (flat)", f"5-{bins[2]:.0f} deg", f"{bins[2]:.0f}-{bins[3]:.0f} deg (SLOW-GO)",
              f">{bins[3]:.0f} deg (NO-GO)"]
    for lab, col in zip(labels, cols):
        m.add_legend_patch(lab, col)
    shares = [100 * (cl == i).mean() for i in range(4)]
    m.notes = ["Area share:"] + [f" {l.split(' (')[0]:<12}{s:5.1f}%" for l, s in zip(labels, shares)] + ["", LINEAGE]
    m.save(path)


def drainage_map(ctx, path):
    L = ctx["layers"]
    m = MapSheet(ctx["grid"], "DRAINAGE & WETNESS - AOI KESTREL",
                 "Topographic Wetness Index, DTM-derived drainage and mapped water", "PRD-05")
    im = m.imshow(L["twi"], cmap="Blues", vmin=2, vmax=14)
    m.imshow(hillshade(ctx["uas"]["dtm"]), cmap="gray", alpha=0.2)
    L["drainage"].plot(ax=m.ax, color="#08306b", lw=0.9, zorder=6)
    feats = ctx["features"]
    plot_vectors(m.ax, feats, ("water_bodies", "marsh", "streams"))
    m.colorbar(im, "TWI  ln(a / tan b)")
    m.add_legend_line("Derived drainage line (D8)", "#08306b", 1)
    m.add_legend_line("Mapped stream (digitised)", "#1f6fbf", 2.2)
    m.add_legend_patch("Water body", "#3b7fbf")
    m.add_legend_patch("Marsh", "none", hatch="///")
    se = ctx["season"]
    m.notes = [f"Season: {ctx['season_name'].upper()}", f"TWI >= {se['twi_slow_go']} flat -> SLOW-GO",
               f"TWI >= {se['twi_recce']} -> RECCE", "TWI is a proxy, not soil strength.", "", LINEAGE]
    m.save(path)


def vegetation_map(ctx, path):
    L = ctx["layers"]
    m = MapSheet(ctx["grid"], "VEGETATION STRUCTURE - AOI KESTREL",
                 "Canopy height model (DSM - DTM) classified by height and canopy cover", "PRD-06")
    cols = ["#f0f0d8", "#c2d97a", "#4f9a3a", "#0f4d1c"]
    m.imshow(L["veg"], cmap=ListedColormap(cols), vmin=-0.5, vmax=3.5)
    m.imshow(hillshade(ctx["uas"]["dsm"]), cmap="gray", alpha=0.25)
    from .terrain import VEG_CLASSES
    for k, col in enumerate(cols):
        m.add_legend_patch(VEG_CLASSES[k], col)
    sh = [100 * (L["veg"] == k).mean() for k in range(4)]
    m.notes = [f"Open {sh[0]:.1f}%  Scrub {sh[1]:.1f}%", f"Light wood {sh[2]:.1f}%", f"Dense wood {sh[3]:.1f}%",
               f"Dense = cover >= {ctx['profile']['canopy_cover_no_go']:.2f}",
               "UAS sees canopy top only:", "stem spacing / undergrowth", "NOT observable.", "", LINEAGE]
    m.save(path)


def obstacle_map(ctx, path):
    feats = ctx["digitised"]
    m = MapSheet(ctx["grid"], "OBSTACLE OVERLAY - AOI KESTREL",
                 "Natural and man-made obstacles digitised from the orthomosaic and DTM", "PRD-07")
    m.imshow(ctx["uas"]["ortho"], alpha=0.45)
    steep = np.ma.masked_where(ctx["layers"]["slope"] < ctx["profile"]["slope_no_go_deg"], np.ones(ctx["grid"].shape))
    m.imshow(steep, cmap=ListedColormap(["#d7301f"]), alpha=0.8)
    plot_vectors(m.ax, feats, ("water_bodies", "marsh", "streams", "roads", "buildings"))
    lo = feats["linear_obstacles"]
    styles = {"hedgerow": ("#2d6a1f", "-"), "stone_wall": ("#7f3b08", "-"), "ditch": ("#08519c", ":")}
    for t, (col, ls) in styles.items():
        sub = lo[lo["type"] == t]
        if len(sub):
            sub.plot(ax=m.ax, color=col, lw=3, ls=ls, zorder=12)
        m.add_legend_line(t.replace("_", " ").title(), col, 3, ls)
    feats["quarry"].plot(ax=m.ax, facecolor="none", edgecolor="#d7301f", lw=1.5, hatch="xx", zorder=8)
    feats["pylons"].plot(ax=m.ax, color="#9400d3", marker="^", markersize=50, zorder=13)
    for _, r in feats["crossings"].iterrows():
        m.ax.plot(r.geometry.x, r.geometry.y, marker="D", ms=11, mfc="#7b4fd6", mec="w", zorder=14)
        m.ax.text(r.geometry.x + 18, r.geometry.y + 12, r["name"] + "\n(class unknown)", fontsize=7, weight="bold",
                  zorder=15, bbox=dict(fc="white", alpha=0.8, lw=0))
    m.add_legend_patch("Slope > NO-GO limit", "#d7301f")
    m.add_legend_patch("Quarry (steep faces)", "none", hatch="xx")
    m.add_legend_marker("Crossing (needs recce)", "#7b4fd6", "D", 9)
    m.add_legend_marker("Pylon", "#9400d3", "^", 8)
    m.add_legend_line("Paved road", "#202020", 3)
    m.add_legend_line("Unpaved track", "#5a3d1e", 1.5, "--")
    m.add_legend_line("Stream", "#1f6fbf", 2.2)
    m.add_legend_patch("Building", "#333333")
    missed = sorted(set(ctx["features"]["linear_obstacles"].obs_id) - set(lo.obs_id))
    m.notes = [f"Linear obstacles mapped: {len(lo)}",
               f"Not detected (under canopy): {', '.join(missed) if missed else 'none'}",
               "-> UAS cannot see below canopy;", "   ground recce required.", "", LINEAGE]
    m.save(path)


def going_map(ctx, going, path, title, subtitle, pid, extra_notes=()):
    m = MapSheet(ctx["grid"], title, subtitle, pid)
    m.imshow(going, cmap=GOING_CMAP, norm=GOING_NORM)
    m.imshow(hillshade(ctx["uas"]["dtm"]), cmap="gray", alpha=0.22)
    plot_vectors(m.ax, ctx["digitised"], ("roads", "streams"), lw_scale=0.7)
    going_overlay_points(m.ax, ctx["points_xy"])
    m.going_legend()
    m.add_legend_line("Paved road", "#202020", 3)
    m.add_legend_line("Unpaved track", "#5a3d1e", 1.5, "--")
    m.add_legend_line("Stream", "#1f6fbf", 2)
    tot = going.size
    m.notes = ["Area share:"] + [f" {CLASS_NAMES[c]:<15}{100 * (going == c).sum() / tot:5.1f}%"
                                 for c in (GO, SLOW_GO, NO_GO, RECCE)] + [""] + list(extra_notes) + [
        "Criteria: config/going_criteria.json", "ILLUSTRATIVE CRITERIA ONLY", "", LINEAGE]
    m.save(path)


def going_comparison(ctx, maps: dict, path):
    fig, axes = plt.subplots(1, len(maps), figsize=(6 * len(maps), 6.6))
    fig.suptitle("GOING SENSITIVITY TO SEASON AND VEHICLE PROFILE  |  UNCLASSIFIED // EXERCISE // SYNTHETIC",
                 fontsize=12, weight="bold")
    for ax, (title, arr) in zip(axes, maps.items()):
        ax.imshow(arr, cmap=GOING_CMAP, norm=GOING_NORM, extent=ctx["grid"].extent, interpolation="nearest")
        ax.set_title(title + "\n" + "  ".join(f"{CLASS_NAMES[c].split()[0]}:{100 * (arr == c).mean():.0f}%"
                                              for c in (GO, SLOW_GO, NO_GO, RECCE)), fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    import matplotlib.patches as mp
    fig.legend(handles=[mp.Patch(color=CLASS_COLOURS[c], label=CLASS_NAMES[c]) for c in (GO, SLOW_GO, NO_GO, RECCE)],
               loc="lower center", ncol=4, fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def route_map(ctx, routes, path):
    m = MapSheet(ctx["grid"], "MOBILITY ASSESSMENT - ROUTE COMPARISON",
                 f"Alternative routes SP ALPHA -> OBJ BRAVO  |  {ctx['profile_name']}, {ctx['season_name']} season",
                 "PRD-10")
    m.imshow(ctx["going"], cmap=GOING_CMAP, norm=GOING_NORM, alpha=0.6)
    m.imshow(hillshade(ctx["uas"]["dtm"]), cmap="gray", alpha=0.12)
    g = ctx["grid"]
    x0, x1, y0, y1 = g.extent
    xs = np.linspace(x0, x1, g.width)
    ys = np.linspace(y1, y0, g.height)
    m.ax.contourf(xs, ys, ctx["visible"], levels=[0.5, 1.5], colors="none", hatches=["...."], zorder=6)
    m.ax.contour(xs, ys, ctx["visible"], levels=[0.5], colors="#c000c0", linewidths=0.9, zorder=6)
    plot_vectors(m.ax, ctx["digitised"], ("roads", "streams"), lw_scale=0.6)
    for _, r in routes.iterrows():
        col = ROUTE_COLOURS[r.route]
        m.ax.plot(*r.geometry.xy, color="white", lw=5, zorder=24)
        m.ax.plot(*r.geometry.xy, color=col, lw=2.6, zorder=25)
        mid = r.geometry.interpolate(0.5, normalized=True)
        m.ax.text(mid.x, mid.y, r.route.split("-")[0], fontsize=11, weight="bold", color="white", zorder=26,
                  ha="center", va="center", bbox=dict(boxstyle="circle", fc=col, ec="white"))
        m.add_legend_line(f"Route {r.route} (rank {r['rank']})", col, 3)
    op = ctx["op_xy"]
    m.ax.plot(*op, marker="*", ms=20, mfc="#ff00ff", mec="k", zorder=27)
    m.ax.text(op[0] - 40, op[1] + 30, "OP SIERRA", fontsize=9, weight="bold", ha="right", zorder=27,
              bbox=dict(fc="white", alpha=0.85, lw=0))
    going_overlay_points(m.ax, ctx["points_xy"])
    m.going_legend()
    m.add_legend_patch("Visible from OP SIERRA", "none", hatch="....")
    m.handles[-1].set_edgecolor("#c000c0")
    m.add_legend_marker("OP / sensor site", "#ff00ff", "*", 12)
    m.notes = [f"{r.route:<12}{r.length_m / 1000:4.1f} km {r.est_time_min:5.1f} min" for _, r in routes.iterrows()]
    m.notes += ["", "Times are ILLUSTRATIVE", "(speed table in criteria).", "", LINEAGE]
    m.save(path)


def route_chart(routes, path):
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2))
    fig.suptitle("ROUTE COMPARISON METRICS  |  UNCLASSIFIED // EXERCISE // SYNTHETIC", fontsize=11, weight="bold")
    names = [r.split("-")[0] for r in routes.route]
    cols = [ROUTE_COLOURS[r] for r in routes.route]
    axes[0].bar(names, routes.est_time_min, color=cols); axes[0].set_title("Est. transit time (min)")
    axes[1].bar(names, routes.length_m / 1000, color=cols); axes[1].set_title("Length (km)")
    bottom = np.zeros(len(routes))
    for k, c in (("pct_GO", GO), ("pct_SLOW_GO", SLOW_GO), ("pct_RECCE", RECCE)):
        axes[2].bar(names, routes[k], bottom=bottom, color=CLASS_COLOURS[c], label=CLASS_NAMES[c])
        bottom += routes[k].to_numpy()
    axes[2].set_title("Going composition (% length)"); axes[2].legend(fontsize=7)
    axes[3].bar(names, routes.pct_exposed_to_OP, color=cols); axes[3].set_title("Exposed to OP (% length)")
    for ax in axes:
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def validation_map(ctx, obs, path):
    m = MapSheet(ctx["grid"], "VALIDATION - SIMULATED GROUND OBSERVATIONS",
                 "Stratified random sample by map class; agreement with patrol observation", "PRD-12")
    m.imshow(ctx["going"], cmap=GOING_CMAP, norm=GOING_NORM, alpha=0.45)
    det = obs[obs.map_code != RECCE]
    ok = det[det.map_code == det.obs_code]
    bad = det[det.map_code != det.obs_code]
    rec = obs[obs.map_code == RECCE]
    ok.plot(ax=m.ax, marker="o", color="white", edgecolor="k", markersize=28, zorder=20)
    bad.plot(ax=m.ax, marker="X", color="#ff0000", edgecolor="k", markersize=60, zorder=21)
    rec.plot(ax=m.ax, marker="D", color="#7b4fd6", edgecolor="white", markersize=30, zorder=20)
    m.going_legend()
    m.add_legend_marker("Agreement", "white", "o", 7)
    m.add_legend_marker("Disagreement", "#ff0000", "X", 9)
    m.add_legend_marker("RECCE point (resolved)", "#7b4fd6", "D", 7)
    m.notes = [f"Points: {len(obs)} ({len(det)} determinate)", f"Agree: {len(ok)}  Disagree: {len(bad)}",
               "", "Observations are SIMULATED", "from a hidden truth model.", "", LINEAGE]
    m.save(path)


def confusion_figure(acc, dem_summary, dem_cp, path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    fig.suptitle("ACCURACY ASSESSMENT  |  UNCLASSIFIED // EXERCISE // SYNTHETIC", fontsize=11, weight="bold")
    cm = acc["confusion_matrix"]
    ax = axes[0]
    ax.imshow(cm.values, cmap="Blues")
    ax.set_xticks(range(cm.shape[1])); ax.set_xticklabels(cm.columns)
    ax.set_yticks(range(cm.shape[0])); ax.set_yticklabels(cm.index)
    ax.set_xlabel("Observed on ground (reference)"); ax.set_ylabel("Mapped class")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm.values[i, j]), ha="center", va="center", fontsize=12,
                    color="white" if cm.values[i, j] > cm.values.max() / 2 else "black")
    ax.axhline(2.5, color="k", lw=2)
    ax.set_title(f"OA {acc['overall_accuracy']:.0%} (95% CI {acc['oa_95ci']})  kappa {acc['kappa']:.2f}\n"
                 f"area-weighted OA {acc['area_weighted_oa']:.0%}  |  RECCE row shows what patrols found")
    ax = axes[1]
    for label, col in (("non-vegetated", "#2e9e44"), ("vegetated", "#8c510a")):
        sub = dem_cp[dem_cp.land_class == label]
        ax.hist(sub.dz_m, bins=12, alpha=0.7, color=col,
                label=f"{label}: RMSEz {dem_summary[label]['rmse_z_m']:.2f} m (n={dem_summary[label]['n']})")
    ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("DTM - checkpoint (m)"); ax.set_ylabel("Count")
    ax.set_title("DTM vertical error at independent check points")
    ax.legend(fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=130)
    plt.close(fig)


def confidence_map(ctx, path):
    m = MapSheet(ctx["grid"], "DATA CONFIDENCE - AOI KESTREL",
                 "Fraction of ground actually observed by the UAS (photogrammetric ground visibility)", "PRD-08")
    im = m.imshow(ctx["uas"]["confidence"], cmap="RdYlGn", vmin=0, vmax=1)
    m.colorbar(im, "Confidence (0-1)")
    m.notes = [f"< {ctx['criteria']['data_confidence']['recce_below']} -> REQUIRES RECCE",
               "Low: water voids, closed canopy", "Use with every GOING product.", "", LINEAGE]
    m.save(path)


def viewshed_map(ctx, path):
    m = MapSheet(ctx["grid"], "LINE-OF-SIGHT ANALYSIS - OP / SENSOR SITE SIERRA",
                 "Ground visible from OP SIERRA (DSM occlusion: terrain, vegetation, buildings)", "PRD-09")
    m.imshow(ctx["uas"]["ortho"], alpha=0.6)
    vis = np.ma.masked_where(ctx["visible"] < 0.5, ctx["visible"])
    m.imshow(vis, cmap=ListedColormap(["#ff00ff"]), alpha=0.35)
    m.ax.plot(*ctx["op_xy"], marker="*", ms=22, mfc="#ff00ff", mec="k", zorder=27)
    m.add_legend_patch("Visible (2.5 m target)", "#ff00ff80")
    m.add_legend_marker("OP / C-UAS sensor site", "#ff00ff", "*", 12)
    m.notes = [f"Visible area: {100 * ctx['visible'].mean():.1f}% of AOI",
               "Uses: route exposure; C-UAS /", "ISR sensor siting; UAS launch", "site masking.", "", LINEAGE]
    m.save(path)
