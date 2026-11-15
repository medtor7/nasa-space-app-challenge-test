#!/usr/bin/env python3
"""Re-compute data/validation_summary_v2.csv from daily_grid_v2.csv and compare.

Only the two methods that the product uses are checked ("tek" = single factor,
"aylik" = monthly factor); other rows of the CSV (experiments) are ignored.

Definitions (all on monthly totals of the whole region):
    factor  = sum(VIIRS) / sum(MODIS) over the training years - one factor for
              all months ("tek") or one factor per calendar month ("aylik")
    pred    = MODIS monthly total x factor
    WAPE %  = 100 * sum|obs - pred| / sum(obs)
    bias %  = 100 * (sum(pred) - sum(obs)) / sum(obs)   (positive = pred > obs)
Schemes:
    1  fixed split: train 2012-2018, test 2019-2025
    2  expanding window: test years 2015..2025, each trained on 2012..(year-1)
    3  leave-one-year-out over 2012..2025

Usage (from the project folder):
    python tools/verify_validation_csv.py [daily_grid_v2.csv] [data/validation_summary_v2.csv]
Exit code 0 if every number agrees within 0.05 percentage points, 1 otherwise.

AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import csv
import re
import sys
from collections import defaultdict

grid = sys.argv[1] if len(sys.argv) > 1 else "daily_grid_v2.csv"
table = sys.argv[2] if len(sys.argv) > 2 else "data/validation_summary_v2.csv"

MOD, VII = defaultdict(float), defaultdict(float)
with open(grid, newline="") as f:
    for row in csv.DictReader(f):
        key = (int(row["date"][:4]), int(row["date"][5:7]))
        MOD[key] += float(row["raw_modis"])
        VII[key] += float(row["raw_viirs"])


def fit(years):
    single = sum(VII[(y, m)] for y in years for m in range(1, 13)) / sum(MOD[(y, m)] for y in years for m in range(1, 13))
    monthly = {m: sum(VII[(y, m)] for y in years) / sum(MOD[(y, m)] for y in years) for m in range(1, 13)}
    return single, monthly


def score(pairs):
    obs = sum(o for o, _ in pairs)
    pred = sum(p for _, p in pairs)
    err = sum(abs(o - p) for o, p in pairs)
    return 100 * err / obs, 100 * (pred - obs) / obs


def evaluate(folds):
    """folds = [(train_years, test_years), ...] -> {"tek": (wape, bias), "aylik": (wape, bias)}"""
    tek, aylik = [], []
    for train, test in folds:
        single, monthly = fit(train)
        for y in test:
            for m in range(1, 13):
                tek.append((VII[(y, m)], MOD[(y, m)] * single))
                aylik.append((VII[(y, m)], MOD[(y, m)] * monthly[m]))
    return {"tek": score(tek), "aylik": score(aylik)}


years = list(range(2012, 2026))
mine = {
    "1": evaluate([(range(2012, 2019), range(2019, 2026))]),
    "2": evaluate([(range(2012, y), [y]) for y in range(2015, 2026)]),
    "3": evaluate([([x for x in years if x != y], [y]) for y in years]),
}

bad = 0
checked = 0
with open(table, newline="") as f:
    for row in csv.DictReader(f):
        method = row["yontem"].strip().lower()
        if method not in ("tek", "aylik"):
            continue
        num = re.match(r"\s*(\d+)", row["sema"])
        if not num or num.group(1) not in mine:
            print("UNKNOWN SCHEME:", row["sema"])
            bad += 1
            continue
        wape, bias = mine[num.group(1)][method]
        ok = abs(wape - float(row["WAPE_%"])) <= 0.05 and abs(bias - float(row["bias_%"])) <= 0.05
        checked += 1
        bad += 0 if ok else 1
        print(("OK       " if ok else "MISMATCH ") +
              f"scheme {num.group(1)} {method:5s} csv WAPE {row['WAPE_%']:>5} bias {row['bias_%']:>5} | "
              f"recomputed WAPE {wape:5.1f} bias {bias:+5.1f}")
print(f"\n{checked} rows checked, {bad} problem(s)")
sys.exit(1 if bad or not checked else 0)
