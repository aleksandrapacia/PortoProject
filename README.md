# Porto land-cover: Sentinel-1 + Sentinel-2 (SNAP + Python)

**Title:** Fusing Sentinel-1 SAR and Sentinel-2 optical data in SNAP for land-cover classification of Porto (Random Forest, spatial-block validation)

Mini-project for a SNAP / remote-sensing

## Idea in one sentence

Collocate radar and optical Sentinel data over Porto–Douro in SNAP, then classify **water / vegetation / urban / bare soil** in Python — and show that a random 100% accuracy score is **not** a scientific result.

## What is already done

1. SNAP collocation of Sentinel-1 (σ⁰ VV, VH) with Sentinel-2 (including MNDWI, NDVI)
2. Random Forest on **raw bands** (B2, B3, B8, B11, VV, VH)
3. Labels first taken from index thresholds (this leaked into the score)
4. Spatial block cross-validation (`GroupKFold`)
5. Classified GeoTIFF, feature-importance plot, confidence layer in SNAP

Code: `code_Porto/ml_Porto_analysis.py`  
Notes : `docs/Porto_S1S2_classification_brief.pdf`  

## Honest limit

Scores near 99–100% are still too high: labels come from NDVI/MNDWI/SAR thresholds, not from independent polygons. The scientific point of the meeting is that leak, not the pretty map.

## Next (after the supervisor comments)

- Independent ROIs or CORINE / ESA WorldCover as test labels
- DEM (slope / aspect) in the feature stack
- Compare Random Forest with SVM or XGBoost under the same spatial CV

## Reproduce

Raw SNAP products (`.dim` / `.tif`) stay local — they are too large for GitHub. Place `collocate.tif` and `collocate.dim` next to the script, then:

```bash
cd code_Porto
python ml_Porto_analysis.py
```

Repo: https://github.com/aleksandrapacia/PortoProject
