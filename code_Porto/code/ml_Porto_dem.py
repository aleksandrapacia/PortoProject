#!/usr/bin/env python3
"""Next analysis step: Copernicus DEM + WorldCover labels.

The first RF (ml_Porto_analysis.py) was trained on NDVI/MNDWI thresholds.
That score is a leak. Here the labels are ESA WorldCover 2021 (already on
the collocate grid). Features are still raw S1+S2 bands. Then the same
model is trained again with elevation, slope and aspect.

Spatial-block CV is the number to report. Full-scene maps are for looking.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import planetary_computer
import rasterio
from pystac_client import Client
from rasterio.warp import Resampling, reproject, transform_bounds
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"

TIF_PATH = DATA / "collocate.tif"
DIM_PATH = DATA / "collocate.dim"
WC_PATH = RESULTS / "map_worldcover_4class.tif"
DEM_PATH = RESULTS / "map_copernicus_dem.tif"

OPTICAL_SAR = [
    "B2_M",
    "B3_M",
    "B8_M",
    "B11_M",
    "Sigma0_VV_S",
    "Sigma0_VH_S",
]
DEM_NAMES = ["elevation", "slope", "aspect_sin", "aspect_cos"]
CLASS_NAMES = ["Water", "Vegetation", "Urban", "Bare Soil"]
CLASS_IDS = [1, 2, 3, 4]
COLORS = ["#000000", "#1f77b4", "#2ca02c", "#d62728", "#8c564b"]


def load_stack() -> tuple[np.ndarray, list[str], rasterio.Affine, object, dict]:
    with rasterio.open(TIF_PATH) as src:
        cube = src.read()
        transform = src.transform
        crs = src.crs
        profile = src.profile.copy()
        print(f"collocate: {src.height} x {src.width}  CRS={crs}  res={src.res}")

    band_names = [
        elem.text for elem in ET.parse(DIM_PATH).getroot().findall(".//BAND_NAME")
    ]
    missing = [b for b in OPTICAL_SAR if b not in band_names]
    if missing:
        raise SystemExit(f"Missing bands in {DIM_PATH}: {missing}")
    idx = [band_names.index(b) for b in OPTICAL_SAR]
    optical = np.transpose(cube[idx], (1, 2, 0)).astype(np.float32)
    optical = np.nan_to_num(optical, nan=0.0, posinf=0.0, neginf=0.0)
    return optical, OPTICAL_SAR, transform, crs, profile


def fetch_dem(ref: rasterio.io.DatasetReader) -> np.ndarray:
    bbox = transform_bounds(ref.crs, "EPSG:4326", *ref.bounds)
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    items = list(catalog.search(collections=["cop-dem-glo-30"], bbox=bbox).items())
    if not items:
        raise SystemExit("No Copernicus DEM tile over this AOI.")
    print(f"DEM tiles: {[it.id for it in items]}")

    dst = np.full((ref.height, ref.width), np.nan, dtype=np.float32)
    for it in items:
        signed = planetary_computer.sign(it)
        href = signed.assets["data"].href
        tmp = np.full_like(dst, np.nan)
        with rasterio.open(href) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=tmp,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref.transform,
                dst_crs=ref.crs,
                resampling=Resampling.bilinear,
                src_nodata=src.nodata,
                dst_nodata=np.nan,
            )
        ok = np.isfinite(tmp)
        dst[ok] = tmp[ok]
    if not np.isfinite(dst).any():
        raise SystemExit("DEM reprojection produced no valid pixels.")
    fill = float(np.nanmedian(dst))
    dst = np.where(np.isfinite(dst), dst, fill).astype(np.float32)
    return dst


def slope_aspect(elev: np.ndarray, res_x: float, res_y: float) -> tuple[np.ndarray, np.ndarray]:
    d_row, d_col = np.gradient(elev, abs(res_y), abs(res_x))
    dz_dy = -d_row
    dz_dx = d_col
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy))).astype(np.float32)
    aspect = np.degrees(np.arctan2(dz_dx, dz_dy))
    aspect = np.mod(aspect + 360.0, 360.0).astype(np.float32)
    return slope, aspect


def dem_features(elev: np.ndarray, res_x: float, res_y: float) -> tuple[np.ndarray, np.ndarray]:
    slope, aspect = slope_aspect(elev, res_x, res_y)
    rad = np.radians(aspect)
    stack = np.stack(
        [elev, slope, np.sin(rad).astype(np.float32), np.cos(rad).astype(np.float32)],
        axis=-1,
    )
    return stack, slope


def spatial_groups(height: int, width: int, valid: np.ndarray, n_blocks: int = 10) -> np.ndarray:
    rows, cols = np.unravel_index(np.where(valid.ravel())[0], (height, width))
    br = max(height // n_blocks, 1)
    bc = max(width // n_blocks, 1)
    r = np.clip(rows // br, 0, n_blocks - 1)
    c = np.clip(cols // bc, 0, n_blocks - 1)
    return r * n_blocks + c


def run_spatial_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray, title: str) -> dict:
    sample_size = 80000
    if len(y) > sample_size:
        rng = np.random.default_rng(42)
        sel = rng.choice(len(y), size=sample_size, replace=False)
        X, y, groups = X[sel], y[sel], groups[sel]

    gkf = GroupKFold(n_splits=5)
    accs = []
    y_true_all, y_hat_all = [], []
    print(f"\n=== SPATIAL CV  {title} ===")
    for fold, (tr, va) in enumerate(gkf.split(X, y, groups=groups), 1):
        rf = RandomForestClassifier(
            n_estimators=40, max_depth=14, random_state=42, n_jobs=-1
        )
        rf.fit(X[tr], y[tr])
        hat = rf.predict(X[va])
        acc = float((hat == y[va]).mean())
        accs.append(acc)
        y_true_all.append(y[va])
        y_hat_all.append(hat)
        print(f"Fold {fold}: {acc:.4f}")
    y_true = np.concatenate(y_true_all)
    y_hat = np.concatenate(y_hat_all)
    print(f"Mean spatial accuracy: {np.mean(accs):.4f} (+/- {np.std(accs):.4f})")
    print(
        classification_report(
            y_true, y_hat, labels=CLASS_IDS, target_names=CLASS_NAMES, zero_division=0
        )
    )
    return {
        "title": title,
        "accs": accs,
        "mean": float(np.mean(accs)),
        "std": float(np.std(accs)),
        "cm": confusion_matrix(y_true, y_hat, labels=CLASS_IDS),
        "y_true": y_true,
        "y_hat": y_hat,
        "n": int(len(y_true)),
    }


def fit_and_predict(X_valid, y_valid, X_all, sample_size=120000) -> tuple[RandomForestClassifier, np.ndarray]:
    if len(y_valid) > sample_size:
        rng = np.random.default_rng(42)
        sel = rng.choice(len(y_valid), size=sample_size, replace=False)
        X_fit, y_fit = X_valid[sel], y_valid[sel]
    else:
        X_fit, y_fit = X_valid, y_valid
    rf = RandomForestClassifier(
        n_estimators=80, max_depth=16, random_state=42, n_jobs=-1
    )
    rf.fit(X_fit, y_fit)
    pred = np.zeros(X_all.shape[0], dtype=np.uint8)
    chunk = 400000
    for i in range(0, X_all.shape[0], chunk):
        pred[i : i + chunk] = rf.predict(X_all[i : i + chunk])
    return rf, pred


def plot_class_png(arr: np.ndarray, path: Path, title: str) -> None:
    cmap = mcolors.ListedColormap(COLORS)
    norm = mcolors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(arr, cmap=cmap, norm=norm)
    fig.colorbar(
        im,
        ax=ax,
        ticks=[0, 1, 2, 3, 4],
        label="0 unlabeled · 1 water · 2 vegetation · 3 urban · 4 bare soil",
    )
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {path}")


def plot_cm(cm: np.ndarray, acc: float, n: int, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(4), CLASS_NAMES, rotation=30, ha="right")
    ax.set_yticks(range(4), CLASS_NAMES)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("WorldCover (spatial-block hold-out)")
    ax.set_title(f"{title}\naccuracy = {acc:.3f}  n = {n:,}")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {path}")


def plot_importance(names: list[str], values: np.ndarray, path: Path, title: str) -> None:
    order = np.argsort(values)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(np.array(names)[order], values[order], color="#1a7a7a")
    ax.set_xlabel("Feature importance")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {path}")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    optical, feat_s1s2, transform, crs, profile = load_stack()
    height, width = optical.shape[:2]
    res_x, res_y = 20.0, 20.0

    if not WC_PATH.exists():
        raise SystemExit(f"Missing {WC_PATH}. Run independent_labels.py first.")
    with rasterio.open(WC_PATH) as src:
        wc = src.read(1)
    print("WorldCover class counts:")
    for i, name in zip(CLASS_IDS, CLASS_NAMES):
        print(f"  {name}: {int((wc == i).sum()):,}")

    with rasterio.open(TIF_PATH) as ref:
        if DEM_PATH.exists():
            with rasterio.open(DEM_PATH) as dsrc:
                elev = dsrc.read(1).astype(np.float32)
            print(f"Loaded cached DEM {DEM_PATH}")
        else:
            elev = fetch_dem(ref)
            dem_profile = ref.profile.copy()
            dem_profile.update(count=1, dtype=rasterio.float32, nodata=None, compress="lzw")
            with rasterio.open(DEM_PATH, "w", **dem_profile) as dst:
                dst.write(elev, 1)
            print(f"Wrote {DEM_PATH}")

    dem_stack, slope = dem_features(elev, res_x, res_y)
    print(
        f"Elevation m: {elev.min():.1f} … {elev.max():.1f}  "
        f"slope deg: {slope.min():.1f} … {slope.max():.1f}"
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(elev, cmap="terrain")
    fig.colorbar(im, ax=ax, label="Elevation (m)")
    ax.set_title("Copernicus GLO-30 DEM (Porto)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(RESULTS / "09_copernicus_dem_elevation.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(slope, cmap="YlOrBr")
    fig.colorbar(im, ax=ax, label="Slope (degrees)")
    ax.set_title("Slope from Copernicus DEM")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(RESULTS / "10_copernicus_dem_slope.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("Wrote DEM figures 09–10")

    labels = wc.ravel()
    valid = labels > 0
    X_s1s2 = optical.reshape(-1, optical.shape[-1])
    X_dem = np.concatenate([X_s1s2, dem_stack.reshape(-1, dem_stack.shape[-1])], axis=1)
    y = labels[valid]
    groups = spatial_groups(height, width, wc > 0)

    cv_base = run_spatial_cv(X_s1s2[valid], y, groups, "S1+S2 (WorldCover labels)")
    cv_dem = run_spatial_cv(X_dem[valid], y, groups, "S1+S2+DEM (WorldCover labels)")

    print("\nFitting full-scene models (subsampled training)...")
    rf_base, pred_base = fit_and_predict(X_s1s2[valid], y, X_s1s2)
    rf_dem, pred_dem = fit_and_predict(X_dem[valid], y, X_dem)
    map_base = pred_base.reshape(height, width)
    map_dem = pred_dem.reshape(height, width)

    out_profile = profile.copy()
    out_profile.update(count=1, dtype=rasterio.uint8, nodata=0, compress="lzw")
    with rasterio.open(RESULTS / "map_python_rf_worldcover_labels.tif", "w", **out_profile) as dst:
        dst.write(map_base, 1)
    with rasterio.open(RESULTS / "map_python_rf_worldcover_labels_dem.tif", "w", **out_profile) as dst:
        dst.write(map_dem, 1)

    plot_class_png(
        map_base,
        RESULTS / "11_python_rf_worldcover_labels.png",
        "RF trained on WorldCover labels (S1+S2 only)",
    )
    plot_class_png(
        map_dem,
        RESULTS / "12_python_rf_worldcover_labels_dem.png",
        "RF trained on WorldCover labels (S1+S2+DEM)",
    )

    cmap = mcolors.ListedColormap(COLORS)
    norm = mcolors.BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    axes[0].imshow(wc, cmap=cmap, norm=norm)
    axes[0].set_title("ESA WorldCover 2021")
    axes[1].imshow(map_base, cmap=cmap, norm=norm)
    axes[1].set_title("RF  S1+S2")
    axes[2].imshow(map_dem, cmap=cmap, norm=norm)
    axes[2].set_title("RF  S1+S2+DEM")
    for ax in axes:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(RESULTS / "13_python_rf_wc_vs_s1s2_vs_dem.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {RESULTS / '13_python_rf_wc_vs_s1s2_vs_dem.png'}")

    names_dem = feat_s1s2 + DEM_NAMES
    plot_importance(
        names_dem,
        rf_dem.feature_importances_,
        RESULTS / "14_python_feature_importance_dem.png",
        "Feature importance: S1+S2+DEM (WorldCover labels)",
    )

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.bar(
        ["S1+S2", "S1+S2+DEM"],
        [cv_base["mean"], cv_dem["mean"]],
        yerr=[cv_base["std"], cv_dem["std"]],
        color=["#4c78a8", "#f58518"],
        capsize=6,
    )
    ax.set_ylim(0, 1)
    ax.set_ylabel("Spatial-block CV accuracy")
    ax.set_title("Does DEM help? (WorldCover labels, GroupKFold)")
    fig.tight_layout()
    fig.savefig(RESULTS / "15_spatial_cv_s1s2_vs_dem.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {RESULTS / '15_spatial_cv_s1s2_vs_dem.png'}")

    plot_cm(
        cv_dem["cm"],
        cv_dem["mean"],
        cv_dem["n"],
        "S1+S2+DEM vs WorldCover (spatial CV)",
        RESULTS / "16_python_rf_dem_spatial_cv_confusion.png",
    )

    print("\nDone. Maps and figures 09–16 are in", RESULTS)


if __name__ == "__main__":
    main()
