#!/usr/bin/env python3
"""Generate small synthetic sample data for the geospatial toolkit.

Creates three files in sample_data/ so every tool in the repo can be run end to
end without any real or sensitive data:

    sample_data/grid.tif              a small synthetic GeoTIFF (defines the grid)
    sample_data/reference_points.gpkg a few reference points inside the grid
    sample_data/candidates.csv        candidate points, some near the references

Run once from the repository root:

    python make_sample_data.py

Requires rasterio, geopandas, shapely, numpy, and pandas.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
import geopandas as gpd
from shapely.geometry import Point

# A neutral synthetic extent in geographic coordinates (no real location implied).
WEST, EAST = 10.000, 10.300
SOUTH, NORTH = 50.000, 50.200
WIDTH, HEIGHT = 300, 200          # pixels
CRS = "EPSG:4326"

OUT_DIR = Path("sample_data")
SEED = 42


def make_grid(path: Path) -> None:
    """Write a small synthetic single-band GeoTIFF."""
    rng = np.random.default_rng(SEED)
    # A smooth gradient plus mild noise, just so the raster has structure.
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    data = (xx / WIDTH + yy / HEIGHT) * 100.0
    data = (data + rng.normal(0, 3, size=data.shape)).astype("float32")

    transform = from_bounds(WEST, SOUTH, EAST, NORTH, WIDTH, HEIGHT)
    profile = {
        "driver": "GTiff",
        "height": HEIGHT,
        "width": WIDTH,
        "count": 1,
        "dtype": "float32",
        "crs": CRS,
        "transform": transform,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    print(f"Wrote {path} ({WIDTH}x{HEIGHT}, CRS {CRS})")


def make_reference_points(path: Path) -> gpd.GeoDataFrame:
    """Write a few reference points spread inside the grid extent."""
    coords = [
        (10.05, 50.05),
        (10.15, 50.10),
        (10.25, 50.15),
        (10.10, 50.17),
    ]
    gdf = gpd.GeoDataFrame(
        {"ref_id": range(1, len(coords) + 1)},
        geometry=[Point(lon, lat) for lon, lat in coords],
        crs=CRS,
    )
    gdf.to_file(path, driver="GPKG")
    print(f"Wrote {path} ({len(gdf)} reference points)")
    return gdf


def make_candidates(path: Path, reference: gpd.GeoDataFrame) -> None:
    """Write candidate points: some clustered near references, some far away.

    About 0.02 degrees of longitude here is roughly 1.4 km, so the near points
    sit within a few km of a reference and the far points clearly do not.
    """
    rng = np.random.default_rng(SEED)
    rows = []
    cid = 1

    # Near points: small jitter around each reference point.
    for geom in reference.geometry:
        for _ in range(3):
            lon = geom.x + rng.normal(0, 0.01)
            lat = geom.y + rng.normal(0, 0.01)
            rows.append({"site_id": cid, "longitude": lon, "latitude": lat})
            cid += 1

    # Far points: random across the extent, mostly outside any small buffer.
    for _ in range(8):
        lon = rng.uniform(WEST, EAST)
        lat = rng.uniform(SOUTH, NORTH)
        rows.append({"site_id": cid, "longitude": lon, "latitude": lat})
        cid += 1

    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"Wrote {path} ({len(rows)} candidate points)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_grid(OUT_DIR / "grid.tif")
    reference = make_reference_points(OUT_DIR / "reference_points.gpkg")
    make_candidates(OUT_DIR / "candidates.csv", reference)
    print("Sample data ready in", OUT_DIR.resolve())


if __name__ == "__main__":
    main()
