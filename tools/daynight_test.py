#!/usr/bin/env python3
"""Day/night test: do separate day and night factors harmonize MODIS -> VIIRS better than monthly factors?

    python tools/daynight_test.py MODIS_SP.csv VIIRS_SNPP_SP.csv [data/daynight_test_v2.csv]

In Colab, with the yearly raw files written by pipeline/nasa2.py (quote the patterns):
    !python daynight_test.py "/content/drive/MyDrive/nasa_v2/raw/MODIS_SP_*.csv" \
                             "/content/drive/MyDrive/nasa_v2/raw/VIIRS_SNPP_SP_*.csv" daynight_test_v2.csv

Input: the raw NASA FIRMS CSVs (the 0.25 deg grid does not keep the `daynight` column). Each argument
may be a file, a comma-separated list or a glob pattern. The filters are those of pipeline/nasa2.py:
type = 0, MODIS confidence >= 30, VIIRS confidence nominal/high; only 2012-2025 are used.

Methods (factors always learned on training years only; predictions are regional monthly totals)
    monthly            V/M per calendar month                                  (the product)
    daynight           V/M per calendar month and per day/night overpass; prediction = sum of both
    daynight_shrunk    as daynight, but each night factor is pulled toward the month's factor
                       when few night MODIS detections stand behind it (k = 100 detections)
    terra_monthly      Terra-only monthly factors (what the product uses before 4 July 2002)
    terra_daynight     Terra-only factors per month and day/night

Schemes: 1 fixed split 2012-18 -> 2019-25, 2 expanding window (test 2015-25), 3 leave one year out.

Why this matters: MODIS records `daynight` for the whole 2000-2011 period, so day/night factors could
be applied backward. As with the monthly factors, that backward application cannot be tested (there is
no VIIRS before 2012); this script measures only what can be measured: how well each method predicts
VIIRS in held-out overlap years.

AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import glob
import sys

import numpy as np
import pandas as pd

K_SHRINK = 100.0


def read(paths, viirs):
    files = sorted(f for p in paths.split(",") for f in (glob.glob(p) or [p]))
    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f, low_memory=False))
        except pd.errors.EmptyDataError:
            pass
    d = pd.concat(frames, ignore_index=True)
    d.columns = [c.strip().lower() for c in d.columns]
    if "type" in d:
        d = d[d["type"].fillna(0).astype(int) == 0]
    conf = d["confidence"].astype(str).str.strip().str.lower()
    d = d[conf.isin(["n", "h", "nominal", "high"])] if viirs else d[pd.to_numeric(conf, errors="coerce") >= 30]
    dt = pd.to_datetime(d["acq_date"])
    d = d.assign(year=dt.dt.year, month=dt.dt.month, dn=d["daynight"].astype(str).str.upper().str[0])
    d = d[d.year.between(2012, 2025) & d.dn.isin(["D", "N"])]
    if not viirs:
        d = d.assign(terra=d["satellite"].astype(str).str.upper().str.startswith("T"))
    return d


def tables(m, v):
    """Monthly totals per year, month and day/night: M (all MODIS), MT (Terra), V (VIIRS)."""
    idx = ["year", "month", "dn"]
    t = pd.DataFrame({
        "M": m.groupby(idx).size(),
        "MT": m[m.terra].groupby(idx).size(),
        "V": v.groupby(idx).size(),
    }).fillna(0.0)
    full = pd.MultiIndex.from_product([range(2012, 2026), range(1, 13), ["D", "N"]], names=idx)
    return t.reindex(full, fill_value=0.0).reset_index()


def ratio(num, den):
    return num / den if den > 0 else np.nan


def predict(tr, te, col, by_dn, shrink):
    """Regional monthly prediction for the test rows, using MODIS column `col` (M or MT)."""
    fm = tr.groupby("month").apply(lambda x: ratio(x.V.sum(), x[col].sum()), include_groups=False)
    pooled = ratio(tr.V.sum(), tr[col].sum())
    fm = fm.fillna(pooled)
    if not by_dn:
        p = te[col] * te.month.map(fm)
    else:
        g = tr.groupby(["month", "dn"])[[col, "V"]].sum()
        f = {}
        for (mo, dn), r in g.iterrows():
            raw = ratio(r.V, r[col])
            if shrink:  # pull toward the month's factor when few MODIS detections stand behind it
                raw = (r.V + K_SHRINK * fm[mo]) / (r[col] + K_SHRINK)
            f[(mo, dn)] = fm[mo] if np.isnan(raw) else raw
        p = te[col] * [f.get((mo, dn), fm[mo]) for mo, dn in zip(te.month, te.dn)]
    return te.assign(p=p).groupby(["year", "month"])[["V", "p"]].sum()


METHODS = {
    "monthly": ("M", False, False),
    "daynight": ("M", True, False),
    "daynight_shrunk": ("M", True, True),
    "terra_monthly": ("MT", False, False),
    "terra_daynight": ("MT", True, True),
}


def main(mpath, vpath, out):
    m, v = read(mpath, False), read(vpath, True)
    T = tables(m, v)
    night_share = T.groupby("dn").M.sum() / T.M.sum()
    print(f"MODIS 2012-2025: {int(T.M.sum())} detections, night share {100 * night_share.get('N', 0):.1f} %; "
          f"VIIRS: {int(T.V.sum())}, night share {100 * (T.groupby('dn').V.sum() / T.V.sum()).get('N', 0):.1f} %")
    schemes = {
        "1": [(T[T.year <= 2018], T[T.year >= 2019])],
        "2": [(T[T.year < y], T[T.year == y]) for y in range(2015, 2026)],
        "3": [(T[T.year != y], T[T.year == y]) for y in range(2012, 2026)],
    }
    rows = []
    for sid, folds in schemes.items():
        for name, (col, by_dn, shrink) in METHODS.items():
            R = pd.concat([predict(tr, te, col, by_dn, shrink) for tr, te in folds])
            rows.append(dict(scheme=sid, method=name,
                             wape=round(100 * (R.V - R.p).abs().sum() / R.V.sum(), 1),
                             bias=round(100 * (R.p.sum() - R.V.sum()) / R.V.sum(), 1)))
    out_t = pd.DataFrame(rows)
    out_t.to_csv(out, index=False)
    print(out_t.pivot(index="method", columns="scheme", values=["wape", "bias"]).to_string())


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else "data/daynight_test_v2.csv")
