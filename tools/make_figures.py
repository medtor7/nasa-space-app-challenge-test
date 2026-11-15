#!/usr/bin/env python3
"""Re-draw three of the figures with English labels, straight from the data files.

    python tools/make_figures.py <app folder> <output folder>

Outputs (same names as the files the app shows in its Method panel):
    fig1_v2_before_after.png      yearly raw MODIS / raw VIIRS, and the harmonized series
    fig2_v2_monthly_factors.png   the 12 monthly conversion factors VIIRS / MODIS
    fig4_v2_test_period.png       held-out test 2019-2025, scheme 1 of the validation table

fig3_v2_manavgat_2021.png (the 2021 Manavgat case study) comes from the team's Colab notebook;
its Turkish labels were replaced by English ones and the plotted data were left untouched.

Scheme 1 = factors learned from 2012-2018 only, then applied to the MODIS monthly totals of
2019-2025 and compared with the real VIIRS monthly totals (same definition as
tools/verify_validation_csv.py). The script prints the WAPE / bias of the figure it draws, so
the numbers can be compared with data/validation_summary_v2.csv.

AI/SI disclosure: this script was written with the help of Claude (Anthropic).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BLUE, ORANGE, GREEN = "#1f77b4", "#ff7f0e", "green"


def load(path):
    g = pd.read_csv(path, usecols=["date", "intensity", "raw_modis", "raw_viirs"])
    d = pd.to_datetime(g["date"])
    g["year"], g["month"] = d.dt.year, d.dt.month
    return g


def fig1(g, out):
    y = g.groupby("year")[["raw_modis", "raw_viirs", "intensity"]].sum()
    v = y["raw_viirs"][y["raw_viirs"] > 0]
    fig, ax = plt.subplots(1, 2, figsize=(14, 4), dpi=150)
    ax[0].plot(y.index, y["raw_modis"], "o-", color=BLUE, label="MODIS (raw)")
    ax[0].plot(v.index, v, "o-", color=ORANGE, label="VIIRS (raw)")
    ax[0].set(title="Before: raw sensor records", xlabel="year", ylabel="Detections per year")
    ax[0].legend()
    ax[1].plot(y.index, y["intensity"], "o-", color=GREEN)
    ax[1].set(title="After: harmonized single series", xlabel="year",
              ylabel="Harmonized hotspot count per year")
    for a in ax:
        a.axvspan(1999.5, 2002.5, color="grey", alpha=0.2)
    ax[1].text(2000.1, ax[1].get_ylim()[1] * 0.93, "Terra only\n(until 3 Jul 2002)",
               va="top", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig2(factors, out):
    f = pd.Series({int(k): v for k, v in factors.items()}).sort_index()
    fig, ax = plt.subplots(figsize=(8, 3.5), dpi=150)
    ax.bar(f.index, f.values, width=0.5, color="steelblue")
    ax.axhline(f.mean(), color="grey", linestyle="--",
               label=f"mean of the 12 factors ({f.mean():.2f})")
    ax.set(title="Monthly conversion factor (VIIRS / MODIS)", xlabel="Month",
           ylabel="VIIRS detections per MODIS detection")
    ax.set_xticks(range(1, 13))
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def scheme1(g):
    m = g.groupby(["year", "month"])[["raw_modis", "raw_viirs"]].sum().reset_index()
    tr, te = m[m.year.between(2012, 2018)].copy(), m[m.year >= 2019].copy()
    f1 = tr.raw_viirs.sum() / tr.raw_modis.sum()
    fm = tr.groupby("month").apply(lambda d: d.raw_viirs.sum() / d.raw_modis.sum(),
                                   include_groups=False)
    te["single"] = te.raw_modis * f1
    te["monthly"] = te.raw_modis * te.month.map(fm)
    te["date"] = pd.to_datetime(dict(year=te.year, month=te.month, day=1))
    return te.reset_index(drop=True)


def report(tag, te):
    for col in ("single", "monthly"):
        wape = 100 * (te.raw_viirs - te[col]).abs().sum() / te.raw_viirs.sum()
        bias = 100 * (te[col].sum() - te.raw_viirs.sum()) / te.raw_viirs.sum()
        print(f"{tag} {col:8s} WAPE {wape:5.1f}%  bias {bias:+5.1f}%")


def test_fig(te, out, title, size, dpi):
    fig, ax = plt.subplots(figsize=size, dpi=dpi)
    ax.plot(te.date, te.raw_viirs, color="black", lw=2.2, label="Real VIIRS")
    ax.plot(te.date, te.single, color="orange", lw=1.6, label="Prediction, single factor")
    ax.plot(te.date, te.monthly, color="green", lw=1.6, label="Prediction, monthly factors")
    ax.set(title=title, ylabel="Hotspot detections per month")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def main(app, outdir):
    app, outdir = Path(app), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    g2 = load(app / "daily_grid_v2.csv")
    fig1(g2, outdir / "fig1_v2_before_after.png")
    fig2(json.load(open(app / "monthly_factors_v2.json")), outdir / "fig2_v2_monthly_factors.png")
    te2 = scheme1(g2)
    report("scheme 1", te2)
    test_fig(te2, outdir / "fig4_v2_test_period.png",
             "Held-out test 2019-2025 (factors learned from 2012-2018 only): "
             "real VIIRS vs. prediction from MODIS", (12, 4), 150)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
