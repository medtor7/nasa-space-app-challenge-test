#!/usr/bin/env python3
"""Sensitivity check: would the harmonized 2003-2011 series change if gradient boosting replaced
the monthly factors?

    python tools/gbm_sensitivity.py daily_grid_v2.csv data/gbm_sensitivity_v2.csv

tools/compare_methods.py shows that gradient boosting (GBM) scores best on the whole-region
monthly totals, but not on small areas. Here the same model (scikit-learn
HistGradientBoostingRegressor, Poisson loss; features log1p(MODIS), month, 1 deg square centre)
is trained on ALL square-months of 2012-2025 and applied to the MODIS square-months of 2003-2011.
Its yearly totals are compared with the product's series (the "intensity" column = MODIS x monthly
factor). 2000-2002 are left out: before 4 July 2002 only Terra flew, and the grid does not keep
Terra and Aqua apart, so the model cannot be trained for that period.

Output CSV columns: year, monthly_factor, gbm, diff_pct (gbm vs. monthly factor).
AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


def main(path, out):
    g = pd.read_csv(path, usecols=["date", "lat", "lon", "raw_modis", "raw_viirs", "intensity"])
    d = pd.to_datetime(g["date"])
    g["year"], g["month"] = d.dt.year, d.dt.month
    g["sla"], g["slo"] = np.floor(g.lat).astype(int), np.floor(g.lon).astype(int)
    D = g.groupby(["sla", "slo", "year", "month"])[["raw_modis", "raw_viirs", "intensity"]].sum().reset_index()

    def X(x):
        return np.column_stack([np.log1p(x.raw_modis), x.month, x.sla + .5, x.slo + .5])

    tr = D[(D.year >= 2012) & ((D.raw_modis > 0) | (D.raw_viirs > 0))]
    m = HistGradientBoostingRegressor(loss="poisson", max_iter=300, learning_rate=.05, max_leaf_nodes=15,
                                      min_samples_leaf=40, random_state=0).fit(X(tr), tr.raw_viirs)
    te = D[D.year.between(2003, 2011)].copy()
    te["gbm"] = np.where(te.raw_modis > 0, m.predict(X(te)), 0.0)
    y = te.groupby("year")[["intensity", "gbm"]].sum().rename(columns={"intensity": "monthly_factor"})
    y["diff_pct"] = 100 * (y.gbm / y.monthly_factor - 1)
    y = y.round({"monthly_factor": 0, "gbm": 0, "diff_pct": 1}).reset_index()
    y.to_csv(out, index=False)
    print(y.to_string(index=False))
    print(f"correlation of yearly totals: {np.corrcoef(y.monthly_factor, y.gbm)[0, 1]:.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
