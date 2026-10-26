# Data

Do not commit full SAFE archives. The first working SNAP product is local BEAM-DIMAP.

## First product (downloaded)

| Field | Value |
|-------|--------|
| File | `data/processed/S2C_MSIL2A_20251010T112131_R037_T29TNF_20251010T151313_douro.dim` |
| Format | **BEAM-DIMAP** (`.dim` + `.data/`) |
| Tile | T29TNF (Porto / Douro) |
| Date | 2025-10-10, ~11:21 UTC |
| Cloud cover | ~0% |
| AOI | 8.85°W–8.45°W, 41.05°N–41.22°N |
| Bands | B01–B08, B8A, B11, B12, SCL |
| Level | **L2A** subset (for opening in SNAP now) |

Open in SNAP: **File → Open** → the `.dim` file.

GeoTIFF copy: `data/raw/…_douro_subset.tif`  
STAC metadata: `data/raw/…_stac.json`

This L2A DIMAP is to inspect RGB and water pixels. **C2RCC in the method needs Sentinel-2 L1C** (top-of-atmosphere). Next downloads for the time series should be L1C from Copernicus Browser / CDSE, then SNAP subset → BEAM-DIMAP.

## Time series still to collect

- **8–15 cloud-free L1C** scenes, high Crestuma \(Q\) and low \(Q\)
- Crestuma–Lever \(Q\) — SNIRH
- Tide at overpass — Instituto Hidrográfico / Leixões

Rule of thumb: plume often visible when \(Q > 500\,\mathrm{m^3/s}\).
