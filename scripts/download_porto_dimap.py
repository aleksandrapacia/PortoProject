#!/usr/bin/env python3
"""Download a Porto / Douro Sentinel-2 subset and write BEAM-DIMAP via SNAP gpt."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import planetary_computer
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from pystac_client import Client

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
GPT = Path("/Users/olapacia/Desktop/esa-snap/bin/gpt")

# Douro mouth + inner shelf + lower estuary (Porto–Gaia)
BBOX = [-8.85, 41.05, -8.45, 41.22]  # W,S,E,N
# C2RCC-relevant MSI bands (L2A asset names on Planetary Computer)
BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12", "SCL"]
TARGET_RES = 10.0


def find_scene() -> dict:
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=BBOX,
        datetime="2023-01-01/2025-12-31",
        query={"eo:cloud_cover": {"lt": 8}},
        sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        max_items=20,
    )
    items = list(search.items())
    if not items:
        raise SystemExit("No low-cloud Sentinel-2 scenes over Porto.")

    # Prefer tile T29TNF (Porto)
    items.sort(key=lambda it: (0 if "T29TNF" in it.id else 1, it.properties.get("eo:cloud_cover", 99)))
    item = items[0]
    signed = planetary_computer.sign(item)
    meta = {
        "id": item.id,
        "datetime": item.datetime.isoformat() if item.datetime else None,
        "cloud_cover": item.properties.get("eo:cloud_cover"),
        "platform": item.properties.get("platform"),
        "mgrs": item.properties.get("s2:mgrs_tile"),
        "hrefs": {b: signed.assets[b].href for b in BANDS if b in signed.assets},
    }
    return meta


def utm_bbox(crs) -> tuple[float, float, float, float]:
    return transform_bounds("EPSG:4326", crs, *BBOX)


def read_window(href: str, bounds_utm, height: int, width: int) -> np.ndarray:
    with rasterio.open(href) as src:
        window = from_bounds(*bounds_utm, transform=src.transform)
        data = src.read(
            1,
            window=window,
            boundless=True,
            fill_value=0,
            out_shape=(height, width),
            resampling=Resampling.bilinear,
        )
        return data.astype(np.float32)


def write_stack(meta: dict) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)

    # Use 10 m band B04 to define the grid
    ref_href = meta["hrefs"]["B04"]
    with rasterio.open(ref_href) as ref:
        bounds_utm = utm_bbox(ref.crs)
        window = from_bounds(*bounds_utm, transform=ref.transform)
        win = window.round_offsets().round_lengths()
        transform = rasterio.windows.transform(win, ref.transform)
        height, width = int(win.height), int(win.width)
        crs = ref.crs
        nodata = 0

    arrays = []
    names = []
    for band in BANDS:
        href = meta["hrefs"].get(band)
        if not href:
            continue
        print(f"  reading {band} …")
        arr = read_window(href, bounds_utm, height, width)
        arrays.append(arr)
        names.append(band)

    tif = RAW / f"{meta['id']}_douro_subset.tif"
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": len(arrays),
        "height": height,
        "width": width,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": "deflate",
        "tiled": True,
    }
    with rasterio.open(tif, "w", **profile) as dst:
        for i, (arr, name) in enumerate(zip(arrays, names), start=1):
            dst.write(arr, i)
            dst.set_band_description(i, name)
    (RAW / f"{meta['id']}_stac.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote GeoTIFF {tif}  ({width} x {height}, {len(arrays)} bands)")
    return tif


def to_dimap(tif: Path, product_id: str) -> Path:
    out = PROC / f"{product_id}_douro"
    out.parent.mkdir(parents=True, exist_ok=True)
    dim = Path(str(out) + ".dim")
    cmd = [
        str(GPT),
        "Write",
        f"-Ssource={tif}",
        f"-Pfile={dim}",
        "-PformatName=BEAM-DIMAP",
    ]
    print("SNAP gpt:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    if not dim.exists():
        raise SystemExit(f"SNAP did not write {dim}")
    print(f"Wrote BEAM-DIMAP {dim}")
    return dim


def main() -> None:
    print("Searching Planetary Computer for a low-cloud Porto scene …")
    meta = find_scene()
    print(f"Scene: {meta['id']}  cloud={meta['cloud_cover']}%  {meta['datetime']}")
    tif = write_stack(meta)
    if not GPT.exists():
        print("SNAP gpt not found; left GeoTIFF only.", file=sys.stderr)
        return
    to_dimap(tif, meta["id"])


if __name__ == "__main__":
    main()
