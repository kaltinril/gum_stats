"""
star_chart.py - draws Gum's all-time star history as static SVG images.

The interactive page needs JavaScript, which a GitHub README can't run, so the
README embeds these plain images instead and links to the page:

    stars-light.svg / stars-dark.svg

The line is star_history_gum.csv (every star since 2015, see
backfill_star_history.py) continued by the daily STARS_gum values in data.csv
after the last date in that file. build_site.py calls write_star_charts().
"""

import csv
import datetime
import math
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(HERE, "star_history_gum.csv")
DATA_FILE = os.path.join(HERE, "data.csv")
SITE_URL = "kaltinril.github.io/gum_stats"

# Colors from the dataviz reference palette: series slot 1 (blue, Gum's color on
# the chart page) and the chart chrome, each stepped for its own mode.
THEMES = {
    "light": {
        "surface": "#fcfcfb", "border": "rgba(11,11,11,0.10)", "ink": "#0b0b0b",
        "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7",
        "series": "#2a78d6",
    },
    "dark": {
        "surface": "#1a1a19", "border": "rgba(255,255,255,0.10)", "ink": "#f0efec",
        "ink2": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835",
        "series": "#3987e5",
    },
}

WIDTH, HEIGHT = 800, 340
LEFT, RIGHT, TOP, BOTTOM = 52, 64, 66, 36
FONT = 'system-ui, -apple-system, &quot;Segoe UI&quot;, sans-serif'


def load_series():
    """[(date, stars)] in date order."""
    points = []
    with open(HISTORY_FILE, newline="") as f:
        for row in csv.DictReader(f):
            points.append((datetime.date.fromisoformat(row["DATE"]), int(row["STARS"])))
    last = points[-1][0]
    with open(DATA_FILE, newline="") as f:
        for row in csv.DictReader(f):
            day = datetime.date.fromisoformat(row["DATE"].strip())
            value = (row.get("STARS_gum") or "").strip()
            if day > last and value:
                points.append((day, int(value)))
    return points


def nice_step(max_value, target_ticks=5):
    raw = max_value / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiple in (1, 2, 5, 10):
        if multiple * magnitude >= raw:
            return multiple * magnitude
    return 10 * magnitude


def render(points, theme):
    c = THEMES[theme]
    start, end = points[0][0], points[-1][0]
    total = points[-1][1]
    step = nice_step(total)
    y_max = math.ceil(total / step) * step

    plot_w = WIDTH - LEFT - RIGHT
    plot_h = HEIGHT - TOP - BOTTOM
    span = (end - start).days or 1

    def x(day):
        return LEFT + (day - start).days / span * plot_w

    def y(value):
        return TOP + plot_h - value / y_max * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="t d" font-family=\'{FONT}\'>',
        f'<title id="t">Gum GitHub stars</title>',
        f'<desc id="d">Gum had {total} GitHub stars on {end.isoformat()}, '
        f'up from its first star on {start.isoformat()}.</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="8" '
        f'fill="{c["surface"]}" stroke="{c["border"]}"/>',
        f'<text x="{LEFT}" y="30" font-size="16" font-weight="600" fill="{c["ink"]}">Gum GitHub stars</text>',
        f'<text x="{LEFT}" y="49" font-size="12" fill="{c["ink2"]}">'
        f'Every star since {start.year}, updated daily. Last updated {end.isoformat()}</text>',
        f'<text x="{WIDTH - 16}" y="30" font-size="11" fill="{c["muted"]}" text-anchor="end">{SITE_URL}</text>',
    ]

    # Horizontal gridlines with their values; the zero line is the baseline.
    for value in range(0, y_max + 1, step):
        gy = round(y(value)) + 0.5
        color = c["axis"] if value == 0 else c["grid"]
        out.append(f'<line x1="{LEFT}" x2="{WIDTH - RIGHT}" y1="{gy}" y2="{gy}" stroke="{color}"/>')
        out.append(
            f'<text x="{LEFT - 8}" y="{gy + 4}" font-size="11" fill="{c["muted"]}" '
            f'text-anchor="end" font-variant-numeric="tabular-nums">{value}</text>'
        )

    # Year ticks on January 1st; thin them out if the years get crowded.
    years = range(start.year + 1, end.year + 1)
    every = 1 if plot_w / max(len(years), 1) >= 56 else 2
    base_y = TOP + plot_h
    for year in years:
        if (year - start.year) % every:
            continue
        tx = round(x(datetime.date(year, 1, 1))) + 0.5
        out.append(f'<line x1="{tx}" x2="{tx}" y1="{base_y}" y2="{base_y + 4}" stroke="{c["axis"]}"/>')
        out.append(
            f'<text x="{tx}" y="{base_y + 18}" font-size="11" fill="{c["muted"]}" text-anchor="middle">{year}</text>'
        )

    line = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in points)
    area = f"{x(start):.1f},{y(0):.1f} {line} {x(end):.1f},{y(0):.1f}"
    out.append(f'<polygon points="{area}" fill="{c["series"]}" fill-opacity="0.12"/>')
    out.append(
        f'<polyline points="{line}" fill="none" stroke="{c["series"]}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Latest value: a marker with a surface ring, labeled directly.
    ex, ey = x(end), y(total)
    out.append(
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{c["series"]}" stroke="{c["surface"]}" stroke-width="2"/>'
    )
    out.append(
        f'<text x="{ex + 10:.1f}" y="{ey + 4:.1f}" font-size="12" font-weight="600" fill="{c["ink"]}">'
        f'{escape(f"{total:,}")}</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def write_star_charts(out_dir):
    points = load_series()
    for theme in THEMES:
        with open(os.path.join(out_dir, f"stars-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(points, theme))
    return points


if __name__ == "__main__":
    pts = write_star_charts(HERE)
    print(f"Wrote stars-light.svg and stars-dark.svg: {len(pts)} points, {pts[-1][1]} stars")
