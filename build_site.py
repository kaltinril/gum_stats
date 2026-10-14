"""
build_site.py — assembles the static GitHub Pages site into _site/.

Output:
  _site/index.html   the chart page (copied from site/)
  _site/data.csv     the raw collected data, unchanged
  _site/data.json    the same data as JSON, one object per date
  _site/repos.json   tracked repos from repos_config.py (names, links, chart flags)

Standard library only, so the workflow doesn't need pandas/matplotlib to deploy.

Usage:
    python build_site.py
    python -m http.server -d _site 8000     # then open http://localhost:8000
"""

import csv
import datetime
import json
import os
import shutil

from repos_config import ALL_REPOS, METRICS
from starcounts import CSV_FILE

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_SRC = os.path.join(HERE, "site")
OUT = os.path.join(HERE, "_site")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SITE_SRC, OUT)
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

    print(f"Built {OUT}: {len(records)} rows, {len(ALL_REPOS)} repos")


if __name__ == "__main__":
    main()
