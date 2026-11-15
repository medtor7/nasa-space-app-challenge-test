#!/usr/bin/env python3
"""How much worse is the MODIS -> VIIRS scaling for a SMALL area than for the whole region?

    python tools/small_area_check.py daily_grid_v2.csv

The validation table (data/validation_summary_v2.csv) judges the monthly factors on the monthly
totals of the WHOLE bounding box. This script repeats the same three held-out schemes with the
monthly factors, but scores them on 1 deg x 1 deg squares (about 110 x 85 km), which is closer to what a
user sees after drawing a small area.

Per scheme it prints
    region WAPE             must equal the "monthly" rows of the validation CSV (17.9 / 16.7 / 15.4)
    square-month WAPE       sum |VIIRS - predicted| / sum VIIRS over all square-months
    median square |bias|    median over squares of |sum predicted - sum VIIRS| / sum VIIRS
                            (squares with at least 300 VIIRS detections in the test years)
    squares with |bias|>20%  share of those squares

Schemes: 1 = learn 2012-2018, test 2019-2025; 2 = expanding window, test 2015-2025;
3 = leave one year out, 2012-2025 (the same definitions as tools/verify_validation_csv.py).

AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import sys

import numpy as np
import pandas as pd


def main(path):
    g = pd.read_csv(path, usecols=["date", "lat", "lon", "raw_modis", "raw_viirs"])
    d = pd.to_datetime(g["date"])
    g["year"], g["month"] = d.dt.year, d.dt.month
    g = g[g.year >= 2012]
    g["sq"] = np.floor(g.lat).astype(int).astype(str) + "_" + np.floor(g.lon).astype(int).astype(str)
    D = (g.groupby(["sq", "year", "month"])[["raw_modis", "raw_viirs"]].sum()
         .rename(columns={"raw_modis": "M", "raw_viirs": "V"}).reset_index())

    def predict(tr, te):
        pooled = tr.V.sum() / tr.M.sum()
        gm = tr.groupby("month")[["V", "M"]].sum()
        fm = gm.V / gm.M
        return te.M * te.month.map(fm).fillna(pooled)

    schemes = {
        "1 fixed split 2012-18 -> 2019-25": [(D[D.year <= 2018], D[D.year >= 2019])],
        "2 expanding window, test 2015-25": [(D[D.year < y], D[D.year == y]) for y in range(2015, 2026)],
        "3 leave one year out, 2012-25": [(D[D.year != y], D[D.year == y]) for y in range(2012, 2026)],
    }
    print(f"{'scheme':36s} {'region':>8s} {'sq-month':>9s} {'median sq':>10s} {'sq>20%':>7s}")
    print(f"{'':36s} {'WAPE':>8s} {'WAPE':>9s} {'|bias|':>10s}")
    for name, folds in schemes.items():
        R = pd.concat([te.assign(p=predict(tr, te)) for tr, te in folds])
        reg = R.groupby(["year", "month"])[["V", "p"]].sum()
        region = 100 * (reg.V - reg.p).abs().sum() / reg.V.sum()
        sqm = 100 * (R.V - R.p).abs().sum() / R.V.sum()
        s = R.groupby("sq")[["V", "p"]].sum()
        s = s[s.V >= 300]
        bias = (100 * (s.p - s.V) / s.V).abs()
        print(f"{name:36s} {region:7.1f}% {sqm:8.1f}% {bias.median():9.1f}% {100 * (bias > 20).mean():6.0f}%")
    print(f"({len(s)} squares with >= 300 VIIRS detections in the last scheme's test years)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
