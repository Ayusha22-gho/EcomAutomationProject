"""Rule-based GOING classification (GO / SLOW-GO / NO-GO / REQUIRES RECONNAISSANCE)."""
from __future__ import annotations

import numpy as np
from rasterio import features

from . import GO, LC, NO_GO, RECCE, SLOW_GO
from .grid import Grid


def rasterise_features(feats: dict, grid: Grid, stream_zone_m: float = 15.0) -> dict:
    """Burn the vector layers of the terrain database onto the analysis grid."""
    roads = feats["roads"]
    lin = feats["linear_obstacles"]
    crossings = feats["crossings"]
    out = {
        "water": (grid.rasterize(feats["water_bodies"].geometry) |
                  grid.rasterize(feats["streams"].geometry.buffer(4.0))) == 1,
        "marsh": grid.rasterize(feats["marsh"].geometry) == 1,
        "building": grid.rasterize(feats["buildings"].geometry, all_touched=False) == 1,
        "built_up": grid.rasterize(feats["built_up"].geometry) == 1,
        "cultivated": grid.rasterize(feats["fields"].geometry) == 1,
        "road": grid.rasterize(roads[roads.surface == "paved"].geometry.buffer(3.5)) == 1,
        "track": grid.rasterize(roads[roads.surface == "unpaved"].geometry.buffer(2.0)) == 1,
        "crossing": grid.rasterize(crossings.geometry.buffer(9.0)) == 1,
        "stream_zone": grid.rasterize(feats["streams"].geometry.buffer(stream_zone_m)) == 1,
        "pylon": grid.rasterize(feats["pylons"].geometry.buffer(3.0)) == 1,
    }
    if len(lin):
        h = grid.rasterize([(g.buffer(max(w / 2, 0.75)), int(round(v * 100)))
                            for g, v, w in zip(lin.geometry, lin.height_or_depth_m, lin.width_m)],
                           dtype="int32")
        out["linear_height"] = h / 100.0
    else:
        out["linear_height"] = np.zeros(grid.shape)
    return out


def classify_going(L: dict, profile: dict, season: dict, criteria: dict, mmu_px: int | None = None):
    """Classify UAS-derived layers. Returns (class raster, reason-code raster).

    Precedence: NO-GO > REQUIRES RECCE > SLOW-GO > GO, then roads, crossings and
    linear obstacles are burned in after generalisation so that narrow features survive.
    """
    slope, veg, cover, twi, conf = L["slope"], L["veg"], L["cover"], L["twi"], L["confidence"]
    R = L["raster_features"]
    cls = np.full(slope.shape, GO, "uint8")
    reason = np.zeros(slope.shape, "uint8")

    def put(mask, value, why):
        cls[mask] = value
        reason[mask] = why

    flat = slope < 5.0
    put(R["cultivated"] & season["cultivated_is_slow_go"], SLOW_GO, 10)
    put(R["built_up"] & profile["built_up_is_slow_go"], SLOW_GO, 11)
    put(veg == 1, SLOW_GO, 12)
    put(veg == 2, SLOW_GO, 13)
    put((twi >= season["twi_slow_go"]) & flat, SLOW_GO, 14)
    put(slope >= profile["slope_slow_go_deg"], SLOW_GO, 15)

    put((twi >= season["twi_recce"]) & (slope < 3.0), RECCE, 20)
    dc = criteria["data_confidence"]
    put(conf < dc["recce_below"], RECCE, 21)
    put(R["stream_zone"] & (conf < dc["stream_bank_recce_below"]), RECCE, 24)
    if season["marsh_class"] == "RECCE":
        put(R["marsh"], RECCE, 22)

    put(slope >= profile["slope_no_go_deg"], NO_GO, 30)
    put(veg == 3, NO_GO, 31)
    if season["marsh_class"] == "NO_GO":
        put(R["marsh"], NO_GO, 32)
    put(R["water"], NO_GO, 33)
    put(R["building"], NO_GO, 34)

    if mmu_px:
        sieved = features.sieve(cls, size=mmu_px, connectivity=8)
        reason[sieved != cls] = 90
        cls = sieved

    lh = R["linear_height"]
    put((lh > 0.3) & (lh < profile["step_height_no_go_m"]), SLOW_GO, 16)
    put(lh >= profile["step_height_no_go_m"], NO_GO, 35)
    put(R["pylon"], NO_GO, 36)
    put(R["track"] & ~R["water"], GO, 1)
    put(R["road"] & ~R["water"], GO, 2)
    put(R["crossing"] & (R["water"] | R["road"] | R["track"]), RECCE, 23)
    return cls, reason


REASONS = {
    0: "Open, firm, gentle slope", 1: "Unpaved track", 2: "Paved road",
    10: "Cultivated (soft when wet)", 11: "Built-up area", 12: "Scrub", 13: "Light woodland",
    14: "Wet ground (TWI)", 15: "Slope SLOW-GO band", 16: "Low linear obstacle",
    20: "Very wet ground (TWI) - soil unknown", 21: "Low UAS data confidence", 22: "Marsh (dry season)",
    23: "Crossing - capacity/depth unknown", 24: "Stream banks obscured by vegetation",
    30: "Slope above NO-GO limit", 31: "Dense woodland", 32: "Marsh (wet season)", 33: "Water",
    34: "Building", 35: "Linear obstacle above step limit", 36: "Pylon footing", 90: "Generalised (MMU)",
}


def classify_truth(world: dict, truth_layers: dict, profile: dict, season_name: str) -> np.ndarray:
    """What a ground observer would actually find (hidden variables included).

    Uses the true DTM slope, true canopy, actual soil wetness, understorey density,
    real crossing capacities and every linear obstacle (including those under canopy).
    """
    lc = world["landcover"]
    slope, cover, chm = truth_layers["slope"], truth_layers["cover"], world["chm"]
    R = truth_layers["raster_features"]
    wet = truth_layers["soil_wetness"]
    soft_slow, soft_no = (0.55, 0.85) if season_name == "wet" else (0.8, 0.97)

    cls = np.full(lc.shape, GO, "uint8")
    cls[(lc == LC["CULTIVATED"]) & (season_name == "wet") & (wet > 0.35)] = SLOW_GO
    cls[lc == LC["BUILT_UP"]] = SLOW_GO
    cls[(chm >= profile["scrub_height_min_m"]) & (chm < profile["canopy_height_tree_m"])] = SLOW_GO
    cls[(lc == LC["SCRUB"])] = SLOW_GO
    cls[lc == LC["FOREST_LIGHT"]] = SLOW_GO
    cls[wet > soft_slow] = SLOW_GO
    cls[slope >= profile["slope_slow_go_deg"]] = SLOW_GO

    cls[slope >= profile["slope_no_go_deg"]] = NO_GO
    cls[(lc == LC["FOREST_DENSE"]) & (cover >= profile["canopy_cover_no_go"] - 0.05)] = NO_GO
    cls[world["understorey"]] = NO_GO
    cls[wet > soft_no] = NO_GO
    cls[(lc == LC["MARSH"]) & ((season_name == "wet") | (wet > 0.7))] = NO_GO
    cls[(lc == LC["MARSH"]) & ~((season_name == "wet") | (wet > 0.7))] = SLOW_GO
    cls[world["water"]] = NO_GO
    cls[lc == LC["BUILDING"]] = NO_GO

    lh = R["linear_height"]
    cls[(lh > 0.3) & (lh < profile["step_height_no_go_m"])] = SLOW_GO
    cls[lh >= profile["step_height_no_go_m"]] = NO_GO
    cls[R["track"] & ~R["water"]] = GO
    cls[R["road"] & ~R["water"]] = GO

    cr = truth_layers["crossing_truth"]
    cls[cr == 1] = GO
    cls[cr == 2] = NO_GO
    return cls


def soil_wetness(world: dict, twi_true: np.ndarray) -> np.ndarray:
    """Hidden soil-moisture state: driven by topographic wetness plus unmapped local variability."""
    z = (twi_true - 7.5) / 1.5 + 0.9 * world["wet_noise"]
    return (1.0 / (1.0 + np.exp(-z))).astype("float32")
