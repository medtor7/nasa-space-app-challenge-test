#!/usr/bin/env python3
"""Build data/yearly_ratio_v2.csv from daily_grid_v2.csv.

For every year 2012-2025 (the VIIRS era) the file holds
    ratio = (sum of raw VIIRS detections) / (sum of raw MODIS detections)
over all cell-days of the dataset - the same "ratio of sums" definition that the
calendar-month scaling factors use.

AI/SI disclosure: this script was written with the help of Claude (Anthropic).

Usage (from the project folder):
    python tools/make_yearly_ratio.py [daily_grid_v2.csv] [data/yearly_ratio_v2.csv]
"""
import csv
import sys
from collections import defaultdict

src = sys.argv[1] if len(sys.argv) > 1 else "daily_grid_v2.csv"
dst = sys.argv[2] if len(sys.argv) > 2 else "data/yearly_ratio_v2.csv"

modis, viirs = defaultdict(float), defaultdict(float)
with open(src, newline="") as f:
    for row in csv.DictReader(f):
        year = int(row["date"][:4])
        modis[year] += float(row["raw_modis"])
        viirs[year] += float(row["raw_viirs"])

with open(dst, "w", newline="") as f:
    out = csv.writer(f, lineterminator="\n")
    out.writerow(["year", "modis", "viirs", "ratio"])
    for year in range(2012, 2026):
        if modis[year] > 0 and viirs[year] > 0:
            out.writerow([year, int(round(modis[year])), int(round(viirs[year])),
                          round(viirs[year] / modis[year], 4)])
print("wrote", dst)
