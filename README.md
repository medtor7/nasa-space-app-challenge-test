# Burning Activity Calendar — Harmonized MODIS + VIIRS Hotspots
NASA Space Apps Challenge 2026 · *Harmonization of MODIS and VIIRS Hot Spots*

## Overview
**What it is.** A web app that turns 25 years of NASA FIRMS active-fire detections (MODIS from November 2000, VIIRS from 2012; the series ends on 31 December 2025) into one comparable *burning-activity calendar* for Türkiye and its surroundings. The user draws or picks an area, reads the fire season week by week or month by month, sees the hotspots over satellite imagery and can download the numbers.

**The problem.** VIIRS (375 m pixels) detects many more small fires than MODIS (1 km pixels). In our data, after the quality filters listed below, VIIRS records about 3.6 detections for every MODIS detection (590,023 vs. 162,829 in 2012–2025). Putting the two records one after the other therefore creates a jump in 2012 that comes from the instrument, not from fire (`fig1_v2_before_after.png`).

**What we did.** MODIS counts of 2000–2011 are scaled to VIIRS-equivalent counts with one factor per calendar month, learned on the 2012–2025 overlap. Before 4 July 2002 only Terra delivered MODIS data, so for that period the factors are learned from Terra alone. From 2012 on, VIIRS is used as it is. The result is one daily series on a 0.25° grid. The calendar, the season summary and the list of unusual weeks (for example the July 2021 Manavgat fires, `fig3_v2_manavgat_2021.png`) are computed from it.

**How well it works.** The scaling was tested by predicting the real VIIRS monthly totals from MODIS alone, always for years that were not used to learn the factors (three held-out schemes, see *Validation*): the error (WAPE) of the region's monthly totals is 15–18% and the bias is +0.4% to +7.6%. For small areas the error is much larger (see *Known limitations*).

**Why it matters.** Without harmonization, the sensor change of 2012 looks like a change in fire activity, so fire-season timing and "is this year unusual?" cannot be compared across it. With it, the same calendar can be read for 2003 and for 2023. The method only needs FIRMS downloads for a new bounding box, so it could be repeated for other regions (not done here).

## NASA Data and Other Resources
| Resource | What we used |
|---|---|
| **NASA FIRMS** archive, Area API ([earthdata.nasa.gov/firms](https://earthdata.nasa.gov/firms)) | `MODIS_SP` (MODIS Terra + Aqua, 1 km) and `VIIRS_SNPP_SP` (VIIRS Suomi NPP, 375 m) standard-processing active-fire detections, 1 Nov 2000 – 31 Dec 2025, bounding box 25.5–44.9°E, 35.7–42.2°N (Türkiye and surroundings). Kept: `type = 0` (presumed vegetation fire), MODIS confidence ≥ 30, VIIRS confidence nominal or high. Counted per 0.25° cell and day. |
| **NASA GIBS** ([earthdata.nasa.gov/gibs](https://earthdata.nasa.gov/gibs)) | *MODIS Terra Corrected Reflectance (True Color)* tiles, shown behind the hotspots for the week or month selected in the calendar. |
| Link to the **NASA FIRMS Live Map** | A button opens the official map for near-real-time fires; nothing from it is copied. |

Not NASA: Esri World Imagery and World Boundaries and Places (satellite background and place names), Leaflet, Leaflet-Geoman, Plotly.js, country outlines for the offline map (`libs/world.geojson`), Barlow fonts (Google Fonts), Python with pandas, NumPy and matplotlib for the scripts in `tools/`. Versions and licenses are listed at the end of this file.

*Space Agency Partner data:* none was used. The interface layout was inspired by the NASA FIRMS Live Map; it uses no NASA logos or other NASA branding, and the app states that this is an independent student project.

## Run Locally or on GitHub Pages
Serve the folder locally:
```bash
python -m http.server 8000
```
Then open `http://localhost:8000` (or use VS Code **Live Server** / publish directly on **GitHub Pages**). All file paths are relative, all code libraries (`libs/`) are bundled locally and no API key is exposed in the frontend. Three things load from the internet: the satellite background (Esri World Imagery), NASA's true-colour image for a selected week (NASA GIBS) and the web fonts (Google Fonts). Without a connection the app falls back to its built-in dark map and system fonts; everything else keeps working. (Opening `index.html` directly from the file system does not work: the browser blocks the data files.)

## Interface (v6)
The map fills the whole screen and every tool opens from the icon bar at the bottom, in the spirit of the NASA FIRMS live map:

| Icon | What it opens |
|---|---|
| **Area** | Draw a rectangle, polygon or circle, pick a ready-made or saved area, use your location, type coordinates, toggle the lat/lon grid |
| **Layers** | Years, sensor mode, recurrent-cell filter, map background (satellite or dark offline map), place names, cell opacity, NASA weekly image |
| **Calendar** | The burning-activity calendar drawer (weekly/monthly); click a cell to map that week or month |
| **Insights** | Area size, hotspot-days, critical and core season, unusual weeks, this month vs. history, seasonal and yearly charts |
| **Unusual** | Anomaly method and sensitivity, list of unusual weeks (click to map) |
| **Method** | Validation table, yearly-ratio chart, reference check, method notes and figures |
| **Download / Share / Help / View** | CSV and PNG exports, a link that restores the current view, how-to and data credit, map-only and full-screen modes |

- The map zooms to level 18. From zoom 9 the 0.25° cells are drawn as outlines so the imagery stays visible.
- Clicking a calendar cell writes its note (value, z-score, MODIS-scaling caveat) above the calendar, so the note is also available on touch screens, and loads the MODIS Terra true-colour image of that week from NASA GIBS behind the hotspots.
- The layout adapts to phones: the panels become full-width sheets and the icon bar stays at the bottom.
- The interface opens in English; the **TR** button switches it to Turkish.

## Dataset
The app ships with one pre-processed dataset: the NASA FIRMS Area API extract for the bounding box `25.5–44.9°E, 35.7–42.2°N` (Türkiye and surroundings), gridded by the team's pipeline. The suffix `_v2` in the file names is the pipeline's version tag; there is no other dataset in the package.
- Files: `daily_grid_v2.csv` (309,998 cell-days), `monthly_factors_v2.json`, `monthly_factors_terra_v2.json` (Terra-only factors, used before 4 July 2002), `summary_v2.json`, `data/validation_summary_v2.csv`, `data/yearly_ratio_v2.csv`, and figures `fig1_v2_before_after.png`, `fig2_v2_monthly_factors.png`, `fig3_v2_manavgat_2021.png`, `fig4_v2_test_period.png` (the last one shows scheme ① of the validation table below).
- Validation: see **Validation** below.
- Team Reference Check (2003–2025, $z \ge 2$, $\min 20$): **critical weeks 25–27, 32–42** (0-based JS index: `24,25,26,31..41`); **core weeks 34–40** (0-based JS index: `33..39`); **10 anomalies** (exact 100% match between `summary_v2.json` and `reference/JS_fonksiyonu.txt`).

## Validation
MODIS (2000–2011) is scaled to VIIRS-equivalent counts with one factor per calendar month (Terra-only factors before 4 July 2002, see below). To see whether such factors keep working over time, the scaling is used to *predict the monthly VIIRS totals of the whole region* in years where VIIRS exists, and the prediction is compared with the real VIIRS. This is done in three ways (rows of `data/validation_summary_v2.csv`; the app reads this file, nothing is typed by hand):

| Scheme | Single factor (WAPE / bias) | Monthly factor (WAPE / bias) |
|---|---|---|
| ① Fixed split: learn 2012–2018 → test 2019–2025 | 22.7% / +7.2% | 17.9% / +7.6% |
| ② Expanding window: test years 2015–2025, each learned from all earlier years since 2012 | 23.8% / +2.2% | 16.7% / +1.9% |
| ③ Leave one year out: each year 2012–2025 held out in turn | 23.2% / +0.1% | 15.4% / +0.4% |

- **WAPE** = Σ|observed − predicted| ÷ Σ observed on monthly totals of the whole region (lower is better). **Bias** = (Σ predicted − Σ observed) ÷ Σ observed; **positive = predicted VIIRS is higher than real VIIRS**.
- **Terra-only period.** Terra started on 1 November 2000, Aqua only on 4 July 2002. MODIS counts of that period are about half of what Terra + Aqua would give, so the Terra + Aqua factors would scale them too low. For dates before 4 July 2002 the calendar therefore uses factors learned from Terra detections alone (`monthly_factors_terra_v2.json`, about twice as large and noisier in winter). A separate held-out test (Terra counts × Terra-only factors, scored against the real VIIRS, same three schemes) gave WAPE 24.5 / 22.4 / 21.5 % and bias +4.2 / +1.1 / +0.7 %; with the Terra + Aqua factors the same test gave WAPE ≈ 51 % and bias ≈ −50 %. These numbers are from the team's Colab notebook and are not in `data/validation_summary_v2.csv`. The test covers Terra in 2012–2025, not the early years themselves.
- **Learned vs. used factors.** In the fixed split the factors were learned from 2012–2018 only. The final series (the calendar) uses factors learned from the whole 2012–2025 overlap (`monthly_factors_v2.json`).
- **Forward test only.** ① and ② learn from earlier years and predict later ones; ③ also learns from later years and is therefore the most optimistic. Applying the factors *backward* to 2000–2011 cannot be tested, because there is no VIIRS record for those years.
- **Why the bias is positive.** The VIIRS/MODIS ratio of 2019–2025 is lower than that of 2012–2018 (`data/yearly_ratio_v2.csv`: plain average of the yearly ratios 3.80 → 3.48, −8.6%; individual years range 3.23–4.26 and 3.08–4.02). Factors learned from the earlier period are therefore a little too high for the later one. For the single factor the bias is exactly this drift of the pooled ratio (3.751 → 3.499 = +7.2%); the pooled ratios weight each year by its fire count, so they differ slightly from the plain averages drawn in the app. The bias shrinks in ② and ③ because their training years also include recent years. *Why the ratio changed was not investigated.*
- **Hover note on MODIS-scaled years (◇).** The calendar shows "Value scaled from MODIS. Typical validation error for the region's monthly total: ~18%". The 18% is the fixed-split monthly-factor WAPE of the CSV (17.9%, the largest of the three), rounded by the app. It was measured for the **whole-region monthly total** in 2019–2025 — not for a single cell, week or day, not for a smaller selected area (the factors are fitted on the whole bounding box and the ratio is not uniform in space; on 1° squares the monthly error is more than twice as large, see *Known limitations*), and not for 2000–2002 (Terra only until 3 July 2002; see *Terra-only period* above). The app says so in the tooltip.
- **Experiments.** A power-law ("üs") scaling was also tried (rows `us` in the CSV). It was an experiment ("deneme"): the product does not use it and the app does not show it (the CSV reader only accepts `tek` and `aylik`).

## Known limitations
- **Whole region, not every area.** The validation table scores monthly totals of the whole bounding box. Scored on 1° × 1° squares (about 110 × 85 km) with the same monthly factors, the monthly error is much larger: WAPE 47% / 46% / 45% for schemes ① / ② / ③, and the total over the test years of a typical square is off by 23% / 19% / 16% (median |bias| over the squares with at least 300 VIIRS detections; 57% / 48% / 42% of those squares are off by more than 20%). Reproduce with `python tools/small_area_check.py daily_grid_v2.csv`. The "~18%" note in the calendar is the whole-region number only.
- **2000–2002 are the least certain years.** The record starts on 1 November 2000 and only Terra delivered MODIS data until 3 July 2002. These dates use Terra-only factors (expected error about 22–25 % for the monthly regional total, measured on Terra in 2012–2025); the yearly totals are about 3,900 (2000, November and December only), 56,700 (2001) and 34,300 (2002). 2001 is high compared with 2003–2007 and the winter factors are noisy, so treat these years as rough estimates. They are flagged ⚠ in the calendar and cannot be validated directly.
- **No backward test.** The factors are tested forward in time only; there is no VIIRS record before 2012 to test them on MODIS years.
- **End of the series.** The standard-processing archive used here ends on 31 December 2025; 2026 is not included. Use the FIRMS Live Map button for current fires.
- **The region is a box, not the country.** The default numbers are for the whole bounding box, which includes parts of neighbouring countries. There is no clip to the national border; draw a polygon to approximate one.
- **Open question.** Why the VIIRS/MODIS ratio fell after 2018 was not investigated.

## Data Files & Tools
- `data/validation_summary_v2.csv` — validation results from the team's Colab (columns `sema, yontem, WAPE_%, bias_%`; Turkish names: `sema` = scheme, `yontem` = method, `tek` = single factor, `aylik` = monthly factors, `us` = power-law experiment).
- `data/yearly_ratio_v2.csv` — VIIRS ÷ MODIS detections per year (2012–2025), the team's Colab output (columns `year,M,V,oran`: M = MODIS, V = VIIRS detections, `oran` = ratio; ratios rounded to 2 decimals). `tools/make_yearly_ratio.py daily_grid_v2.csv out.csv` regenerates it from the grid; the values agree to rounding.
- `tools/verify_validation_csv.py` — recomputes every `tek`/`aylik` number of the validation CSV from `daily_grid_v2.csv` and compares them: `python tools/verify_validation_csv.py daily_grid_v2.csv data/validation_summary_v2.csv` (all 6 rows agree).

- `tools/small_area_check.py` — the same three schemes scored on 1° squares instead of the whole region (see *Known limitations*): `python tools/small_area_check.py daily_grid_v2.csv`.
- `tools/make_figures.py` — re-draws `fig1`, `fig2` and `fig4` with English labels from the data files and prints the WAPE/bias of the test figure: `python tools/make_figures.py . out_folder`. `fig3` comes from the team's Colab notebook; only its text labels were replaced by English ones.

## Verification Script
Run `node reference/verify_reference.js` to recompute the reference check from `daily_grid_v2.csv` with the team's function in `reference/JS_fonksiyonu.txt`; the result is written to `reference/validation_values_v2.json`.

## License & AI/SI Tool Disclosure
- **License**: MIT License (`LICENSE`). Third-party libraries in `libs/`: Leaflet 1.9.4 (BSD-2-Clause), Leaflet-Geoman 2.20.6 (MIT), Plotly.js 2.32.0 (MIT). Online map layers: Esri World Imagery and World Boundaries and Places (© Esri, Maxar, Earthstar Geographics and the GIS user community) and NASA GIBS (MODIS Terra Corrected Reflectance). Fonts: Barlow and Barlow Condensed (SIL Open Font License) via Google Fonts.
- **AI/SI Disclosure** (Super Intelligence tools were used in this project; where and how):
  - *Code.* Claude (Anthropic) and Gemini (Google) helped write the front-end (`index.html`: interface scaffolding and the bilingual EN/TR texts; the v6 full-screen interface was written with Claude) and the Colab data pipeline and validation experiments that produced `daily_grid_v2.csv`, the two `monthly_factors*.json` files, `summary_v2.json` and the files in `data/`. The helper scripts in `tools/` were written with Claude. AI-assisted scripts carry a note in their header, `index.html` carries one in its head and the in-app *Help* panel repeats it.
  - *Figures.* The plots are drawn by code from the data (matplotlib). No AI image or video generation was used, so there is no watermark. `fig1`, `fig2` and `fig4` were re-drawn in English with `tools/make_figures.py` (written with Claude); in `fig3` only the text labels were replaced.
  - *Text.* The documentation and the interface texts were drafted with AI help.
  - *Checks.* The pipeline was run on the real FIRMS data by the team. The numbers of the validation table were additionally recomputed from `daily_grid_v2.csv` with `tools/verify_validation_csv.py`.

## Colour scale (v6.5)

- Calendar and map use the same 5-stop inferno-style palette; the legend gradient matches it exactly. Grey-brown = zero hotspots.
- Colour is a **log scale** of hotspots per cell, stretched between the **5th and 98th percentile of the non-zero values currently in view** (below 30 non-zero values: 0..max). Cells at the ends are clipped (legend shows "≤" and "≥"); the tooltip on the legend gives the exact maximum.
- The scale is **relative to the current view** (area, years, week/month), so colours are not comparable between different views; use the legend numbers.
- The map has its own legend (bottom-left). It is hidden when no cells are shown.
- Hotspot count is a detection count, not burned area.

