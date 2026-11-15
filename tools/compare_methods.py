#!/usr/bin/env python3
"""Compare alternative MODIS -> VIIRS harmonization methods under the same held-out schemes.

    python tools/compare_methods.py daily_grid_v2.csv data/method_comparison_v2.csv

Why: the product uses ONE factor per calendar month (column "aylik" of
data/validation_summary_v2.csv). This script checks that choice against simpler, more flexible
and machine-learning alternatives, always learning on training years only and predicting
held-out years (no leakage). Every number the app shows in "Other methods we tested" comes from
the CSV this script writes.

Two scores per method and scheme (WAPE = sum|obs - pred| / sum obs, bias = (sum pred - sum obs) / sum obs):
    region      monthly totals of the whole bounding box (same as the validation table)
    square      monthly totals of 1 deg x 1 deg squares (~110 x 85 km; what a user sees after
                drawing a small area). Region-level methods (fitted on regional monthly totals)
                cannot be applied to a square, so they have no square score.

Methods
    single        one VIIRS/MODIS ratio for all months
    monthly       one ratio per calendar month                     <- used in the product
    power_law     log V = a + b log M, fitted on regional monthly totals
    linear        V = a + b M (ordinary least squares), regional monthly totals
    quantile_map  empirical quantile mapping of regional monthly totals (MODIS CDF -> VIIRS CDF)
    subregion     monthly ratios fitted separately for 4 sub-regions (split at 39.0N and 35.2E)
    square_shrunk monthly ratio x per-square correction, shrunk toward 1 (k = 200 detections)
    gbm_poisson   gradient boosting (scikit-learn HistGradientBoostingRegressor, Poisson loss) on
                  square-months; features: log1p(MODIS), month, square lat/lon centre

Schemes (same as tools/verify_validation_csv.py):
    1 fixed split 2012-2018 -> 2019-2025, 2 expanding window (test 2015-2025), 3 leave one year out.

Not testable with the packaged grid: day/night splits and fire-radiative-power classes need the
raw FIRMS records (daynight, frp columns), which the 0.25 deg daily grid does not keep.

Requires pandas, numpy and (for gbm_poisson only) scikit-learn.
AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import sys

import numpy as np
import pandas as pd

K_SHRINK = 200.0


def load(path):
    g = pd.read_csv(path, usecols=["date", "lat", "lon", "raw_modis", "raw_viirs"])
    d = pd.to_datetime(g["date"])
    g["year"], g["month"] = d.dt.year, d.dt.month
    g = g[g.year >= 2012].copy()
    g["sla"], g["slo"] = np.floor(g.lat).astype(int), np.floor(g.lon).astype(int)
    D = (g.groupby(["sla", "slo", "year", "month"])[["raw_modis", "raw_viirs"]].sum()
         .rename(columns={"raw_modis": "M", "raw_viirs": "V"}).reset_index())
    D["sq"] = D.sla.astype(str) + "_" + D.slo.astype(str)
    D["sub"] = (D.sla + .5 >= 39.0).astype(int) * 2 + (D.slo + .5 >= 35.2).astype(int)
    return D


def regional(D):
    return D.groupby(["year", "month"])[["M", "V"]].sum().reset_index()


def monthly_ratio(tr):
    pooled = tr.V.sum() / tr.M.sum()
    gm = tr.groupby("month")[["V", "M"]].sum()
    fm = gm.V / gm.M
    return fm, pooled


# ---- region-level methods: (train regional df, test regional df) -> predictions ----
def r_single(tr, te):
    return te.M * tr.V.sum() / tr.M.sum()


def r_monthly(tr, te):
    fm, pooled = monthly_ratio(tr)
    return te.M * te.month.map(fm).fillna(pooled)


def r_power(tr, te):
    t = tr[(tr.M > 0) & (tr.V > 0)]
    b, a = np.polyfit(np.log(t.M), np.log(t.V), 1)
    return np.exp(a) * np.power(te.M.clip(lower=0), b)


def r_linear(tr, te):
    b, a = np.polyfit(tr.M, tr.V, 1)
    return (a + b * te.M).clip(lower=0)


def r_qmap(tr, te):
    qs = np.linspace(0, 1, 101)
    qm, qv = np.quantile(tr.M, qs), np.quantile(tr.V, qs)
    # beyond the training range keep the ratio of the top quantiles instead of flattening
    p = np.interp(te.M, qm, qv)
    hi = te.M > qm[-1]
    p[hi.values] = te.M[hi] * qv[-1] / qm[-1]
    return pd.Series(p, index=te.index)


# ---- square-level methods: (train square df, test square df) -> square predictions ----
def s_monthly(tr, te):
    fm, pooled = monthly_ratio(tr)
    return te.M * te.month.map(fm).fillna(pooled)


def s_subregion(tr, te):
    out = pd.Series(0.0, index=te.index)
    fm_all, pooled = monthly_ratio(tr)
    for s, t in tr.groupby("sub"):
        idx = te["sub"] == s
        gm = t.groupby("month")[["V", "M"]].sum()
        fm = gm.V / gm.M.where(gm.M > 0)
        f = te.loc[idx, "month"].map(fm).fillna(te.loc[idx, "month"].map(fm_all)).fillna(pooled)
        out[idx] = te.loc[idx, "M"] * f
    rest = ~te["sub"].isin(tr["sub"].unique())
    out[rest] = te.loc[rest, "M"] * te.loc[rest, "month"].map(fm_all).fillna(pooled)
    return out


def s_shrunk(tr, te):
    fm, pooled = monthly_ratio(tr)
    base_tr = tr.M * tr.month.map(fm).fillna(pooled)
    agg = pd.DataFrame({"sq": tr.sq, "V": tr.V, "B": base_tr}).groupby("sq")[["V", "B"]].sum()
    corr = (agg.V + K_SHRINK) / (agg.B + K_SHRINK)
    return te.M * te.month.map(fm).fillna(pooled) * te.sq.map(corr).fillna(1.0)


def s_gbm(tr, te):
    from sklearn.ensemble import HistGradientBoostingRegressor

    def X(d):
        return np.column_stack([np.log1p(d.M), d.month, d.sla + .5, d.slo + .5])

    t = tr[(tr.M > 0) | (tr.V > 0)]
    m = HistGradientBoostingRegressor(loss="poisson", max_iter=300, learning_rate=.05,
                                      max_leaf_nodes=15, min_samples_leaf=40, random_state=0)
    m.fit(X(t), t.V)
    p = m.predict(X(te))
    p[(te.M <= 0).values] = 0.0  # like every other method: no MODIS detection -> no prediction
    return pd.Series(p, index=te.index)


REGION_METHODS = {"single": r_single, "monthly": r_monthly, "power_law": r_power,
                  "linear": r_linear, "quantile_map": r_qmap}
SQUARE_METHODS = {"monthly": s_monthly, "subregion": s_subregion,
                  "square_shrunk": s_shrunk, "gbm_poisson": s_gbm}


def score(obs, pred):
    return 100 * (obs - pred).abs().sum() / obs.sum(), 100 * (pred.sum() - obs.sum()) / obs.sum()


def main(path, out):
    D = load(path)
    R = regional(D)
    schemes = {
        "1": lambda d: [(d[d.year <= 2018], d[d.year >= 2019])],
        "2": lambda d: [(d[d.year < y], d[d.year == y]) for y in range(2015, 2026)],
        "3": lambda d: [(d[d.year != y], d[d.year == y]) for y in range(2012, 2026)],
    }
    rows = []
    for sid, folds in schemes.items():
        for name, fn in REGION_METHODS.items():
            P = pd.concat([te.assign(p=fn(tr, te)) for tr, te in folds(R)])
            w, b = score(P.V, P.p)
            rows.append(dict(scheme=sid, method=name, level="region", wape=w, bias=b))
        for name, fn in SQUARE_METHODS.items():
            P = pd.concat([te.assign(p=fn(tr, te)) for tr, te in folds(D)])
            w, b = score(P.V, P.p)
            rows.append(dict(scheme=sid, method=name, level="square", wape=w, bias=b))
            if name != "monthly":  # the regional score of "monthly" is identical to r_monthly
                g = P.groupby(["year", "month"])[["V", "p"]].sum()
                w, b = score(g.V, g.p)
                rows.append(dict(scheme=sid, method=name, level="region", wape=w, bias=b))
    T = pd.DataFrame(rows)
    T["wape"], T["bias"] = T.wape.round(1), T.bias.round(1)
    T.to_csv(out, index=False)
    piv = T.pivot_table(index=["method", "level"], columns="scheme", values=["wape", "bias"])
    print(piv.to_string())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
