#!/usr/bin/env python3
"""Why did the VIIRS/MODIS ratio fall after 2018? Test two candidate explanations with the grid.

    python tools/ratio_drift_check.py daily_grid_v2.csv data/ratio_drift_v2.csv

The pooled VIIRS/MODIS ratio is 3.75 in 2012-2018 and 3.50 in 2019-2025 (-6.7 %), which is why
the fixed-split validation has a positive bias. Two explanations can be tested with the 0.25 deg
daily grid:

 1. Fire size ("bigger fires -> MODIS catches a larger share -> lower ratio"). Cell-days are split
    into LARGE (>= 10 VIIRS detections in the 0.25 deg cell that day) and SMALL (the rest). If the
    share of VIIRS detections coming from large cell-days rose, the pooled ratio would fall.
 2. Season mix ("more fires in months whose ratio is low"). The expected ratio of each period is
    computed from the full-period monthly ratios weighted by that period's MODIS monthly counts.

Orbit drift of Terra (earlier overpass, after 2020) and Aqua (later overpass, after 2022) is a third
candidate; the grid does not separate Terra from Aqua, so it cannot be tested here.

Output CSV: one row per year 2012-2025 and one per period (year = "2012-2018" / "2019-2025"), columns
    year, ratio, share_large, ratio_large, ratio_small, season_mix_ratio

AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import sys

import pandas as pd

LARGE = 10


def row(x, f):
    big = x.raw_viirs >= LARGE
    mm = x.groupby("month").raw_modis.sum()
    return {
        "ratio": x.raw_viirs.sum() / x.raw_modis.sum(),
        "share_large": x[big].raw_viirs.sum() / x.raw_viirs.sum(),
        "ratio_large": x[big].raw_viirs.sum() / max(x[big].raw_modis.sum(), 1),
        "ratio_small": x[~big].raw_viirs.sum() / x[~big].raw_modis.sum(),
        "season_mix_ratio": (mm * f.reindex(mm.index)).sum() / mm.sum(),
    }


def main(path, out):
    g = pd.read_csv(path, usecols=["date", "raw_modis", "raw_viirs"])
    d = pd.to_datetime(g["date"])
    g["year"], g["month"] = d.dt.year, d.dt.month
    g = g[g.year >= 2012]
    f = g.groupby("month").apply(lambda x: x.raw_viirs.sum() / x.raw_modis.sum(), include_groups=False)
    rows = [{"year": str(y), **row(x, f)} for y, x in g.groupby("year")]
    for a, b in [(2012, 2018), (2019, 2025)]:
        rows.append({"year": f"{a}-{b}", **row(g[g.year.between(a, b)], f)})
    T = pd.DataFrame(rows).round(3)
    T.to_csv(out, index=False)
    print(T.to_string(index=False))
    p, q = T.iloc[-2], T.iloc[-1]
    print(f"\npooled ratio {p.ratio:.3f} -> {q.ratio:.3f} ({100 * (q.ratio / p.ratio - 1):+.1f} %)")
    print(f"large-fire share of VIIRS {100 * p.share_large:.1f} % -> {100 * q.share_large:.1f} %")
    print(f"ratio large {p.ratio_large:.2f} -> {q.ratio_large:.2f} ({100 * (q.ratio_large / p.ratio_large - 1):+.1f} %), "
          f"small {p.ratio_small:.2f} -> {q.ratio_small:.2f} ({100 * (q.ratio_small / p.ratio_small - 1):+.1f} %)")
    print(f"season-mix expected ratio {p.season_mix_ratio:.3f} -> {q.season_mix_ratio:.3f} "
          f"({100 * (q.season_mix_ratio / p.season_mix_ratio - 1):+.1f} %)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
