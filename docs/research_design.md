# Research design — turbidity as a flood proxy, not chemical pollution

## What Sentinel can and cannot see

Satellites do **not** measure metals, bacteria, sewage, nitrates or “pollution” as a lab would.

They **do** measure how the water **looks**:

| Product | Sensor | SNAP | Meaning |
|---------|--------|------|---------|
| Turbidity / TSM (suspended sediment) | Sentinel-2 (optical bands) | **C2RCC / C2X** | brown, muddy water |
| Chlorophyll-a (careful) | Sentinel-2 | C2RCC | algae — easy to get wrong in muddy estuaries |
| Coloured dissolved organic matter | Sentinel-2 | C2RCC | “tea” colour, not toxins |
| Water extent through clouds | Sentinel-1 VV | Graph | where water is, not how dirty |
| Water temperature | Landsat TIR | optional | Douro is narrow → mixed pixels. **Not the main thesis.** Sentinel-2 has **no** thermal band. Sentinel-3 SST is ~1 km — too coarse here. |

In Douro, “pollution” that people worry about (WWTP, metals in sediment) is real, but the satellite sees the **sediment pulse**. After high discharge, more mud is in the water and a **turbid plume** leaves the mouth. That mud can carry contaminants, but you will **not** map Pb or E. coli. You map **TSM / turbidity** and treat it as a **proxy** for the flood-driven sediment pulse.

Published fact you can cite: the Douro plume is clearly seen from space when river flow exceeds about **500 m³/s** (MODIS/MERIS studies). You do not discover the plume. You test it at **Sentinel-2 10 m** in SNAP, event by event, against Crestuma discharge.

## Thesis (one sentence)

After a high Crestuma discharge (flood / large release), cloud-free Sentinel-2 scenes show **higher turbidity / TSM** in the Douro mouth and a **larger coastal plume** than on low-discharge days.

## Hypotheses

**H1 — estuary gets muddier after high Q**  
Median TSM (or turbidity) in the lower estuary is higher on cloud-free Sentinel-2 dates in the 1–10 days after Crestuma \(Q > 500\,\mathrm{m^3/s}\) than on low-\(Q\) dates.

**H2 — the plume grows with discharge**  
The area (km²) where TSM exceeds a stated threshold, from the mouth onto the shelf, increases with \(Q\).

Accept or reject is a valid result. Clouds after storms will limit \(n\); say so.

Do **not** add temperature or chlorophyll as extra theses. Chlorophyll after a flood is a possible appendix (nutrients later, not during the brown pulse). Temperature is a Landsat side note only if time remains.

## What you use (bands and tools)

**Sentinel-2 L1C** — this is the “bands” project:

- Visible + NIR + red edge (B1–B8A): water colour
- SWIR (B11): help separate water from land, clouds

**SNAP (this is what she teaches)**

1. Read S2 L1C
2. **C2RCC** (or **C2X** if the water is extremely turbid) — atmospheric correction + water constituents
3. Export TSM (and optionally turbidity / \(K_d\)) as GeoTIFF
4. Same graph / parameters on every date

**Ancillary (one number per date)**

- Crestuma–Lever discharge \(Q\) (SNIRH) — the flood switch
- Tide at overpass — so you do not compare only high vs only low tide by accident

**Sentinel-1 (optional, small)**  
Mark the high-water / storm week when S2 is cloudy. The **quality map is always S2**, because S1 does not see mud vs clean water.

## Calculations (so it is not a photo album)

For each usable S2 date:

| Quantity | What it is |
|----------|------------|
| \(TSM_{\mathrm{est}}\) | median TSM in a fixed lower-estuary polygon (away from mixed bank pixels) |
| \(A_{\mathrm{plume}}\) | km² on the inner shelf with TSM above a fixed threshold |
| \(Q\) | mean Crestuma discharge on that day (or 1–3 days before) |
| \(\eta\) | tidal height at overpass |

Then:

1. Two groups: **high Q** vs **low Q** → boxplot of \(TSM_{\mathrm{est}}\) (test H1)
2. Scatter: \(A_{\mathrm{plume}}\) vs \(Q\) (test H2)
3. Sensitivity: one other TSM threshold; if H2 dies, say so
4. 2 maps only: one low-\(Q\) day, one high-\(Q\) day

Target: **8–15 cloud-free S2 scenes** spanning both regimes. Not two pretty pictures.

## What you must write in the report

- “TSM is a **proxy**, not a pollutant concentration.”
- C2RCC in an estuary is uncertain (adjacency, bottom, very turbid water). No field spectrometer → **relative** comparison between dates, not “exact mg/L for the city.”
- You are not the first to see the Douro plume; you are testing **event-scale S2 + SNAP + Q**.

## What not to promise

- Maps of metals, sewage, or bacteria
- Water temperature as a main result
- Quality during the storm itself (S2 needs a clear sky **after** the event)
- An operational pollution alert for Porto
