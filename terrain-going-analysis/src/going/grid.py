"""Raster grid definition and pixel/map coordinate helpers."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from affine import Affine
from rasterio import features
from shapely.geometry import LineString, Point, Polygon
from shapely.affinity import affine_transform


@dataclass(frozen=True)
class Grid:
    crs: str
    origin_x: float
    origin_y: float
    res: float
    width: int
    height: int

    @classmethod
    def from_config(cls, cfg: dict) -> "Grid":
        g = cfg["grid"]
        return cls(g["crs"], g["origin_x"], g["origin_y"], g["resolution_m"], g["width_px"], g["height_px"])

    @property
    def shape(self) -> tuple[int, int]:
        return self.height, self.width

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0.0, self.origin_x, 0.0, -self.res, self.origin_y)

    @property
    def extent(self) -> tuple[float, float, float, float]:
        """(xmin, xmax, ymin, ymax) for matplotlib imshow."""
        return (self.origin_x, self.origin_x + self.width * self.res,
                self.origin_y - self.height * self.res, self.origin_y)

    @property
    def bounds_polygon(self) -> Polygon:
        x0, x1, y0, y1 = self.extent
        return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def rc_to_xy(self, row, col):
        """Pixel centre (row, col) -> map (x, y)."""
        x = self.origin_x + (np.asarray(col) + 0.5) * self.res
        y = self.origin_y - (np.asarray(row) + 0.5) * self.res
        return x, y

    def xy_to_rc(self, x, y):
        col = np.floor((np.asarray(x) - self.origin_x) / self.res).astype(int)
        row = np.floor((self.origin_y - np.asarray(y)) / self.res).astype(int)
        return row, col

    def px_geom(self, geom):
        """Convert a geometry drawn in pixel space (x=col, y=row) to map space."""
        return affine_transform(geom, [self.res, 0, 0, -self.res, self.origin_x, self.origin_y])

    def px_line(self, pts_colrow) -> LineString:
        return self.px_geom(LineString(pts_colrow))

    def px_poly(self, pts_colrow) -> Polygon:
        return self.px_geom(Polygon(pts_colrow))

    def px_point(self, col, row) -> Point:
        return self.px_geom(Point(col + 0.5, row + 0.5))

    def rasterize(self, geoms, value=1, dtype="uint8", fill=0, all_touched=True) -> np.ndarray:
        geoms = list(geoms)
        pairs = geoms if geoms and isinstance(geoms[0], tuple) else [(g, value) for g in geoms]
        shapes = [(g, v) for g, v in pairs if g is not None and not g.is_empty]
        if not shapes:
            return np.full(self.shape, fill, dtype=dtype)
        return features.rasterize(shapes, out_shape=self.shape, transform=self.transform,
                                  fill=fill, dtype=dtype, all_touched=all_touched)
