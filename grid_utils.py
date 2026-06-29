#!/usr/bin/env python3
"""Shared helpers for the tiling and grid-cell tools.

Holds the small pieces both command-line tools depend on: reading and writing the
tile JSON, and parsing R##C## grid-cell labels.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

_GRID_CELL_RE = re.compile(r"^R(\d+)C(\d+)$", re.IGNORECASE)


def parse_grid_cell(cell: str) -> Tuple[int, int]:
    """Parse a grid-cell label such as 'R07C12' into a (row, col) tuple."""
    match = _GRID_CELL_RE.match(cell.strip())
    if not match:
        raise ValueError(f"Invalid grid-cell label: {cell!r} (expected R##C##)")
    return int(match.group(1)), int(match.group(2))


def expand_grid_cell_range(token: str) -> List[str]:
    """Expand a token like 'R00C00-R01C03' into the inclusive rectangle of labels.

    A token without a hyphen is returned unchanged, wrapped in a list.
    """
    if "-" not in token:
        return [token]
    start, end = token.split("-", 1)
    r0, c0 = parse_grid_cell(start)
    r1, c1 = parse_grid_cell(end)
    return [f"R{r:02d}C{c:02d}"
            for r in range(r0, r1 + 1)
            for c in range(c0, c1 + 1)]


def load_tiles(path: Path) -> List[dict]:
    """Load a list of tile windows from a JSON file."""
    with open(path) as f:
        return json.load(f)


def save_tiles(tiles: List[dict], path: Path) -> None:
    """Write a list of tile windows to a JSON file, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(tiles, f, indent=2)
        f.write("\n")
