# Douro flood-driven turbidity (Porto)

**Title:** Flood-driven turbidity in the Douro estuary: a Sentinel-2 C2RCC test against Crestuma discharge

Erasmus project for a SNAP supervisor. Separate from the AGH engineering thesis.

## Thesis

Sentinel cannot see metals or sewage. It **can** see **mud in the water** (TSM / turbidity). After high Crestuma discharge the Douro is known to send a turbid plume to the shelf. This project tests whether that pulse is visible, date by date, in **Sentinel-2 processed in SNAP (C2RCC)**.

## Hypotheses

- **H1:** Lower-estuary TSM is higher after high discharge (\(Q > 500\,\mathrm{m^3/s}\)) than on low-\(Q\) days.
- **H2:** Coastal plume area (km² above a TSM threshold) increases with \(Q\).

Full design: [`docs/research_design.md`](docs/research_design.md).

## What you process

- **Main:** Sentinel-2 L1C optical bands → SNAP **C2RCC/C2X** → TSM
- **Context:** Crestuma \(Q\), tide
- **Optional:** Sentinel-1 only to mark the wet week when S2 is cloudy
- **Not main:** water temperature (no S2 thermal band)

## Deliverables

1. PDF (8–12 pages) organised around H1/H2
2. Repo: SNAP graph + Python + two example maps + table
3. Honest language: proxy, not chemistry

## Status

Chosen topic: **Sentinel-2 C2RCC turbidity vs Crestuma Q** (not S1 water-extent, not temperature).

- Preliminary write-up: `docs/Porto_Douro_turbidity_preliminary.docx`
- First SNAP product: `data/processed/S2C_MSIL2A_20251010T112131_R037_T29TNF_20251010T151313_douro.dim` (BEAM-DIMAP, Porto / Douro, 2025-10-10)
