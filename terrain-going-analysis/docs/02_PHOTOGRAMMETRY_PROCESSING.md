# 02 - Photogrammetry Processing and 3D Terrain Modelling (Requirement 2)

**UNCLASSIFIED // EXERCISE ONLY**

> **Status:** the processing **procedure** below is real and can be used with any authorised image set
> (for example the public OpenDroneMap sample datasets). In this project the resulting products are
> **simulated** by `src/going/uas.py`, so the course can run without flying and without a processing
> server.

## 1. Product specification

| Product | File (this project) | Equivalent ODM output | Specification |
|---|---|---|---|
| Orthomosaic (RGB) | `outputs/rasters/orthomosaic_rgb.tif` | `odm_orthophoto/odm_orthophoto.tif` | Native about 3 cm, distributed at 1 m for analysis; RMSEr ≤ 0.10 m |
| Digital Surface Model | `dsm.tif` | `odm_dem/dsm.tif` | 1 m (native 5-10 cm); tops of vegetation and buildings |
| Digital Terrain Model | `dtm.tif` | `odm_dem/dtm.tif` | 1 m; bare earth after ground filtering; RMSEz ≤ 0.10 m in the open |
| Canopy/feature height | `chm.tif` | DSM − DTM (QGIS Raster Calculator) | 1 m |
| Hillshade, contours | `hillshade.tif`; map 03 | GDAL hillshade / contour | 315°/45°, 5 m contour interval |
| Data confidence | `data_confidence.tif` | derived from point density and ground classification | 0-1 |
| Processing report | `reports/VALIDATION_REPORT.md` §1 | `odm_report/report.pdf` | RMSE at ICPs by stratum |

## 2. Real processing procedure (WebODM / ODM)

1. **Ingest.** Copy the images from all sorties into one task folder. Check the image count against the
   plan (about 1,540) and check for blur. Reject blurred frames (for example Laplacian variance well below that of known-sharp frames from the same sortie).
2. **GCP file.** Create `gcp_list.txt` (header = EPSG code, then `X Y Z px py image_name gcp_id`) with
   at least 3 image tags per GCP. Do **not** include the ICPs.
3. **Task options** (WebODM ▸ Edit ▸ Options):

   | Option | Value | Reason |
   |---|---|---|
   | `dsm`, `dtm` | true | Elevation products |
   | `dem-resolution` | 5 (cm) | Native DEM |
   | `orthophoto-resolution` | 3 (cm) | About 1 × GSD |
   | `pc-quality` | high | Dense matching quality |
   | `feature-quality` | high | Tie points in vegetation |
   | `pc-classify` / `smrf-*` | enabled, defaults | Ground filtering for the DTM |
   | `use-3dmesh` | false | Faster for 2.5D terrain |
   | `gcp` | `gcp_list.txt` | Absolute accuracy |
   | `cog` | true | Cloud-optimised GeoTIFF |

   Command-line equivalent:
   `docker run -ti --rm -v /data:/datasets opendronemap/odm --project-path /datasets kestrel --dsm --dtm --dem-resolution 5 --orthophoto-resolution 3 --pc-quality high --feature-quality high --pc-classify --cog`
4. **QA in WebODM.** Check the processing report: calibrated image count (≥ 98 %), GCP residuals
   (< 2 × GSD), reprojection error (< 1 px) and overlap map coverage (≥ 5 images per point inside the AOI).
5. **Export** the ortho, DSM and DTM. In QGIS, resample to the 1 m analysis grid (Warp, average for
   continuous rasters), clip to the AOI and write tiled, compressed GeoTIFFs.
6. **Accuracy assessment.** Sample the DTM at the ICPs and report RMSEz separately for non-vegetated and
   vegetated ground (ASPRS 2023 NVA/VVA convention), plus RMSEr for the ortho. See VALIDATION_REPORT §1.

Metashape and Pix4D follow the same sequence: align, add GCPs and optimise, build the dense cloud,
classify ground points, then build the DEM and orthomosaic.

## 3. How the simulation reproduces real behaviour (`src/going/uas.py`)

| Real SfM behaviour | Simulation |
|---|---|
| Few-cm noise over textured open ground | DSM noise σ = 0.04 m plus a smooth residual block deformation of about 2.5 cm |
| No stable tie points over water | Voids over water and their margins, filled by interpolation; confidence 0.1 |
| Closed canopy hides the ground | No ground "returns" under canopy: the DTM is interpolated from visible ground, biased high (+0.4 × cover) and noisier |
| Hedgerows partly classified as ground | 25 % of hedge cells leak into the DTM |
| Dense matching smooths tree crowns | Gaussian smoothing of DSM crowns, σ = 0.25 m noise |
| Analyst digitising from the ortho | Linear obstacles less than 60 % visible under canopy are missed (W2 and W3 in this run) |
| RGB-only camera (no NIR) | Vegetation index computed as VARI = (G − R)/(G + R − B) |

Resulting accuracy (reference run): RMSEz **0.05 m** non-vegetated and **0.65 m** vegetated, with
RMSEr **0.046 m**. This matches the pattern reported for real RGB surveys: accurate in the open,
unreliable under canopy.

## 4. Limitations

* SfM fails on water, uniform fields, fresh snow and moving vegetation (wind). Plan to fly in light wind
  under diffuse light.
* Shadows reduce matching density. Avoid flying with the sun lower than about 25° elevation.
* RGB cannot measure soil moisture or bearing strength. Multispectral, thermal or LiDAR payloads reduce
  but do not remove this limitation.
