#!/usr/bin/env python3
"""2–3 page meeting note PDF (English)."""

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
OUT = ROOT / "docs" / "Porto_S1S2_classification_brief.pdf"
FIG_MAP = ROOT / "outputs" / "figures" / "fig_classification.png"
FIG_IMP = ROOT / "outputs" / "figures" / "fig_importance.png"


class Doc(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Doc", size=8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, f"{self.page_no()}/{{nb}}", align="C")


def h(pdf: Doc, text: str) -> None:
    pdf.ln(2)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Doc", size=13)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 7, text)
    pdf.ln(1)


def p(pdf: Doc, text: str, size: int = 11) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Doc", size=size)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5.4, text)
    pdf.ln(1.2)


def bullet(pdf: Doc, text: str) -> None:
    pdf.set_font("Doc", size=11)
    pdf.set_x(pdf.l_margin + 4)
    usable = pdf.w - pdf.r_margin - pdf.l_margin - 4
    pdf.multi_cell(usable, 5.2, f"-  {text}")
    pdf.ln(0.4)


def main() -> None:
    pdf = Doc(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("Doc", fname=FONT)
    pdf.add_page()
    pdf.set_margins(18, 16, 18)

    w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Doc", size=11)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(w, 6, "Supervisor meeting note  |  26 October 2026", align="C")
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Doc", size=16)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(
        w,
        8,
        "Sentinel-1 / Sentinel-2 land-cover classification of Porto",
        align="C",
    )
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Doc", size=12)
    pdf.multi_cell(
        w,
        6,
        "SNAP collocation, Random Forest, and why 100 percent accuracy is not a result",
        align="C",
    )
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Doc", size=10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(
        w,
        5,
        "Aleksandra Pacia  |  Erasmus, Geospatial Engineering, Universidade do Porto  |  "
        "AGH Krakow  |  github.com/aleksandrapacia/PortoProject",
        align="C",
    )
    pdf.ln(3)

    h(pdf, "1. Aim")
    p(
        pdf,
        "Test whether collocated Sentinel-1 SAR and Sentinel-2 optical data, processed in SNAP "
        "and classified in Python, can separate four land-cover classes over Porto and the Douro "
        "valley — water, vegetation, urban, bare soil — and treat accuracy numbers as something "
        "to audit, not to advertise.",
    )

    h(pdf, "2. Method (what was actually run)")
    bullet(
        pdf,
        "SNAP: collocation of Sentinel-1 GRD (sigma0 VV, VH) with Sentinel-2; MNDWI and NDVI as auxiliary layers.",
    )
    bullet(
        pdf,
        "Labels (v1): pixel thresholds on MNDWI, NDVI and VH. These are not independent ground truth.",
    )
    bullet(
        pdf,
        "Classifier: Random Forest on raw bands only (B2, B3, B8, B11, sigma0 VV, sigma0 VH). Indices were removed from the feature vector after a 100 percent score showed leakage.",
    )
    bullet(
        pdf,
        "Validation: stratified random split and spatial block cross-validation (GroupKFold on a 10×10 grid).",
    )

    h(pdf, "3. Results")
    p(
        pdf,
        "A random split produced essentially perfect scores (water and vegetation F1 = 1.00; "
        "urban about 0.97; overall accuracy about 1.00). Spatial-block CV stayed near 0.99. That is still "
        "too high to believe as map accuracy: the labels remain threshold rules on the same image.",
    )
    p(
        pdf,
        "What is usable: the classified map is spatially coherent (ocean and Douro as water; "
        "built-up as fragmented red; vegetation dominant inland). Feature importance shows optical "
        "structure as the main driver, with VH backscatter contributing to the urban class — radar "
        "is not redundant.",
    )

    if FIG_MAP.exists():
        pdf.ln(1)
        pdf.set_x(pdf.l_margin)
        pdf.image(str(FIG_MAP), w=170)
        pdf.set_font("Doc", size=9)
        pdf.set_text_color(70, 70, 70)
        pdf.multi_cell(
            0,
            4.5,
            "Figure 1. Random Forest map from SNAP-collocated S1+S2. Blue: water; green: vegetation; red: urban; brown: bare soil.",
        )
        pdf.ln(2)

    if FIG_IMP.exists():
        pdf.set_x(pdf.l_margin)
        pdf.image(str(FIG_IMP), w=155)
        pdf.set_font("Doc", size=9)
        pdf.set_text_color(70, 70, 70)
        pdf.multi_cell(
            0,
            4.5,
            "Figure 2. Feature importance (diagnostic run with indices). NDVI dominates; sigma0 VH is the strongest radar contributor.",
        )
        pdf.ln(2)

    h(pdf, "4. Limitation (the point of this meeting)")
    p(
        pdf,
        "The 100 percent figure was a data leak: labels derived from NDVI/MNDWI, then a tree model "
        "reproducing that formula, plus neighbouring pixels in both train and test (spatial "
        "autocorrelation). Removing indices from training and using block CV is necessary but not "
        "sufficient. Independent polygons (hand ROIs, or CORINE / ESA WorldCover) are required "
        "before any accuracy is reported as a scientific result.",
    )

    h(pdf, "5. Proposed next steps")
    bullet(pdf, "Independent test labels: SNAP/QGIS ROIs versus CORINE or ESA WorldCover.")
    bullet(pdf, "Add DEM derivatives (slope, aspect) — Douro valley relief.")
    bullet(
        pdf,
        "Same spatial CV, second classifier (SVM or XGBoost) for a method comparison, not a leaderboard.",
    )
    p(
        pdf,
        "Question for the supervisor: which of these is the right next increment at Erasmus scale?",
    )
    pdf.ln(2)
    p(
        pdf,
        "I would be grateful for comments on this SNAP–Python workflow, and — if you are willing "
        "to guide the next step — for a short recommendation letter in due course. I can provide "
        "a one-paragraph description of the method and of my own contribution.",
        size=10,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
