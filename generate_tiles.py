#!/usr/bin/env python3
"""Generate a JSON list of tile windows covering a raster grid.

Splits a raster of a given height and width into non-overlapping tiles of
`tile_size` x `tile_size` pixels, starting from the origin (0, 0). Each tile is
recorded as a window with `row_off`, `col_off`, `height`, and `width`, suitable
for tools that process a raster one tile at a time.

The optional row and column anchors shift the first tile boundary to a chosen
pixel index. This is useful when a dense region of interest would otherwise
straddle a default boundary: placing a boundary at the anchor keeps that region
within fewer tiles and spreads work more evenly.

Example:
    python generate_tiles.py --raster grid.tif --tile-size 1024 --output tiles.json
    python generate_tiles.py --height 4000 --width 6000 --tile-size 1024 \
        --row-anchor 750 --col-anchor 750 --output tiles.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

from grid_utils import save_tiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def axis_segments(length: int, tile: int, anchor: int) -> List[Tuple[int, int]]:
    """Split [0, length) into contiguous windows along one axis.

    anchor == 0: regular tiling [0, tile), [tile, 2*tile), ...
    anchor > 0:  [0, anchor), [anchor, anchor + tile), ... so a boundary
                 falls exactly at `anchor`.
    """
    if length <= 0:
        return []
    if tile <= 0:
        raise ValueError("tile must be positive")
    anchor = max(0, min(anchor, length))

    out: List[Tuple[int, int]] = []
    pos = 0
    if anchor > 0:
        out.append((0, anchor))
        pos = anchor
    while pos < length:
        out.append((pos, min(pos + tile, length)))
        pos += tile
    return out


def build_tiles(height: int, width: int, tile: int,
                row_anchor: int, col_anchor: int) -> List[dict]:
    """Build the full list of tile windows for a raster of (height, width)."""
    row_segs = axis_segments(height, tile, row_anchor)
    col_segs = axis_segments(width, tile, col_anchor)
    tiles: List[dict] = []
    for r0, r1 in row_segs:
        for c0, c1 in col_segs:
            tiles.append({
                "row_off": r0,
                "col_off": c0,
                "height": r1 - r0,
                "width": c1 - c0,
            })
    return tiles


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--height", type=int, help="Raster height in pixels (y).")
    p.add_argument("--width", type=int, help="Raster width in pixels (x).")
    p.add_argument("--raster", type=str,
                   help="Read height/width from this GeoTIFF instead of --height/--width.")
    p.add_argument("--tile-size", type=int, default=1024,
                   help="Tile size in pixels (default: 1024).")
    p.add_argument("--row-anchor", type=int, default=0,
                   help="First row boundary in pixels (0 = regular tiling).")
    p.add_argument("--col-anchor", type=int, default=0,
                   help="First column boundary in pixels (0 = regular tiling).")
    p.add_argument("--output", type=Path, default=Path("tiles.json"),
                   help="Output JSON path (default: tiles.json).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print a summary only, do not write the file.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    height, width = args.height, args.width
    if args.raster:
        try:
            import rasterio
            with rasterio.open(args.raster) as src:
                width, height = src.width, src.height
        except Exception as exc:
            logger.error("Could not read raster %s: %s", args.raster, exc)
            return 1
    if height is None or width is None:
        logger.error("Set --height/--width, or --raster.")
        return 1

    tiles = build_tiles(height, width, args.tile_size, args.row_anchor, args.col_anchor)

    logger.info("Raster size: %d x %d", width, height)
    logger.info("Tile size: %d, row_anchor=%d, col_anchor=%d",
                args.tile_size, args.row_anchor, args.col_anchor)
    logger.info("Tiles: %d", len(tiles))
    if tiles:
        hs = [t["height"] for t in tiles]
        ws = [t["width"] for t in tiles]
        logger.info("Height range: %d-%d, width range: %d-%d",
                    min(hs), max(hs), min(ws), max(ws))

    if args.dry_run:
        return 0

    save_tiles(tiles, args.output)
    logger.info("Wrote %s", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
