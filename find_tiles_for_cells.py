#!/usr/bin/env python3
"""Find which tile windows cover a set of grid cells.

A grid cell is a square block of `--grid-size` pixels, labelled R##C## by its row
and column index. This tool converts each requested grid cell to a geographic
bounding box using a reference raster, then reports which tiles (from a tiles JSON
produced by generate_tiles.py) overlap that region.

Grid cells may be listed individually or as inclusive ranges, e.g.
"R00C00 R01C02" or "R00C00-R02C05".

Example:
    python find_tiles_for_cells.py \
        --raster grid.tif --tiles tiles.json \
        --grid-cells R07C07 R07C08 --grid-size 100
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Tuple

from grid_utils import parse_grid_cell, expand_grid_cell_range, load_tiles

try:
    import rasterio
    from rasterio.transform import xy
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def grid_cell_to_geo_bbox(raster_path: str, grid_size: int,
                          row: int, col: int) -> Tuple[float, float, float, float]:
    """Convert a grid cell to a geographic bounding box (xmin, xmax, ymin, ymax)."""
    with rasterio.open(raster_path) as src:
        bounds = src.bounds
        width, height = src.width, src.height

        cell_x = (bounds.right - bounds.left) / width * grid_size
        cell_y = (bounds.top - bounds.bottom) / height * grid_size

        x_min = bounds.left + col * cell_x
        x_max = bounds.left + (col + 1) * cell_x
        y_min = bounds.bottom + row * cell_y
        y_max = bounds.bottom + (row + 1) * cell_y
        return x_min, x_max, y_min, y_max


def tile_geo_bbox(tile: dict, transform) -> Tuple[float, float, float, float]:
    """Geographic bounding box of a tile window (xmin, xmax, ymin, ymax)."""
    r0, c0 = tile["row_off"], tile["col_off"]
    r1, c1 = r0 + tile["height"], c0 + tile["width"]
    corners = [(r0, c0), (r0, c1), (r1, c1), (r1, c0)]

    xs, ys = [], []
    for r, c in corners:
        x, y = xy(transform, r, c)
        xs.append(x)
        ys.append(y)
    return min(xs), max(xs), min(ys), max(ys)


def tiles_overlapping(bbox: Tuple[float, float, float, float],
                      tiles: List[dict], transform) -> List[int]:
    """Return indices of tiles whose bounding box overlaps `bbox`."""
    x_min, x_max, y_min, y_max = bbox
    overlapping = []
    for idx, tile in enumerate(tiles):
        tx_min, tx_max, ty_min, ty_max = tile_geo_bbox(tile, transform)
        if x_max >= tx_min and x_min <= tx_max and y_max >= ty_min and y_min <= ty_max:
            overlapping.append(idx)
    return overlapping


def find_tiles_for_cells(raster_path: str, tiles_path: str,
                         grid_cells: List[str], grid_size: int = 100) -> None:
    """Report which tiles cover the requested grid cells."""
    if not HAS_RASTERIO:
        logger.error("rasterio is required for this tool.")
        return
    if not Path(raster_path).exists():
        logger.error("Raster not found: %s", raster_path)
        return
    if not Path(tiles_path).exists():
        logger.error("Tiles JSON not found: %s", tiles_path)
        return

    tiles = load_tiles(Path(tiles_path))
    if not tiles:
        logger.error("No tiles loaded from %s", tiles_path)
        return

    logger.info("Raster: %s | grid size: %d px | cells: %s",
                raster_path, grid_size, ", ".join(grid_cells))

    all_x, all_y = [], []
    for cell in grid_cells:
        try:
            row, col = parse_grid_cell(cell)
            x_min, x_max, y_min, y_max = grid_cell_to_geo_bbox(
                raster_path, grid_size, row, col)
            all_x.extend([x_min, x_max])
            all_y.extend([y_min, y_max])
            logger.info("  %-8s x [%.4f, %.4f]  y [%.4f, %.4f]",
                        cell, x_min, x_max, y_min, y_max)
        except Exception as exc:
            logger.warning("  Skipping %s: %s", cell, exc)

    if not all_x:
        logger.error("No valid grid cells processed.")
        return

    region = (min(all_x), max(all_x), min(all_y), max(all_y))
    logger.info("Region bounds: x [%.4f, %.4f]  y [%.4f, %.4f]", *(
        region[0], region[1], region[2], region[3]))

    with rasterio.open(raster_path) as src:
        transform = src.transform

    overlapping = tiles_overlapping(region, tiles, transform)
    if not overlapping:
        logger.info("No tiles overlap this region.")
        return

    logger.info("Tiles overlapping this region:")
    for idx in sorted(overlapping):
        tile = tiles[idx]
        tx_min, tx_max, ty_min, ty_max = tile_geo_bbox(tile, transform)
        logger.info("  tile %3d: x [%.4f, %.4f]  y [%.4f, %.4f]  "
                    "(row_off=%d, col_off=%d, %dx%d)",
                    idx, tx_min, tx_max, ty_min, ty_max,
                    tile["row_off"], tile["col_off"], tile["height"], tile["width"])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--raster", required=True,
                   help="Reference raster defining the grid extent and transform.")
    p.add_argument("--tiles", required=True,
                   help="Tiles JSON produced by generate_tiles.py.")
    p.add_argument("--grid-cells", nargs="+", required=True,
                   help="Grid cells or ranges, e.g. R00C00 R01C02 or R00C00-R02C05.")
    p.add_argument("--grid-size", type=int, default=100,
                   help="Grid cell size in pixels (default: 100).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cells: List[str] = []
    for token in args.grid_cells:
        cells.extend(expand_grid_cell_range(token))
    find_tiles_for_cells(args.raster, args.tiles, cells, args.grid_size)


if __name__ == "__main__":
    main()
