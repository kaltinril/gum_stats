"""
build_site.py — assembles the static GitHub Pages site into _site/.

Output:
  _site/index.html   the chart page (copied from site/)
  _site/data.js      data.csv + repo config for the page (works from file:// too)
  _site/data.csv     the raw collected data, unchanged
  _site/data.json    the same data as JSON, one object per date
  _site/repos.json   tracked repos from repos_config.py (names, links, chart flags)
  _site/stars-light.svg, _site/stars-dark.svg
                     Gum's all-time star history as plain images, for READMEs (star_chart.py)

Standard library only, so the workflow doesn't need pandas/matplotlib to deploy.

Usage:
    python build_site.py
    then open _site/index.html (not site/index.html, which is the template with no data)
"""

import csv
import datetime
import json
import os
import shutil

from repos_config import ALL_REPOS, METRICS
from star_chart import write_star_charts
from starcounts import CSV_FILE

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_SRC = os.path.join(HERE, "site")
OUT = os.path.join(HERE, "_site")


def main():
    # Empty _site/ rather than delete it: on Windows an editor or OneDrive often holds the
    # folder itself open, and removing it then fails with "Access is denied".
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        path = os.path.join(OUT, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    shutil.copytree(SITE_SRC, OUT, dirs_exist_ok=True)
    shutil.copyfile(os.path.join(HERE, CSV_FILE), os.path.join(OUT, "data.csv"))

    with open(os.path.join(HERE, CSV_FILE), "r", newline="") as f:
        reader = csv.reader(f)
        header = [c.strip() for c in next(reader)]
        records = []
        for row in reader:
            if not row:
                continue
            record = {"DATE": row[0].strip()}
            for col, value in zip(header[1:], row[1:]):
                value = value.strip()
                record[col] = int(value) if value else None
            records.append(record)

    with open(os.path.join(OUT, "data.json"), "w") as f:
        json.dump(records, f, separators=(",", ":"))

    repos = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "metrics": METRICS,
        "repos": [
            {
                "alias": r["alias"],
                "display_name": r["display_name"],
                "url": f"https://github.com/{r['owner']}/{r['repo']}",
                "excluded_from_chart": r["excluded_from_chart"],
            }
            for r in ALL_REPOS
        ],
    }
    with open(os.path.join(OUT, "repos.json"), "w") as f:
        json.dump(repos, f, indent=2)

    # The page reads its data from data.js through a <script> tag rather than fetch(),
    # because browsers block fetch() on file:// pages; this way _site/index.html also
    # works when opened straight from disk.
    with open(os.path.join(HERE, CSV_FILE), "r", newline="") as f:
        csv_text = f.read()
    with open(os.path.join(OUT, "data.js"), "w") as f:
        f.write("window.GUM_STATS = ")
        json.dump({"csv": csv_text, "config": repos}, f, separators=(",", ":"))
        f.write(";\n")

    write_star_charts(OUT)

    print(f"Built {OUT}: {len(records)} rows, {len(ALL_REPOS)} repos")


if __name__ == "__main__":
    main()
