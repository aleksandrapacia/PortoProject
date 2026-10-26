# SNAP processing (Sentinel-2 water quality)

This project is **optical**, not a Sentinel-1 water mask.

Planned graph (same settings on every date):

1. Read Sentinel-2 **L1C**
2. **C2RCC** (default) or **C2X** if the flood water is extremely turbid
3. Keep **TSM** (and optionally turbidity / \(K_d\))
4. Valid-water mask (avoid banks, ships, sunglint)
5. Write GeoTIFF for Python

C2RCC uses the visible–NIR water-colour bands after atmospheric correction. It does not use Sentinel-1 and it does not produce temperature.

Put the exported Graph XML here when it exists.
