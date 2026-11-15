# Submission kit — Burning Activity Calendar

Live app: https://medtor7.github.io/nasa-space-app-challenge-test/ · Code: https://github.com/medtor7/nasa-space-app-challenge-test

Ready-to-paste texts for the NASA Space Apps submission form, the 30-second demo, the 7-slide deck and the judges' questions. Every number below is in `data/` or printed by a script in `tools/`.

## 1. Project summary (form, ≤ 1 paragraph)
MODIS has watched fires since 2000; VIIRS, since 2012, sees about 3.6× more of them because its pixels are smaller. As MODIS reaches the end of its mission, more than ten years of fire history (2000–2011) risk becoming incomparable with today. We harmonize 25 years of NASA FIRMS detections over Türkiye and its surroundings into one VIIRS-equivalent daily series on a 0.25° grid: one factor per calendar month, learned on the 2012–2025 overlap, with separate Terra-only factors before Aqua joined on 4 July 2002. Tested on years the factors never saw, the region's monthly totals are predicted with 15–18% error. Nine alternatives — including day/night factors, fire-intensity (FRP) classes and gradient boosting — were scored the same way; none is better for small areas, and which years stand out does not depend on the method (r = 0.996). The web app turns the series into a burning-activity calendar: pick any area, read the fire season week by week, see if this month or this day is unusual compared with 25 years, test the trend, map how often each place burns and print a one-page brief. It runs for any region from FIRMS CSV files, entirely in the browser.

## 1b. Project Details (form field — paste as is)
*The 7 slides give the first look; this text holds the details that did not fit on them. Slide → judging criterion: 1 Relevance & Impact · 2 Validity (method) · 3 Validity (test) · 4 Creativity & Validity (methods compared) · 5 Validity (uncertainty) · 6 Impact & Presentation (the tool in use) · 7 Relevance (any region, after MODIS).*

**What does it do?**
Burning Activity Calendar is a free web app that turns 25 years of NASA FIRMS active-fire detections over Türkiye and its surroundings (1 Nov 2000 – 31 Dec 2025) into one consistent fire record in which the satellite sensor no longer matters. A user picks an area — by drawing a rectangle, polygon or circle, choosing a preset, typing coordinates or using their location — and a range of years. The app then shows a burning-activity calendar, week by week or month by month: which periods of the year burn most, which years were unusual, and how a given month or day compares with the past. Clicking a calendar cell maps that week's hotspots over NASA's true-colour image of the same week. The app also lists unusual weeks, tests the long-term trend, maps how often each place burns, and exports CSV files, chart images and a one-page printable report. Live app: https://medtor7.github.io/nasa-space-app-challenge-test/ (press ▶ Demo for a 4-step tour).

**How does it work?**
1. *Data.* MODIS (Terra + Aqua, 1 km) and VIIRS (Suomi NPP, 375 m) standard-processing detections were downloaded from the FIRMS Area API for the box 25.5–44.9°E, 35.7–42.2°N. We kept vegetation fires (type 0), MODIS confidence ≥ 30 and VIIRS confidence nominal or high, and counted detections per 0.25° cell and day (309,998 cell-days).
2. *Harmonization.* In the overlap years 2012–2025 VIIRS records about 3.6 detections for every MODIS detection (590,023 vs. 162,829), so the sensor change of 2012 looks like a jump in fire activity. MODIS counts of 2000–2011 are therefore scaled to VIIRS-equivalent counts with one factor per calendar month, learned on the overlap — from 2.49 in June to 5.09 in April, because small spring and autumn agricultural burns are missed by MODIS far more often than large summer forest fires. Before 4 July 2002 only Terra was flying, so that period has its own Terra-only factors. From 2012 on, VIIRS is used unchanged.
3. *Validation.* We predicted the real VIIRS monthly totals from MODIS alone, always in years the factors had not seen, in three ways: learn 2012–2018 and test 2019–2025; an expanding window; and leaving one year out. The error (WAPE) of the region's monthly totals is 17.9%, 16.7% and 15.4% (about 23% with a single factor). The Terra-only factors score 21.5–24.5%. In the app, an overlap check repeats the test for any drawn area.
4. *Alternatives.* We scored ten methods under the same tests: single factor, power law, linear regression, quantile mapping, sub-region and per-square factors, separate day/night factors, fire-intensity (FRP) classes, and gradient boosting. Gradient boosting is best for the whole region (15.2%) but worse for small areas (48.4% vs. 47.1% on 1° squares), its bias changes sign and it cannot be trained for the Terra-only years, so the monthly factor was kept; as a sensitivity check, gradient boosting gives yearly totals that correlate with ours at r = 0.996. Day/night factors fail because VIIRS sees far more night fires than MODIS (January: 20.5% vs. 1.5% of detections); FRP classes add nothing because fire intensity is already encoded in the month.
5. *Uncertainty.* The error depends on area and time window: about 25% / 18% / 11% for weekly / monthly / yearly totals of the whole region, but 65% / 47% / 29% for a 1° square (~9,600 km²). It is random, not systematic: 56% of VIIRS detections fall in cell-days in which MODIS saw nothing. The app shows the measured error for the user's own area and view, draws it as error bars on the yearly chart, and recommends monthly and yearly totals when it is high.
6. *Analytics.* Weekly climatology in log space; critical and core fire season (weeks above 50% and 75% of the seasonal peak); unusual weeks by z-score (mean/SD or robust median/MAD, baseline 2003–2025); a Theil–Sen trend with a Mann–Kendall test; "this month vs. the median of the other years"; "on this day" (±3 days in every year); a fire-frequency map; and a filter for 493 recurrent cells (agricultural burning and industrial sources).
7. *Reproducibility.* The Colab pipeline that builds every data file and the scripts that re-check every published number (validation table 9/9, method comparison, error tables, figures) are in the repository.

**What benefits does it have?**
- It makes the 2000–2011 MODIS record comparable with today, so 25 years can be read on one scale, and it keeps working after MODIS is switched off: from 2012 the series is pure VIIRS.
- It gives decision-ready sentences instead of raw maps. In our case study of the July–August 2021 Manavgat–Muğla megafires, August 2021 had 4,149 hotspots — 66 times the median August of the other years — and the calendar shows the week the fires began.
- It is honest about uncertainty: every MODIS-based value carries the error measured for that area and view.
- It is free, needs no login or API key, works in English and Turkish, adapts to phones and falls back to an offline map without a connection.

**What is the intended impact?**
- *Early warning and emergency responders:* know when the fire season starts and peaks in their area, and see whether this month or week is unusual, to plan staff and resources.
- *Land managers and firefighters:* see where fire comes back year after year (fire-frequency map, recurrent-source filter) and brief teams with a one-page report.
- *Scientists:* a validated, consistent 25-year series with downloadable CSV files and a documented, reproducible method.
- *Beyond Türkiye:* any user can load NASA FIRMS files for another region; the app grids them in the browser and learns that region's own factors, so the same tool can serve any Space Apps partner agency. The method also bridges the end of MODIS: VIIRS continues on S-NPP, NOAA-20 and NOAA-21.

**What tools, coding languages, hardware or software did you use?**
Python (pandas, NumPy, SciPy, scikit-learn, matplotlib) in Google Colab for the data pipeline and the experiments; JavaScript, HTML and CSS for the single-page app; Leaflet and Leaflet-Geoman for the map and drawing tools; Plotly.js for charts; NASA FIRMS (Area API) and NASA GIBS (MODIS Terra true-colour imagery); Esri World Imagery as satellite background; GitHub and GitHub Pages for code and hosting; Node.js for the reference check. No special hardware. AI assistants (Claude, Gemini) helped write code and text; see the AI disclosure.

**How is your project creative?**
- The calendar view: 26 years × 52 weeks of fire activity on one screen; one click links a week to the map and to NASA's image of that week.
- Plain-language comparisons — "this month vs. history" and "on this day across 25 years" — instead of raw numbers alone.
- Uncertainty that follows the user: the error shown changes with the area drawn and the time window read.
- Showing what did not work: we tested ten methods and present the failures too; the day/night test turned into a finding about where the two sensors differ most.
- A region-agnostic tool: users can load their own FIRMS files, and the app learns that region's conversion factors in the browser.

**What factors did your team consider?**
- *Scientific honesty:* no data leakage (factors learned only on training years), forward-in-time tests, limits stated in the app; the single-satellite years 2000–2002 are flagged and kept out of the anomaly baseline; the drop in the VIIRS/MODIS ratio after 2018 was tested (fire size and season mix explain little).
- *Consistency:* a factor per month keeps every area, week and day additive — any area's value is the sum of its cells.
- *Users and accessibility:* a colour ramp with numbered legends; anomalies marked by outlines and ★, not colour alone; text colour chosen for contrast; English/Turkish; phone layout; offline fallback.
- *Data quality:* vegetation-fire filter and confidence thresholds; recurrent industrial and agricultural sources can be excluded; 2000 is shown as a partial year (November–December only).
- *Scope and limits:* hotspot counts are detections, not burned area; the region is a box, not the national border; the archive ends on 31 December 2025, so a button opens the FIRMS live map for current fires.
- *Openness:* MIT license; third-party licenses checked and listed; the pipeline and verification scripts are public.

## 2. 30-second demo video (English, voice-over)
| Time | Screen | Voice-over |
|---|---|---|
| 0–6 s | Method panel, before/after figure | "MODIS sees fewer fires than VIIRS. When MODIS retires, ten years of fire history stop being comparable." |
| 6–14 s | ▶ Demo step 2: 2021 case study, calendar week 31 lights up, map over NASA true-colour image | "We put both sensors on one scale. Here are the 2021 Manavgat megafires, week by week, over NASA's image of that week." |
| 14–21 s | Step 3: "Aug 2021: 4,149 · median 63", On-this-day bars | "Is this unusual? About sixty-five times the August median of the other years — and the same dates in every other year were far quieter." |
| 21–27 s | Method → overlap check + method comparison table | "Tested on years it never saw: 18% error; ten methods compared, the result holds." |
| 27–30 s | Layers → Another region; report | "Any region, any agency, one click to a field brief." |

*(Check the August numbers on screen before recording: they depend on the preset area.)*

## 3. Seven slides (the deck)
Deck: https://claude.ai/artifact/Nct6uosYBurYMyn7MRC3Ec (share it, or export it as PowerPoint/PDF, from its Share menu). English speaker notes on every slide.
1. **Burning Activity Calendar** — the problem: VIIRS sees 3.6× more fires than MODIS; 2012 looks like a false jump; the 2000–2011 record is at risk as MODIS retires. *(Relevance, Impact)*
2. **One conversion factor per calendar month** — before/after figure; Terra-only → Terra + Aqua (2.49–5.09) → VIIRS as is from 2012. *(Validity: method)*
3. **Tested only on years the factors never saw** — WAPE 17.9 / 16.7 / 15.4% (single factor ~23%). *(Validity: test)*
4. **Ten methods, same tests: the simple one holds** — gradient boosting, FRP, day/night and others; r = 0.996. *(Creativity, Validity)*
5. **We measure the error for every view, and show it** — error by area and time window; 56% of VIIRS detections where MODIS saw nothing. *(Validity: uncertainty)*
6. **Is this unusual? One screen answers it** — app screenshot of the 2021 Manavgat–Muğla case: “Aug 2021: 4,149, 66× the median”; five steps of use. *(Impact, Presentation)*
7. **Any region. After MODIS. Open.** — FIRMS files for any region, continuity on VIIRS, open code; live link and ▶ Demo. *(Relevance, Impact)*

## 4. Judges' hardest questions
**"Gradient boosting is better — why don't you use it?"**
It is better only for the whole region (15.2% vs. 17.9% in the forward test). For 1° squares it is worse (48.4% vs. 47.1%), its bias flips sign between schemes, it cannot be trained for the Terra-only years, and a non-linear monthly model does not add up from the daily 0.25° cells the calendar is built from. We use it as a sensitivity check: the 2003–2011 yearly totals change by 2–15% but correlate at r = 0.996, so which years were high or low does not depend on the method.

**"Why does the error rise from ~18% to ~45% when I draw a small area?"**
The VIIRS/MODIS ratio is not uniform in space; it depends on land cover and fire size. We measured it on 1° × 1° squares (`tools/small_area_check.py`): 45–47% per square-month, 16–23% median bias on multi-year square totals. Learning a separate factor per square made it worse in the forward test (59.6%), because the spatial pattern is not stable over time. The error falls steadily with area and time window (1° square: 65% per week, 47% per month, 29% per year; whole region: 25 / 18 / 11%), which shows it is random, not systematic: 56% of VIIRS detections are in cell-days where MODIS saw nothing, and no scaling can recover fires MODIS never saw. So the app shows the measured error for the user's own area and view — in the ◇ note, as error bars on the yearly chart, and as a banner that recommends monthly and yearly totals when the error is high.

**"Why is 2001 so much higher than 2003–2007 (56,714)?"**
Only Terra flew before 4 July 2002, so those dates use Terra-only factors. Raw Terra detections in September and October 2001 (2,092 and 1,387) were already higher than Terra + Aqua together in 2003 (1,523 and 970). Aug–Oct make up 77% of the 2001 total; the noisy winter factors (Jan 17.8, Dec 17.1) touch less than 9%. The period is marked ⚠ and excluded from the anomaly baseline (2003+).

**"Why did the ratio fall after 2018?"**
We tested it. Not because of bigger fires: the large-fire share stayed at ~30% and the drop is in small fires (−7.8%). Season mix explains 1.6 of 6.7 points. Terra/Aqua orbit drift is the remaining candidate; testing it needs the satellites kept apart, which our grid does not do. The drop is why the forward test has a +7.6% bias; schemes that include recent years stay within ±2%.

**"The sensors pass at different times of day. Did you try day and night separately?"**
Yes, on the raw FIRMS records. Separate day and night factors are worse in every scheme (region 25.3% vs. 17.9% in the forward test; +2.6 ± 1.0 points over 14 leave-one-year-out folds). The reason is itself a finding: VIIRS sees far more night fires than MODIS (January: 20.5% vs. 1.5% of detections), so in winter the night factors rest on a handful of MODIS detections and come out at 30–50. One factor per month pools day and night and stays stable.

**"Doesn't the conversion depend on fire size? Did you use FRP?"**
Yes, on the raw records: MODIS detections split into low / mid / high fire radiative power, one coefficient per class and season. It is worse than one factor per month (region 19.2% vs. 17.9% in the forward test; +4.1 ± 1.0 points over 14 folds). The reason: fire intensity is already encoded in the month — high-FRP detections are 47.5% in July and 10.5% in February — so the classes add no new information.

**"Is fire activity increasing?"**
For the whole region, 2003–2025: Theil–Sen +94 hotspots/year, Mann–Kendall p = 0.64, so no significant trend. Some sub-regions differ; the app tests any drawn area.

## 5. AI / SI disclosure (form field)
Tools used: Claude (Anthropic) and Gemini (Google). They helped write the web interface (`index.html`), the bilingual texts, the Colab data pipeline and the helper scripts in `tools/` (validation re-computation, method comparison, gradient-boosting sensitivity check, ratio-drift test, error-by-scale table, figures), and helped design the day/night and FRP-class tests. The team chose the harmonization method, ran the pipeline and these tests on the real NASA FIRMS data, and checked every reported number with the scripts (`tools/verify_validation_csv.py`, `reference/verify_reference.js`). No AI-generated images, video or voice were used.

## 6. Before you press "Submit"
- [ ] Demo ≤ 30 s video **or** ≤ 7 slides, in English.
- [ ] Project and demo links open without login (GitHub Pages, not a Live Server address).
- [ ] AI/SI disclosure pasted (section 5).
- [ ] NASA data named: FIRMS (MODIS_SP, VIIRS_SNPP_SP), GIBS.
- [x] `libs/world.geojson` source confirmed (D3 Graph Gallery, MIT; notice in `libs/LICENSE-world-geojson.txt`).
- [x] The Colab pipeline is in `pipeline/nasa2.py` (the FIRMS key is read from Colab Secrets, never stored).
- [ ] All team members registered at the same local event; form submitted before the deadline.
