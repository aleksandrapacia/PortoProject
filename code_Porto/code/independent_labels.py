#!/usr/bin/env python3
"""Independent test of the RF map vs ESA WorldCover (and optional QGIS ROIs).

Training labels in ml_Porto_analysis.py came from NDVI/MNDWI thresholds.
This script does not retrain. It scores map_python_random_forest.tif against
an external 10 m product (WorldCover) and, if present, hand ROIs.

CORINE is 100 m — too coarse for this 20 m stack — so WorldCover is the
reference. DEM is a later step, not here.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import planetary_computer
import rasterio
from pystac_client import Client
from rasterio.features import rasterize
from rasterio.warp import Resampling, reproject, transform_bounds, transform_geom
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
CLASS_TIF = ROOT / "results" / "map_python_random_forest.tif"
ROI_PATH = ROOT / "labels" / "rois.geojson"
OUT_DIR = ROOT / "results"
FIG_DIR = ROOT / "results"

CLASS_NAMES = ["Water", "Vegetation", "Urban", "Bare Soil"]
CLASS_IDS = [1, 2, 3, 4]

# ESA WorldCover v200 -> our 4 classes (0 = ignore)
WC_MAP = {
    10: 2,  # tree cover
    20: 2,  # shrubland
    30: 2,  # grassland
    40: 2,  # cropland
    50: 3,  # built-up
    60: 4,  # bare / sparse
    70: 0,  # snow/ice
    80: 1,  # permanent water
    90: 2,  # herbaceous wetland
    95: 2,  # mangroves
    100: 2,  # moss/lichen
}


def remap_worldcover(arr: np.ndarray) -> np.ndarray:
    out = np.zeros(arr.shape, dtype=np.uint8)
    for src, dst in WC_MAP.items():
        out[arr == src] = dst
    return out


def fetch_worldcover(ref: rasterio.io.DatasetReader) -> np.ndarray:
    bbox = transform_bounds(ref.crs, "EPSG:4326", *ref.bounds)
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    items = list(
        catalog.search(collections=["esa-worldcover"], bbox=bbox).items()
    )
    items = [it for it in items if "2021" in it.id] or items
    if not items:
        raise SystemExit("No ESA WorldCover item over this AOI.")
    item = planetary_computer.sign(items[0])
    href = item.assets["map"].href
    print(f"WorldCover item: {items[0].id}")

    dst = np.zeros((ref.height, ref.width), dtype=np.uint8)
    with rasterio.open(href) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref.transform,
            dst_crs=ref.crs,
            resampling=Resampling.nearest,
        )
    return dst


def rasterize_rois(ref: rasterio.io.DatasetReader, path: Path) -> np.ndarray | None:
    if not path.exists():
        print(f"No ROI file at {path} — skip QGIS labels for now.")
        return None
    data = json.loads(path.read_text())
    feats = data.get("features") or []
    if not feats:
        print("ROI GeoJSON is empty. Draw polygons in QGIS (class = 1..4) and rerun.")
        return None

    shapes = []
    for feat in feats:
        props = feat.get("properties") or {}
        cls = props.get("class", props.get("class_id"))
        if cls is None:
            continue
        cls = int(cls)
        if cls not in CLASS_IDS:
            continue
        geom = feat["geometry"]
        geom = transform_geom("EPSG:4326", ref.crs.to_string(), geom, precision=6)
        shapes.append((geom, cls))

    if not shapes:
        print("ROI file has no features with class 1-4.")
        return None

    roi = rasterize(
        shapes,
        out_shape=(ref.height, ref.width),
        transform=ref.transform,
        fill=0,
        dtype=np.uint8,
        all_touched=True,
    )
    print(f"Rasterized {len(shapes)} ROI polygon(s).")
    return roi


def score(pred: np.ndarray, ref: np.ndarray, title: str) -> dict | None:
    mask = (ref > 0) & (pred > 0)
    n = int(mask.sum())
    if n < 50:
        print(f"\n{title}: too few overlapping pixels ({n}).")
        return None
    y_true, y_hat = ref[mask], pred[mask]
    print(f"\n=== {title}  (n = {n:,} pixels) ===")
    print(
        classification_report(
            y_true,
            y_hat,
            labels=CLASS_IDS,
            target_names=CLASS_NAMES,
            zero_division=0,
        )
    )
    cm = confusion_matrix(y_true, y_hat, labels=CLASS_IDS)
    return {"title": title, "n": n, "cm": cm, "acc": float((y_true == y_hat).mean())}


def plot_cm(result: dict, path: Path) -> None:
    cm = result["cm"]
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(4), CLASS_NAMES, rotation=30, ha="right")
    ax.set_yticks(range(4), CLASS_NAMES)
    ax.set_xlabel("Predicted (RF map)")
    ax.set_ylabel("Independent label")
    ax.set_title(f"{result['title']}\naccuracy = {result['acc']:.3f}  n = {result['n']:,}")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f"Wrote {path}")


def plot_side_by_side(pred, wc, path: Path) -> None:
    colors = ["#000000", "#1f77b4", "#2ca02c", "#d62728", "#8c564b"]
    cmap = mcolors.ListedColormap(colors)
    norm = mcolors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    axes[0].imshow(pred, cmap=cmap, norm=norm)
    axes[0].set_title("RF map (this project)")
    axes[1].imshow(wc, cmap=cmap, norm=norm)
    axes[1].set_title("ESA WorldCover 2021 (mapped to 4 classes)")
    for ax in axes:
        ax.axis("off")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    print(f"Wrote {path}")


def main() -> None:
    if not CLASS_TIF.exists():
        raise SystemExit(f"Missing {CLASS_TIF}. Run ml_Porto_analysis.py first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    with rasterio.open(CLASS_TIF) as ref:
        pred = ref.read(1)
        profile = ref.profile.copy()
        print(f"RF map: {pred.shape}  CRS={ref.crs}  res={ref.res}")
        wc_raw = fetch_worldcover(ref)
        wc = remap_worldcover(wc_raw)
        roi = rasterize_rois(ref, ROI_PATH)

        profile.update(count=1, dtype=rasterio.uint8, nodata=0, compress="lzw")
        wc_tif = OUT_DIR / "map_worldcover_4class.tif"
        with rasterio.open(wc_tif, "w", **profile) as dst:
            dst.write(wc, 1)
        print(f"Wrote {wc_tif}")

    plot_side_by_side(pred, wc, FIG_DIR / "06_python_rf_vs_worldcover.png")

    wc_res = score(pred, wc, "RF vs ESA WorldCover 2021")
    if wc_res:
        plot_cm(wc_res, FIG_DIR / "07_python_rf_vs_worldcover_confusion.png")

    if roi is not None:
        roi_res = score(pred, roi, "RF vs QGIS ROIs")
        if roi_res:
            plot_cm(roi_res, FIG_DIR / "08_python_rf_vs_qgis_rois_confusion.png")
        print(
            "WorldCover is wall-to-wall. ROIs are few polygons you trust. "
            "They will not match each other pixel-for-pixel; that comparison is the point."
        )
    else:
        print(
            "\nNext: in QGIS, digitize a few polygons per class into "
            f"{ROI_PATH} (property class = 1 water, 2 veg, 3 urban, 4 soil, CRS WGS84) "
            "and rerun this script. DEM comes after that."
        )


if __name__ == "__main__":
    main()
