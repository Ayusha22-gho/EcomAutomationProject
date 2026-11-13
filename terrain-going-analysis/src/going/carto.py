"""Map-sheet template and standard map products (PNG) for briefing and reporting."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from . import CLASS_COLOURS, CLASS_NAMES, GO, NO_GO, RECCE, SLOW_GO  # noqa: E402
from .grid import Grid  # noqa: E402

MARKING = "UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA"
GOING_CMAP = ListedColormap([CLASS_COLOURS[c] for c in (GO, SLOW_GO, NO_GO, RECCE)])
GOING_NORM = BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], 4)


class MapSheet:
    def __init__(self, grid: Grid, title: str, subtitle: str = "", product_id: str = "", figsize=(13, 10)):
        self.grid = grid
        self.fig = plt.figure(figsize=figsize, facecolor="white")
        self.ax = self.fig.add_axes([0.05, 0.08, 0.66, 0.82])
        self.side = self.fig.add_axes([0.73, 0.08, 0.25, 0.82])
        self.side.axis("off")
        self.handles: list = []
        self.notes: list[str] = []
        for y in (0.975, 0.012):
            self.fig.text(0.5, y, MARKING, ha="center", va="center", fontsize=10, color="#b30000", weight="bold")
        self.fig.text(0.05, 0.935, title, fontsize=15, weight="bold", va="bottom")
        self.fig.text(0.05, 0.915, subtitle, fontsize=10, color="#333", va="bottom")
        if product_id:
            self.fig.text(0.98, 0.935, product_id, fontsize=9, ha="right", va="bottom", family="monospace")
        x0, x1, y0, y1 = grid.extent
        self.ax.set_xlim(x0, x1)
        self.ax.set_ylim(y0, y1)
        self.ax.set_aspect("equal")

    def imshow(self, arr, **kw):
        return self.ax.imshow(arr, extent=self.grid.extent, origin="upper", interpolation="nearest", **kw)

    def add_legend_patch(self, label, colour, **kw):
        self.handles.append(mpatches.Patch(facecolor=colour, edgecolor="#333", label=label, **kw))

    def add_legend_line(self, label, colour, lw=2, ls="-"):
        self.handles.append(Line2D([0], [0], color=colour, lw=lw, ls=ls, label=label))

    def add_legend_marker(self, label, colour, marker="o", size=8, edge="k"):
        self.handles.append(Line2D([0], [0], marker=marker, color="none", markerfacecolor=colour,
                                   markeredgecolor=edge, markersize=size, label=label))

    def going_legend(self):
        for c in (GO, SLOW_GO, NO_GO, RECCE):
            self.add_legend_patch(CLASS_NAMES[c], CLASS_COLOURS[c])

    def colorbar(self, mappable, label):
        cax = self.fig.add_axes([0.745, 0.55, 0.015, 0.25])
        cb = self.fig.colorbar(mappable, cax=cax)
        cb.set_label(label, fontsize=9)
        cb.ax.tick_params(labelsize=8)

    def _furniture(self):
        ax, g = self.ax, self.grid
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        ticks_x = np.arange(np.ceil(x0 / 200) * 200, x1 + 1, 200)
        ticks_y = np.arange(np.ceil(y0 / 200) * 200, y1 + 1, 200)
        ax.set_xticks(ticks_x)
        ax.set_yticks(ticks_y)
        ax.set_xticklabels([f"{t / 1000:.1f}" for t in ticks_x], fontsize=8)
        ax.set_yticklabels([f"{t / 1000:.1f}" for t in ticks_y], fontsize=8)
        ax.set_xlabel("Easting (km)  " + g.crs, fontsize=8)
        ax.set_ylabel("Northing (km)", fontsize=8)
        ax.grid(color="k", alpha=0.25, lw=0.5)
        bx, by = x1 - 290, y0 + 40
        for i in range(4):
            ax.add_patch(mpatches.Rectangle((bx + i * 62.5, by), 62.5, 10, facecolor="k" if i % 2 == 0 else "w",
                                            edgecolor="k", lw=0.8, zorder=20))
        ax.add_patch(mpatches.Rectangle((bx - 15, by - 30), 285, 62, facecolor="white", alpha=0.75, zorder=19, lw=0))
        for d in (0, 125, 250):
            ax.text(bx + d, by + 14, f"{d}", ha="center", fontsize=7, zorder=21)
        ax.text(bx + 125, by - 20, "metres", ha="center", fontsize=7, zorder=21)
        ax.annotate("N", xy=(x0 + 50, y1 - 40), xytext=(x0 + 50, y1 - 120), ha="center", fontsize=12, weight="bold",
                    arrowprops=dict(facecolor="black", width=4, headwidth=12), zorder=21,
                    bbox=dict(boxstyle="round", fc="white", alpha=0.7, lw=0))

    def save(self, path, dpi=150):
        self._furniture()
        y = 0.99
        if self.handles:
            leg = self.side.legend(handles=self.handles, loc="upper left", fontsize=8.5, frameon=True,
                                   title="LEGEND", title_fontsize=9, bbox_to_anchor=(0, y))
            leg.get_frame().set_edgecolor("#333")
        if self.notes:
            self.side.text(0, 0.0, "\n".join(self.notes), fontsize=7.5, va="bottom", ha="left", wrap=True,
                           family="monospace",
                           bbox=dict(boxstyle="square", fc="#f4f4f4", ec="#999"))
        self.fig.savefig(path, dpi=dpi)
        plt.close(self.fig)


def plot_vectors(ax, feats, which=("roads", "streams", "water_bodies", "buildings"), lw_scale=1.0):
    if "water_bodies" in which:
        feats["water_bodies"].plot(ax=ax, color="#3b7fbf", edgecolor="#1f4e79", lw=0.6, zorder=5)
    if "marsh" in which:
        feats["marsh"].plot(ax=ax, facecolor="none", edgecolor="#4a7a9c", hatch="///", lw=0.8, zorder=5)
    if "streams" in which:
        feats["streams"].plot(ax=ax, color="#1f6fbf", lw=2.2 * lw_scale, zorder=6)
    if "roads" in which:
        r = feats["roads"]
        r[r.surface == "paved"].plot(ax=ax, color="#202020", lw=3.2 * lw_scale, zorder=7)
        r[r.surface == "paved"].plot(ax=ax, color="#f5d36b", lw=1.6 * lw_scale, zorder=8)
        r[r.surface == "unpaved"].plot(ax=ax, color="#5a3d1e", lw=1.5 * lw_scale, ls="--", zorder=7)
    if "buildings" in which:
        feats["buildings"].plot(ax=ax, color="#333333", zorder=9)


def going_overlay_points(ax, points: dict):
    for name, (x, y) in points.items():
        ax.plot(x, y, marker="^" if "OBJ" in name else "s", ms=12, mfc="white", mec="k", mew=2, zorder=30)
        ax.text(x + 18, y + 18, name.replace("_", " "), fontsize=9, weight="bold", zorder=31,
                bbox=dict(boxstyle="round", fc="white", alpha=0.85, lw=0.5))
