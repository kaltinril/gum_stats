"""
chartit_stars.py — star-history style chart of stars over time.

Two view modes (imgui has ~100x everyone else, so a shared absolute axis is
dominated by it — the growth view fixes that):

  --mode growth   (default)  Percent change from each repo's starting value in
                             the shown window. Every line starts at 0%, so you
                             compare growth *rate*/momentum, not star count.
  --mode absolute            Raw cumulative stars in two panels: linear (shows
                             the absolute spread) and logarithmic (separates the
                             smaller repos).

Every repo gets its own color; the legend is sorted best-first and annotated
with the relevant figure (final % for growth, current stars for absolute).

Usage:
    python chartit_stars.py                 # growth view, full history
    python chartit_stars.py -y 1            # growth view, last year
    python chartit_stars.py --mode absolute # old linear + log view
"""

import argparse

import matplotlib.pyplot as plt
import pandas as pd

from repos_config import ALL_REPOS
from starcounts import CSV_FILE


def load_star_series(years):
    """Return (dates, [(display_name, stars_series), ...]) for every tracked repo."""
    data = pd.read_csv(CSV_FILE)
    data.columns = data.columns.str.strip()
    data["DATE"] = pd.to_datetime(data["DATE"])
    data = data.sort_values("DATE")

    if years is not None:
        cutoff = data["DATE"].max() - pd.DateOffset(days=round(years * 365.25))
        data = data[data["DATE"] >= cutoff]

    series = []
    for r in ALL_REPOS:
        col = f"STARS_{r['alias']}"
        if col not in data.columns:
            continue
        # Drop non-positive values (no repo has 0 stars; log can't plot 0).
        stars = pd.to_numeric(data[col], errors="coerce").mask(lambda s: s <= 0)
        if stars.dropna().empty:
            continue
        series.append((r["display_name"], stars))

    return data["DATE"], series


def plot_growth(dates, series):
    """Percent change from each repo's first value in the window."""
    growth = []
    for name, stars in series:
        valid = stars.dropna()
        first = valid.iloc[0]
        pct = (stars - first) / first * 100.0
        growth.append((name, pct, pct.dropna().iloc[-1]))

    growth.sort(key=lambda t: t[2], reverse=True)
    cmap = plt.get_cmap("tab10")

    fig, ax = plt.subplots(figsize=(13, 8), constrained_layout=True)
    for i, (name, pct, final) in enumerate(growth):
        ax.plot(dates, pct, label=f"{name} (+{final:.0f}%)", color=cmap(i % 10), linewidth=1.9)

    ax.set_title("GitHub Stars — Growth Since Start of Window (% change)", fontsize=14)
    ax.set_ylabel("Growth vs. start (%)")
    ax.set_xlabel("Date")
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper left", fontsize=9, ncol=2)
    fig.autofmt_xdate()


def plot_absolute(dates, series):
    """Raw cumulative stars on linear + log panels."""
    ranked = sorted(series, key=lambda t: t[1].dropna().iloc[-1], reverse=True)
    cmap = plt.get_cmap("tab10")

    fig, (ax_lin, ax_log) = plt.subplots(
        2, 1, figsize=(13, 11), sharex=True, constrained_layout=True
    )
    for i, (name, stars) in enumerate(ranked):
        last = int(stars.dropna().iloc[-1])
        label = f"{name} ({last:,})"
        color = cmap(i % 10)
        ax_lin.plot(dates, stars, label=label, color=color, linewidth=1.8)
        ax_log.plot(dates, stars, label=label, color=color, linewidth=1.8)

    ax_lin.set_title("GitHub Stars Over Time — Linear Scale", fontsize=14)
    ax_lin.set_ylabel("Stars")
    ax_lin.grid(True, linestyle="--", alpha=0.4)
    ax_lin.legend(loc="upper left", fontsize=9, ncol=2)

    ax_log.set_yscale("log")
    ax_log.set_title("GitHub Stars Over Time — Logarithmic Scale", fontsize=14)
    ax_log.set_ylabel("Stars (log scale)")
    ax_log.set_xlabel("Date")
    ax_log.grid(True, which="both", linestyle="--", alpha=0.4)
    fig.autofmt_xdate()


def main():
    parser = argparse.ArgumentParser(description="Star-history style chart of stars over time.")
    parser.add_argument(
        "-y", "--years", type=float, default=None,
        help="Limit to the last N years (e.g. -y 1). Omit to show everything.",
    )
    parser.add_argument(
        "--mode", choices=["growth", "absolute"], default="growth",
        help="growth = %% change from each repo's start (default); absolute = raw stars (linear + log).",
    )
    args = parser.parse_args()

    dates, series = load_star_series(args.years)
    if args.mode == "absolute":
        plot_absolute(dates, series)
    else:
        plot_growth(dates, series)
    plt.show()


if __name__ == "__main__":
    main()
