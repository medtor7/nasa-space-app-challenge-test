#!/usr/bin/env python3
"""How does the error of the MODIS -> VIIRS scaling depend on the size of the area and the time window?

    python tools/scale_error_check.py daily_grid_v2.csv data/scale_error_v2.csv

The validation table scores the monthly totals of the whole region. A user who draws a small area and
reads single weeks sees much noisier numbers. This script repeats the held-out test at four spatial
scales (0.25 deg cell, 1 deg square, 2 deg square, whole region) and four time windows (calendar week as
in the app, month, 3-month season, year), with the product's monthly factors learned on training years.

WAPE = sum|VIIRS - predicted| / sum VIIRS over all units (cells/squares) and periods of the test years.
Schemes: 1 = learn 2012-2018, test 2019-2025 (forward; the app uses this one, the most cautious);
         3 = leave one year out 2012-2025.
It also prints where the 1 deg monthly error comes from, and the share of VIIRS detections made in
0.25 deg cell-days in which MODIS detected nothing.

Output CSV: scheme, scale, area_km2 (area of one unit at 39 N; region = whole bounding box), window, wape
AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import sys

import numpy as np
import pandas as pd

R = 6371.0088


def box_km2(dlat, dlon, lat=39.0):
    r = np.pi / 180
    return R * R * abs(np.sin((lat + dlat / 2) * r) - np.sin((lat - dlat / 2) * r)) * dlon * r


def main(path, out):
    g = pd.read_csv(path, usecols=["date", "lat", "lon", "raw_modis", "raw_viirs"])
    d = pd.to_datetime(g["date"])
    g["year"], g["month"] = d.dt.year, d.dt.month
    g["week"] = ((d.dt.dayofyear - 1) // 7).clip(upper=51)  # same calendar weeks as the app
    g["season"] = (g.month - 1) // 3
    g = g[g.year >= 2012].copy()
    g["cell"] = g.lat.astype(str) + "_" + g.lon.astype(str)
    g["sq1"] = np.floor(g.lat).astype(int).astype(str) + "_" + np.floor(g.lon).astype(int).astype(str)
    g["sq2"] = ((np.floor(g.lat / 2) * 2).astype(int).astype(str) + "_" +
                (np.floor(g.lon / 2) * 2).astype(int).astype(str))
    cells = g.drop_duplicates("cell")
    region_km2 = sum(box_km2(.25, .25, la) for la in cells.lat)
    scales = [("cell_0.25", "cell", box_km2(.25, .25)), ("square_1", "sq1", box_km2(1, 1)),
              ("square_2", "sq2", box_km2(2, 2)), ("region", None, region_km2)]
    windows = [("week", ["year", "week"]), ("month", ["year", "month"]),
               ("season", ["year", "season"]), ("year", ["year"])]
    schemes = {"1": [(g[g.year <= 2018], g[g.year >= 2019])],
               "3": [(g[g.year != y], g[g.year == y]) for y in range(2012, 2026)]}
    rows = []
    for sid, folds in schemes.items():
        parts = []
        for tr, te in folds:
            f = tr.groupby("month").raw_viirs.sum() / tr.groupby("month").raw_modis.sum()
            parts.append(te.assign(p=te.raw_modis * te.month.map(f)))
        T = pd.concat(parts)
        for sname, col, km2 in scales:
            for wname, keys in windows:
                a = T.groupby(keys + ([col] if col else []))[["raw_viirs", "p"]].sum()
                rows.append(dict(scheme=sid, scale=sname, area_km2=round(km2), window=wname,
                                 wape=round(100 * (a.raw_viirs - a.p).abs().sum() / a.raw_viirs.sum(), 1)))
        if sid == "1":
            a = T.groupby(["sq1", "year", "month"])[["raw_modis", "raw_viirs", "p"]].sum()
            err, tot = (a.raw_viirs - a.p).abs(), a.raw_viirs.sum()
            m0, small = a.raw_modis == 0, (a.raw_viirs < 20) & (a.raw_modis > 0)
            print("1 deg square-months, scheme 1: error %.1f %% of VIIRS = no-MODIS months %.1f + small months "
                  "(<20 VIIRS) %.1f + larger months %.1f points; Poisson floor ~%.1f %%" % (
                      100 * err.sum() / tot, 100 * err[m0].sum() / tot, 100 * err[small].sum() / tot,
                      100 * err[~m0 & ~small].sum() / tot, 100 * np.sqrt(2 * a.raw_viirs / np.pi).sum() / tot))
    print("VIIRS detections in 0.25 deg cell-days with no MODIS detection: %.1f %%" %
          (100 * g[g.raw_modis == 0].raw_viirs.sum() / g.raw_viirs.sum()))
    T = pd.DataFrame(rows)
    T.to_csv(out, index=False)
    print(T.pivot_table(index=["scheme", "scale", "area_km2"], columns="window", values="wape", sort=False)
          [["week", "month", "season", "year"]].to_string())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
