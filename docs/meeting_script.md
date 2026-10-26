# Monday meeting — what to say (≈5 minutes)

Speak English. Hand her the PDF. Do not ask for the letter in the first sentence.

## 1. What I did (≈90 s)

I collocated Sentinel-1 SAR and Sentinel-2 optical data over Porto in SNAP, then classified four classes in Python with Random Forest: water, vegetation, urban, bare soil.

SNAP is the core processor (collocation, σ⁰, indices). Python is for the classifier, spatial validation, and maps.

## 2. What went wrong — this is the interesting part (≈90 s)

A random train/test split gave about **100% accuracy**. That is not a good model. The labels were built from NDVI and MNDWI, so the forest was reproducing a formula, not land cover. Neighbouring pixels also leaked into both train and test (spatial autocorrelation).

I therefore trained only on raw bands and used **spatial block cross-validation**. The map still looks coherent (Douro and ocean as water, built-up as red), and VH backscatter helps the urban class — but I do **not** treat 99% as real accuracy. Independent polygons are the next step.

## 3. What I would like to ask you (≈60 s)

1. Would you recommend adding a DEM (slope, aspect) for this Douro valley scene?
2. For independent labels: hand-drawn ROIs in SNAP/QGIS, or CORINE / ESA WorldCover?
3. Is a Random Forest vs SVM comparison under the same spatial CV worth doing at this scale?

## 4. Letter — only after she engages (≈30 s)

I would also be grateful if, on the basis of this SNAP–Python work and if you are willing to supervise the next step, you could write a short recommendation letter for my later applications. I can send a one-paragraph summary of the method and of what I did myself.

If she hesitates: thank her, leave the PDF and GitHub, ask what she wants changed, do **not** push.

## GitHub to write down

https://github.com/aleksandrapacia/PortoProject
