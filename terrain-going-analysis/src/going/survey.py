"""UAS photogrammetric survey design and QGroundControl mission export."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from scipy import ndimage as ndi
from shapely.geometry import LineString, Point

from .grid import Grid


@dataclass
class Camera:
    name: str = "DJI Mavic 3 Enterprise (M3E) wide camera, mechanical shutter"
    sensor_w_mm: float = 17.3
    sensor_h_mm: float = 13.0
    focal_mm: float = 12.29
    img_w_px: int = 5280
    img_h_px: int = 3956
    min_trigger_interval_s: float = 0.7


@dataclass
class SurveyParams:
    altitude_agl_m: float = 100.0
    front_overlap: float = 0.80
    side_overlap: float = 0.70
    speed_ms: float = 10.0
    shutter_s: float = 1 / 1000
    buffer_m: float = 60.0
    line_azimuth: str = "N-S"
    usable_endurance_min: float = 25.0
    turn_time_s: float = 15.0


def design(cam: Camera, sp: SurveyParams, aoi_w_m: float, aoi_h_m: float) -> dict:
    gsd = cam.sensor_w_mm * sp.altitude_agl_m / (cam.focal_mm * cam.img_w_px)       # m/px
    foot_across = gsd * cam.img_w_px      # camera long side across track
    foot_along = gsd * cam.img_h_px
    trigger = foot_along * (1 - sp.front_overlap)
    spacing = foot_across * (1 - sp.side_overlap)
    block_w = aoi_w_m + 2 * sp.buffer_m
    block_h = aoi_h_m + 2 * sp.buffer_m
    n_lines = math.ceil(block_w / spacing) + 1
    imgs_per_line = math.ceil(block_h / trigger) + 1
    line_time = block_h / sp.speed_ms + sp.turn_time_s
    total_min = n_lines * line_time / 60.0
    sorties = math.ceil(total_min / (sp.usable_endurance_min - 5))
    blur_px = sp.speed_ms * sp.shutter_s / gsd
    return {
        "camera": asdict(cam), "params": asdict(sp),
        "gsd_cm": round(gsd * 100, 2), "footprint_across_m": round(foot_across, 1),
        "footprint_along_m": round(foot_along, 1), "trigger_distance_m": round(trigger, 1),
        "trigger_interval_s": round(trigger / sp.speed_ms, 2), "line_spacing_m": round(spacing, 1),
        "block_w_m": block_w, "block_h_m": block_h, "n_lines": n_lines, "images_per_line": imgs_per_line,
        "total_images": n_lines * imgs_per_line, "flight_time_min": round(total_min, 1), "sorties": sorties,
        "motion_blur_px": round(blur_px, 2),
        "checks": {
            "trigger_interval_ok": trigger / sp.speed_ms >= cam.min_trigger_interval_s,
            "motion_blur_ok(<0.5px)": blur_px < 0.5,
            "gsd_meets_5cm_requirement": gsd * 100 <= 5.0,
        },
    }


def plan_mission(d: dict, grid: Grid, ref_dem: np.ndarray, out_dir: Path) -> dict:
    """Lay out flight lines, photo centres and GCPs; write one QGC .plan per sortie."""
    out_dir.mkdir(parents=True, exist_ok=True)
    to_ll = Transformer.from_crs(grid.crs, "EPSG:4326", always_xy=True)
    x0, x1, y0, y1 = grid.extent
    buf = d["params"]["buffer_m"]
    xs = np.linspace(x0 - buf, x0 - buf + (d["n_lines"] - 1) * d["line_spacing_m"], d["n_lines"])
    alt = d["params"]["altitude_agl_m"]
    smooth = ndi.gaussian_filter(ref_dem, 30)

    def ground(x, y):
        r, c = grid.xy_to_rc(x, y)
        return float(smooth[np.clip(r, 0, grid.height - 1), np.clip(c, 0, grid.width - 1)])

    lines, photos = [], []
    for i, x in enumerate(xs):
        ya, yb = (y0 - buf, y1 + buf) if i % 2 == 0 else (y1 + buf, y0 - buf)
        lines.append({"line_id": i + 1, "geometry": LineString([(x, ya), (x, yb)])})
        n = d["images_per_line"]
        for k, y in enumerate(np.linspace(ya, yb, n)):
            photos.append({"line_id": i + 1, "photo_id": f"L{i + 1:02d}P{k + 1:03d}",
                           "alt_amsl_m": round(ground(x, y) + alt, 1), "geometry": Point(x, y)})
    lines_gdf = gpd.GeoDataFrame(lines, crs=grid.crs)
    photos_gdf = gpd.GeoDataFrame(photos, crs=grid.crs)

    gcp_rc = [(60, 60), (60, 500), (60, 940), (500, 60), (500, 520), (500, 940), (940, 60), (940, 500), (940, 940)]
    gcps = []
    for j, (r, c) in enumerate(gcp_rc):
        x, y = grid.rc_to_xy(r, c)
        gcps.append({"gcp_id": f"GCP{j + 1}", "role": "control", "target": "1 m chequerboard panel",
                     "survey": "GNSS RTK, 3 min occupation", "geometry": Point(float(x), float(y))})
    gcps_gdf = gpd.GeoDataFrame(gcps, crs=grid.crs)

    home_x, home_y = grid.rc_to_xy(985, 30)
    home_lon, home_lat = to_ll.transform(float(home_x), float(home_y))
    home_alt = ground(float(home_x), float(home_y))
    per = math.ceil(d["n_lines"] / d["sorties"])
    plans = []
    for s in range(d["sorties"]):
        sub = lines[s * per:(s + 1) * per]
        items, jid = [], 1

        def add(cmd, params, frame=0):
            nonlocal jid
            items.append({"type": "SimpleItem", "autoContinue": True, "command": cmd, "doJumpId": jid,
                          "frame": frame, "params": params})
            jid += 1

        add(22, [15, 0, 0, None, home_lat, home_lon, home_alt + 40], 0)
        for ln in sub:
            (xa, ya), (xb, yb) = ln["geometry"].coords
            for f in np.linspace(0, 1, 12):
                x, y = xa + (xb - xa) * f, ya + (yb - ya) * f
                lon, lat = to_ll.transform(x, y)
                if f == 0:
                    add(16, [0, 0, 0, None, lat, lon, round(ground(x, y) + alt, 1)])
                    add(206, [d["trigger_distance_m"], 0, 1, 0, 0, 0, 0], 2)
                else:
                    add(16, [0, 0, 0, None, lat, lon, round(ground(x, y) + alt, 1)])
            add(206, [0, 0, 1, 0, 0, 0, 0], 2)
        add(20, [0, 0, 0, 0, 0, 0, 0], 2)
        fence = [[lat, lon] for lon, lat in (to_ll.transform(px, py) for px, py in
                 [(x0 - 150, y0 - 150), (x1 + 150, y0 - 150), (x1 + 150, y1 + 150), (x0 - 150, y1 + 150)])]
        plan = {
            "fileType": "Plan", "groundStation": "QGroundControl", "version": 1,
            "mission": {"cruiseSpeed": d["params"]["speed_ms"], "hoverSpeed": 5, "firmwareType": 12,
                        "vehicleType": 2, "globalPlanAltitudeMode": 1, "version": 2,
                        "plannedHomePosition": [home_lat, home_lon, round(home_alt, 1)], "items": items},
            "geoFence": {"circles": [], "polygons": [{"inclusion": True, "polygon": fence, "version": 1}],
                         "version": 2},
            "rallyPoints": {"points": [[home_lat, home_lon, round(home_alt + 30, 1)]], "version": 2},
        }
        p = out_dir / f"AOI_KESTREL_sortie_{chr(65 + s)}.plan"
        p.write_text(json.dumps(plan, indent=2))
        plans.append(p.name)

    (out_dir / "survey_design.json").write_text(json.dumps(d, indent=2))
    return {"flight_lines": lines_gdf, "photo_centres": photos_gdf, "gcps": gcps_gdf, "plans": plans,
            "home_xy": (float(home_x), float(home_y))}
