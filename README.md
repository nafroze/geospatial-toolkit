# geospatial-toolkit

A small set of command-line tools for tiling rasters, mapping grid cells to
processing tiles, and selecting points by distance. Each tool is self-contained,
argument-driven, and built on the open-source Python geospatial stack.

## Tools

| Script | Purpose | Key libraries |
|--------|---------|---------------|
| `generate_tiles.py` | Split a raster into a JSON list of tile windows. | rasterio, numpy |
| `find_tiles_for_cells.py` | Report which tiles cover a set of R##C## grid cells. | rasterio |
| `points_within_buffer.py` | Find points within a distance of any reference point. | geopandas, shapely, pyproj, scipy |

`grid_utils.py` holds shared helpers (tile JSON read/write and grid-cell parsing)
used by the tiling tools.

## Installation

```bash
git clone https://github.com/nafroze/geospatial-toolkit.git
cd geospatial-toolkit
pip install -r requirements.txt
```

Run the tools from the repository root so the shared `grid_utils` module resolves.

## Usage

### Generate tiles

Split a raster into non-overlapping tile windows and write them to JSON:

```bash
python generate_tiles.py --raster sample_data/grid.tif --tile-size 1024 --output tiles.json
```

Height and width can be given directly instead of a raster, and optional row and
column anchors shift the first tile boundary to a chosen pixel index:

```bash
python generate_tiles.py --height 4000 --width 6000 --tile-size 1024 \
    --row-anchor 750 --col-anchor 750 --output tiles.json
```

### Find tiles for grid cells

Given a reference raster and a tiles JSON, report which tiles overlap a set of
grid cells. Cells may be listed individually or as inclusive ranges:

```bash
python find_tiles_for_cells.py \
    --raster sample_data/grid.tif --tiles tiles.json \
    --grid-cells R07C07 R07C08 --grid-size 100
```

```bash
python find_tiles_for_cells.py \
    --raster sample_data/grid.tif --tiles tiles.json \
    --grid-cells R00C00-R02C05 --grid-size 100
```

### Points within a buffer

Find candidate points within a distance (in metres) of the nearest reference
point. Distances are computed in a projected CRS, estimated automatically from the
data unless `--metric-crs` is given. Inputs may be vector files or CSVs with
longitude and latitude columns:

```bash
python points_within_buffer.py \
    --points sample_data/candidates.csv --lon-col longitude --lat-col latitude \
    --reference sample_data/reference_points.gpkg \
    --distance 4000 \
    --output matches.gpkg
```

The output keeps a `dist_m` column with each selected point's distance to its
nearest reference point. Output format follows the `--output` extension (`.gpkg`,
`.shp`, `.geojson`, or `.csv`).

## Sample data

The `sample_data/` folder holds small inputs so every tool can be run end to end
without a large download.

## Repository layout

```
geospatial-toolkit/
├── README.md
├── LICENSE
├── requirements.txt
├── grid_utils.py
├── generate_tiles.py
├── find_tiles_for_cells.py
├── points_within_buffer.py
└── sample_data/
```

## License

Released under the MIT License. See `LICENSE`.
