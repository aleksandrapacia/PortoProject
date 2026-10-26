import xml.etree.ElementTree as ET
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupKFold, train_test_split

# ==========================================
# 1. READ RASTER & METADATA
# ==========================================
tif_path = 'collocate.tif'
dim_path = 'collocate.dim'

with rasterio.open(tif_path) as src:
    print("- - - RASTER METADATA - - -")
    print(f"Dimensions (Height x Width): {src.height} x {src.width}")
    print(f"Number of bands: {src.count}")
    print(f"CRS: {src.crs}")
    print(f"Pixel resolution: {src.res}")

    data = src.read()  # (bands, H, W)
    profile = src.profile.copy()
    height, width = src.height, src.width

# ==========================================
# 2. MATCH BAND NAMES FROM SNAP .DIM
# ==========================================
tree = ET.parse(dim_path)
root = tree.getroot()
band_names = [elem.text for elem in root.findall('.//BAND_NAME')]

print(f"\nDiscovered {len(band_names)} bands in .dim file.")

# ==========================================
# 3. SELECT REQUIRED BANDS & FLATTEN
# ==========================================
target_bands = [
    'B2_M',
    'B3_M',
    'B8_M',
    'B11_M',
    'MNDWI_M',
    'NDVI_M',
    'Sigma0_VV_S',
    'Sigma0_VH_S',
]

# Verify all required bands exist
missing = [b for b in target_bands if b not in band_names]
if missing:
    raise ValueError(f"Missing expected bands in {dim_path}: {missing}")

selected_indices = [band_names.index(b) for b in target_bands]

# Extract selected 3D cube and reshape to 2D (pixels, features)
X_selected = data[selected_indices, :, :]
X_matrix = np.transpose(X_selected, (1, 2, 0)).reshape(-1, len(target_bands))
X_matrix = np.nan_to_num(X_matrix, nan=0.0, posinf=0.0, neginf=0.0)

# ==========================================
# 4. PSEUDO-GROUND TRUTH VIA THRESHOLDS
# ==========================================
y_matrix = np.zeros(X_matrix.shape[0], dtype=np.uint8)

mndwi = X_matrix[:, target_bands.index('MNDWI_M')]
ndvi = X_matrix[:, target_bands.index('NDVI_M')]
sar_vh = X_matrix[:, target_bands.index('Sigma0_VH_S')]

# NOTE: If your SAR band is in dB rather than linear amplitude,
# replace (sar_vh > 0.15) with an appropriate dB threshold (e.g. sar_vh > -12.0)
water_mask = mndwi > 0.1
veg_mask = (ndvi > 0.4) & (~water_mask)
urban_mask = (sar_vh > 0.15) & (~water_mask) & (~veg_mask)
soil_mask = (ndvi < 0.2) & (mndwi < -0.1) & (~urban_mask) & (~water_mask)

y_matrix[water_mask] = 1  # Water
y_matrix[veg_mask] = 2  # Vegetation
y_matrix[urban_mask] = 3  # Urban
y_matrix[soil_mask] = 4  # Bare Soil

print("\nSample count per class:")
for label_id, name in enumerate(
    ['Water', 'Vegetation', 'Urban', 'Bare Soil'], 1
):
    print(f" - {name}: {np.sum(y_matrix == label_id):,}")

# ==========================================
# 5. PREPARE TRAINING DATA (RAW BANDS ONLY)
# ==========================================
raw_train_bands = [
    'B2_M',
    'B3_M',
    'B8_M',
    'B11_M',
    'Sigma0_VV_S',
    'Sigma0_VH_S',
]
raw_cols = [target_bands.index(b) for b in raw_train_bands]

valid_mask = y_matrix > 0
X_valid = X_matrix[valid_mask][:, raw_cols]
y_valid = y_matrix[valid_mask]

X_train, X_test, y_train, y_test = train_test_split(
    X_valid, y_valid, test_size=0.2, random_state=42, stratify=y_valid
)

# Train baseline Random Forest
rf_model = RandomForestClassifier(
    n_estimators=100, max_depth=15, random_state=42, n_jobs=-1
)
rf_model.fit(X_train, y_train)

# Evaluate
y_pred = rf_model.predict(X_test)
print("\n- - - Classification Report - - -")
print(
    classification_report(
        y_test,
        y_pred,
        target_names=['Water', 'Vegetation', 'Urban', 'Bare Soil'],
    )
)

# ==========================================
# 6. SPATIAL BLOCK CROSS-VALIDATION
# ==========================================
pixel_indices = np.where(valid_mask)[0]
row_coords, col_coords = np.unravel_index(pixel_indices, (height, width))

num_blocks = 10
block_r = height // num_blocks
block_c = width // num_blocks

# Clip grid indices so border pixels do not overflow into extra blocks
r_grp = np.clip(row_coords // block_r, 0, num_blocks - 1)
c_grp = np.clip(col_coords // block_c, 0, num_blocks - 1)
groups = r_grp * num_blocks + c_grp

# Subsample for cross-validation efficiency
sample_size = 50000
if len(y_valid) > sample_size:
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(y_valid), size=sample_size, replace=False)
    X_cv, y_cv, groups_cv = (
        X_valid[sample_idx],
        y_valid[sample_idx],
        groups[sample_idx],
    )
else:
    X_cv, y_cv, groups_cv = X_valid, y_valid, groups

gkf = GroupKFold(n_splits=5)
spatial_scores = []

print("\n=== SPATIAL BLOCK CROSS-VALIDATION ===")
for fold, (train_idx, val_idx) in enumerate(
    gkf.split(X_cv, y_cv, groups=groups_cv), 1
):
    fast_rf = RandomForestClassifier(
        n_estimators=30, max_depth=12, random_state=42, n_jobs=-1
    )
    fast_rf.fit(X_cv[train_idx], y_cv[train_idx])
    acc = fast_rf.score(X_cv[val_idx], y_cv[val_idx])
    spatial_scores.append(acc)
    print(f"Fold {fold} Spatial Accuracy: {acc:.4f}")

print(
    f"Mean Spatial Accuracy: {np.mean(spatial_scores):.4f} (+/- {np.std(spatial_scores):.4f})"
)

# ==========================================
# 7. BATCHED FULL-SCENE INFERENCE & EXPORT
# ==========================================
print("\nPredicting classes across full raster scene (batched)...")
X_all_raw = X_matrix[:, raw_cols]
full_prediction = np.zeros(X_all_raw.shape[0], dtype=np.uint8)

# Process in chunks of 500k pixels to prevent memory overflow
chunk_size = 500000
for i in range(0, X_all_raw.shape[0], chunk_size):
    full_prediction[i : i + chunk_size] = rf_model.predict(
        X_all_raw[i : i + chunk_size]
    )

classified_map = full_prediction.reshape(height, width)

# Update profile and export
profile.update(
    count=1, dtype=rasterio.uint8, nodata=0, compress='lzw'  # saves disk space
)

out_tif = 'classified_porto_python.tif'
with rasterio.open(out_tif, 'w', **profile) as dst:
    dst.write(classified_map, 1)

print(f"SUCCESS: Saved to {out_tif}")

# ==========================================
# 8. VISUALIZATION
# ==========================================
colors = ['#000000', '#1f77b4', '#2ca02c', '#d62728', '#8c564b']
cmap = mcolors.ListedColormap(colors)
bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
norm = mcolors.BoundaryNorm(bounds, cmap.N)

plt.figure(figsize=(12, 9))
im = plt.imshow(classified_map, cmap=cmap, norm=norm)
cbar = plt.colorbar(
    im,
    ticks=[0, 1, 2, 3, 4],
    label='0: Unlabeled, 1: Water, 2: Veg, 3: Urban, 4: Soil',
)
plt.title(
    'Sentinel-1 SAR + Sentinel-2 Optical Classification (Porto)', fontsize=13
)
plt.axis('off')
plt.tight_layout()
plt.show()