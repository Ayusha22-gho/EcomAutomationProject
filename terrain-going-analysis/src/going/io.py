"""Product export: Cloud-Optimised-style GeoTIFFs, the GeoPackage terrain database, metadata."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

from .grid import Grid


def write_raster(path: Path, arr, grid: Grid, nodata=None, description="", band_names=None, colormap=None):
    arr = np.asarray(arr)
    if arr.ndim == 2:
        arr = arr[None]
    elif arr.ndim == 3 and arr.shape[2] in (3, 4) and arr.shape[0] not in (3, 4):
        arr = np.transpose(arr, (2, 0, 1))
    profile = dict(driver="GTiff", height=grid.height, width=grid.width, count=arr.shape[0], dtype=arr.dtype,
                   crs=grid.crs, transform=grid.transform, compress="deflate", tiled=True,
                   blockxsize=256, blockysize=256, nodata=nodata)
    if arr.dtype.kind == "f":
        profile["predictor"] = 3
    if arr.shape[0] == 3 and arr.dtype == np.uint8:
        profile["photometric"] = "RGB"
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(arr)
        ds.update_tags(DESCRIPTION=description, MARKING="UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA")
        if band_names:
            for i, n in enumerate(band_names, 1):
                ds.set_band_description(i, n)
        if colormap:
            ds.write_colormap(1, colormap)
        ds.build_overviews([2, 4, 8], rasterio.enums.Resampling.nearest if arr.dtype.kind in "ui"
                           else rasterio.enums.Resampling.average)
    return path


def write_gpkg(path: Path, layers: dict[str, gpd.GeoDataFrame]):
    if path.exists():
        path.unlink()
    for name, gdf in layers.items():
        if gdf is None or len(gdf) == 0:
            continue
        g = gdf.copy()
        for col in g.columns:
            if col != "geometry" and g[col].dtype == object:
                g[col] = g[col].astype(str)
            elif g[col].dtype == bool:
                g[col] = g[col].astype(int)
        g.to_file(path, layer=name, driver="GPKG")
    return path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metadata_record(path: Path, title: str, abstract: str, lineage: list[str], grid: Grid, cfg: dict,
                    accuracy: str = "", keywords=None, product_type="raster", criteria_version=None) -> dict:
    x0, x1, y0, y1 = grid.extent
    return {
        "standard": "ISO 19115-1 core profile (course subset) - see docs/05_GIS_METADATA_STANDARD.md",
        "file_identifier": path.stem,
        "file_name": path.name,
        "title": title,
        "abstract": abstract,
        "product_type": product_type,
        "security_marking": cfg["project"]["marking"],
        "point_of_contact": cfg["project"]["producer"],
        "date_created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_currency": "Synthetic capture 'D-day 0'. Treat as stale after the period in docs/07_MAP_UPDATE_PROCEDURE.md",
        "reference_system": grid.crs,
        "vertical_datum": "Ellipsoidal heights reduced to local geoid (notional)",
        "extent_bbox": [x0, y0, x1, y1],
        "spatial_resolution_m": grid.res if product_type == "raster" else None,
        "lineage": lineage,
        "positional_accuracy": accuracy,
        "data_status": "SIMULATED - training product, not for operational use",
        "criteria_version": criteria_version,
        "vehicle_profile": cfg.get("vehicle_profile"),
        "season": cfg.get("primary_season"),
        "keywords": keywords or [],
        "checksum_sha256": sha256(path),
        "software": "going-pipeline (Python/GDAL) v" + cfg["project"]["version"],
    }


def write_metadata(meta_dir: Path, records: list[dict]):
    meta_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        (meta_dir / f"{rec['file_identifier']}.json").write_text(json.dumps(rec, indent=2))
    (meta_dir / "catalogue.json").write_text(json.dumps(
        [{k: r[k] for k in ("file_identifier", "file_name", "title", "product_type", "data_status")} for r in records],
        indent=2))
