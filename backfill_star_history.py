"""
backfill_star_history.py - one-time snapshot of Gum's full star history.

Writes star_history_gum.csv (DATE,STARS): the running star count on every day
someone starred vchelaru/Gum, back to the first star in 2015. star_chart.py draws
this history and continues it with the daily rows in data.csv.

GitHub only returns star dates to someone with push access to the repo, so this
needs a token from a Gum collaborator (secret.txt or GITHUB_TOKEN). The Action's
own token can't do it, which is why the result is committed rather than rebuilt.
Rerunning it is safe: it rewrites the file from scratch.

Usage:
    python backfill_star_history.py
"""

import collections
import csv

import requests

from starcounts import load_token

OWNER, REPO = "vchelaru", "Gum"
OUT_FILE = "star_history_gum.csv"


def main():
    headers = {"Accept": "application/vnd.github.star+json"}
    token = load_token()
    if token:
        headers["Authorization"] = f"token {token}"

    per_day = collections.Counter()
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/stargazers?per_page=100"
    while url:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(
                f"GitHub returned {response.status_code} for {url}. Star dates need a "
                f"token with push access to {OWNER}/{REPO}."
            )
        for star in response.json():
            per_day[star["starred_at"][:10]] += 1
        url = response.links.get("next", {}).get("url")

    total = 0
    with open(OUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["DATE", "STARS"])
        for day in sorted(per_day):
            total += per_day[day]
            writer.writerow([day, total])
    print(f"Wrote {OUT_FILE}: {len(per_day)} days, {total} stars")


if __name__ == "__main__":
    main()
