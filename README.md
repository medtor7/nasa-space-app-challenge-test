# Burning Activity Calendar — Harmonized MODIS + VIIRS Hotspots
NASA Space Apps Challenge 2026 · *Harmonization of MODIS and VIIRS Hot Spots*

## Overview
**What it is.** A web app that turns 25 years of NASA FIRMS active-fire detections (MODIS from November 2000, VIIRS from 2012; the series ends on 31 December 2025) into one comparable *burning-activity calendar* for Türkiye and its surroundings. The user draws or picks an area, reads the fire season week by week or month by month, sees the hotspots over satellite imagery and can download the numbers.

**The problem.** VIIRS (375 m pixels) detects many more small fires than MODIS (1 km pixels). In our data, after the quality filters listed below, VIIRS records about 3.6 detections for every MODIS detection (590,023 vs. 162,829 in 2012–2025). Putting the two records one after the other therefore creates a jump in 2012 that comes from the instrument, not from fire (`fig1_v2_before_after.png`).

**What we did.** MODIS counts of 2000–2011 are scaled to VIIRS-equivalent counts with one factor per calendar month, learned on the 2012–2025 overlap. Before 4 July 2002 only Terra delivered MODIS data, so for that period the factors are learned from Terra alone. From 2012 on, VIIRS is used as it is. The result is one daily series on a 0.25° grid. The calendar, the season summary and the list of unusual weeks (for example the July 2021 Manavgat fires, `fig3_v2_manavgat_2021.png`) are computed from it.

**How well it works.** The scaling was tested by predicting the real VIIRS monthly totals from MODIS alone, always for years that were not used to learn the factors (three held-out schemes, see *Validation*): the error (WAPE) of the region's monthly totals is 15–18% and the bias is +0.4% to +7.6%. Seven alternative methods, including gradient boosting, were scored under the same schemes; none is better for small areas in the forward test, and the harmonized record barely depends on the method chosen (see *Other methods we tested*). For small areas the error is much larger (see *Known limitations*).

**Why it matters.** MODIS on Terra and Aqua is near the end of its mission. Without a bridge to VIIRS, the 2000–2011 record — more than ten years of fire history — cannot be compared with today: the sensor change of 2012 looks like a change in fire activity. With harmonization, the same calendar can be read for 2003 and for 2023, and from 2012 on it is pure VIIRS, so it keeps working after MODIS is switched off (see *Continuity*). The method only needs FIRMS downloads: the app itself can grid a user's own FIRMS CSV files for any region and learn that region's factors in the browser (*Layers → Another region*).

## Challenge objectives → where they are answered
| Objective / consideration | Where in the app | Evidence |
|---|---|---|
| Harmonize MODIS and VIIRS so patterns, trends and anomalies are not driven by the sensor | Calendar (harmonized series), **Method → Overlap check** (scaled MODIS vs. real VIIRS for any drawn area) | Validation table (3 held-out schemes), method comparison (8 methods), `tools/verify_validation_csv.py` |
| Choose a region and time range, download analytics | **Area** (draw / preset / coordinates / location), **Layers** (years), **Download** (CSV, PNG, one-page report) | Share link restores the view |
| Fire calendar from the 2000s to today; compare the present with the past | **Calendar** (weekly / monthly), **Insights → This month vs. history**, **On this day (±3 days)** | Critical / core season, top years and months |
| Trends | **Insights → Trend** (Theil–Sen slope, Mann–Kendall test) | Trend line on the yearly chart |
| Anomalies | **Unusual** (mean/SD or median/MAD z-scores), outlined calendar cells | `reference/verify_reference.js` reproduces the team's reference exactly |
| Colour ramps that show similarities and differences | One inferno-style log ramp for calendar and map, WCAG-contrast text, outlines + ★ for anomalies (not colour alone) | Legends with numbers |
| Users: emergency managers, scientists, land managers, firefighters | **Demo** (4 steps), one-page printable report, **fire-frequency map** (in how many years each cell burned), recurrent-source filter | Case study: 2021 Manavgat–Marmaris megafires |
| Works beyond Türkiye | **Layers → Another region**: any FIRMS archive CSV, factors learned from that region's overlap | Runs fully in the browser |

## NASA Data and Other Resources
| Resource | What we used |
|---|---|
| **NASA FIRMS** archive, Area API ([earthdata.nasa.gov/firms](https://earthdata.nasa.gov/firms)) | `MODIS_SP` (MODIS Terra + Aqua, 1 km) and `VIIRS_SNPP_SP` (VIIRS Suomi NPP, 375 m) standard-processing active-fire detections, 1 Nov 2000 – 31 Dec 2025, bounding box 25.5–44.9°E, 35.7–42.2°N (Türkiye and surroundings). Kept: `type = 0` (presumed vegetation fire), MODIS confidence ≥ 30, VIIRS confidence nominal or high. Counted per 0.25° cell and day. |
| **NASA GIBS** ([earthdata.nasa.gov/gibs](https://earthdata.nasa.gov/gibs)) | *MODIS Terra Corrected Reflectance (True Color)* tiles, shown behind the hotspots for the week or month selected in the calendar. |
| Link to the **NASA FIRMS Live Map** | A button opens the official map for near-real-time fires; nothing from it is copied. |

Not NASA: Esri World Imagery and World Boundaries and Places (satellite background and place names), Leaflet, Leaflet-Geoman, Plotly.js, country outlines for the offline map (`libs/world.geojson`), Barlow fonts (Google Fonts), Python with pandas, NumPy and matplotlib for the scripts in `tools/`. Versions and licenses are listed at the end of this file.

*Space Agency Partner data:* none was used. The challenge was written by a member of CONAE (Argentina), and the Turkish Space Agency (TUA) is among the Space Apps partner agencies; because the method is region-agnostic (only FIRMS CSVs are needed), the same tool can be run for an Argentine province or any other region with no code change — through *Layers → Another region*. The interface layout was inspired by the NASA FIRMS Live Map; it uses no NASA logos or other NASA branding, and the app states that this is an independent student project.

## Run Locally or on GitHub Pages
Serve the folder locally:
```bash
python -m http.server 8000
```
Then open `http://localhost:8000` (or use VS Code **Live Server** / publish directly on **GitHub Pages**). All file paths are relative, all code libraries (`libs/`) are bundled locally and no API key is exposed in the frontend. Three things load from the internet: the satellite background (Esri World Imagery), NASA's true-colour image for a selected week (NASA GIBS) and the web fonts (Google Fonts). Without a connection the app falls back to its built-in dark map and system fonts; everything else keeps working. (Opening `index.html` directly from the file system does not work: the browser blocks the data files.)

## Interface (v7)
The map fills the whole screen and every tool opens from the icon bar at the bottom, in the spirit of the NASA FIRMS live map:

| Icon | What it opens |
|---|---|
| **Area** | Draw a rectangle, polygon or circle, pick a ready-made or saved area, use your location, type coordinates, toggle the lat/lon grid |
| **Layers** | Years, sensor mode, recurrent-cell filter, **map mode: hotspot total or fire frequency** (in how many selected years a cell burned), map background, place names, cell opacity, NASA weekly image, **another region** (grid your own FIRMS CSVs) |
| **Calendar** | The burning-activity calendar drawer (weekly/monthly); click a cell to map that week or month |
| **Insights** | Area size, hotspot-days, critical and core season, unusual weeks, **trend** (Theil–Sen + Mann–Kendall), **one-page report**, this month vs. history, **on this day (±3 days, every year)**, seasonal and yearly charts |
| **Unusual** | Anomaly method and sensitivity, list of unusual weeks (click to map) |
| **Method** | Validation table, **overlap check for the drawn area** (scaled MODIS vs. real VIIRS 2012–2025 with R², WAPE and a live forward test), **other methods tested** + gradient-boosting sensitivity check, **Terra + Aqua vs. Terra-only factors**, yearly-ratio chart and **why the ratio fell**, continuity, reference check, figures |
| **▶ Demo** (top right) | A 4-step guided tour: the problem → 2021 megafire case study on the map → "is this unusual?" → field use |
| **Download / Share / Help / View** | CSV and PNG exports, a link that restores the current view, how-to and data credit, map-only and full-screen modes |

- The map caption under the calendar title gives the number of cells and the **highest single-cell value**, so the map's colour scale (per 0.25° cell) is not confused with the calendar's (per week or month of the whole area).
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
- **Terra-only period.** Terra started on 1 November 2000, Aqua only on 4 July 2002. MODIS counts of that period are about half of what Terra + Aqua would give, so the Terra + Aqua factors would scale them too low. For dates before 4 July 2002 the calendar therefore uses factors learned from Terra detections alone (`monthly_factors_terra_v2.json`, on average about 2.5 times as large and noisier in winter; the app plots both sets side by side in the Method panel). A separate held-out test (Terra counts × Terra-only factors, scored against the real VIIRS, same three schemes) gave WAPE 24.5 / 22.4 / 21.5 % and bias +4.2 / +1.1 / +0.7 %; with the Terra + Aqua factors the same test gave WAPE ≈ 51 % and bias ≈ −50 %. These numbers come from the last cell of `pipeline/nasa2.py` (the grid does not keep Terra and Aqua apart, so they cannot be re-computed from `daily_grid_v2.csv`) and are not in `data/validation_summary_v2.csv`. The test covers Terra in 2012–2025, not the early years themselves.
- **Learned vs. used factors.** In the fixed split the factors were learned from 2012–2018 only. The final series (the calendar) uses factors learned from the whole 2012–2025 overlap (`monthly_factors_v2.json`).
- **Forward test only.** ① and ② learn from earlier years and predict later ones; ③ also learns from later years and is therefore the most optimistic. Applying the factors *backward* to 2000–2011 cannot be tested, because there is no VIIRS record for those years.
- **Why the bias is positive.** The VIIRS/MODIS ratio of 2019–2025 is lower than that of 2012–2018 (`data/yearly_ratio_v2.csv`: plain average of the yearly ratios 3.80 → 3.48, −8.6%; individual years range 3.23–4.26 and 3.08–4.02). Factors learned from the earlier period are therefore a little too high for the later one. For the single factor the bias is exactly this drift of the pooled ratio (3.751 → 3.499 = +7.2%); the pooled ratios weight each year by its fire count, so they differ slightly from the plain averages drawn in the app. The bias shrinks in ② and ③ because their training years also include recent years.
- **Why did the ratio fall? What we tested** (`tools/ratio_drift_check.py` → `data/ratio_drift_v2.csv`; pooled ratio 3.75 → 3.50, −6.7%):
  - *Bigger fires?* Large fires saturate the 1 km MODIS pixel, so a year dominated by large fires has a lower ratio. But the share of VIIRS detections from large fire cell-days (≥ 10 VIIRS detections in one 0.25° cell in one day) did **not** rise (30.6% → 29.3%), and the ratio fell mostly for **small** fires (3.57 → 3.29, −7.8%; large fires 4.23 → 4.12, −2.5%). Fire size is therefore not the main cause, except in 2021, the megafire year (large-fire share 39.7%, ratio 3.41).
  - *Different season mix?* Explains only 1.6% of the 6.7% drop (expected ratio from the month mix 3.65 → 3.60).
  - *Orbit drift of Terra and Aqua* (both stopped orbit-maintenance manoeuvres around 2020–2022, so their local overpass times drift) is a plausible third cause, but testing it needs Terra and Aqua kept apart, which the grid does not do.
  - Conclusion: the drop is real, driven by small fires and only partly explained. It is measured, it is why scheme ① has a positive bias, and the schemes that include recent years keep the bias within ±2%.
- **Hover note on MODIS-scaled years (◇).** The calendar shows "Value scaled from MODIS. Typical validation error for the region's monthly total: ~18%". The 18% is the fixed-split monthly-factor WAPE of the CSV (17.9%, the largest of the three), rounded by the app. It was measured for the **whole-region monthly total** in 2019–2025 — not for a single cell, week or day, not for a smaller selected area (the factors are fitted on the whole bounding box and the ratio is not uniform in space; on 1° squares the monthly error is more than twice as large, see *Known limitations*), and not for 2000–2002 (Terra only until 3 July 2002; see *Terra-only period* above). The app says so in the tooltip.
- **Team experiment.** A power-law ("üs") scaling was also tried in the team's Colab (rows `us` in the CSV; 20.1 / 16.6 / 15.4%): 12 month coefficients plus one shared exponent, fitted by least squares on log1p of the regional monthly totals, with a smearing correction (`pipeline/nasa2.py`, validation cell). It is as good as the monthly factor in ② and ③ but worse in the forward test ①, and it is non-additive, so the product does not use it; the app shows it greyed out. `tools/verify_validation_csv.py` re-computes it too.

### Other methods we tested
`tools/compare_methods.py daily_grid_v2.csv data/method_comparison_v2.csv` scores eight methods with the same three schemes, at two scales: **region** (monthly totals of the whole box, as above) and **1° square** (monthly totals of ~110 × 85 km squares, closer to an area a user draws). Its "monthly factor" row reproduces the validation table exactly. WAPE, % (bias in brackets):

| Method | Region ① | Region ② | Region ③ | 1° square ① | 1° square ③ |
|---|---|---|---|---|---|
| Single factor | 22.7 (+7.2) | 23.8 | 23.2 | – | – |
| **Monthly factor (used)** | **17.9 (+7.6)** | **16.7** | **15.4** | **47.1** | **45.4** |
| Power law, regional totals | 23.9 (+2.3) | 24.2 | 24.1 | – | – |
| Linear regression | 23.8 (+7.0) | 23.8 | 23.0 | – | – |
| Quantile mapping | 21.3 (+5.6) | 23.9 | 23.9 | – | – |
| Monthly factor per sub-region (4) | 19.2 (+9.1) | 16.8 | 15.1 | 48.2 | 45.1 |
| Monthly × per-square correction (shrunk) | 27.3 (+21.1) | 20.4 | 16.1 | 59.6 | 44.8 |
| Gradient boosting (Poisson; MODIS, month, lat, lon) | 15.2 (+4.5) | 15.1 | 13.2 (−5.2) | 48.4 | 40.3 |

**Why we kept the monthly factor although gradient boosting scores best on the whole region:**
1. The gain is regional only. In the forward test ① gradient boosting is *worse* for 1° squares (48.4% vs. 47.1%), and small areas are what users draw.
2. Its bias changes sign between schemes (+4.5% … −5.2%); the monthly factor's bias has one sign and a measured cause (the ratio drift above).
3. It cannot be trained for the Terra-only period (2000 – 3 July 2002): the grid does not keep Terra and Aqua apart.
4. The calendar is built from daily 0.25° cells. A factor is additive: any area, week or day is the sum of its cells. A non-linear monthly 1° model is not; its daily cell values would not add up to its own monthly prediction.
5. One number per month can be printed, checked and re-used by anyone; a tree ensemble cannot.

Instead, gradient boosting is used as a **sensitivity check** (`tools/gbm_sensitivity.py` → `data/gbm_sensitivity_v2.csv`): trained on all of 2012–2025 and applied to the MODIS square-months of 2003–2011, its yearly totals are 1.7–15.1% lower than the product's (most in the big fire years 2009 and 2011) and correlate at r = 0.996 (Spearman ρ shown in the app). Which years were high or low does not depend on the method; only the size of the largest peaks does.

Power law, regression and quantile mapping fitted on regional totals are worse and also non-additive. Spatial refinements (sub-region factors, per-square corrections) do not beat the monthly factor in the forward test: the spatial pattern of the ratio is not stable enough over time to be learned. **Not testable with the grid:** day/night and fire-radiative-power classes need the raw FIRMS records (`daynight`, `frp` columns), which the 0.25° grid does not keep. `tools/daynight_test.py` runs the day/night test on the raw FIRMS archive CSVs (monthly vs. month × day/night factors, Terra-only variants, same three schemes); its results will be added here once it has been run on the full files. MODIS records `daynight` for the whole 2000–2011 period, so day/night factors could be applied backward — like the monthly factors, that backward use cannot be tested, because there is no VIIRS before 2012.

### Continuity: what happens when MODIS is switched off
Once 2000–2011 are on the VIIRS scale, the calendar no longer needs MODIS: from 2012 it is pure VIIRS S-NPP, and FIRMS also distributes the identical VIIRS instruments on NOAA-20 and NOAA-21, which can extend or back up the series. Only the factors need MODIS and VIIRS flying together, and they are learned from 14 overlap years (2012–2025). The same pipeline runs for any region: *Layers → Another region* grids a user's FIRMS CSV files and learns that region's own factors in the browser.

## Known limitations
- **Whole region, not every area.** The validation table scores monthly totals of the whole bounding box. Scored on 1° × 1° squares (about 110 × 85 km) with the same monthly factors, the monthly error is much larger: WAPE 47% / 46% / 45% for schemes ① / ② / ③, and the total over the test years of a typical square is off by 23% / 19% / 16% (median |bias| over the squares with at least 300 VIIRS detections; 57% / 48% / 42% of those squares are off by more than 20%). Reproduce with `python tools/small_area_check.py daily_grid_v2.csv`. The "~18%" note in the calendar is the whole-region number only.
- **2000–2002 are the least certain years.** The record starts on 1 November 2000 and only Terra delivered MODIS data until 3 July 2002. These dates use Terra-only factors (expected error about 22–25 % for the monthly regional total, measured on Terra in 2012–2025); the yearly totals are about 3,900 (2000, November and December only), 56,700 (2001) and 34,300 (2002). 2001 is high compared with 2003–2007 and the winter factors are noisy, so treat these years as rough estimates. They are flagged ⚠ in the calendar and cannot be validated directly.
- **No backward test.** The factors are tested forward in time only; there is no VIIRS record before 2012 to test them on MODIS years.
- **End of the series.** The standard-processing archive used here ends on 31 December 2025; 2026 is not included. Use the FIRMS Live Map button for current fires.
- **The region is a box, not the country.** The default numbers are for the whole bounding box, which includes parts of neighbouring countries. There is no clip to the national border; draw a polygon to approximate one.
- **Ratio drift only partly explained.** The VIIRS/MODIS ratio fell after 2018. Fire size and season mix were tested and explain little; Terra/Aqua orbit drift could not be tested with the grid (see *Validation*).
- **Trend test.** Mann–Kendall assumes independent years and ignores ties; with 23 years and large year-to-year swings, a "no significant trend" result is common and is not proof that there is no trend.
- **Another region.** For uploaded FIRMS files the factors are learned from that region's own 2012+ overlap (if it has at least 300 MODIS and 300 VIIRS detections; otherwise the Türkiye factors are used). The validation table and figures describe the bundled Türkiye dataset only.

## Reproducibility: from the FIRMS API to the app
`pipeline/nasa2.py` is the team's Colab notebook (exported as Python; English summary at the top, Turkish comments inside). With a free FIRMS `MAP_KEY` stored in Colab Secrets as `FIRMS_KEY` it:
1. downloads `MODIS_SP` (from 1 Nov 2000) and `VIIRS_SNPP_SP` (from 2012) through the FIRMS Area API for the bounding box, in 5-day requests, one raw file per source and year;
2. filters (type 0, MODIS confidence ≥ 30, VIIRS nominal/high), grids to 0.25° per day, learns the monthly and the Terra-only factors and writes `daily_grid_v2.csv`, `monthly_factors_v2.json`, `monthly_factors_terra_v2.json` and `summary_v2.json`;
3. draws the figures and writes `data/validation_summary_v2.csv` and `data/yearly_ratio_v2.csv`;
4. runs the extra checks quoted in this README (counting measures, Terra vs. Aqua, 1° squares, the Terra-only held-out test).

The scripts in `tools/` and `reference/` then re-check its outputs independently from the shipped files.

## Data Files & Tools
- `data/validation_summary_v2.csv` — validation results from the team's Colab (columns `sema, yontem, WAPE_%, bias_%`; Turkish names: `sema` = scheme, `yontem` = method, `tek` = single factor, `aylik` = monthly factors, `us` = power-law experiment).
- `data/yearly_ratio_v2.csv` — VIIRS ÷ MODIS detections per year (2012–2025), the team's Colab output (columns `year,M,V,oran`: M = MODIS, V = VIIRS detections, `oran` = ratio; ratios rounded to 2 decimals). `tools/make_yearly_ratio.py daily_grid_v2.csv out.csv` regenerates it from the grid; the values agree to rounding.
- `tools/verify_validation_csv.py` — recomputes every number of the validation CSV (`tek`, `aylik` and the `us` experiment) from `daily_grid_v2.csv` and compares them: `python tools/verify_validation_csv.py daily_grid_v2.csv data/validation_summary_v2.csv` (all 9 rows agree).

- `tools/small_area_check.py` — the same three schemes scored on 1° squares instead of the whole region (see *Known limitations*): `python tools/small_area_check.py daily_grid_v2.csv`.
- `tools/compare_methods.py` — eight harmonization methods × three schemes, region and 1° square scores → `data/method_comparison_v2.csv` (needs scikit-learn for the gradient-boosting row).
- `tools/gbm_sensitivity.py` — gradient boosting vs. monthly factor for the yearly totals 2003–2011 → `data/gbm_sensitivity_v2.csv`.
- `tools/ratio_drift_check.py` — tests fire size and season mix as causes of the 2019–2025 ratio drop → `data/ratio_drift_v2.csv`.
- `tools/daynight_test.py` — day/night factors vs. monthly factors on the raw FIRMS archive CSVs (the grid has no `daynight` column): `python tools/daynight_test.py MODIS_SP.csv VIIRS_SNPP_SP.csv`.
- `tools/make_figures.py` — re-draws `fig1`, `fig2` and `fig4` with English labels from the data files and prints the WAPE/bias of the test figure: `python tools/make_figures.py . out_folder`. `fig3` comes from the team's Colab notebook; only its text labels were replaced by English ones.

## Verification Script
Run `node reference/verify_reference.js` to recompute the reference check from `daily_grid_v2.csv` with the team's function in `reference/JS_fonksiyonu.txt`; the result is written to `reference/validation_values_v2.json`.

## License & AI/SI Tool Disclosure
- **License**: MIT License (`LICENSE`). Third-party libraries in `libs/`: Leaflet 1.9.4 (BSD-2-Clause), Leaflet-Geoman 2.20.6 (MIT), Plotly.js 2.32.0 (MIT). `libs/world.geojson` (177 country outlines, offline map) is a low-resolution country file derived from Natural Earth 1:110m (public domain); the same file (ISO3 ids, a `name` property) is distributed by the *world.geo.json* project of Johan Sundström (UNLICENSE) and in early D3.js examples. *(Team: confirm which of these you downloaded it from.)* Python scripts: pandas, NumPy, matplotlib (BSD) and scikit-learn (BSD-3-Clause, only for the gradient-boosting comparison). Online map layers: Esri World Imagery and World Boundaries and Places (© Esri, Maxar, Earthstar Geographics and the GIS user community) and NASA GIBS (MODIS Terra Corrected Reflectance). Fonts: Barlow and Barlow Condensed (SIL Open Font License) via Google Fonts.
- **AI/SI Disclosure** (Super Intelligence tools were used in this project; where and how):
  - *Code.* Claude (Anthropic) and Gemini (Google) helped write the front-end (`index.html`: interface scaffolding and the bilingual EN/TR texts; the v6 full-screen interface was written with Claude) and the Colab data pipeline and validation experiments that produced `daily_grid_v2.csv`, the two `monthly_factors*.json` files, `summary_v2.json` and the files in `data/`. The helper scripts in `tools/` (including the method comparison, the gradient-boosting sensitivity check and the ratio-drift test) and the v7 features of the app (overlap check, trend test, on-this-day, fire-frequency map, one-page report, guided demo, loading other regions) were written with Claude. The choice of what to test, and the decision to keep the monthly factor, were reviewed by the team against the numbers in `data/`. AI-assisted scripts carry a note in their header, `index.html` carries one in its head and the in-app *Help* panel repeats it.
  - *Figures.* The plots are drawn by code from the data (matplotlib). No AI image or video generation was used, so there is no watermark. `fig1`, `fig2` and `fig4` were re-drawn in English with `tools/make_figures.py` (written with Claude); in `fig3` only the text labels were replaced.
  - *Text.* The documentation and the interface texts were drafted with AI help.
  - *Checks.* The pipeline was run on the real FIRMS data by the team. The numbers of the validation table were additionally recomputed from `daily_grid_v2.csv` with `tools/verify_validation_csv.py`.

## Colour scale (v6.5)

- Calendar and map use the same 5-stop inferno-style palette; the legend gradient matches it exactly. Grey-brown = zero hotspots.
- Colour is a **log scale** of hotspots per cell, stretched between the **5th and 98th percentile of the non-zero values currently in view** (below 30 non-zero values: 0..max). Cells at the ends are clipped (legend shows "≤" and "≥"); the tooltip on the legend gives the exact maximum.
- The scale is **relative to the current view** (area, years, week/month), so colours are not comparable between different views; use the legend numbers.
- The map has its own legend (bottom-left). It is hidden when no cells are shown.
- Hotspot count is a detection count, not burned area.
- Numbers printed on calendar cells are dark or white, whichever has the higher WCAG contrast against the cell colour.
- The fire-frequency map uses the same ramp on a linear scale from 1 to the number of selected years.

