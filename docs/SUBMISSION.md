# Submission kit — Burning Activity Calendar

Ready-to-paste texts for the NASA Space Apps submission form, the 30-second demo, the 7-slide deck and the judges' questions. Every number below is in `data/` or printed by a script in `tools/`.

## 1. Project summary (form, ≤ 1 paragraph)
MODIS has watched fires since 2000; VIIRS, since 2012, sees about 3.6× more of them because its pixels are smaller. As MODIS reaches the end of its mission, more than ten years of fire history (2000–2011) risk becoming incomparable with today. We harmonize 25 years of NASA FIRMS detections over Türkiye and its surroundings into one VIIRS-equivalent daily series on a 0.25° grid: one factor per calendar month, learned on the 2012–2025 overlap, with separate Terra-only factors before Aqua joined on 4 July 2002. Tested on years the factors never saw, the region's monthly totals are predicted with 15–18% error. Seven alternatives, including gradient boosting, were scored the same way; none is better for small areas and the record barely depends on the method (r = 0.996). The web app turns the series into a burning-activity calendar: pick any area, read the fire season week by week, see if this month or this day is unusual compared with 25 years, test the trend, map how often each place burns and print a one-page brief. It runs for any region from FIRMS CSV files, entirely in the browser.

## 2. 30-second demo video (English, voice-over)
| Time | Screen | Voice-over |
|---|---|---|
| 0–6 s | Method panel, before/after figure | "MODIS sees fewer fires than VIIRS. When MODIS retires, ten years of fire history stop being comparable." |
| 6–14 s | ▶ Demo step 2: 2021 case study, calendar week 31 lights up, map over NASA true-colour image | "We put both sensors on one scale. Here are the 2021 Manavgat megafires, week by week, over NASA's image of that week." |
| 14–21 s | Step 3: "Aug 2021: 4,149 · median 63", On-this-day bars | "Is this unusual? About sixty-five times the August median of the other years — and the same dates in every other year were far quieter." |
| 21–27 s | Method → overlap check + method comparison table | "Tested on years it never saw: 18% error; eight methods compared, the result holds." |
| 27–30 s | Layers → Another region; report | "Any region, any agency, one click to a field brief." |

*(Check the August numbers on screen before recording: they depend on the preset area.)*

## 3. Seven slides
1. **The problem** — 1 km vs. 375 m pixels, different sensitivity, different overpass times; MODIS retiring → 2000–2011 at risk.
2. **Our bridge** — monthly VIIRS/MODIS factors (2.49 in June … 5.09 in April), Terra-only factors before 4 July 2002, VIIRS as is from 2012.
3. **Does it hold?** — three held-out schemes, WAPE 17.9 / 16.7 / 15.4%; live overlap check for any drawn area.
4. **We tried harder models** — 9-method table incl. day/night factors; gradient boosting wins on the region but not on small areas; sensitivity r = 0.996.
5. **Honest limits** — small areas ~45% monthly error; 2000–02 least certain (⚠); ratio drift tested (fire size, season mix) and only partly explained.
6. **For the people who fight fires** — demo: area → calendar → "this month vs. median" → on this day → fire-frequency map → one-page report.
7. **Beyond Türkiye and beyond MODIS** — any FIRMS region in the browser; continues on VIIRS S-NPP / NOAA-20 / NOAA-21.

## 4. Judges' hardest questions
**"Gradient boosting is better — why don't you use it?"**
It is better only for the whole region (15.2% vs. 17.9% in the forward test). For 1° squares it is worse (48.4% vs. 47.1%), its bias flips sign between schemes, it cannot be trained for the Terra-only years, and a non-linear monthly model does not add up from the daily 0.25° cells the calendar is built from. We use it as a sensitivity check: the 2003–2011 yearly totals change by 2–15% but correlate at r = 0.996, so which years were high or low does not depend on the method.

**"Why does the error rise from ~18% to ~45% when I draw a small area?"**
The VIIRS/MODIS ratio is not uniform in space; it depends on land cover and fire size. We measured it on 1° × 1° squares (`tools/small_area_check.py`): 45–47% per square-month, 16–23% median bias on multi-year square totals. Learning a separate factor per square made it worse in the forward test (59.6%), because the spatial pattern is not stable over time. So we keep regional monthly factors and tell the user: the overlap check in the Method panel recomputes the error for whatever area is drawn.

**"Why is 2001 so much higher than 2003–2007 (56,714)?"**
Only Terra flew before 4 July 2002, so those dates use Terra-only factors. Raw Terra detections in September and October 2001 (2,092 and 1,387) were already higher than Terra + Aqua together in 2003 (1,523 and 970). Aug–Oct make up 77% of the 2001 total; the noisy winter factors (Jan 17.8, Dec 17.1) touch less than 9%. The period is marked ⚠ and excluded from the anomaly baseline (2003+).

**"Why did the ratio fall after 2018?"**
We tested it. Not because of bigger fires: the large-fire share stayed at ~30% and the drop is in small fires (−7.8%). Season mix explains 1.6 of 6.7 points. Terra/Aqua orbit drift is the remaining candidate; testing it needs the satellites kept apart, which our grid does not do. The drop is why the forward test has a +7.6% bias; schemes that include recent years stay within ±2%.

**"The sensors pass at different times of day. Did you try day and night separately?"**
Yes, on the raw FIRMS records. Separate day and night factors are worse in every scheme (region 25.3% vs. 17.9% in the forward test; +2.6 ± 1.0 points over 14 leave-one-year-out folds). The reason is itself a finding: VIIRS sees far more night fires than MODIS (January: 20.5% vs. 1.5% of detections), so in winter the night factors rest on a handful of MODIS detections and come out at 30–50. One factor per month pools day and night and stays stable.

**"Is fire activity increasing?"**
For the whole region, 2003–2025: Theil–Sen +94 hotspots/year, Mann–Kendall p = 0.64, so no significant trend. Some sub-regions differ; the app tests any drawn area.

## 5. AI / SI disclosure (form field)
Tools used: Claude (Anthropic) and Gemini (Google). They helped write the web interface (`index.html`), the bilingual texts, the Colab data pipeline and the helper scripts in `tools/` (validation re-computation, method comparison, gradient-boosting sensitivity check, ratio-drift test, figures). The team chose the harmonization method, ran the pipeline on the real NASA FIRMS data, and checked every reported number with the scripts (`tools/verify_validation_csv.py`, `reference/verify_reference.js`). No AI-generated images, video or voice were used.

## 6. Before you press "Submit"
- [ ] Demo ≤ 30 s video **or** ≤ 7 slides, in English.
- [ ] Project and demo links open without login (GitHub Pages, not a Live Server address).
- [ ] AI/SI disclosure pasted (section 5).
- [ ] NASA data named: FIRMS (MODIS_SP, VIIRS_SNPP_SP), GIBS.
- [ ] `libs/world.geojson` source confirmed in README (see License section).
- [x] The Colab pipeline is in `pipeline/nasa2.py` (the FIRMS key is read from Colab Secrets, never stored).
- [ ] All team members registered at the same local event; form submitted before the deadline.
